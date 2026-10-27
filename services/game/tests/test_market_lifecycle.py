"""Expiry preserves holdings; retention leaves durable private history intact."""

import base64
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from typing import Literal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_order_book import market_content, place
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from test_trade import ITEM, seed
from test_travel import ApiFixture

from app.main import app
from app.models import Character, Currency, Inventory, MarketMatch, MarketOrder
from app.services.market_lifecycle import run_market_lifecycle
from app.services.order_book import (
    cancel_order,
    collect_order,
    owned_order,
    prepare_market,
)


def test_expiry_preserves_escrow_and_purge_only_old_closed(
    realm_session: Session,
) -> None:
    character, _ = seed(realm_session)
    other, _ = seed(realm_session)
    realm_session.commit()
    sale, _ = place(realm_session, character, "sell", 5, 10)
    filled, _ = place(realm_session, other, "buy", 2, 10)
    buy, _ = place(realm_session, other, "buy", 2, 1)
    fresh, _ = place(realm_session, other, "buy", 1, 1, seconds=1)
    closed, _ = place(realm_session, character, "buy", 1, 1)
    cancel_order(closed)
    collect_order(realm_session, character, closed, NOW, market_content())
    closed_id = closed.id
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    expiry = NOW + timedelta(days=14)
    assert run_market_lifecycle(factory, market_content(), expiry)
    realm_session.expire_all()
    assert (sale.status, sale.fill_items, sale.quantity_remaining) == (
        "collectable",
        3,
        0,
    )
    assert (buy.status, buy.fill_gold, buy.escrow_gold_remaining) == (
        "collectable",
        2,
        0,
    )
    assert sale.fill_gold == 19
    assert filled.status == "collectable" and filled.fill_items == 2
    assert fresh.status == "open"
    assert realm_session.get(MarketOrder, closed_id) is not None
    realm_session.commit()
    # Strictly past retention, rather than at its boundary.
    boundary = NOW + timedelta(days=market_content().economy.market.retention_days)
    assert run_market_lifecycle(factory, market_content(), boundary)
    realm_session.expire_all()
    assert realm_session.get(MarketOrder, closed_id) is not None
    realm_session.commit()
    assert run_market_lifecycle(
        factory, market_content(), boundary + timedelta(seconds=1)
    )
    realm_session.expire_all()
    assert realm_session.get(MarketOrder, closed_id) is None
    assert realm_session.get(MarketOrder, sale.id) is not None
    assert realm_session.get(MarketOrder, buy.id) is not None
    realm_session.commit()
    assert run_market_lifecycle(
        factory, market_content(), boundary + timedelta(seconds=1)
    )


@pytest.mark.anyio
async def test_history_private_remote_and_durable_after_purge(
    estate_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, headers, clock = estate_client
    monkeypatch.setattr(app.state, "content", market_content())
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        session.add(Inventory(character_id=character.id, item_id=ITEM, quantity=10))
        other, _ = seed(session)
        third, _ = seed(session)
        session.commit()
        # Cover both participant predicates and exclude unrelated executions.
        place(session, character, "buy", 1, 5)
        _, first = place(session, other, "sell", 1, 5)
        place(session, other, "buy", 1, 5, seconds=1)
        _, second = place(session, character, "sell", 1, 5, seconds=1)
        place(session, other, "buy", 1, 5, seconds=2)
        place(session, third, "sell", 1, 5, seconds=2)
        place(session, character, "buy", 1, 5, seconds=3)
        _, self_match = place(session, character, "sell", 1, 5, seconds=3)
        expected = [str(self_match[0].id), str(second[0].id), str(first[0].id)]
        for order in session.scalars(select(MarketOrder)):
            owner = session.get(Character, order.character_id)
            assert owner is not None
            collect_order(session, owner, order, NOW, market_content())
        session.commit()
    assert run_market_lifecycle(factory, market_content(), NOW + timedelta(days=31))
    with factory() as session:
        assert not list(session.scalars(select(MarketOrder)))
        assert len(list(session.scalars(select(MarketMatch)))) == 4
    # No market access is required for history.
    monkeypatch.setattr(app.state, "content", CONTENT)
    response = await client.get("/market/history/me", headers=headers)
    assert response.status_code == 200
    matches = response.json()["matches"]
    assert [row["id"] for row in matches] == expected
    assert all(row["item_id"] == ITEM and row["unit_price"] == 5 for row in matches)
    assert [row["side"] for row in matches] == ["buy", "sell", "buy"]
    assert all(
        "buyer_character_id" not in row and "seller_character_id" not in row
        for row in matches
    )
    assert response.json()["next_cursor"] is None
    assert (await client.get("/market/history/me")).status_code == 401


def race_slot_mutation(
    session: Session, mutation: Literal["collect", "cancel"]
) -> None:
    """Race a real partial fill's mutation against its scheduled expiry."""
    buyer, _ = seed(session)
    seller, _ = seed(session)
    session.commit()
    sale, _ = place(session, seller, "sell", 1 if mutation == "collect" else 3, 7)
    buy, _ = place(
        session, buyer, "buy", 2 if mutation == "collect" else 1, 10, seconds=1
    )
    order = buy if mutation == "collect" else sale
    character_id = order.character_id
    order_id = order.id
    session.commit()
    factory = sessionmaker(bind=session.get_bind())
    barrier = Barrier(2)
    now = NOW + timedelta(days=14, seconds=1)

    def expire() -> None:
        barrier.wait(timeout=5)
        assert run_market_lifecycle(factory, market_content(), now)

    def mutate() -> None:
        barrier.wait(timeout=5)
        with factory() as worker:
            owner = worker.get(Character, character_id)
            assert owner is not None
            prepare_market(worker, owner, NOW, market_content())
            slot = owned_order(worker, owner, order_id)
            if mutation == "collect":
                items, gold = collect_order(worker, owner, slot, NOW, market_content())
                # Price improvement is available before expiry, so either
                # serialization must move both goods and gold exactly once.
                assert items == 1 and gold in (3, 13)
            else:
                cancel_order(slot)
            worker.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(expire), pool.submit(mutate)]
        for future in futures:
            future.result(timeout=15)
    with factory() as worker:
        slot = worker.get(MarketOrder, order_id)
        wallet = worker.get(Currency, character_id)
        stack = worker.get(Inventory, (character_id, ITEM))
        assert slot is not None and wallet is not None and stack is not None
        assert slot.escrow_gold_remaining == slot.quantity_remaining == 0
        if mutation == "collect":
            assert wallet.gold + slot.fill_gold == 993
            assert stack.quantity + slot.fill_items == 51
            assert slot.status in ("collectable", "closed")
        else:
            assert (slot.status, slot.fill_items, slot.fill_gold) == (
                "collectable",
                2,
                6,
            )
            assert (stack.quantity + slot.fill_items, wallet.gold) == (49, 1000)
            owner = worker.get(Character, character_id)
            assert owner is not None
            assert collect_order(worker, owner, slot, NOW, market_content()) == (2, 6)
            assert (wallet.gold, stack.quantity, slot.status) == (1006, 49, "closed")
            worker.commit()


def test_lifecycle_races_collection_without_losing_escrow(
    realm_session: Session,
) -> None:
    """Partial fills and price improvements survive collection racing expiry."""
    race_slot_mutation(realm_session, "collect")


def test_lifecycle_races_cancellation_without_duplicate_refund(
    realm_session: Session,
) -> None:
    """Partial fills and sell remainders survive cancellation racing expiry."""
    race_slot_mutation(realm_session, "cancel")


def test_postgres_lifecycle_advisory_exclusion(realm_session: Session) -> None:
    """A second process skips while the transaction-scoped job guard is held."""
    from sqlalchemy import text

    from app.services.market_lifecycle import MARKET_LIFECYCLE_LOCK

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("PostgreSQL advisory locks")
    realm_session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": MARKET_LIFECYCLE_LOCK}
    )
    factory = sessionmaker(bind=realm_session.get_bind())
    assert not run_market_lifecycle(factory, market_content(), NOW)
    realm_session.commit()
    assert run_market_lifecycle(factory, market_content(), NOW)


def test_scheduled_lifecycle_callback_and_failure_logging(
    realm_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """The registered job invokes the transactional driver and reports failures."""
    from unittest.mock import patch

    from app.services.scheduler import start_scheduler

    factory = sessionmaker(bind=realm_session.get_bind())
    with (
        patch("apscheduler.schedulers.background.BackgroundScheduler") as constructor,
        patch("app.services.scheduler.run_market_lifecycle") as run,
    ):
        start_scheduler(factory, market_content())
        job = next(
            call.args[0]
            for call in constructor.return_value.add_job.call_args_list
            if call.kwargs["id"] == "market_lifecycle"
        )
        job()
        assert run.call_args.args[:2] == (factory, market_content())
        run.side_effect = RuntimeError("injected lifecycle failure")
        job()
        assert "Market lifecycle failed" in caplog.text
        assert "injected lifecycle failure" in caplog.text


def test_failed_expiry_rolls_back_the_whole_pass(
    realm_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exception after mutation cannot leave half an expiry pass committed."""
    from app.services import market_lifecycle

    character, _ = seed(realm_session)
    realm_session.commit()
    order, _ = place(realm_session, character, "buy", 2, 3)
    order_id = order.id
    realm_session.commit()

    def fail_after_cancel(slot: MarketOrder) -> None:
        cancel_order(slot)
        raise RuntimeError("injected expiry failure")

    monkeypatch.setattr(market_lifecycle, "cancel_order", fail_after_cancel)
    factory = sessionmaker(bind=realm_session.get_bind())
    with pytest.raises(RuntimeError, match="injected expiry failure"):
        run_market_lifecycle(factory, market_content(), NOW + timedelta(days=14))
    realm_session.expire_all()
    slot = realm_session.get(MarketOrder, order_id)
    assert slot is not None
    assert (slot.status, slot.escrow_gold_remaining, slot.fill_gold) == ("open", 6, 0)


@pytest.mark.anyio
async def test_history_cursor_pagination_ties_limits_and_validation(
    estate_client: ApiFixture,
) -> None:
    """Keyset pages neither skip nor repeat timestamp ties and stay bounded."""
    client, factory, headers, _ = estate_client
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        other = uuid.UUID(int=10000)
        matches = []
        for index in range(203):
            identifier = uuid.UUID(int=index + 1)
            matches.append(
                MarketMatch(
                    id=identifier,
                    maker_order_id=uuid.uuid4(),
                    taker_order_id=uuid.uuid4(),
                    buyer_character_id=character.id if index % 2 else other,
                    seller_character_id=other if index % 2 else character.id,
                    item_id=ITEM,
                    quantity=1,
                    unit_price=5,
                    tax_gold=0,
                    burned_gold=0,
                    tax_realm_id="realm.verdant_vale",
                    matched_at=NOW if index > 0 else NOW - timedelta(seconds=1),
                )
            )
        session.add_all(matches)
        session.commit()
    default = await client.get("/market/history/me", headers=headers)
    assert default.status_code == 200 and len(default.json()["matches"]) == 50
    maximum = await client.get(
        "/market/history/me", headers=headers, params={"limit": 200}
    )
    assert maximum.status_code == 200 and len(maximum.json()["matches"]) == 200
    assert maximum.json()["next_cursor"] is not None
    expected = [str(uuid.UUID(int=i)) for i in range(203, 0, -1)]
    seen: list[str] = []
    params: dict[str, str | int] = {"limit": 17}
    while True:
        response = await client.get(
            "/market/history/me", headers=headers, params=params
        )
        assert response.status_code == 200, response.text
        data = response.json()
        seen.extend(row["id"] for row in data["matches"])
        for row in data["matches"]:
            assert row["side"] in ("buy", "sell")
            assert "buyer_character_id" not in row and "seller_character_id" not in row
        if data["next_cursor"] is None:
            break
        params["before"] = data["next_cursor"]
        if len(seen) == 17:
            # A new execution arriving between requests must not shift pages.
            with factory() as session:
                session.add(
                    MarketMatch(
                        id=uuid.UUID(int=204),
                        maker_order_id=uuid.uuid4(),
                        taker_order_id=uuid.uuid4(),
                        buyer_character_id=character.id,
                        seller_character_id=other,
                        item_id=ITEM,
                        quantity=1,
                        unit_price=5,
                        tax_gold=0,
                        burned_gold=0,
                        tax_realm_id="realm.verdant_vale",
                        matched_at=NOW + timedelta(seconds=1),
                    )
                )
                session.commit()
    assert seen == expected
    fresh = await client.get("/market/history/me", headers=headers)
    assert fresh.json()["matches"][0]["id"] == str(uuid.UUID(int=204))
    for invalid in (0, -1, 201):
        result = await client.get(
            "/market/history/me", headers=headers, params={"limit": invalid}
        )
        assert result.status_code == 422
    naive_cursor = base64.urlsafe_b64encode(
        f"2026-01-01T00:00:00|{uuid.UUID(int=1)}".encode()
    ).decode()
    overflowing_cursor = base64.urlsafe_b64encode(
        f"0001-01-01T00:00:00+14:00|{uuid.UUID(int=1)}".encode()
    ).decode()
    for invalid_cursor in (
        "not-a-cursor",
        "",
        "a" * 257,
        naive_cursor,
        overflowing_cursor,
    ):
        result = await client.get(
            "/market/history/me", headers=headers, params={"before": invalid_cursor}
        )
        assert result.status_code == 422
    result = await client.get(
        "/market/history/me", headers=headers, params={"before": "not-a-cursor"}
    )
    assert result.json()["error"]["code"] == "INVALID_CURSOR"


@pytest.mark.anyio
async def test_immediate_fills_return_caller_side_without_counterparty_identity(
    estate_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Buyer and seller projections reveal side and execution, never participant ids."""
    client, factory, headers, _ = estate_client
    monkeypatch.setattr(app.state, "content", market_content())
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        session.add(Inventory(character_id=character.id, item_id=ITEM, quantity=10))
        other, _ = seed(session)
        session.commit()
        place(session, other, "sell", 1, 5)
    response = await client.post(
        "/market/orders",
        headers=headers,
        json={
            "side": "buy",
            "item_id": ITEM,
            "quantity": 1,
            "unit_price": 5,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["fills"][0]["side"] == "buy"
    assert str(other.id) not in response.text
    with factory() as session:
        resting_buyer = session.get(Character, other.id)
        assert resting_buyer is not None
        place(session, resting_buyer, "buy", 1, 5)
    response = await client.post(
        "/market/orders",
        headers=headers,
        json={
            "side": "sell",
            "item_id": ITEM,
            "quantity": 1,
            "unit_price": 5,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["fills"][0]["side"] == "sell"
    assert str(other.id) not in response.text
    assert all(
        "buyer_character_id" not in fill and "seller_character_id" not in fill
        for fill in response.json()["fills"]
    )
