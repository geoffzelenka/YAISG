"""Transactional realm-development and relocation finalizers."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.runtime import CONTENT
from app.models import Character, Estate, RealmEdgeProgress, RealmProject, RealmState


class InvalidEdgeAwardError(RuntimeError):
    """Raised when an internal caller tries to award an unavailable edge."""

    code = "INVALID_EDGE_AWARD"


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def prepare_sqlite_write(session: Session) -> None:
    """Acquire SQLite's database writer lock before realm state is loaded."""
    if session.get_bind().dialect.name != "sqlite":
        return
    if session.in_transaction():
        session.commit()
    session.connection(execution_options={"sqlite_write_intent": True})


def _lock_realm(session: Session, realm_id: str) -> RealmState | None:
    statement = select(RealmState).where(RealmState.realm_id == realm_id)
    if session.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    return session.scalar(statement)


def _finalize_locked_realm(
    session: Session,
    state: RealmState | None,
    now: datetime,
    content: ContentIndex,
) -> RealmState | None:
    """Apply a due transition to an already-locked realm row."""
    if (
        state is None
        or state.transition_to_node_id is None
        or state.transition_completes_at is None
        or _as_utc(state.transition_completes_at) > now
    ):
        return state
    realm_id = state.realm_id
    departed_node_id = state.node_id
    state.node_id = state.transition_to_node_id
    state.transition_to_node_id = None
    state.transition_completes_at = None
    outgoing_ids = [
        edge.id
        for edge in content.development_edges
        if edge.from_node == departed_node_id
    ]
    if outgoing_ids:
        session.execute(
            delete(RealmEdgeProgress).where(
                RealmEdgeProgress.realm_id == realm_id,
                RealmEdgeProgress.edge_id.in_(outgoing_ids),
            )
        )
    offered = set(content.development_node(state.node_id).projects)
    projects = session.scalars(
        select(RealmProject).where(RealmProject.realm_id == realm_id)
    )
    for project in projects:
        if project.project_id not in offered and project.status != "closed":
            project.status = "closed"
    return state


def finalize_realms(
    session: Session,
    realm_ids: set[str],
    now: datetime,
    content: ContentIndex,
) -> dict[str, RealmState | None]:
    """Lock realm rows in stable order, then finalize every due transition."""
    states = {
        realm_id: _lock_realm(session, realm_id) for realm_id in sorted(realm_ids)
    }
    return {
        realm_id: _finalize_locked_realm(session, state, now, content)
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
    resolved_content = content or CONTENT
    if prepare_sqlite:
        prepare_sqlite_write(session)
    state = _lock_realm(session, realm_id)
    return _finalize_locked_realm(session, state, now, resolved_content)


def award_edge_progress(
    session: Session,
    realm_id: str,
    edge_id: str,
    amount: int,
    source: str,
    now: datetime | None = None,
    content: ContentIndex | None = None,
) -> RealmEdgeProgress:
    """Award an outgoing development edge and begin its transition if filled."""
    del source  # Reserved for audit attribution when more award sources exist.
    award_time = now or datetime.now(UTC)
    resolved_content = content or CONTENT
    if amount <= 0:
        raise ValueError("edge progress award must be positive")
    state = _lock_realm(session, realm_id)
    if state is None:
        raise InvalidEdgeAwardError(f"realm {realm_id!r} has no state")
    try:
        edge = resolved_content.development_edge(edge_id)
    except KeyError:
        raise InvalidEdgeAwardError(f"unknown edge {edge_id!r}") from None
    if (
        edge.kind != "development"
        or edge.from_node != state.node_id
        or state.transition_to_node_id is not None
    ):
        raise InvalidEdgeAwardError(
            f"edge {edge_id!r} cannot be awarded from realm {realm_id!r}"
        )
    progress = session.get(RealmEdgeProgress, (realm_id, edge_id))
    if progress is None:
        progress = RealmEdgeProgress(
            realm_id=realm_id, edge_id=edge_id, progress=0, updated_at=award_time
        )
        session.add(progress)
    progress.progress += amount
    progress.updated_at = award_time
    if progress.progress >= edge.progress_target:
        state.transition_to_node_id = edge.to_node
        state.transition_completes_at = award_time + timedelta(
            milliseconds=edge.transition_ms or 0
        )
    return progress


def finalize_relocation(
    session: Session,
    character: Character,
    now: datetime,
    *,
    prepare_sqlite: bool = False,
) -> Estate:
    """Complete a due home-estate relocation and synchronize residence cache."""
    if prepare_sqlite:
        prepare_sqlite_write(session)
    statement = select(Estate).where(Estate.id == character.home_estate_id)
    if session.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    estate = session.scalar(statement)
    if estate is None:
        raise RuntimeError(f"character {character.id} has no home estate")
    if (
        estate.relocating_to_realm_id is not None
        and estate.relocation_completes_at is not None
        and _as_utc(estate.relocation_completes_at) <= now
    ):
        estate.realm_id = estate.relocating_to_realm_id
        character.current_realm_id = estate.realm_id
        estate.relocating_to_realm_id = None
        estate.relocation_completes_at = None
        estate.status = "active"
    return estate
