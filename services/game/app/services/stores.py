"""Recompute materialized demand under the caller's realm lock."""

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import ActionInput, DecayStage, DevelopmentNode, Tag
from app.engine.market import PRECISION, allocate_budgets, band_from_upkeep
from app.engine.stores import (
    Demand,
    Line,
    derive_lines,
    line_weight,
    membership,
    mint_demands,
    project_demands,
)
from app.engine.tags import TagHolder, economy_tags
from app.errors import api_error
from app.models import (
    Estate,
    RealmLine,
    RealmShipment,
    RealmState,
    RealmStore,
    RealmTag,
)
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


def _realm_holders(
    session: Session, realm: RealmState, content: ContentIndex
) -> tuple[DevelopmentNode, tuple[Tag, ...]]:
    node = content.development_node(realm.current_node_id)
    ids = set(node.inherent_tags) | set(
        session.scalars(select(RealmTag.tag_id).where(RealmTag.realm_id == realm.id))
    )
    tags = economy_tags(
        TagHolder(
            tuple(t for t in content.tags if t.id in ids),
            content.economy.decay.faltering_factor,
        ),
        DecayStage(realm.decay_stage),
    )
    return node, tags


def derive_realm_lines(
    session: Session, realm: RealmState, content: ContentIndex
) -> tuple[Line, ...]:
    """Derive current stock and demand without mutating materialized rows."""
    node, tags = _realm_holders(session, realm, content)
    estates = tuple(
        content.estate_form(e.form_id)
        for e in session.scalars(
            select(Estate).where(Estate.realm_id == realm.id, Estate.status == "active")
        )
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
        mint_demands(tags),
    )
    transit = dict.fromkeys((line.key for line in lines), 0)
    for shipment in session.scalars(
        select(RealmShipment).where(
            RealmShipment.to_realm_id == realm.id, RealmShipment.status == "in_transit"
        )
    ):
        item = content.item(shipment.item_id)
        line = membership(item, lines)
        if line is not None:
            transit[line.key] += (
                shipment.quantity_arriving * 1000 * line_weight(item, line)
            )
    return tuple(replace(line, in_transit=transit[line.key]) for line in lines)


def require_project_stock(
    session: Session, realm: RealmState, content: ContentIndex
) -> None:
    """Require some stock in every demand line before project kickoff."""
    if any(line.stock <= 0 for line in derive_realm_lines(session, realm, content)):
        raise api_error(409, "RESERVE_SHORT", "Every demand line needs positive stock")


def require_vote_stock(
    session: Session, realm: RealmState, content: ContentIndex
) -> None:
    """Require the authored number of demand days independently of reserves."""
    days = Fraction(str(content.economy.vote.min_stock_days))
    if any(
        line.stock < line.draw_per_day * days
        for line in derive_realm_lines(session, realm, content)
    ):
        raise api_error(
            409, "RESERVE_SHORT", "The realm lacks the stock needed to call a vote"
        )


def recompute_lines(
    session: Session, realm: RealmState, content: ContentIndex
) -> list[RealmLine]:
    """Replace all derived rows; caller owns transaction and persistence."""
    lines = derive_realm_lines(session, realm, content)
    previous = {
        r.line_key: r.budget_gold
        for r in session.scalars(
            select(RealmLine).where(RealmLine.realm_id == realm.id)
        )
    }
    if previous:
        lines = tuple(
            replace(line, budget_gold=previous.get(line.key, 0)) for line in lines
        )
    elif not realm.isolated and realm.treasury_band is None:
        lines = allocate_budgets(lines, realm.treasury, content)
    if not realm.isolated and realm.treasury_band is None:
        node, tags = _realm_holders(session, realm, content)
        holders: tuple[DevelopmentNode | Tag, ...] = (node, *tags)
        with localcontext() as precision:
            precision.prec = PRECISION
            daily = sum(
                Decimal(str(upkeep.per_day))
                * next(
                    i.reference_price
                    for i in content.items
                    if upkeep.selector.matches(i)
                )
                for holder in holders
                for upkeep in holder.upkeep
            )
            realm.treasury_band = band_from_upkeep(
                realm.treasury,
                Decimal(daily)
                + sum(
                    (
                        Decimal(d.daily_milli.numerator)
                        / Decimal(d.daily_milli.denominator)
                        / 1000
                        for d in mint_demands(tags)
                    ),
                    Decimal(0),
                ),
                None,
                content.economy.market,
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
