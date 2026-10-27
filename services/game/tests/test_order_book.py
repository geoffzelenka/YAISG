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
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from test_trade import ITEM, REALM, seed
from test_travel import ApiFixture

from app.content.loader import ContentIndex
from app.main import app
from app.models import (
    Character,
    Currency,
    GoldLedger,
    Inventory,
    MarketMatch,
    MarketOrder,
    RealmState,
)
from app.services.order_book import (
    cancel_order,
    collect_order,
    create_order,
    prepare_market,
)


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
    prepare_market(session, character, now, content)
    result = create_order(session, character, side, ITEM, quantity, price, now, content)
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
    from app.models import RealmTag
    from app.services.realms import push_realm_tag

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
    from app.engine.order_book import seller_tax

    config = CONTENT.economy.market.model_copy(
        update={"tax_pct": tax_pct, "tax_burn_pct": burn_pct}
    )
    assert seller_tax(gross, config) == expected
