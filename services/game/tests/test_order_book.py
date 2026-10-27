"""Global slots preserve holdings, priority, access and concurrent execution."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier
from types import MappingProxyType
from typing import Literal

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import Connection, ExecutionContext
from sqlalchemy.orm import Session, sessionmaker
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from test_trade import ITEM, REALM, seed
from test_travel import ApiFixture

from app.content.loader import ContentIndex
from app.engine.order_book import seller_tax
from app.main import app
from app.models import (
    Character,
    Currency,
    GoldLedger,
    Inventory,
    MarketMatch,
    MarketOrder,
    RealmState,
    RealmTag,
)
from app.services.order_book import (
    cancel_order,
    collect_order,
    create_order,
    prepare_market,
)
from app.services.realms import push_realm_tag


def market_content() -> ContentIndex:
    """Grant synthetic market access independently of production content balance."""
    nodes = {
        n.id: n.model_copy(update={"inherent_tags": (*n.inherent_tags, "access.fake")})
        for n in CONTENT.development_nodes
    }
    return replace(CONTENT, _nodes_by_id=MappingProxyType(nodes))


def place(
    session: Session,
    character: Character,
    side: Literal["buy", "sell"],
    quantity: int,
    price: int,
    seconds: int = 0,
    content: ContentIndex | None = None,
) -> tuple[MarketOrder, list[MarketMatch]]:
    """Use the same transaction preparation as the HTTP mutation."""
    content = content or market_content()
    now = NOW + timedelta(seconds=seconds)
    locked_realm_ids = prepare_market(session, character, now, content)
    result = create_order(
        session, character, side, ITEM, quantity, price, now, content, locked_realm_ids
    )
    session.commit()
    return result


def test_price_time_maker_price_refund_and_partial_fills(
    realm_session: Session,
) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    realm_session.commit()
    expensive, _ = place(realm_session, seller, "sell", 2, 9)
    first, _ = place(realm_session, seller, "sell", 2, 7, 1)
    second, _ = place(realm_session, seller, "sell", 3, 7, 2)
    before = realm_session.get(Currency, seller.id)
    assert before is not None
    seller_gold = before.gold
    order, matches = place(realm_session, buyer, "buy", 4, 10, 3)
    assert [(m.maker_order_id, m.quantity, m.unit_price) for m in matches] == [
        (first.id, 2, 7),
        (second.id, 2, 7),
    ]
    assert (
        order.fill_items,
        order.fill_gold,
        order.escrow_gold_remaining,
        order.status,
    ) == (4, 12, 0, "collectable")
    assert first.status == "collectable" and first.fill_gold == 13
    assert second.status == "open" and second.quantity_remaining == 1
    assert expensive.quantity_remaining == 2
    assert realm_session.get(Currency, seller.id).gold == seller_gold  # type: ignore[union-attr]
    assert realm_session.get(Currency, buyer.id).gold == 960  # type: ignore[union-attr]
    assert realm_session.get(Inventory, (buyer.id, ITEM)).quantity == 50  # type: ignore[union-attr]
    # Early collection leaves the unfilled remainder on the book.
    prepare_market(realm_session, seller, NOW + timedelta(seconds=4), market_content())
    assert collect_order(realm_session, seller, second, NOW, market_content()) == (
        0,
        13,
    )
    assert second.status == "open" and second.quantity_remaining == 1
    realm_session.commit()


def test_sell_taker_sweeps_highest_bids_at_maker_price(realm_session: Session) -> None:
    buyer, _ = seed(realm_session)
    seller, _ = seed(realm_session)
    realm_session.commit()
    low, _ = place(realm_session, buyer, "buy", 2, 5)
    high, _ = place(realm_session, buyer, "buy", 2, 8, 1)
    order, matches = place(realm_session, seller, "sell", 5, 4, 2)
    assert [(m.maker_order_id, m.unit_price) for m in matches] == [
        (high.id, 8),
        (low.id, 5),
    ]
    assert (order.quantity_remaining, order.fill_gold, order.status) == (1, 24, "open")
    assert high.fill_items == low.fill_items == 2


def test_cancel_remainder_slots_and_capped_collection(realm_session: Session) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    realm_session.commit()
    sale, _ = place(realm_session, seller, "sell", 5, 5)
    buy, _ = place(realm_session, buyer, "buy", 3, 6, 1)
    cancel_order(sale)
    assert (sale.fill_items, sale.fill_gold, sale.status) == (2, 14, "collectable")
    content = market_content().with_overrides(
        items=[CONTENT.item(ITEM).model_copy(update={"stack_limit": 51})]
    )
    assert collect_order(realm_session, buyer, buy, NOW, content) == (1, 3)
    assert buy.status == "collectable" and buy.fill_items == 2
    realm_session.commit()
    # Filled and cancelled slots count, even after partial collection.
    content = replace(content, caps=content.caps.model_copy(update={"order_slots": 1}))
    with pytest.raises(HTTPException) as caught:
        place(realm_session, buyer, "buy", 1, 1, content=content)
    assert isinstance(caught.value.detail, dict)
    assert caught.value.detail["error"]["code"] == "NO_ORDER_SLOT"
    realm_session.rollback()
    prepare_market(realm_session, buyer, NOW, content)
    stack = realm_session.get(Inventory, (buyer.id, ITEM))
    assert stack is not None
    stack.quantity = 48
    assert collect_order(realm_session, buyer, buy, NOW, content) == (2, 0)
    assert buy.status == "closed" and buy.closed_at == NOW
    realm_session.commit()
    assert place(realm_session, buyer, "buy", 1, 1, content=content)[0].status == "open"
    # Unfilled buy gold is refunded to the slot, never directly to the wallet.
    pending, _ = place(realm_session, seller, "buy", 2, 1)
    wallet = realm_session.get(Currency, seller.id)
    assert wallet is not None
    balance = wallet.gold
    cancel_order(pending)
    assert pending.fill_gold == 2 and pending.escrow_gold_remaining == 0
    assert wallet.gold == balance


def test_tax_uses_sell_creation_realm_and_ledgers_burn(realm_session: Session) -> None:
    seller, origin = seed(realm_session)
    buyer, _ = seed(realm_session)
    other = RealmState(
        id="realm.test_other",
        template_id=REALM,
        current_node_id="node.verdant_t1",
        last_tick_at=NOW,
    )
    realm_session.add(other)
    realm_session.flush()
    buyer.current_realm_id = other.id
    realm_session.commit()
    content = market_content()
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "market": content.economy.market.model_copy(
                    update={"tax_pct": 10, "tax_burn_pct": 50}
                )
            }
        ),
    )
    sale, _ = place(realm_session, seller, "sell", 2, 11, content=content)
    seller.current_realm_id = other.id
    realm_session.commit()
    original = origin.treasury
    other_gold = other.treasury
    _, matches = place(realm_session, buyer, "buy", 2, 12, content=content)
    match = matches[0]
    assert (match.tax_gold, match.burned_gold, match.tax_realm_id) == (3, 1, origin.id)
    assert origin.treasury == original + 2 and other.treasury == other_gold
    assert sale.fill_gold == 19
    assert (
        realm_session.scalar(
            select(GoldLedger.amount).where(GoldLedger.cause == "tax_burn")
        )
        == -1
    )


def test_two_takers_race_one_resting_order(realm_session: Session) -> None:
    """Actual separate transactions contend on both SQLite and PostgreSQL."""
    seller, _ = seed(realm_session)
    buyers = [seed(realm_session)[0] for _ in range(2)]
    realm_session.commit()
    sale, _ = place(realm_session, seller, "sell", 1, 7)
    buyer_ids = [b.id for b in buyers]
    factory = sessionmaker(bind=realm_session.get_bind(), expire_on_commit=False)
    barrier = Barrier(2)

    def take(character_id: uuid.UUID) -> int:
        with factory() as session:
            character = session.get(Character, character_id)
            assert character is not None
            barrier.wait(timeout=10)
            _, matches = place(session, character, "buy", 1, 8, 1)
            return len(matches)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(take, cid) for cid in buyer_ids]
        assert sorted(f.result(timeout=20) for f in futures) == [0, 1]
    realm_session.expire_all()
    assert sale.quantity_remaining == 0
    assert realm_session.scalar(select(func.sum(MarketMatch.quantity))) == 1
    assert realm_session.scalar(select(func.sum(MarketOrder.fill_items))) == 1
    assert (
        realm_session.scalar(select(func.sum(MarketOrder.escrow_gold_remaining))) == 8
    )


@pytest.mark.anyio
async def test_api_access_cancel_visibility_validation_and_ownership(
    estate_client: ApiFixture,
) -> None:
    client, factory, headers, _ = estate_client
    unauthenticated = await client.get(f"/market/book/{ITEM}")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "UNAUTHORIZED"
    body = {"side": "buy", "item_id": ITEM, "quantity": 2, "unit_price": 3}
    denied = await client.post("/market/orders", headers=headers, json=body)
    assert denied.json()["error"]["code"] == "NO_MARKET_ACCESS"
    app.state.content = market_content()
    result = await client.post("/market/orders", headers=headers, json=body)
    assert result.status_code == 201, result.text
    order_id = result.json()["order"]["id"]
    app.state.content = CONTENT
    assert (await client.get("/market/orders/me", headers=headers)).json()["orders"][0][
        "id"
    ] == order_id
    book = await client.get(f"/market/book/{ITEM}?depth=1", headers=headers)
    assert book.json()["buy"] == [{"unit_price": 3, "quantity": 2}]
    assert all(type(value) is int for value in book.json()["buy"][0].values())
    denied = await client.post(f"/market/orders/{order_id}/collect", headers=headers)
    assert denied.json()["error"]["code"] == "NO_MARKET_ACCESS"
    cancelled = await client.post(f"/market/orders/{order_id}/cancel", headers=headers)
    assert cancelled.json()["order"]["fill_gold"] == 6
    with factory() as session:
        assert session.scalar(select(Currency.gold)) == 94
    app.state.content = market_content()
    collected = await client.post(f"/market/orders/{order_id}/collect", headers=headers)
    assert collected.json()["collected"] == {"items": 0, "gold": 6}
    assert collected.json()["order"]["status"] == "closed"
    for values in (
        {"quantity": 0},
        {"unit_price": -1},
        {"quantity": True},
        {"quantity": 2**63 - 1, "unit_price": 2},
    ):
        result = await client.post(
            "/market/orders", headers=headers, json={**body, **values}
        )
        assert result.status_code == 422
    unknown = await client.post(
        f"/market/orders/{uuid.uuid4()}/cancel", headers=headers
    )
    assert unknown.status_code == 404
    with factory() as session:
        foreign, _ = seed(session)
        session.commit()
        foreign_order, _ = place(session, foreign, "sell", 1, 9)
        foreign_id = foreign_order.id
    for action in ("collect", "cancel"):
        result = await client.post(
            f"/market/orders/{foreign_id}/{action}", headers=headers
        )
        assert result.status_code == 404
    own = await client.get("/market/orders/me", headers=headers)
    assert [o["id"] for o in own.json()["orders"]] == [order_id]
    poor = await client.post(
        "/market/orders", headers=headers, json={**body, "quantity": 200}
    )
    assert poor.json()["error"]["code"] == "INSUFFICIENT_GOLD"
    book = await client.get(f"/market/book/{ITEM}", headers=headers)
    assert book.json()["buy"] == []
    assert book.json()["sell"] == [{"unit_price": 9, "quantity": 1}]
    assert all(type(value) is int for value in book.json()["sell"][0].values())
    app.state.content = market_content().with_overrides(
        items=[CONTENT.item(ITEM).model_copy(update={"instanced": True})]
    )
    result = await client.post("/market/orders", headers=headers, json=body)
    assert result.json()["error"]["code"] == "INSTANCED_ITEM"


def test_inventory_slot_cap_never_blocks_a_fill(realm_session: Session) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    stack = realm_session.get(Inventory, (buyer.id, ITEM))
    assert stack is not None
    realm_session.delete(stack)
    realm_session.add(
        Inventory(character_id=buyer.id, item_id="item.fake_bullion", quantity=1)
    )
    realm_session.commit()
    content = market_content()
    content = replace(
        content, caps=content.caps.model_copy(update={"inventory_slots": 1})
    )
    place(realm_session, seller, "sell", 2, 3, content=content)
    order, matches = place(realm_session, buyer, "buy", 2, 4, content=content)
    assert len(matches) == 1 and order.fill_items == 2
    assert collect_order(realm_session, buyer, order, NOW, content) == (0, 2)
    assert order.status == "collectable" and order.fill_items == 2
    blocker = realm_session.get(Inventory, (buyer.id, "item.fake_bullion"))
    assert blocker is not None
    realm_session.delete(blocker)
    realm_session.flush()
    assert collect_order(realm_session, buyer, order, NOW, content) == (2, 0)
    assert order.status == "closed"


@pytest.mark.parametrize("stage", ["fed", "strained", "faltering", "failing"])
def test_market_access_survives_weak_stages_until_shed(
    realm_session: Session, stage: str
) -> None:
    character, realm = seed(realm_session)
    realm.decay_stage = stage
    push_realm_tag(realm_session, realm, "access.fake", NOW)
    realm_session.commit()
    order, _ = place(realm_session, character, "buy", 1, 1, content=CONTENT)
    tag = realm_session.get(RealmTag, (realm.id, "access.fake"))
    assert tag is not None
    realm_session.delete(tag)
    realm_session.commit()
    # Cancelling remains possible after the access tag has been shed.
    cancel_order(order)
    with pytest.raises(HTTPException) as caught:
        collect_order(realm_session, character, order, NOW, CONTENT)
    assert isinstance(caught.value.detail, dict)
    assert caught.value.detail["error"]["code"] == "NO_MARKET_ACCESS"


@pytest.mark.parametrize(
    "tax_pct,burn_pct,gross,expected",
    [
        (5, 0, 1, (1, 0)),
        (10, 50, 21, (3, 1)),
        (0.1, 100, 1000, (1, 1)),
        (100, 100, 9, (9, 9)),
        (0, 0, 17, (0, 0)),
    ],
)
def test_tax_rounding(
    tax_pct: float, burn_pct: float, gross: int, expected: tuple[int, int]
) -> None:
    config = CONTENT.economy.market.model_copy(
        update={"tax_pct": tax_pct, "tax_burn_pct": burn_pct}
    )
    assert seller_tax(gross, config) == expected


@pytest.mark.parametrize("tax_pct,price", [(5, 1), (100, 7)])
@pytest.mark.parametrize("maker_side", ["buy", "sell"])
def test_empty_sell_fill_closes_and_frees_slot(
    realm_session: Session, tax_pct: float, price: int, maker_side: str
) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    realm_session.commit()
    content = market_content()
    content = replace(
        content,
        caps=content.caps.model_copy(update={"order_slots": 1}),
        economy=content.economy.model_copy(
            update={
                "market": content.economy.market.model_copy(update={"tax_pct": tax_pct})
            }
        ),
    )
    if maker_side == "sell":
        sale, _ = place(realm_session, seller, "sell", 1, price, content=content)
        place(realm_session, buyer, "buy", 1, price, 1, content)
    else:
        place(realm_session, buyer, "buy", 1, price, content=content)
        sale, _ = place(realm_session, seller, "sell", 1, price, 1, content)
    assert sale.quantity_remaining == sale.fill_items == sale.fill_gold == 0
    assert sale.status == "closed" and sale.closed_at == NOW + timedelta(seconds=1)
    assert realm_session.scalar(select(func.count()).select_from(MarketMatch)) == 1
    # The insert/commit checks the existing closed-slot constraints, and the
    # single slot is reusable without an access-gated collection request.
    assert (
        place(realm_session, seller, "sell", 1, price + 1, 2, content)[0].status
        == "open"
    )


@pytest.mark.parametrize("maker_side", ["buy", "sell"])
@pytest.mark.parametrize("expiry_offset", [-1, 0, 1])
def test_sweep_ignores_expired_orders(
    realm_session: Session, maker_side: Literal["buy", "sell"], expiry_offset: int
) -> None:
    maker_character, _ = seed(realm_session)
    taker_character, _ = seed(realm_session)
    realm_session.commit()
    maker, _ = place(realm_session, maker_character, maker_side, 2, 3)
    maker.expires_at = NOW + timedelta(seconds=1 + expiry_offset)
    realm_session.commit()
    _, matches = place(
        realm_session,
        taker_character,
        "sell" if maker_side == "buy" else "buy",
        1,
        3,
        1,
    )
    assert len(matches) == (1 if expiry_offset > 0 else 0)
    assert maker.quantity_remaining == (1 if expiry_offset > 0 else 2)
    assert maker.status == "open"  # The lifecycle job belongs to Prompt 24.
    if expiry_offset <= 0:
        assert maker.fill_items == maker.fill_gold == 0
        assert maker.escrow_gold_remaining == (6 if maker_side == "buy" else 0)


@pytest.mark.anyio
@pytest.mark.parametrize("expiry_offset", [-1, 0, 1])
async def test_book_ignores_expired_orders(
    estate_client: ApiFixture, expiry_offset: int
) -> None:
    client, factory, headers, clock = estate_client
    with factory() as session:
        buyer, _ = seed(session)
        seller, _ = seed(session)
        session.commit()
        bid, _ = place(session, buyer, "buy", 2, 3)
        ask, _ = place(session, seller, "sell", 2, 9)
        bid.expires_at = ask.expires_at = clock["now"] + timedelta(
            seconds=expiry_offset
        )
        session.commit()
    result = await client.get(f"/market/book/{ITEM}", headers=headers)
    assert result.status_code == 200
    assert result.json()["buy"] == (
        [{"unit_price": 3, "quantity": 2}] if expiry_offset > 0 else []
    )
    assert result.json()["sell"] == (
        [{"unit_price": 9, "quantity": 2}] if expiry_offset > 0 else []
    )
    with factory() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(MarketOrder)
                .where(MarketOrder.status == "open")
            )
            == 2
        )


def test_market_locks_character_before_enumerating_realms(
    realm_session: Session,
) -> None:
    character, _ = seed(realm_session)
    realm_session.commit()
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
        prepare_market(realm_session, character, NOW, market_content())
    finally:
        event.remove(engine, "before_cursor_execute", record)
    character_lock = next(
        i for i, sql in enumerate(statements) if "FROM characters" in sql
    )
    realm_enumeration = next(
        i
        for i, sql in enumerate(statements)
        if sql.strip() == "SELECT realm_state.id \nFROM realm_state"
    )
    assert character_lock < realm_enumeration


def test_market_retries_when_tax_recipient_is_not_locked(
    realm_session: Session,
) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    realm_session.commit()
    sale, _ = place(realm_session, seller, "sell", 1, 3)
    content = market_content()
    locked = prepare_market(realm_session, buyer, NOW, content)
    with pytest.raises(HTTPException) as caught:
        create_order(
            realm_session,
            buyer,
            "buy",
            ITEM,
            1,
            3,
            NOW,
            content,
            locked - {sale.realm_id},
        )
    assert isinstance(caught.value.detail, dict)
    assert caught.value.detail["error"]["code"] == "MARKET_RETRY"
    realm_session.rollback()
    assert sale.status == "open" and sale.quantity_remaining == 1
    wallet = realm_session.get(Currency, buyer.id)
    assert wallet is not None and wallet.gold == 1000
    assert realm_session.scalar(select(func.count()).select_from(MarketMatch)) == 0


def test_postgres_market_retries_realm_created_after_enumeration(
    realm_session: Session,
) -> None:
    """A newly committed lower-id tax realm cannot be locked after the estate."""
    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("Only PostgreSQL permits a second writer after market preparation")
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    realm_session.commit()
    seller_id = seller.id
    factory = sessionmaker(bind=realm_session.get_bind(), expire_on_commit=False)
    inserted = False
    late_id = "realm.000_late"

    def insert_late_realm(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        nonlocal inserted
        if inserted or statement.strip() != "SELECT realm_state.id \nFROM realm_state":
            return
        inserted = True
        # The SELECT snapshot is already fixed, but no realm locks have been
        # taken yet. Commit another seller's new realm and order in this gap.
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            session.add(
                RealmState(
                    id=late_id,
                    template_id=REALM,
                    current_node_id="node.verdant_t1",
                    last_tick_at=NOW,
                )
            )
            other_seller = session.get(Character, seller_id)
            assert other_seller is not None
            other_seller.current_realm_id = late_id
            place(session, other_seller, "sell", 1, 3)

    engine = realm_session.get_bind()
    event.listen(engine, "after_cursor_execute", insert_late_realm)
    try:
        locked = prepare_market(realm_session, buyer, NOW, market_content())
        assert inserted and late_id not in locked
        with pytest.raises(HTTPException) as caught:
            create_order(
                realm_session, buyer, "buy", ITEM, 1, 3, NOW, market_content(), locked
            )
        assert isinstance(caught.value.detail, dict)
        assert caught.value.detail["error"]["code"] == "MARKET_RETRY"
        realm_session.rollback()
    finally:
        event.remove(engine, "after_cursor_execute", insert_late_realm)
    assert realm_session.scalar(select(func.count()).select_from(MarketMatch)) == 0
    # A fresh preparation sees the new realm and locks it in the right order.
    assert len(place(realm_session, buyer, "buy", 1, 3)[1]) == 1
    recipient = realm_session.get(RealmState, late_id)
    assert recipient is not None and recipient.treasury == 1
