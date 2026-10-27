"""Caravan ordering, deterministic loss, conservation and durable pass claims."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from fractions import Fraction
from types import MappingProxyType

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.content.loader import ContentIndex
from app.content.schemas import CaravanConfig, MapPack, Selector, TagUpkeep
from app.engine.caravans import Route, candidate, remoteness, survival
from app.engine.market import QuoteContext
from app.models import RealmLine, RealmShipment, RealmState, RealmStore, WorldState
from app.services.caravans import run_caravan_pass
from app.services.realm_ticks import load_context, step_0_arrivals

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
    session.add(
        RealmState(
            id=SELLER,
            template_id=SELLER,
            current_node_id="node.ashen_t1",
            last_tick_at=NOW,
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
    step_0_arrivals(context, buyer, now + timedelta(hours=1), content)
    step_0_arrivals(context, buyer, now + timedelta(hours=1), content)
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
        assert choice.delivered == int(choice.sent * retained)
        assert choice.sent == choice.delivered + (choice.sent - choice.delivered)
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
    from app.models import GoldLedger

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
    from threading import Barrier

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
    third = "realm.fake_far"
    realm_session.add(
        RealmState(
            id=third,
            template_id=third,
            current_node_id="node.ashen_t1",
            last_tick_at=NOW,
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
    assert run_caravan_pass(realm_session, content, NOW + timedelta(days=1))
    shipment = realm_session.scalar(select(RealmShipment))
    assert shipment and shipment.from_realm_id == SELLER


def test_random_passes_conserve_goods_and_gold(realm_session: Session) -> None:
    """Random road losses and burn settings account for every dispatched unit."""
    from hypothesis import settings

    from app.models import GoldLedger

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
    from app.services.realms import resolve_realm

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
