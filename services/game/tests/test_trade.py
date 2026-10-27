"""Player realm transfers, exact holdings, and transaction serialization."""

import uuid
from typing import Any, Literal, cast

import pytest
from fastapi import HTTPException
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from test_travel import ApiFixture

from app.models import (
    Character,
    Currency,
    Estate,
    Inventory,
    Player,
    RealmLine,
    RealmState,
    RealmStore,
)
from app.services.stores import recompute_lines
from app.services.trade import gift, trade

REALM = "realm.verdant_vale"
ITEM = "item.fake_sprig"


def seed(session: Session) -> tuple[Character, RealmState]:
    """Seed a funded line, fractional stores and a player carrying whole goods."""
    realm = session.get(RealmState, REALM)
    assert realm is not None
    realm.treasury = 1000
    player = Player(auth_user_id=uuid.uuid4(), created_at=NOW)
    session.add(player)
    session.flush()
    estate = Estate(realm_id=REALM, form_id="form.fake_workshop")
    session.add(estate)
    session.flush()
    character = Character(
        player_id=player.id,
        name=str(player.id)[:20],
        name_normalized=str(player.id)[:20],
        current_realm_id=REALM,
        home_estate_id=estate.id,
        created_at=NOW,
    )
    session.add(character)
    session.flush()
    session.add_all(
        [
            Currency(character_id=character.id, gold=1000),
            Inventory(character_id=character.id, item_id=ITEM, quantity=50),
        ]
    )
    if session.get(RealmStore, (REALM, ITEM)) is None:
        session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=4500))
    session.flush()
    recompute_lines(session, realm, CONTENT)
    session.flush()
    return character, realm


def holdings(
    session: Session, character: Character, realm: RealmState
) -> tuple[int, int, int, int, list[tuple[str, int, int]]]:
    """Snapshot both named holders and exact line stock/budget."""
    session.flush()
    wallet = session.get(Currency, character.id)
    stack = session.get(Inventory, (character.id, ITEM))
    store = session.get(RealmStore, (realm.id, ITEM))
    assert wallet is not None and store is not None
    return (
        wallet.gold,
        realm.treasury,
        stack.quantity if stack else 0,
        store.quantity_milli,
        [
            (r.line_key, r.stock, r.budget_gold)
            for r in session.scalars(
                select(RealmLine)
                .where(RealmLine.realm_id == realm.id)
                .order_by(RealmLine.line_key)
            )
        ],
    )


@pytest.mark.parametrize(
    ("side", "quantity", "limit", "code"),
    [
        ("sell", 100, 0, "STORES_FULL"),
        ("buy", 2, 1000, "NOT_FOR_SALE"),
        ("sell", 1, 1000, "PRICE_MOVED"),
        ("buy", 1, 0, "PRICE_MOVED"),
    ],
)
def test_trade_errors_are_atomic(
    realm_session: Session,
    side: Literal["buy", "sell"],
    quantity: int,
    limit: int,
    code: str,
) -> None:
    character, realm = seed(realm_session)
    realm_session.commit()
    before = holdings(realm_session, character, realm)
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, CONTENT, ITEM, side, quantity, limit)
    assert cast(dict[str, Any], caught.value.detail)["error"]["code"] == code
    realm_session.rollback()
    assert holdings(realm_session, character, realm) == before


def test_trade_funding_inventory_and_presence_errors(realm_session: Session) -> None:
    character, realm = seed(realm_session)

    def fails(item: str, side: Literal["buy", "sell"], code: str) -> HTTPException:
        with pytest.raises(HTTPException) as caught:
            trade(
                realm_session,
                character,
                realm,
                CONTENT,
                item,
                side,
                1,
                0 if side == "sell" else 1000,
            )
        assert cast(dict[str, Any], caught.value.detail)["error"]["code"] == code
        return caught.value

    fails("missing", "sell", "UNKNOWN_ITEM")
    fails("item.mock_ore", "sell", "NO_DEMAND")
    for row in realm_session.scalars(select(RealmLine)):
        row.budget_gold = 0
    realm_session.flush()
    assert (
        cast(dict[str, Any], fails(ITEM, "sell", "UNFUNDED_DEMAND").detail)["error"][
            "max_quantity"
        ]
        == 0
    )
    wallet = realm_session.get(Currency, character.id)
    assert wallet is not None
    wallet.gold = 0
    fails(ITEM, "buy", "INSUFFICIENT_GOLD")
    with pytest.raises(HTTPException) as caught:
        gift(realm_session, character, realm, 1)
    assert (
        cast(dict[str, Any], caught.value.detail)["error"]["code"]
        == "INSUFFICIENT_GOLD"
    )
    wallet.gold = 1000
    stack = realm_session.get(Inventory, (character.id, ITEM))
    assert stack is not None
    stack.quantity = CONTENT.item(ITEM).stack_limit
    fails(ITEM, "buy", "INVENTORY_FULL")
    character.current_realm_id = "realm.ashen_reach"
    fails(ITEM, "buy", "NOT_PRESENT")
    with pytest.raises(HTTPException) as caught:
        gift(realm_session, character, realm, 1)
    assert cast(dict[str, Any], caught.value.detail)["error"]["code"] == "NOT_PRESENT"


@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    st.lists(
        st.tuples(st.sampled_from(["buy", "sell", "gift"]), st.integers(1, 5)),
        min_size=1,
        max_size=25,
    )
)
def test_random_trades_and_gifts_conserve_holdings(
    realm_session: Session, operations: list[tuple[str, int]]
) -> None:
    character, realm = seed(realm_session)
    before = holdings(realm_session, character, realm)
    successes: set[str] = set()
    for side, quantity in [("sell", 1), ("buy", 1), ("gift", 1), *operations]:
        try:
            with realm_session.begin_nested():
                if side == "gift":
                    gift(realm_session, character, realm, quantity)
                else:
                    assert side in ("buy", "sell")
                    trade(
                        realm_session,
                        character,
                        realm,
                        CONTENT,
                        ITEM,
                        cast(Literal["buy", "sell"], side),
                        quantity,
                        0 if side == "sell" else 1000,
                    )
                realm_session.flush()
                successes.add(side)
        except HTTPException:
            pass
        after = holdings(realm_session, character, realm)
        assert after[0] + after[1] == before[0] + before[1]
        assert after[2] * 1000 + after[3] == before[2] * 1000 + before[3]
        assert after[3] % 1000 == 500
        assert after[4][0][1] == after[3]
    assert successes == {"buy", "sell", "gift"}
    # Each Hypothesis example starts from the same database state.
    realm_session.rollback()


@pytest.mark.anyio
async def test_trade_and_gift_routes(estate_client: ApiFixture) -> None:
    client, factory, headers, _ = estate_client
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        session.add(Inventory(character_id=character.id, item_id=ITEM, quantity=5))
        session.add(Estate(realm_id=REALM, form_id="form.fake_workshop"))
        realm = session.get(RealmState, REALM)
        assert realm is not None
        realm.treasury = 1000
        session.flush()
        for row in recompute_lines(session, realm, CONTENT):
            row.budget_gold = 100
        session.commit()
    result = await client.post(
        f"/realms/{REALM}/market/trade",
        headers=headers,
        json={"item_id": ITEM, "side": "sell", "quantity": 1, "limit_gold": 0},
    )
    assert result.status_code == 200, result.text
    assert result.json()["gold"] >= 0
    result = await client.post(
        f"/realms/{REALM}/treasury/gift", headers=headers, json={"gold": 1}
    )
    assert result.status_code == 204, result.text
    for field, value in [("quantity", 0), ("quantity", 1.5), ("limit_gold", -1)]:
        body = {
            "item_id": ITEM,
            "side": "sell",
            "quantity": 1,
            "limit_gold": 0,
            field: value,
        }
        result = await client.post(
            f"/realms/{REALM}/market/trade", headers=headers, json=body
        )
        assert result.status_code == 422


def test_postgres_sellers_cannot_overspend_line(realm_session: Session) -> None:
    """Independent sellers serialize at the realm and share one spent budget."""
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text

    from app.engine.market import total
    from app.services.actions import resolve_character
    from app.services.market import market_contexts

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    first, realm = seed(realm_session)
    second, realm = seed(realm_session)
    line, ctx = market_contexts(realm_session, realm, CONTENT)[ITEM]
    assert line is not None
    budget = total(ctx, "sell", 2)
    assert budget > 0
    row = realm_session.get(RealmLine, (realm.id, line.key))
    assert row is not None
    row.budget_gold = budget
    realm_session.commit()
    ids = first.id, second.id
    held = threading.Event()
    release = threading.Event()
    attempting = threading.Event()
    pid: list[int] = []

    def seller(index: int) -> int:
        with Session(realm_session.get_bind()) as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            if index == 1:
                assert held.wait(5)
                pid.append(
                    session.execute(text("SELECT pg_backend_pid()")).scalar_one()
                )
                attempting.set()
            resolve_character(session, ids[index], NOW, CONTENT, {REALM})
            if index == 0:
                held.set()
                assert release.wait(5)
            character = session.get(Character, ids[index])
            state = session.get(RealmState, REALM)
            assert character is not None and state is not None
            try:
                paid = trade(session, character, state, CONTENT, ITEM, "sell", 2, 0)
                session.commit()
                return paid
            except HTTPException as error:
                assert (
                    cast(dict[str, Any], error.detail)["error"]["code"]
                    == "UNFUNDED_DEMAND"
                )
                session.rollback()
                return 0

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(seller, 0)
        b = pool.submit(seller, 1)
        try:
            assert attempting.wait(5)
            deadline = time.monotonic() + 4
            blocked = False
            while time.monotonic() < deadline:
                with Session(realm_session.get_bind()) as observer:
                    blocked = bool(
                        observer.execute(
                            text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"),
                            {"pid": pid[0]},
                        ).scalar_one()
                    )
                if blocked:
                    break
                time.sleep(0.01)
            assert blocked
        finally:
            release.set()
        payments = [a.result(timeout=10), b.result(timeout=10)]
    assert payments == [budget, 0]
    realm_session.expire_all()
    remaining = realm_session.get(RealmLine, (REALM, line.key))
    assert remaining is not None and remaining.budget_gold == 0
    assert sum(payments) <= budget


def test_funding_maximum_and_gift_preserves_spent_budget(
    realm_session: Session,
) -> None:
    """A funding failure reports an executable maximum and gifts retain budgets."""
    from app.engine.market import total
    from app.services.market import market_contexts

    character, realm = seed(realm_session)
    content = CONTENT.with_overrides(
        items=[CONTENT.item(ITEM).model_copy(update={"reference_price": 10})]
    )
    line, ctx = market_contexts(realm_session, realm, content)[ITEM]
    assert line is not None
    row = realm_session.get(RealmLine, (realm.id, line.key))
    assert row is not None
    row.budget_gold = total(ctx, "sell", 2)
    realm_session.flush()
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, content, ITEM, "sell", 4, 0)
    maximum = cast(dict[str, Any], caught.value.detail)["error"]["max_quantity"]
    assert maximum == 2
    before = holdings(realm_session, character, realm)
    paid = trade(realm_session, character, realm, content, ITEM, "sell", maximum, 0)
    after = holdings(realm_session, character, realm)
    assert before[4][0][2] - after[4][0][2] == paid
    assert after[3] - before[3] == maximum * 1000
    assert before[2] - after[2] == maximum
    # Newly arrived gifts do not replenish the spent line budget.
    gift(realm_session, character, realm, 100)
    realm_session.flush()
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, content, ITEM, "sell", 1, 0)
    assert (
        cast(dict[str, Any], caught.value.detail)["error"]["code"] == "UNFUNDED_DEMAND"
    )


def test_buy_requires_slot_and_only_requested_item_stock(
    realm_session: Session,
) -> None:
    """Unmatched warehouse stock has no reserve but still needs a player slot."""
    from dataclasses import replace

    character, realm = seed(realm_session)
    other = "item.mock_ore"
    realm_session.add(RealmStore(realm_id=realm.id, item_id=other, quantity_milli=1500))
    realm_session.flush()
    content = replace(
        CONTENT, caps=CONTENT.caps.model_copy(update={"inventory_slots": 1})
    )
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, content, other, "buy", 1, 1000)
    assert (
        cast(dict[str, Any], caught.value.detail)["error"]["code"] == "INVENTORY_FULL"
    )
    before = realm_session.get(RealmStore, (realm.id, ITEM))
    assert before is not None
    sprigs = before.quantity_milli
    trade(realm_session, character, realm, CONTENT, other, "buy", 1, 1000)
    store = realm_session.get(RealmStore, (realm.id, other))
    assert store is not None and store.quantity_milli == 500
    assert before.quantity_milli == sprigs
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, CONTENT, other, "buy", 1, 1000)
    assert cast(dict[str, Any], caught.value.detail)["error"]["code"] == "NOT_FOR_SALE"


@pytest.mark.anyio
async def test_price_moved_route_rolls_back_all_state(
    estate_client: ApiFixture,
) -> None:
    """The HTTP transaction also rolls back lazy ticks and derived rows on rejection."""
    from datetime import timedelta

    client, factory, headers, clock = estate_client
    with factory() as session:
        character = session.scalar(select(Character))
        realm = session.get(RealmState, REALM)
        assert character is not None and realm is not None
        session.add(Inventory(character_id=character.id, item_id=ITEM, quantity=5))
        session.add(Estate(realm_id=REALM, form_id="form.fake_workshop"))
        session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=0))
        realm.treasury = 1000
        session.flush()
        for row in recompute_lines(session, realm, CONTENT):
            row.budget_gold = 100
        session.commit()
        snapshot = holdings(session, character, realm)
        tick_at, gauge = realm.last_tick_at, realm.gauge
        character_id = character.id
    clock["now"] += timedelta(hours=1)
    response = await client.post(
        f"/realms/{REALM}/market/trade",
        headers=headers,
        json={"item_id": ITEM, "side": "sell", "quantity": 1, "limit_gold": 1000000},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRICE_MOVED"
    with factory() as session:
        character = session.get(Character, character_id)
        realm = session.get(RealmState, REALM)
        assert character is not None and realm is not None
        assert holdings(session, character, realm) == snapshot
        assert (realm.last_tick_at, realm.gauge) == (tick_at, gauge)


def test_fractional_cap_and_reserve_never_leak_a_whole_unit(
    realm_session: Session,
) -> None:
    """Half a remaining item of capacity or surplus cannot permit a whole trade."""
    character, realm = seed(realm_session)
    trade(realm_session, character, realm, CONTENT, ITEM, "sell", 6, 0)
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, CONTENT, ITEM, "sell", 1, 0)
    assert cast(dict[str, Any], caught.value.detail)["error"]["code"] == "STORES_FULL"
    trade(realm_session, character, realm, CONTENT, ITEM, "buy", 7, 1000)
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, CONTENT, ITEM, "buy", 1, 1000)
    assert cast(dict[str, Any], caught.value.detail)["error"]["code"] == "NOT_FOR_SALE"
    store = realm_session.get(RealmStore, (realm.id, ITEM))
    assert store is not None and store.quantity_milli == 3500


def test_sale_missing_inputs_and_empty_stack_removal(realm_session: Session) -> None:
    """A sale never invents player goods and removes a completely sold stack."""
    character, realm = seed(realm_session)
    stack = realm_session.get(Inventory, (character.id, ITEM))
    assert stack is not None
    stack.quantity = 1
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, CONTENT, ITEM, "sell", 2, 0)
    assert (
        cast(dict[str, Any], caught.value.detail)["error"]["code"] == "MISSING_INPUTS"
    )
    trade(realm_session, character, realm, CONTENT, ITEM, "sell", 1, 0)
    assert realm_session.get(Inventory, (character.id, ITEM)) is None


def test_weighted_line_moves_item_milli_without_rounding_gap(
    realm_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Synthetic value-measured demand exercises the future bullion trade seam."""
    from fractions import Fraction

    from app.content.schemas import Selector
    from app.engine.stores import Demand
    from app.services import stores
    from app.services.market import market_contexts

    character, realm = seed(realm_session)
    other = "item.mock_ore"
    monkeypatch.setattr(
        stores,
        "mint_demands",
        lambda tags: (
            Demand(
                Selector.model_validate({"class": "placeholder"}), Fraction(1000), True
            ),
        ),
    )
    realm_session.add(RealmStore(realm_id=realm.id, item_id=other, quantity_milli=4500))
    realm_session.flush()
    recompute_lines(realm_session, realm, CONTENT)
    realm_session.flush()
    line, _ = market_contexts(realm_session, realm, CONTENT)[other]
    assert line is not None and line.value_measured and line.stock == 9000
    trade(realm_session, character, realm, CONTENT, other, "buy", 2, 1000)
    line, _ = market_contexts(realm_session, realm, CONTENT)[other]
    store = realm_session.get(RealmStore, (realm.id, other))
    stack = realm_session.get(Inventory, (character.id, other))
    assert line is not None and line.stock == 5000
    assert store is not None and store.quantity_milli == 2500
    assert stack is not None and stack.quantity == 2
    with pytest.raises(HTTPException) as caught:
        trade(realm_session, character, realm, CONTENT, other, "buy", 2, 1000)
    assert cast(dict[str, Any], caught.value.detail)["error"]["code"] == "NOT_FOR_SALE"
