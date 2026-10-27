"""Expiry preserves holdings; retention leaves durable private history intact."""

from datetime import timedelta

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
from app.models import Character, Inventory, MarketMatch, MarketOrder
from app.services.market_lifecycle import run_market_lifecycle
from app.services.order_book import cancel_order, collect_order


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
    assert (await client.get("/market/history/me")).status_code == 401


def test_lifecycle_races_collection_without_losing_escrow(
    realm_session: Session,
) -> None:
    """Independent sessions serialize expiry and collection on either CI engine."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from app.models import Currency
    from app.services.order_book import owned_order, prepare_market

    character, _ = seed(realm_session)
    realm_session.commit()
    order, _ = place(realm_session, character, "buy", 2, 3)
    order_id, character_id = order.id, character.id
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    barrier = Barrier(2)
    now = NOW + timedelta(days=14)

    def expire() -> None:
        barrier.wait(timeout=5)
        assert run_market_lifecycle(factory, market_content(), now)

    def collect() -> None:
        barrier.wait(timeout=5)
        with factory() as session:
            owner = session.get(Character, character_id)
            assert owner is not None
            # Resolve at creation time to keep this race about slots alone.
            prepare_market(session, owner, NOW, market_content())
            slot = owned_order(session, owner, order_id)
            collect_order(session, owner, slot, NOW, market_content())
            session.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(expire), pool.submit(collect)]
        for future in futures:
            future.result(timeout=15)
    with factory() as session:
        slot = session.get(MarketOrder, order_id)
        wallet = session.get(Currency, character_id)
        assert slot is not None and wallet is not None
        assert slot.status in ("collectable", "closed")
        assert slot.escrow_gold_remaining == slot.quantity_remaining == 0
        assert wallet.gold + slot.fill_gold == 1000


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
