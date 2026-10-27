"""Caravan ordering, deterministic loss, conservation and durable pass claims."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal as D
from fractions import Fraction
from math import floor
from threading import Barrier
from types import MappingProxyType
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import event, select, update
from sqlalchemy.engine import Connection, ExecutionContext
from sqlalchemy.orm import Session, sessionmaker
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.content.loader import ContentIndex
from app.content.schemas import (
    CaravanConfig,
    MapPack,
    ProductionItem,
    Selector,
    TagUpkeep,
)
from app.engine.caravans import Route, candidate, remoteness, survival
from app.engine.market import QuoteContext, total
from app.engine.stores import Line, line_key
from app.models import (
    Estate,
    GoldLedger,
    RealmLine,
    RealmShipment,
    RealmState,
    RealmStore,
    WorldState,
)
from app.services.caravans import _draw_value, run_caravan_pass
from app.services.market import market_contexts
from app.services.realm_ticks import load_context, step_0_arrivals
from app.services.realms import as_utc, finalize_realm, resolve_realm
from app.services.scheduler import run_realm_ticks
from app.services.stores import recompute_lines

BUYER = "realm.verdant_vale"
SELLER = "realm.ashen_reach"
ITEM = "item.fake_sprig"


def caravan_content() -> ContentIndex:
    """Give the two fake world realms road access and a small shared appetite."""
    tags = tuple(
        t.model_copy(
            update={"effects": t.effects.model_copy(update={"caravan_access": True})}
        )
        for t in CONTENT.tags
    )
    nodes = tuple(
        n.model_copy(
            update={
                "upkeep": (TagUpkeep(selector=Selector(item=ITEM), per_day=10),),
                "reserve_days": 1,
                "cap_days": 10,
            }
        )
        for n in CONTENT.development_nodes
    )
    return replace(
        CONTENT,
        tags=tags,
        development_nodes=nodes,
        _nodes_by_id=MappingProxyType({n.id: n for n in nodes}),
    )


def seed(session: Session) -> ContentIndex:
    """Create a hungry buyer, a stocked seller and a pass cursor."""
    content = caravan_content()
    buyer = session.get(RealmState, BUYER)
    assert buyer
    buyer.treasury = 10000
    buyer.last_tick_at = NOW + timedelta(days=1)
    session.add(
        RealmState(
            id=SELLER,
            template_id=SELLER,
            current_node_id="node.ashen_t1",
            last_tick_at=NOW + timedelta(days=1),
        )
    )
    session.add(
        WorldState(id=1, seeded_at=NOW, last_caravan_pass=NOW, content_version="test")
    )
    session.add(RealmStore(realm_id=SELLER, item_id=ITEM, quantity_milli=100000))
    session.commit()
    return content


def test_nothing_bought_twice_in_transit_and_arrivals(realm_session: Session) -> None:
    content = seed(realm_session)
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "caravan": content.economy.caravan.model_copy(
                    update={"time_mult": 1000}
                )
            }
        ),
    )
    now = NOW + timedelta(days=1)
    assert run_caravan_pass(realm_session, content, now)
    rows = list(realm_session.scalars(select(RealmShipment)))
    assert len(rows) == 1
    shipment = rows[0]
    assert shipment.quantity_arriving == 10
    line = realm_session.scalar(select(RealmLine).where(RealmLine.realm_id == BUYER))
    assert line and line.in_transit == 10000
    assert not run_caravan_pass(realm_session, content, now)
    assert run_caravan_pass(realm_session, content, now + timedelta(hours=6))
    assert len(list(realm_session.scalars(select(RealmShipment)))) == 1
    buyer = realm_session.get(RealmState, BUYER)
    assert buyer
    context = load_context(realm_session, buyer, None, content)
    step_0_arrivals(context, buyer, now, content)
    assert context.stores.get(ITEM, 0) == 0
    step_0_arrivals(context, buyer, now + timedelta(hours=17), content)
    step_0_arrivals(context, buyer, now + timedelta(hours=17), content)
    assert context.stores[ITEM] == 10000
    assert shipment.status == "arrived"


def test_missed_passes_not_replayed(realm_session: Session) -> None:
    content = seed(realm_session)
    now = NOW + timedelta(days=50, minutes=1)
    assert run_caravan_pass(realm_session, content, now)
    assert not run_caravan_pass(realm_session, content, now)
    world = realm_session.get(WorldState, 1)
    assert world and world.last_caravan_pass.replace(
        tzinfo=NOW.tzinfo
    ) == NOW + timedelta(days=50)


def contexts() -> tuple[QuoteContext, QuoteContext]:
    settings = CONTENT.economy.market
    seller = QuoteContext(10, 1, D(100), D(100), D(10), settings, D(25), 0, 0, 100)
    buyer = replace(seller, stock=D(0), treasury=10000)
    return seller, buyer


def test_nearer_seller_and_never_cheaper_than_ask() -> None:
    seller, buyer = contexts()
    near = candidate(
        seller, buyer, 10000, 1000, Route(Fraction(1), ()), Fraction(1), CaravanConfig()
    )
    far = candidate(
        seller, buyer, 10000, 1000, Route(Fraction(2), ()), Fraction(1), CaravanConfig()
    )
    assert near and far
    assert near.unit_cost <= far.unit_cost
    assert near.unit_cost >= Fraction(near.goods, near.sent)


@given(st.integers(1, 1000), st.integers(0, 100))
def test_loss_capacity_and_conservation(capacity: int, reduction: int) -> None:
    edge = CONTENT.map.edges[0].model_copy(update={"base_loss_pct": 20})
    route = Route(Fraction(1), (edge,))
    retained = survival(route, {edge.a: Fraction(reduction)})
    assert retained == 1 - Fraction(20, 100) * (1 - Fraction(reduction, 100))
    seller, buyer = contexts()
    choice = candidate(seller, buyer, 10000, capacity, route, retained, CaravanConfig())
    if choice:
        assert choice.sent * seller.reference_price <= capacity
        assert choice.delivered == floor(
            choice.sent * (1 - Fraction(20, 100) * (1 - Fraction(reduction, 100)))
        )
        assert choice.goods + choice.fee <= buyer.treasury


def test_remoteness_level_gates_direction_and_cheapest_path() -> None:
    edge = CONTENT.map.edges[0].model_copy(
        update={"base_time_s": 3600, "one_way": True}
    )
    gated = edge.model_copy(
        update={"id": "gated", "base_time_s": 1, "min_travel_level": 2}
    )
    routes = remoteness(MapPack(edges=(edge, gated), positions={}))
    assert routes[edge.a, edge.b].hours == 1
    assert (edge.b, edge.a) not in routes


def test_gold_goods_conserved_and_fee_burn(realm_session: Session) -> None:
    content = seed(realm_session)
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "caravan": content.economy.caravan.model_copy(
                    update={"fee_burn_pct": 100}
                )
            }
        ),
    )
    assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    shipment = realm_session.scalar(select(RealmShipment))
    assert shipment
    gold = sum(realm_session.scalars(select(RealmState.treasury)))
    burned = -sum(realm_session.scalars(select(GoldLedger.amount)))
    assert gold + burned == 10000
    stock = sum(realm_session.scalars(select(RealmStore.quantity_milli)))
    assert (
        stock
        + shipment.quantity_arriving * 1000
        + (shipment.quantity_sent - shipment.quantity_arriving) * 1000
        == 100000
    )


def test_two_postgres_schedulers_claim_one_pass(realm_session: Session) -> None:
    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock concurrency")
    content = seed(realm_session)
    engine = realm_session.get_bind()
    barrier = Barrier(2)

    def run() -> bool:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            result = run_caravan_pass(session, content, NOW + timedelta(days=1))
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results) == [False, True]
    assert len(list(realm_session.scalars(select(RealmShipment)))) == 1


@pytest.mark.parametrize("isolated,access", [(True, True), (False, False)])
def test_isolated_and_without_access_never_trade(
    realm_session: Session, isolated: bool, access: bool
) -> None:
    content = seed(realm_session)
    buyer = realm_session.get(RealmState, BUYER)
    assert buyer
    buyer.isolated = isolated
    if not access:
        content = replace(content, tags=CONTENT.tags)
    assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    assert list(realm_session.scalars(select(RealmShipment))) == []


def test_equal_ask_nearer_seller_wins(realm_session: Session) -> None:
    content = seed(realm_session)
    third = "realm.aaa_far"
    realm_session.add(
        RealmState(
            id=third,
            template_id=third,
            current_node_id="node.ashen_t1",
            last_tick_at=NOW + timedelta(days=1),
        )
    )
    realm_session.add(RealmStore(realm_id=third, item_id=ITEM, quantity_milli=100000))
    edge = content.map.edges[0].model_copy(
        update={"id": "far", "a": third, "b": BUYER, "base_time_s": 120}
    )
    content = replace(
        content,
        map=content.map.model_copy(update={"edges": (*content.map.edges, edge)}),
    )
    for realm_id in (BUYER, SELLER, third):
        realm = realm_session.get(RealmState, realm_id)
        assert realm
        recompute_lines(realm_session, realm, content)
    realm_session.flush()
    buyer = realm_session.get(RealmState, BUYER)
    assert buyer
    bid = market_contexts(realm_session, buyer, content)[ITEM][1]
    choices = []
    for realm_id in (SELLER, third):
        seller = realm_session.get(RealmState, realm_id)
        assert seller
        ask = market_contexts(realm_session, seller, content)[ITEM][1]
        route = content.caravan_routes[realm_id, BUYER]
        choice = candidate(
            ask, bid, 10000, 1000, route, Fraction(1), content.economy.caravan
        )
        assert choice
        choices.append(choice)
    assert third < SELLER
    assert choices[0].unit_cost == choices[1].unit_cost
    assert (
        content.caravan_routes[SELLER, BUYER].hours
        < content.caravan_routes[third, BUYER].hours
    )
    assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    shipment = realm_session.scalar(select(RealmShipment))
    assert shipment and shipment.from_realm_id == SELLER


def test_random_passes_conserve_goods_and_gold(realm_session: Session) -> None:
    """Random road losses and burn settings account for every dispatched unit."""
    content = seed(realm_session)

    @settings(max_examples=20, deadline=None)
    @given(
        loss=st.integers(0, 90),
        burn=st.integers(0, 100),
        capacity=st.integers(10, 1000),
    )
    def check(loss: int, burn: int, capacity: int) -> None:
        try:
            edge = content.map.edges[0].model_copy(update={"base_loss_pct": loss})
            settings = content.economy.caravan.model_copy(
                update={"fee_burn_pct": burn, "capacity_value_per_pass": capacity}
            )
            varied = replace(
                content,
                map=content.map.model_copy(update={"edges": (edge,)}),
                economy=content.economy.model_copy(update={"caravan": settings}),
            )
            assert run_caravan_pass(realm_session, varied, NOW + timedelta(days=1))
            shipments = list(realm_session.scalars(select(RealmShipment)))
            stores = sum(realm_session.scalars(select(RealmStore.quantity_milli)))
            arriving = sum(s.quantity_arriving for s in shipments)
            lost = sum(s.quantity_sent - s.quantity_arriving for s in shipments)
            assert stores + 1000 * (arriving + lost) == 100000
            assert sum(
                realm_session.scalars(select(RealmState.treasury))
            ) == 10000 + sum(realm_session.scalars(select(GoldLedger.amount)))
            for shipment in shipments:
                assert (
                    shipment.quantity_sent * content.item(ITEM).reference_price
                    <= capacity
                )
        finally:
            realm_session.rollback()
            realm_session.expire_all()

    check()


def test_multiedge_loss_and_capped_adjoining_road_tags() -> None:
    edge = CONTENT.map.edges[0].model_copy(update={"base_loss_pct": 20})
    route = Route(Fraction(2), (edge, edge))
    assert survival(route, {}) == Fraction(16, 25)
    assert survival(route, {edge.a: Fraction(25), edge.b: Fraction(25)}) == Fraction(
        81, 100
    )
    assert survival(route, {edge.a: Fraction(60), edge.b: Fraction(60)}) == 1


def test_arrival_on_first_due_tick(realm_session: Session) -> None:
    content = seed(realm_session)
    now = NOW + timedelta(days=1)
    buyer = realm_session.get(RealmState, BUYER)
    assert buyer
    buyer.last_tick_at = now
    assert run_caravan_pass(realm_session, content, now)
    shipment = realm_session.scalar(select(RealmShipment))
    assert shipment
    # Arrival is two minutes after dispatch; no realm tick is due yet.
    resolve_realm(realm_session, buyer, now + timedelta(minutes=3), content)
    assert shipment.status == "in_transit"
    assert realm_session.get(RealmStore, (BUYER, ITEM)) is None
    resolve_realm(realm_session, buyer, now + timedelta(hours=1), content)
    assert shipment.status == "arrived"
    stock = realm_session.get(RealmStore, (BUYER, ITEM))
    assert stock and stock.quantity_milli == 9584
    line = realm_session.scalar(select(RealmLine).where(RealmLine.realm_id == BUYER))
    assert line and line.in_transit == 0


def test_scheduled_job_dispatches_due_pass_once(realm_session: Session) -> None:
    """The real job dispatches and advances the cursor on either database."""
    content = seed(realm_session)
    factory = sessionmaker(bind=realm_session.get_bind())
    now = NOW + timedelta(days=1, minutes=5)
    assert run_realm_ticks(factory, content, now)
    realm_session.expire_all()
    shipment = realm_session.scalar(select(RealmShipment))
    world = realm_session.get(WorldState, 1)
    assert shipment and world
    assert as_utc(world.last_caravan_pass) == NOW + timedelta(days=1)
    shipment_id = shipment.id
    realm_session.commit()
    assert run_realm_ticks(factory, content, now)
    realm_session.expire_all()
    assert list(realm_session.scalars(select(RealmShipment.id))) == [shipment_id]
    assert as_utc(world.last_caravan_pass) == NOW + timedelta(days=1)


def test_hungriest_buyer_gets_shared_seller_capacity(realm_session: Session) -> None:
    content = seed(realm_session)
    hungry_id = "realm.zzz_hungry"
    realm_session.add(
        RealmState(
            id=hungry_id,
            template_id=hungry_id,
            current_node_id="node.verdant_t1",
            last_tick_at=NOW + timedelta(days=1),
            treasury=10000,
            gauge=2,
        )
    )
    edge = content.map.edges[0].model_copy(
        update={"id": "hungry", "a": SELLER, "b": hungry_id}
    )
    content = replace(
        content,
        map=content.map.model_copy(update={"edges": (*content.map.edges, edge)}),
        economy=content.economy.model_copy(
            update={
                "caravan": content.economy.caravan.model_copy(
                    update={"capacity_value_per_pass": 10}
                )
            }
        ),
    )
    assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    shipments = list(realm_session.scalars(select(RealmShipment)))
    assert len(shipments) == 1
    assert shipments[0].to_realm_id == hungry_id
    assert shipments[0].quantity_sent == 10


def test_largest_reference_draw_gets_single_capacity_allowance(
    realm_session: Session,
) -> None:
    content = seed(realm_session)
    ore = "item.mock_ore"
    nodes = tuple(
        n.model_copy(
            update={
                "upkeep": (
                    TagUpkeep(selector=Selector(item=ITEM), per_day=10),
                    TagUpkeep(selector=Selector(item=ore), per_day=6),
                )
            }
        )
        for n in content.development_nodes
    )
    content = replace(
        content,
        development_nodes=nodes,
        _nodes_by_id=MappingProxyType({n.id: n for n in nodes}),
        economy=content.economy.model_copy(
            update={
                "caravan": content.economy.caravan.model_copy(
                    update={"capacity_value_per_pass": 2}
                )
            }
        ),
    )
    realm_session.add(RealmStore(realm_id=SELLER, item_id=ore, quantity_milli=100000))
    assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    shipments = list(realm_session.scalars(select(RealmShipment)))
    assert len(shipments) == 1
    assert shipments[0].item_id == ore
    assert shipments[0].quantity_sent == 1


def test_draw_value_uses_actual_members_and_empty_default() -> None:
    """Authored item ordering and more-specific lines cannot change draw value."""
    expensive = CONTENT.item(ITEM).model_copy(update={"reference_price": 10})
    content = CONTENT.with_overrides(items=(expensive,))
    selector = Selector.model_validate({"class": "fake_plant"})
    line = Line(line_key(selector), selector, 1000, 0, 10000, 0, False)
    button = "item.worthless_button"
    assert (
        _draw_value(line, (line,), content)
        == CONTENT.item(button).reference_price * 1000
    )
    selector = Selector(item=button)
    specific = Line(line_key(selector), selector, 1000, 0, 10000, 0, False)
    assert _draw_value(line, (line, specific), content) == 10000
    empty = replace(line, selector=Selector(item="item.missing"))
    assert _draw_value(empty, (empty,), content) == 0
    assert _draw_value(replace(empty, value_measured=True), (empty,), content) == 1000


@pytest.mark.parametrize("scheduler_failure", [False, True])
def test_pass_resolves_stale_seller_before_selection(
    realm_session: Session, scheduler_failure: bool
) -> None:
    """Even a failed first scheduler attempt cannot leave stale sale inventory."""
    content = seed(realm_session)
    now = NOW + timedelta(days=1)
    seller = realm_session.get(RealmState, SELLER)
    stock = realm_session.get(RealmStore, (SELLER, ITEM))
    assert seller and stock
    seller.last_tick_at = now - timedelta(hours=1)
    stock.quantity_milli = 9000
    form = content.estate_form("form.fake_workshop").model_copy(
        update={
            "upkeep": (),
            "production": (ProductionItem(item_id=ITEM, per_day=2400),),
        }
    )
    content = replace(
        content, _forms_by_id=MappingProxyType({**content._forms_by_id, form.id: form})
    )
    realm_session.add(Estate(realm_id=SELLER, form_id=form.id))
    realm_session.commit()
    if scheduler_failure:

        def fail_seller(
            session: Session, realm_id: str, at: object, data: ContentIndex
        ) -> RealmState | None:
            if realm_id == SELLER:
                raise RuntimeError("Simulated first scheduler attempt failure")
            return finalize_realm(session, realm_id, now, data)

        with patch("app.services.scheduler.finalize_realm", side_effect=fail_seller):
            assert run_realm_ticks(
                sessionmaker(bind=realm_session.get_bind()), content, now
            )
        realm_session.expire_all()
    else:
        assert run_caravan_pass(realm_session, content, now)
    assert as_utc(seller.last_tick_at) == now
    shipment = realm_session.scalar(select(RealmShipment))
    assert shipment and shipment.quantity_sent == 10
    assert stock.quantity_milli == 90000


def test_pass_not_due_only_reads_cursor(realm_session: Session) -> None:
    """A skipped pass neither locks nor resolves realms."""
    content = seed(realm_session)
    statements: list[str] = []

    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    engine = realm_session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        assert not run_caravan_pass(realm_session, content, NOW + timedelta(hours=1))
    finally:
        event.remove(engine, "before_cursor_execute", record)
    queries = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(queries) == 1
    assert "world_state.last_caravan_pass" in queries[0]
    assert "FOR UPDATE" not in queries[0].upper()


@pytest.mark.parametrize("reduction", [0, 100])
def test_isolated_route_endpoint_tags_reduce_loss(
    realm_session: Session, reduction: int
) -> None:
    content = seed(realm_session)
    isolated_id = "realm.isolated_road"
    road = content.tags[0].model_copy(
        update={
            "id": "access.isolated_road",
            "effects": content.tags[0].effects.model_copy(
                update={"edge_loss_reduction_pct": reduction}
            ),
        }
    )
    node = content.development_node("node.verdant_t0_stub").model_copy(
        update={"inherent_tags": (road.id,), "upkeep": ()}
    )
    realm_session.add(
        RealmState(
            id=isolated_id,
            template_id=BUYER,
            isolated=True,
            current_node_id=node.id,
            last_tick_at=NOW,
        )
    )
    first = content.map.edges[0].model_copy(
        update={
            "id": "first",
            "a": SELLER,
            "b": isolated_id,
            "base_time_s": 60,
            "base_loss_pct": 20,
        }
    )
    second = first.model_copy(update={"id": "second", "a": isolated_id, "b": BUYER})
    content = replace(
        content,
        tags=(*content.tags, road),
        _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node}),
        map=content.map.model_copy(update={"edges": (first, second)}),
    )
    assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    shipment = realm_session.scalar(select(RealmShipment))
    assert shipment
    assert shipment.from_realm_id == SELLER and shipment.to_realm_id == BUYER
    assert shipment.quantity_sent == (17 if reduction == 0 else 10)
    assert shipment.quantity_arriving == 10
    endpoint = realm_session.get(RealmState, isolated_id)
    assert endpoint and as_utc(endpoint.last_tick_at) == NOW


@given(
    retained_pct=st.integers(1, 100),
    need=st.integers(0, 30000),
    capacity=st.integers(1, 1000),
)
def test_delivery_clamp_preserves_largest_feasible_candidate(
    retained_pct: int, need: int, capacity: int
) -> None:
    """Compare the optimized bound against an exhaustive physical-range search."""
    seller, buyer = contexts()
    retained = Fraction(retained_pct, 100)
    route = Route(Fraction(1), ())
    settings = CaravanConfig()
    expected = None
    for sent in range(1, min(90, capacity // 10) + 1):
        delivered = floor(sent * retained)
        goods = total(seller, "buy", sent)
        fee = (sent + 9) // 10  # 10 reference gold * 1 percent/hour, ceil.
        if (
            delivered > 0
            and delivered * 1000 <= need
            and goods + fee <= min(buyer.treasury, total(buyer, "sell", delivered))
        ):
            expected = (sent, delivered, goods, fee)
    result = candidate(seller, buyer, need, capacity, route, retained, settings)
    actual = (
        (result.sent, result.delivered, result.goods, result.fee) if result else None
    )
    assert actual == expected


def test_remoteness_prefers_cheaper_two_hop_path() -> None:
    direct = CONTENT.map.edges[0].model_copy(update={"base_time_s": 3600})
    first = direct.model_copy(
        update={"id": "first", "b": "realm.middle", "base_time_s": 600}
    )
    second = direct.model_copy(
        update={"id": "second", "a": "realm.middle", "base_time_s": 1200}
    )
    routes = remoteness(MapPack(edges=(direct, first, second), positions={}))
    assert routes[direct.a, direct.b].hours == Fraction(1, 2)
    assert tuple(e.id for e in routes[direct.a, direct.b].edges) == ("first", "second")


def test_sqlite_pass_restarts_with_write_intent_after_competing_commit(
    realm_session: Session,
) -> None:
    """Discard the early WAL snapshot before reading trade state under a writer lock."""
    if realm_session.get_bind().dialect.name != "sqlite":
        pytest.skip("SQLite WAL snapshots and BEGIN IMMEDIATE")
    content = seed(realm_session)
    engine = realm_session.get_bind()
    statements: list[str] = []
    competed = False

    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    def compete(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        nonlocal competed
        if competed or "SELECT world_state.last_caravan_pass" not in statement:
            return
        competed = True
        with Session(engine) as other:
            other.execute(
                update(RealmStore)
                .where(RealmStore.realm_id == SELLER, RealmStore.item_id == ITEM)
                .values(quantity_milli=50000)
            )
            other.commit()

    event.listen(engine, "before_cursor_execute", record)
    event.listen(engine, "after_cursor_execute", compete)
    try:
        assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    finally:
        event.remove(engine, "before_cursor_execute", record)
        event.remove(engine, "after_cursor_execute", compete)
    assert competed
    early_read = next(
        i
        for i, sql in enumerate(statements)
        if "SELECT world_state.last_caravan_pass" in sql
    )
    write_begin = statements.index("BEGIN IMMEDIATE")
    realm_read = next(
        i for i, sql in enumerate(statements) if sql.startswith("SELECT realm_state.")
    )
    assert early_read < write_begin < realm_read
    shipment = realm_session.scalar(select(RealmShipment))
    stock = realm_session.get(RealmStore, (SELLER, ITEM))
    assert shipment and shipment.quantity_sent == 10
    assert stock and stock.quantity_milli == 40000


def test_scheduler_logs_failed_caravan_pass_and_retries(
    realm_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed dispatch transaction rolls back and leaves its boundary retryable."""
    content = seed(realm_session)
    factory = sessionmaker(bind=realm_session.get_bind())
    now = NOW + timedelta(days=1)

    def fail_after_dispatch(session: Session, data: ContentIndex, at: datetime) -> bool:
        assert run_caravan_pass(session, data, at)
        raise RuntimeError("Simulated caravan failure after dispatch")

    with patch(
        "app.services.scheduler.run_caravan_pass", side_effect=fail_after_dispatch
    ):
        assert run_realm_ticks(factory, content, now)
    assert any(
        record.name == "app.services.scheduler"
        and record.getMessage() == "Caravan pass failed"
        and record.exc_info is not None
        for record in caplog.records
    )
    realm_session.expire_all()
    assert list(realm_session.scalars(select(RealmShipment))) == []
    world = realm_session.get(WorldState, 1)
    assert world and as_utc(world.last_caravan_pass) == NOW
    realm_session.commit()
    assert run_realm_ticks(factory, content, now)
    realm_session.expire_all()
    assert len(list(realm_session.scalars(select(RealmShipment)))) == 1
    assert as_utc(world.last_caravan_pass) == now
