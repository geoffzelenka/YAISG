"""Ordered realm tick extension points (design §14.5). Caller holds realm lock."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fractions import Fraction

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import ActionInput, DecayStage, DevelopmentNode, Tag
from app.engine.decay import advance_gauge, advance_shed, gauge_stage
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
from app.engine.tags import TagHolder, economy_tags
from app.models import (
    Character,
    Estate,
    EstateLarder,
    EstateOwnershipHistory,
    EstateUpgrade,
    RealmContribution,
    RealmProjectRun,
    RealmState,
    RealmStore,
    RealmTag,
)
from app.services.projects import apply_project_payment, begin_build
from app.services.realms import (
    TimedEventKind,
    as_utc,
    build_realm_tag,
    start_transition,
)
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
    stack_tag_ids: set[str] = field(default_factory=set)
    lines: tuple[Line, ...] = ()
    line_weights: dict[str, int] = field(default_factory=dict)
    owed: dict[str, list[tuple[uuid.UUID, int]]] = field(default_factory=dict)
    realm_due: dict[str, int] = field(default_factory=dict)
    realm_unmet: dict[str, int] = field(default_factory=dict)
    contributions: list[RealmContribution] = field(default_factory=list)
    acquired_tags: list[RealmTag] = field(default_factory=list)
    stack: list[RealmTag] = field(default_factory=list)
    removed_tags: list[RealmTag] = field(default_factory=list)
    upgrades: list[EstateUpgrade] = field(default_factory=list)
    removed_upgrades: list[EstateUpgrade] = field(default_factory=list)
    owners: dict[uuid.UUID, Character] = field(default_factory=dict)
    histories: list[EstateOwnershipHistory] = field(default_factory=list)
    replacements: list[Estate] = field(default_factory=list)
    replacement_histories: list[EstateOwnershipHistory] = field(default_factory=list)


def load_context(
    session: Session,
    realm: RealmState,
    run: RealmProjectRun | None,
    content: ContentIndex,
) -> RealmTickContext:
    """Load all tick inputs once under the realm lock."""
    estates = list(
        session.scalars(
            select(Estate)
            .where(Estate.realm_id == realm.id, Estate.status == "active")
            .order_by(Estate.id)
        )
    )
    estates = [
        estate
        for estate in estates
        if content.estate_form(estate.form_id).upkeep
        or content.estate_form(estate.form_id).production
    ]
    context = RealmTickContext(active_run=run, estates=estates)
    context.upgrades = list(
        session.scalars(
            select(EstateUpgrade)
            .join(Estate)
            .where(Estate.realm_id == realm.id)
            .order_by(
                EstateUpgrade.purchased_at.desc(), EstateUpgrade.slot_index.desc()
            )
        )
    )
    context.owners = {
        c.id: c
        for c in session.scalars(
            select(Character)
            .join(Estate, Estate.owner_character_id == Character.id)
            .where(Estate.realm_id == realm.id, Estate.status == "active")
        )
    }
    context.histories = list(
        session.scalars(
            select(EstateOwnershipHistory)
            .join(Estate)
            .where(
                Estate.realm_id == realm.id,
                EstateOwnershipHistory.relinquished_at.is_(None),
            )
        )
    )
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
    context.stack = list(
        session.scalars(select(RealmTag).where(RealmTag.realm_id == realm.id))
    )
    refresh_tags(context, realm, content)
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
    for tag in context.removed_tags:
        session.delete(tag)
    for upgrade in context.removed_upgrades:
        session.delete(upgrade)
    session.add_all(context.replacements)
    session.add_all(context.replacement_histories)
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


def production_factor(estate: Estate, content: ContentIndex) -> Fraction:
    """Scale production only at Faltering or worse."""
    if estate.decay_stage in (DecayStage.FED, DecayStage.STRAINED):
        return Fraction(1)
    return Fraction(str(content.economy.decay.faltering_factor))


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
                daily_share(output.per_day, now, content)
                * production_factor(estate, content)
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
    weights = context.line_weights
    due_value = sum(q * weights[k] for k, q in context.realm_due.items())
    unmet = sum(q * weights[k] for k, q in context.realm_unmet.items())
    realm.gauge = advance_gauge(
        realm.gauge,
        due_value,
        unmet,
        content.economy.tick.per_day,
        content.economy.gauge,
    )
    realm.decay_stage = gauge_stage(realm.gauge, content.economy.gauge).value
    if realm.pending_transition and realm.pending_transition["cause"] == "regression":
        realm.decay_stage = DecayStage.REGRESSED.value
    for estate in context.estates:
        due_value = sum(
            daily_share(line.per_day, now, content) * weights[line_key(line.selector)]
            for line in content.estate_form(estate.form_id).upkeep
        )
        unmet = sum(
            q * weights[k]
            for k, claims in context.owed.items()
            for estate_id, q in claims
            if estate_id == estate.id
        )
        estate.gauge = advance_gauge(
            estate.gauge,
            due_value,
            unmet,
            content.economy.tick.per_day,
            content.economy.gauge,
        )
        estate.decay_stage = gauge_stage(estate.gauge, content.economy.gauge).value


def step_9_decay(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Lose current-node tags and estate assets using only preloaded state."""
    if realm.isolated:
        return
    decay_realm(context, realm, now, content)
    for estate in list(context.estates):
        decay_estate(context, estate, now, content)
    refresh_tags(context, realm, content)


def decay_realm(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Unwind the current node's stack before starting its regression edge."""
    threshold = content.economy.gauge.failing_threshold
    if realm.pending_transition is None or realm.gauge <= threshold:
        realm.shed_progress = advance_shed(
            realm.shed_progress,
            realm.gauge,
            content.economy.tick.per_day,
            threshold,
            content.economy.shed,
        )
    if realm.gauge > threshold and realm.pending_transition is None:
        while realm.shed_progress >= 1:
            candidates = [
                t for t in context.stack if t.node_id == realm.current_node_id
            ]
            if not candidates:
                break
            tag = max(candidates, key=lambda t: t.seq)
            context.stack.remove(tag)
            if tag in context.acquired_tags:
                context.acquired_tags.remove(tag)
            else:
                context.removed_tags.append(tag)
            realm.shed_progress -= 1
        if not any(t.node_id == realm.current_node_id for t in context.stack):
            # Empty nodes may retain one pending loss, never a bank of losses
            # that would destroy rebuilt tags or follow a later tier-up.
            realm.shed_progress = min(1.0, realm.shed_progress)
            regression = content.development_node(realm.current_node_id).regression
            if regression is not None:
                start_transition(realm, regression.to_node, "regression", now, content)
                realm.decay_stage = DecayStage.REGRESSED.value


def decay_estate(
    context: RealmTickContext, estate: Estate, now: datetime, content: ContentIndex
) -> None:
    """Uninstall newest purchases before regressing a form or destroying it."""
    threshold = content.economy.gauge.failing_threshold
    estate.shed_progress = advance_shed(
        estate.shed_progress,
        estate.gauge,
        content.economy.tick.per_day,
        threshold,
        content.economy.shed,
    )
    if estate.gauge <= threshold:
        return
    upgrades = [u for u in context.upgrades if u.estate_id == estate.id]
    while estate.shed_progress >= 1 and upgrades:
        upgrade = upgrades.pop(0)
        context.upgrades.remove(upgrade)
        context.removed_upgrades.append(upgrade)
        estate.shed_progress -= 1
    if not upgrades:
        destination = content.estate_form(estate.form_id).regresses_to
        if destination is not None:
            estate.form_id = destination
            estate.gauge = estate.shed_progress = 0
            estate.decay_stage = DecayStage.FED.value
        else:
            destroy_estate(context, estate, now, content)


def refresh_tags(
    context: RealmTickContext, realm: RealmState, content: ContentIndex
) -> None:
    """Recompute live emissions after stage changes, shedding or transitions."""
    context.stack_tag_ids = {t.tag_id for t in context.stack}
    ids = set(content.development_node(realm.current_node_id).inherent_tags)
    ids.update(context.stack_tag_ids)
    context.tags = economy_tags(
        TagHolder(
            tuple(t for t in content.tags if t.id in ids),
            content.economy.decay.faltering_factor,
        ),
        DecayStage(realm.decay_stage),
    )


def destroy_estate(
    context: RealmTickContext, estate: Estate, now: datetime, content: ContentIndex
) -> None:
    """Retain a tombstone for history and acquire a free replacement for its owner.

    The owner's next locked resolve follows replacement_id. Realm ticks never
    acquire a character lock after a realm lock, avoiding an inverted lock order.
    """
    context.estates.remove(estate)
    estate.status = "destroyed"
    context.larders[estate.id] = dict.fromkeys(context.larders[estate.id], 0)
    for history in context.histories:
        if history.estate_id == estate.id:
            history.relinquished_at = now
    owner = (
        context.owners.get(estate.owner_character_id)
        if estate.owner_character_id
        else None
    )
    estate.owner_character_id = None
    if owner is None:
        return
    replacement = Estate(
        id=uuid.uuid4(),
        owner_character_id=owner.id,
        realm_id=owner.current_realm_id,
        form_id=content.progression.basic_mobile_form,
    )
    estate.data = {**estate.data, "replacement_id": str(replacement.id)}
    context.replacements.append(replacement)
    context.replacement_histories.append(
        EstateOwnershipHistory(
            id=uuid.uuid4(),
            estate_id=replacement.id,
            character_id=owner.id,
            acquired_at=now,
        )
    )


def complete_tick_transition(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Finalize a regression created during catch-up without per-tick queries."""
    pending = realm.pending_transition
    if pending is None or as_utc(datetime.fromisoformat(pending["completes_at"])) > now:
        return
    node = content.development_node(pending["to_node"])
    allowed = set(node.carried_tags) | {
        content.project(p).grants_tag for p in node.projects
    }
    for tag in list(context.stack):
        if tag.tag_id not in allowed:
            context.stack.remove(tag)
            if tag in context.acquired_tags:
                context.acquired_tags.remove(tag)
            else:
                context.removed_tags.append(tag)
        elif pending["cause"] == "regression":
            tag.node_id = node.id
    realm.current_node_id = node.id
    if pending["cause"] == "regression":
        realm.gauge = realm.shed_progress = 0
        realm.decay_stage = DecayStage.FED.value
    realm.pending_transition = None
    refresh_tags(context, realm, content)
    step_10_lines(context, realm, now, content)


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
    context.line_weights = {
        line.key: context.line_weights[line.key]
        if line.key in context.line_weights
        else 1
        if line.value_measured
        else next(i.reference_price for i in content.items if line.selector.matches(i))
        for line in context.lines
    }


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
    tag = build_realm_tag(
        realm, tag_id, context.stack_tag_ids, run.build_completes_at, run.id
    )
    context.acquired_tags.append(tag)
    context.stack.append(tag)
    refresh_tags(context, realm, content)
    run.status = "complete"
    step_10_lines(context, realm, now, content)


def complete_tick_events(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Keep exact event order, with builds preceding transitions on a tie."""
    while True:
        events: list[tuple[datetime, TimedEventKind]] = []
        run = context.active_run
        if run is not None and run.status == "building" and run.build_completes_at:
            events.append((as_utc(run.build_completes_at), TimedEventKind.BUILD))
        if realm.pending_transition is not None:
            events.append(
                (
                    as_utc(
                        datetime.fromisoformat(realm.pending_transition["completes_at"])
                    ),
                    TimedEventKind.TRANSITION,
                )
            )
        if not events or min(events)[0] > now:
            return
        due, kind = min(events)
        if kind == TimedEventKind.BUILD:
            complete_tick_build(context, realm, due, content)
        else:
            complete_tick_transition(context, realm, due, content)
