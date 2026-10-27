"""Atomic world caravan pass; caller owns the transaction."""

from datetime import datetime, timedelta
from fractions import Fraction

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.caravans import Candidate, Route, candidate, survival
from app.engine.stores import Line, membership
from app.models import GoldLedger, RealmShipment, RealmState, RealmStore, WorldState
from app.services.market import market_contexts
from app.services.realms import as_utc, resolve_realm
from app.services.stores import realm_holders, recompute_lines


def run_caravan_pass(session: Session, content: ContentIndex, now: datetime) -> bool:
    """Claim a current pass, locking shared realms and map endpoints in id order.

    Realm locks precede the singleton lock, so realm-first request handlers
    retain the global lock order. The cursor and dispatches commit together.
    """
    interval = (
        timedelta(days=1)
        / content.economy.tick.per_day
        * content.economy.caravan.pass_every_ticks
    )
    previous = session.scalar(
        select(WorldState.last_caravan_pass).where(WorldState.id == 1)
    )
    if previous is None or as_utc(now) < as_utc(previous) + interval:
        return False
    endpoints = {
        endpoint for edge in content.map.edges for endpoint in (edge.a, edge.b)
    }
    realms = list(
        session.scalars(
            select(RealmState)
            .where(or_(RealmState.isolated.is_(False), RealmState.id.in_(endpoints)))
            .order_by(RealmState.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    world = session.scalar(
        select(WorldState)
        .where(WorldState.id == 1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if world is None or as_utc(now) < as_utc(world.last_caravan_pass) + interval:
        return False
    for realm in realms:
        resolve_realm(session, realm, now, content)
    # Anchor to the seed cadence, skipping all missed passes.
    world.last_caravan_pass = (
        as_utc(world.seeded_at)
        + ((as_utc(now) - as_utc(world.seeded_at)) // interval) * interval
    )
    _balance(session, realms, content, now)
    session.flush()
    return True


def _balance(
    session: Session, realms: list[RealmState], content: ContentIndex, now: datetime
) -> None:
    """Select against resolved holdings and active endpoint road effects."""
    reductions = {}
    eligible = []
    for realm in realms:
        _, tags = realm_holders(session, realm, content)
        reductions[realm.id] = sum(
            (Fraction(str(t.effects.edge_loss_reduction_pct)) for t in tags),
            Fraction(0),
        )
        if not realm.isolated and any(t.effects.caravan_access for t in tags):
            eligible.append(realm)
    capacity = dict.fromkeys(
        (r.id for r in eligible), content.economy.caravan.capacity_value_per_pass
    )
    for buyer in sorted(eligible, key=lambda r: (-r.gauge, r.id)):
        recompute_lines(session, buyer, content)
        session.flush()
        contexts = market_contexts(session, buyer, content)
        lines = {line.key: line for line, _ in contexts.values() if line is not None}

        for line in sorted(
            lines.values(),
            key=lambda line: (
                -_draw_value(line, tuple(lines.values()), content),
                line.key,
            ),
        ):
            _buy_line(
                session, buyer, line.key, eligible, capacity, reductions, content, now
            )
    for realm in eligible:
        recompute_lines(session, realm, content)


def _draw_value(line: Line, lines: tuple[Line, ...], content: ContentIndex) -> int:
    value = (
        1
        if line.value_measured
        else min(
            (
                item.reference_price
                for item in content.items
                if membership(item, lines) == line
            ),
            default=0,
        )
    )
    return line.draw_per_day * value


def _buy_line(
    session: Session,
    buyer: RealmState,
    key: str,
    sellers: list[RealmState],
    capacity: dict[str, int],
    reductions: dict[str, Fraction],
    content: ContentIndex,
    now: datetime,
) -> None:
    contexts = market_contexts(session, buyer, content)
    choices: list[tuple[Candidate, Route, RealmState, str]] = []
    for seller in sellers:
        if seller.id == buyer.id:
            continue
        route = content.caravan_routes.get((seller.template_id, buyer.template_id))
        if route is None:
            continue
        recompute_lines(session, seller, content)
        session.flush()
        offers = market_contexts(session, seller, content)
        for item_id, (line, bid) in contexts.items():
            if line is None or line.key != key:
                continue
            need = line.reserve - line.stock - line.in_transit
            if need <= 0:
                continue
            choice = candidate(
                offers[item_id][1],
                bid,
                need,
                min(capacity[buyer.id], capacity[seller.id]),
                route,
                survival(route, reductions),
                content.economy.caravan,
            )
            if choice:
                choices.append((choice, route, seller, item_id))
    if not choices:
        return
    choice, route, seller, item_id = min(
        choices, key=lambda c: (c[0].unit_cost, c[1].hours, c[2].id, c[3])
    )
    _dispatch(session, buyer, seller, item_id, choice, route, capacity, content, now)


def _dispatch(
    session: Session,
    buyer: RealmState,
    seller: RealmState,
    item_id: str,
    choice: Candidate,
    route: Route,
    capacity: dict[str, int],
    content: ContentIndex,
    now: datetime,
) -> None:
    """Transfer both holdings and retain the loss as sent minus arriving."""
    burn = int(choice.fee * Fraction(str(content.economy.caravan.fee_burn_pct)) / 100)
    buyer.treasury -= choice.goods + choice.fee
    seller.treasury += choice.goods + choice.fee - burn
    stock = session.get(RealmStore, (seller.id, item_id))
    assert stock is not None
    stock.quantity_milli -= choice.sent * 1000
    value = choice.sent * content.item(item_id).reference_price
    capacity[buyer.id] -= value
    capacity[seller.id] -= value
    if burn:
        session.add(
            GoldLedger(
                cause="caravan_fee_burn", amount=-burn, realm_id=seller.id, at=now
            )
        )
    session.add(
        RealmShipment(
            from_realm_id=seller.id,
            to_realm_id=buyer.id,
            item_id=item_id,
            quantity_sent=choice.sent,
            quantity_arriving=choice.delivered,
            goods_gold=choice.goods,
            fee_gold=choice.fee,
            dispatched_at=now,
            arrives_at=now
            + timedelta(
                hours=float(
                    route.hours * Fraction(str(content.economy.caravan.time_mult))
                )
            ),
            status="in_transit",
        )
    )
    session.flush()
    recompute_lines(session, buyer, content)
    recompute_lines(session, seller, content)
    session.flush()
