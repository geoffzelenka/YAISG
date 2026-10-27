"""Ordered realm tick extension points (design §14.5). Caller holds realm lock."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fractions import Fraction

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import ActionInput, DecayStage, DevelopmentNode, Tag
from app.engine.projects import erode_project
from app.engine.realm_ticks import shares, take
from app.engine.stores import (
    Demand,
    Line,
    derive_lines,
    due,
    line_key,
    membership,
    project_demands,
    warehouse_cap,
)
from app.engine.tags import TagHolder, active_tags
from app.models import (
    Estate,
    EstateLarder,
    RealmContribution,
    RealmProjectRun,
    RealmState,
    RealmStore,
    RealmTag,
)
from app.services.projects import apply_project_payment, begin_build
from app.services.realms import as_utc
from app.services.stores import replace_lines, transition_days


@dataclass
class RealmTickContext:
    """Preloaded mutable tick state; load before catch-up and flush after it.

    Steps must use this state without issuing queries. Future stores, estates,
    and demand lines belong here so database work stays independent of ticks.
    """

    active_run: RealmProjectRun | None
    estates: list[Estate] = field(default_factory=list)
    stores: dict[str, int] = field(default_factory=dict)
    store_rows: dict[str, RealmStore] = field(default_factory=dict)
    larder_rows: list[EstateLarder] = field(default_factory=list)
    larders: dict[uuid.UUID, dict[str, int]] = field(default_factory=dict)
    tags: tuple[Tag, ...] = ()
    lines: tuple[Line, ...] = ()
    owed: dict[str, list[tuple[uuid.UUID, int]]] = field(default_factory=dict)
    realm_due: dict[str, int] = field(default_factory=dict)
    realm_unmet: dict[str, int] = field(default_factory=dict)
    contributions: list[RealmContribution] = field(default_factory=list)
    acquired_tags: list[RealmTag] = field(default_factory=list)


def load_context(
    session: Session,
    realm: RealmState,
    run: RealmProjectRun | None,
    content: ContentIndex,
) -> RealmTickContext:
    """Load all tick inputs once under the realm lock."""
    estates = list(
        session.scalars(
            select(Estate).where(Estate.realm_id == realm.id).order_by(Estate.id)
        )
    )
    estates = [
        e
        for e in estates
        if (
            content.estate_form(e.form_id).upkeep
            or content.estate_form(e.form_id).production
        )
    ]
    context = RealmTickContext(active_run=run, estates=estates)
    context.store_rows = {
        s.item_id: s
        for s in session.scalars(
            select(RealmStore).where(RealmStore.realm_id == realm.id)
        )
    }
    context.stores = {
        item_id: row.quantity_milli for item_id, row in context.store_rows.items()
    }
    context.larders = {e.id: {} for e in estates}
    context.larder_rows = list(
        session.scalars(
            select(EstateLarder).join(Estate).where(Estate.realm_id == realm.id)
        )
    )
    for row in context.larder_rows:
        if row.estate_id in context.larders:
            context.larders[row.estate_id][row.item_id] = row.quantity_milli
    ids = set(content.development_node(realm.current_node_id).inherent_tags)
    ids.update(
        session.scalars(select(RealmTag.tag_id).where(RealmTag.realm_id == realm.id))
    )
    context.tags = tuple(
        t
        for t, _ in active_tags(
            TagHolder(
                tuple(t for t in content.tags if t.id in ids),
                content.economy.decay.faltering_factor,
            ),
            DecayStage(realm.decay_stage),
        )
    )
    step_10_lines(context, realm, realm.last_tick_at, content)
    return context


def persist_context(
    session: Session, realm: RealmState, context: RealmTickContext
) -> None:
    """Write each final holding once, independent of catch-up length."""
    for item_id, amount in context.stores.items():
        row = context.store_rows.get(item_id)
        if row is None:
            session.add(
                RealmStore(realm_id=realm.id, item_id=item_id, quantity_milli=amount)
            )
        else:
            row.quantity_milli = amount
    for larder in context.larder_rows:
        if larder.estate_id not in context.larders:
            continue
        amount = context.larders[larder.estate_id][larder.item_id]
        if amount:
            larder.quantity_milli = amount
        else:
            session.delete(larder)
    session.add_all(context.acquired_tags)
    session.add_all(context.contributions)
    replace_lines(session, realm.id, context.lines)


def tick_index(now: datetime, content: ContentIndex) -> int:
    """Use an absolute UTC tick index so split catch-up preserves rounding."""
    return (as_utc(now) - datetime(1970, 1, 1, tzinfo=as_utc(now).tzinfo)) // (
        timedelta(days=1) / content.economy.tick.per_day
    ) - 1


def daily_share(rate: float, now: datetime, content: ContentIndex) -> int:
    """Convert authored daily units to this tick's integer milli share."""
    return due(
        int(Fraction(str(rate)) * 1000),
        tick_index(now, content),
        content.economy.tick.per_day,
    )


def production_factor(estate: Estate) -> Fraction:
    """Prompt 15 supplies stage scaling; Fed and Strained remain equal."""
    return Fraction(1)


def step_0_arrivals(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 20: receive due caravan shipments; isolated realms have no caravans."""
    if realm.isolated:
        return


def step_1_production(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Credit every producing estate to realm stores, including unowned estates."""
    for estate in context.estates:
        form = content.estate_form(estate.form_id)
        if not set(form.requires_realm_tags).issubset(t.id for t in context.tags):
            continue
        for output in form.production:
            amount = int(
                daily_share(output.per_day, now, content) * production_factor(estate)
            )
            context.stores[output.item_id] = (
                context.stores.get(output.item_id, 0) + amount
            )


def step_2_larder_upkeep(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: consume estate larders; isolated realms have no upkeep."""
    context.owed = {}
    if realm.isolated:
        return
    for estate in context.estates:
        for upkeep in content.estate_form(estate.form_id).upkeep:
            amount = daily_share(upkeep.per_day, now, content)
            paid = take(context.larders[estate.id], upkeep.selector, amount, content)
            context.owed.setdefault(line_key(upkeep.selector), []).append(
                (estate.id, amount - sum(paid.values()))
            )


def step_3_estate_upkeep(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: share upkeep above reserve; isolated realms have no upkeep."""
    if realm.isolated:
        return
    for key, claims in context.owed.items():
        line = next(line for line in context.lines if line.key == key)
        probe = context.stores.copy()
        available = sum(
            take(
                probe, line.selector, sum(q for _, q in claims), content, context.lines
            ).values()
        )
        allocation = shares([q for _, q in claims], available)
        take(context.stores, line.selector, sum(allocation), content, context.lines)
        context.owed[key] = [
            (estate, amount - paid)
            for (estate, amount), paid in zip(claims, allocation, strict=True)
        ]


def step_4_realm_upkeep(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14/18: consume upkeep and coin bullion; skip isolated realm upkeep."""
    context.realm_due = {}
    context.realm_unmet = {}
    if realm.isolated:
        return
    node = content.development_node(realm.current_node_id)
    holders: tuple[DevelopmentNode | Tag, ...] = (node, *context.tags)
    for holder in holders:
        for upkeep in holder.upkeep:
            key = line_key(upkeep.selector)
            amount = daily_share(upkeep.per_day, now, content)
            paid = sum(take(context.stores, upkeep.selector, amount, content).values())
            context.realm_due[key] = context.realm_due.get(key, 0) + amount
            context.realm_unmet[key] = context.realm_unmet.get(key, 0) + amount - paid


def step_5_projects(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Contribute the overlay from surplus, then erode idle funding."""
    run = context.active_run
    if run is None or run.status != "funding":
        return
    days = Fraction(str(content.project(run.project_id).realm_completion_days))
    for index, raw in enumerate(run.required):
        requirement = ActionInput.model_validate(raw)
        remaining = requirement.quantity * 1000 - run.contributed[index]
        amount = due(
            int(Fraction(remaining) / days),
            tick_index(now, content),
            content.economy.tick.per_day,
        )
        paid = take(
            context.stores,
            requirement.selector,
            min(remaining, amount),
            content,
            context.lines,
        )
        for item_id, quantity in paid.items():
            context.contributions.append(
                apply_project_payment(run, index, item_id, quantity, None, now, content)
            )
    begin_build(run, now, content)
    if run.status == "building":
        return
    run.contributed = erode_project(
        [line["quantity"] * 1000 for line in run.required],
        run.contributed,
        as_utc(run.last_contribution_at),
        now,
        content.economy.project,
        content.economy.tick.per_day,
    )
    if now > as_utc(run.last_contribution_at) + timedelta(
        days=content.economy.project.idle_grace_days
    ) and not any(run.contributed):
        run.status = "failed"
        run.failed_at = now


def step_6_spoilage(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Apply content spoilage to stores and larders using exact rational rates."""
    for stock in (context.stores, *context.larders.values()):
        for item_id, amount in stock.items():
            rate = Fraction(str(content.item(item_id).spoilage_pct_per_day)) / (
                100 * content.economy.tick.per_day
            )
            stock[item_id] -= int(amount * rate)


def step_7_caps(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Discard line excess from the most plentiful item, then warehouse excess."""
    for line in context.lines:
        items = [
            i
            for i in context.stores
            if membership(content.item(i), context.lines) == line
        ]
        excess = max(0, sum(context.stores[i] for i in items) - line.cap)
        for item_id in sorted(items, key=lambda i: (-context.stores[i], i)):
            lost = min(excess, context.stores[item_id])
            context.stores[item_id] -= lost
            excess -= lost
    for item_id in context.stores:
        if membership(content.item(item_id), context.lines) is None:
            context.stores[item_id] = min(
                context.stores[item_id], warehouse_cap(content.item(item_id), content)
            )


def step_8_gauges(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 15: update deficit gauges; isolated realms have no upkeep or decay."""
    if realm.isolated:
        return


def step_9_decay(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 15: advance or recover decay; isolated realms have no decay."""
    if realm.isolated:
        return


def step_10_lines(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14/16: recompute lines, including isolated realms' project lines.

    Skip only market budgets, treasury bands and tax work for isolated realms.
    """
    run = context.active_run
    overlay: tuple[Demand, ...] = ()
    if run is not None and run.status == "funding":
        overlay = project_demands(
            tuple(ActionInput.model_validate(raw) for raw in run.required),
            tuple(run.contributed),
            content.project(run.project_id).realm_completion_days,
        )
    context.lines = derive_lines(
        content.development_node(realm.current_node_id),
        context.tags,
        tuple(content.estate_form(e.form_id) for e in context.estates),
        overlay,
        context.stores,
        content,
        transition_days(realm),
    )


TICK_STEPS = (
    step_0_arrivals,
    step_1_production,
    step_2_larder_upkeep,
    step_3_estate_upkeep,
    step_4_realm_upkeep,
    step_5_projects,
    step_6_spoilage,
    step_7_caps,
    step_8_gauges,
    step_9_decay,
    step_10_lines,
)


def complete_tick_build(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Complete a build started during catch-up at its exact timestamp."""
    run = context.active_run
    if run is None or run.status != "building" or run.build_completes_at is None:
        return
    if as_utc(run.build_completes_at) > now:
        return
    tag_id = content.project(run.project_id).grants_tag
    realm.tag_seq += 1
    context.acquired_tags.append(
        RealmTag(
            realm_id=realm.id,
            tag_id=tag_id,
            seq=realm.tag_seq,
            node_id=realm.current_node_id,
            acquired_at=run.build_completes_at,
            project_run_id=run.id,
        )
    )
    context.tags = (*context.tags, next(t for t in content.tags if t.id == tag_id))
    run.status = "complete"
    step_10_lines(context, realm, now, content)
