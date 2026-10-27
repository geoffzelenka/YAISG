"""Transactional realm locks, tag acquisition, and lazy transitions."""

import uuid
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.runtime import CONTENT
from app.models import RealmState, RealmTag


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def prepare_sqlite_write(session: Session) -> None:
    """Acquire SQLite's database writer lock before realm state is loaded."""
    if session.get_bind().dialect.name != "sqlite":
        return
    if session.in_transaction():
        session.commit()
    session.connection(execution_options={"sqlite_write_intent": True})


def _lock_realm(
    session: Session,
    realm_id: str,
    now: datetime,
    content: ContentIndex,
) -> RealmState | None:
    statement = (
        select(RealmState)
        .where(RealmState.id == realm_id)
        .execution_options(populate_existing=True)
    )
    if session.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    state = session.scalar(statement)
    if state is not None:
        return state
    try:
        template = content.realm(realm_id)
    except KeyError:
        return None
    # Before world seeding (Prompt 13), travel can reach untouched templates.
    # The conflict-safe insert serializes concurrent first touches as well.
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
    session.execute(
        insert(RealmState)
        .values(
            id=realm_id,
            template_id=template.id,
            isolated=template.isolated,
            current_node_id=template.starting_node_id,
            last_tick_at=now,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    return session.scalar(statement)


def stack_tags(session: Session, realm_id: str) -> tuple[str, ...]:
    """Load the project stack in acquisition order."""
    return tuple(
        session.scalars(
            select(RealmTag.tag_id)
            .where(RealmTag.realm_id == realm_id)
            .order_by(RealmTag.seq)
        )
    )


def push_realm_tag(
    session: Session,
    realm: RealmState,
    tag_id: str,
    now: datetime,
    project_run_id: uuid.UUID | None = None,
) -> RealmTag:
    """Push a tag under the caller's realm lock, never reusing a removed seq."""
    if session.get(RealmTag, (realm.id, tag_id)) is not None:
        raise ValueError(f"realm {realm.id!r} already holds tag {tag_id!r}")
    realm.tag_seq += 1
    tag = RealmTag(
        realm_id=realm.id,
        tag_id=tag_id,
        seq=realm.tag_seq,
        node_id=realm.current_node_id,
        acquired_at=now,
        project_run_id=project_run_id,
    )
    session.add(tag)
    return tag


def start_transition(
    realm: RealmState,
    to_node: str,
    cause: Literal["upgrade", "regression"],
    now: datetime,
    content: ContentIndex = CONTENT,
) -> None:
    """Start one transition under the caller's realm lock."""
    if realm.pending_transition is not None:
        raise ValueError(f"realm {realm.id!r} is already transitioning")
    if cause not in ("upgrade", "regression"):
        raise ValueError(f"unknown transition cause {cause!r}")
    content.development_node(to_node)
    realm.pending_transition = {
        "to_node": to_node,
        "cause": cause,
        "started_at": now.isoformat(),
        "completes_at": (
            now + timedelta(days=content.economy.transition.duration_days)
        ).isoformat(),
    }


def _finalize_locked_realm(
    session: Session,
    state: RealmState | None,
    now: datetime,
    content: ContentIndex,
) -> RealmState | None:
    """Apply a due transition to an already-locked realm row."""
    if state is None or state.pending_transition is None:
        return state
    pending = state.pending_transition
    if _as_utc(datetime.fromisoformat(pending["completes_at"])) > _as_utc(now):
        return state
    node = content.development_node(pending["to_node"])
    allowed = set(node.carried_tags) | {
        content.project(p).grants_tag for p in node.projects
    }
    for tag in session.scalars(select(RealmTag).where(RealmTag.realm_id == state.id)):
        if tag.tag_id not in allowed:
            session.delete(tag)
        elif pending["cause"] == "regression":
            tag.node_id = node.id
    state.current_node_id = node.id
    if pending["cause"] == "regression":
        state.gauge = 0
        state.shed_progress = 0
        state.decay_stage = "fed"
    state.pending_transition = None
    session.flush()
    return state


def finalize_realms(
    session: Session,
    realm_ids: set[str],
    now: datetime,
    content: ContentIndex,
) -> dict[str, RealmState | None]:
    """Lock realm rows in stable order, then finalize every due transition."""
    states = {
        realm_id: _lock_realm(session, realm_id, now, content)
        for realm_id in sorted(realm_ids)
    }
    return {
        realm_id: resolve_realm(session, state, now, content)
        for realm_id, state in states.items()
    }


def finalize_realm(
    session: Session,
    realm_id: str,
    now: datetime,
    content: ContentIndex | None = None,
    *,
    prepare_sqlite: bool = False,
) -> RealmState | None:
    """Lazily and atomically complete a due realm-node transition."""
    if prepare_sqlite:
        prepare_sqlite_write(session)
    return resolve_realm(
        session,
        _lock_realm(session, realm_id, now, content or CONTENT),
        now,
        content or CONTENT,
    )


def vote_close_event(session: Session, realm: RealmState) -> datetime | None:
    """Prompt 19 supplies the next vote close time."""
    return None


def close_due_vote(
    session: Session, realm: RealmState, due: datetime, content: ContentIndex
) -> None:
    """Prompt 19 closes the vote at its due time, possibly starting a transition."""


class TimedEventKind(IntEnum):
    """Stable tie order for simultaneous realm events."""

    VOTE = 0
    BUILD = 1
    TRANSITION = 2


def _finalize_timed_events(
    session: Session,
    realm: RealmState,
    now: datetime,
    content: ContentIndex,
) -> None:
    from app.services.projects import active_run

    while True:
        run = active_run(session, realm.id)
        events: list[tuple[datetime, TimedEventKind]] = []
        vote_due = vote_close_event(session, realm)
        if vote_due is not None:
            events.append((_as_utc(vote_due), TimedEventKind.VOTE))
        if run is not None and run.build_completes_at is not None:
            events.append((_as_utc(run.build_completes_at), TimedEventKind.BUILD))
        if realm.pending_transition is not None:
            events.append(
                (
                    _as_utc(
                        datetime.fromisoformat(realm.pending_transition["completes_at"])
                    ),
                    TimedEventKind.TRANSITION,
                )
            )
        if not events or min(events)[0] > now:
            break
        due, kind = min(events)
        if kind == TimedEventKind.VOTE:
            close_due_vote(session, realm, due, content)
        elif kind == TimedEventKind.BUILD:
            assert run is not None
            push_realm_tag(
                session, realm, content.project(run.project_id).grants_tag, due, run.id
            )
            run.status = "complete"
        else:
            _finalize_locked_realm(session, realm, due, content)
        session.flush()


def resolve_realm(
    session: Session,
    realm: RealmState | None,
    now: datetime,
    content: ContentIndex,
) -> RealmState | None:
    """Finalize exact timed events, then bounded whole ticks under a held lock.

    The caller owns persistence and the transaction. Events are reconsidered
    after each completion because a vote can schedule another due event.
    """
    from app.services.realm_ticks import TICK_STEPS

    if realm is None:
        return None
    now = _as_utc(now)
    _finalize_timed_events(session, realm, now, content)
    interval = timedelta(days=1) / content.economy.tick.per_day
    ticks = min(
        (now - _as_utc(realm.last_tick_at)) // interval,
        content.economy.tick.max_catchup,
    )
    for _ in range(max(0, ticks)):
        tick_at = _as_utc(realm.last_tick_at) + interval
        if not realm.isolated:
            for step in TICK_STEPS:
                step(session, realm, tick_at, content)
        realm.last_tick_at = tick_at
        session.flush()
    return realm
