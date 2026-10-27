"""Recompute materialized demand under the caller's realm lock."""

from datetime import datetime, timedelta
from fractions import Fraction

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import ActionInput, DecayStage
from app.engine.stores import Demand, Line, derive_lines, mint_demands, project_demands
from app.engine.tags import TagHolder, active_tags
from app.models import Estate, RealmLine, RealmState, RealmStore, RealmTag
from app.services.projects import active_run


def transition_days(realm: RealmState) -> Fraction:
    """Return the full snapshotted transition window, rather than time remaining."""
    pending = realm.pending_transition
    if pending is None:
        return Fraction(0)
    duration = datetime.fromisoformat(pending["completes_at"]) - datetime.fromisoformat(
        pending["started_at"]
    )
    return Fraction(duration // timedelta(microseconds=1), 86400000000)


def recompute_lines(
    session: Session, realm: RealmState, content: ContentIndex
) -> list[RealmLine]:
    """Replace all derived rows; caller owns transaction and persistence."""
    node = content.development_node(realm.current_node_id)
    ids = set(node.inherent_tags) | set(
        session.scalars(select(RealmTag.tag_id).where(RealmTag.realm_id == realm.id))
    )
    tags = tuple(
        t
        for t, _ in active_tags(
            TagHolder(
                tuple(t for t in content.tags if t.id in ids),
                content.economy.decay.faltering_factor,
            ),
            DecayStage(realm.decay_stage),
        )
    )
    estates = tuple(
        content.estate_form(e.form_id)
        for e in session.scalars(select(Estate).where(Estate.realm_id == realm.id))
    )
    stores = {
        s.item_id: s.quantity_milli
        for s in session.scalars(
            select(RealmStore).where(RealmStore.realm_id == realm.id)
        )
    }
    run = active_run(session, realm.id)
    overlay: tuple[Demand, ...] = ()
    if run is not None and run.status == "funding":
        overlay = project_demands(
            tuple(ActionInput.model_validate(line) for line in run.required),
            tuple(run.contributed),
            content.project(run.project_id).realm_completion_days,
        )
    lines = derive_lines(
        node,
        tags,
        estates,
        overlay,
        stores,
        content,
        transition_days(realm),
        mint_demands(),
    )
    return replace_lines(session, realm.id, lines)


def replace_lines(
    session: Session, realm_id: str, lines: tuple[Line, ...]
) -> list[RealmLine]:
    """Persist a pure derivation under the caller's realm lock, without committing."""
    session.execute(delete(RealmLine).where(RealmLine.realm_id == realm_id))
    rows = [
        RealmLine(
            realm_id=realm_id,
            line_key=line.key,
            selector=line.selector.model_dump(),
            value_measured=line.value_measured,
            draw_per_day=line.draw_per_day,
            reserve=line.reserve,
            cap=line.cap,
            stock=line.stock,
            in_transit=line.in_transit,
            budget_gold=line.budget_gold,
        )
        for line in lines
    ]
    session.add_all(rows)
    return rows
