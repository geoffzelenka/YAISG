"""Key listing custody, lifecycle, settlement and concurrent buyouts."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier, Event
from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.engine import Connection, ExecutionContext
from sqlalchemy.orm import Session, sessionmaker
from test_keys import ApiFixture, discover_api, exploration_content, key_state
from test_keys import action_client as action_client
from test_keys import anyio_backend as anyio_backend
from test_order_book import market_content
from test_realms import NOW
from test_realms import realm_session as realm_session
from test_trade import seed

from app.content.loader import ContentIndex
from app.content.schemas import Drop
from app.main import app
from app.models import (
    Character,
    Currency,
    GoldLedger,
    ItemInstance,
    KeyListing,
    RealmState,
)
from app.services.actions import lock_character_and_load_action
from app.services.key_market import list_key, transfer_listing
from app.services.realm_ticks import (
    complete_tick_transition,
    load_context,
    persist_context,
)
from app.services.realms import finalize_realm, start_transition


def wallet(session: Session, character_id: uuid.UUID) -> int:
    """Read a required wallet for settlement assertions."""
    row = session.get(Currency, character_id)
    assert row is not None
    return row.gold


def make_key(session: Session, owner: Character, content: ContentIndex) -> ItemInstance:
    """Persist a rolled unused key with test provenance."""
    rolled = key_state(content)
    key = ItemInstance(
        template_id=rolled.template_id,
        holder_character_id=owner.id,
        discovered_by_character_id=owner.id,
        discovered_by_name=owner.name,
        realm_id=owner.current_realm_id,
        payload=rolled.payload,
        uses_total=rolled.uses_total,
        uses_remaining=rolled.uses_remaining,
        state="active",
        created_at=NOW,
    )
    session.add(key)
    session.flush()
    return key


@pytest.mark.parametrize("unavailable", ["bound", "deprecated", "invalid", "depleted"])
def test_bound_or_deprecated_keys_cannot_be_listed(
    realm_session: Session, unavailable: str
) -> None:
    owner, _ = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, owner, content)
    if unavailable == "bound":
        key.bound_at = NOW
    else:
        key.state = unavailable
    realm_session.commit()
    with pytest.raises(HTTPException) as error:
        list_key(realm_session, owner, key.id, 100, NOW, content)
    assert (
        cast(dict[str, Any], error.value.detail)["error"]["code"] == "KEY_UNAVAILABLE"
    )
    assert key.holder_character_id == owner.id


def test_key_listing_cap_and_cancel_return(realm_session: Session) -> None:
    owner, _ = seed(realm_session)
    content = market_content()
    content = replace(content, caps=content.caps.model_copy(update={"key_listings": 1}))
    first = make_key(realm_session, owner, content)
    second = make_key(realm_session, owner, content)
    realm_session.commit()
    listing = list_key(realm_session, owner, first.id, 100, NOW, content)
    realm_session.commit()
    assert first.holder_character_id is None
    with pytest.raises(HTTPException) as error:
        list_key(realm_session, owner, second.id, 100, NOW, content)
    assert (
        cast(dict[str, Any], error.value.detail)["error"]["code"]
        == "NO_KEY_LISTING_SLOT"
    )
    realm_session.rollback()
    transfer_listing(realm_session, owner, listing.id, "cancel", NOW, content)
    realm_session.commit()
    assert first.holder_character_id == owner.id
    assert listing.status == "cancelled"
    old_id = listing.id
    relisted = list_key(realm_session, owner, first.id, 200, NOW, content)
    realm_session.commit()
    assert relisted.id != old_id
    before = wallet(realm_session, owner.id)
    with pytest.raises(HTTPException) as error:
        transfer_listing(realm_session, owner, old_id, "buy", NOW, content)
    assert error.value.status_code == 404
    assert first.holder_character_id is None
    assert wallet(realm_session, owner.id) == before
    assert relisted.status == "open"


def test_key_tax_and_listing_realm_conserve_gold(realm_session: Session) -> None:
    seller, realm = seed(realm_session)
    buyer, _ = seed(realm_session)
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
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, content)
    realm_session.commit()
    seller.current_realm_id = "realm.ashen_reach"
    realm_session.commit()
    before = realm.treasury
    transfer_listing(realm_session, buyer, listing.id, "buy", NOW, content)
    realm_session.commit()
    assert wallet(realm_session, buyer.id) == 900
    assert wallet(realm_session, seller.id) == 1090
    assert realm.treasury == before + 5
    assert (
        realm_session.scalar(
            select(GoldLedger.amount).where(GoldLedger.cause == "tax_burn")
        )
        == -5
    )
    assert key.holder_character_id == buyer.id
    with pytest.raises(HTTPException) as error:
        transfer_listing(realm_session, buyer, listing.id, "buy", NOW, content)
    assert (
        cast(dict[str, Any], error.value.detail)["error"]["code"]
        == "KEY_LISTING_CLOSED"
    )


@pytest.mark.parametrize("operation", ["buy", "cancel"])
def test_buyer_and_cancelling_seller_need_free_slot(
    realm_session: Session, operation: str
) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, content)
    realm_session.commit()
    full = replace(content, caps=content.caps.model_copy(update={"inventory_slots": 1}))
    with pytest.raises(HTTPException) as error:
        transfer_listing(
            realm_session,
            buyer if operation == "buy" else seller,
            listing.id,
            operation,
            NOW,
            full,
        )
    assert cast(dict[str, Any], error.value.detail)["error"]["code"] == "INVENTORY_FULL"
    assert key.holder_character_id is None
    assert listing.status == "open"


@pytest.mark.parametrize("path", ["session", "tick"])
def test_invalidation_returns_listed_keys_even_when_full(
    realm_session: Session, path: str
) -> None:
    seller, realm = seed(realm_session)
    content = market_content()
    content = replace(
        content, caps=content.caps.model_copy(update={"inventory_slots": 1})
    )
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, content)
    realm_session.commit()
    start_transition(realm, realm.current_node_id, "upgrade", NOW, content)
    realm_session.commit()
    assert key.state == "deprecated" and listing.status == "open"
    completion = NOW + timedelta(days=content.economy.transition.duration_days)
    if path == "session":
        finalize_realm(realm_session, realm.id, completion, content)
    else:
        context = load_context(realm_session, realm, None, content)
        complete_tick_transition(context, realm, completion, content)
        persist_context(realm_session, realm, context)
    realm_session.commit()
    assert key.state == "invalid"
    assert key.holder_character_id == seller.id
    assert listing.status == "cancelled"
    cutoff = key.invalidated_at
    start_transition(
        realm,
        realm.current_node_id,
        "upgrade",
        completion,
        content,
    )
    realm_session.commit()
    finalize_realm(
        realm_session,
        realm.id,
        completion + timedelta(days=content.economy.transition.duration_days),
        content,
    )
    assert key.invalidated_at == cutoff


def test_postgres_concurrent_key_buys_transfer_once(realm_session: Session) -> None:
    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    seller, _ = seed(realm_session)
    first, _ = seed(realm_session)
    second, _ = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, content)
    realm_session.commit()
    listing_id, key_id = listing.id, key.id
    factory = sessionmaker(bind=realm_session.get_bind())
    barrier = Barrier(2)

    def buy(character_id: uuid.UUID) -> str:
        with factory() as session:
            buyer = session.get(Character, character_id)
            assert buyer is not None
            barrier.wait(timeout=10)
            try:
                transfer_listing(session, buyer, listing_id, "buy", NOW, content)
                session.commit()
                return "sold"
            except HTTPException as error:
                session.rollback()
                return str(cast(dict[str, Any], error.detail)["error"]["code"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(buy, [first.id, second.id]))
    assert sorted(results) == ["KEY_LISTING_CLOSED", "sold"]
    realm_session.expire_all()
    transferred = realm_session.get(ItemInstance, key_id)
    assert transferred is not None
    assert transferred.holder_character_id in {
        first.id,
        second.id,
    }
    assert wallet(realm_session, seller.id) == 1095
    assert (
        sum(wallet(realm_session, identifier) for identifier in [first.id, second.id])
        == 1900
    )


@pytest.mark.anyio
async def test_key_market_api_browse_filters_deprecation_access_and_ownership(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, clock, headers = action_client
    identifier = await discover_api(action_client, monkeypatch)
    denied = await client.post(
        "/keys/market",
        headers=headers,
        json={"instance_id": identifier, "price_gold": 100},
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "NO_MARKET_ACCESS"
    opponent = app.state.content.combatants[0].model_copy(
        update={
            "drops": (
                Drop(
                    item_id=app.state.content.items[0].id,
                    quantity_min=1,
                    quantity_max=1,
                    chance=1,
                ),
            )
        }
    )
    content = replace(
        app.state.content,
        _nodes_by_id=market_content()._nodes_by_id,
        combatants=(opponent, *app.state.content.combatants[1:]),
    )
    monkeypatch.setattr(app.state, "content", content)
    invalid = await client.post(
        "/keys/market",
        headers=headers,
        json={"instance_id": identifier, "price_gold": True},
    )
    assert invalid.status_code == 422
    response = await client.post(
        "/keys/market",
        headers=headers,
        json={"instance_id": identifier, "price_gold": 100},
    )
    assert response.status_code == 201, response.text
    listing_id = response.json()["id"]
    mismatch = await client.post(
        f"/keys/market/{listing_id}/buy", headers=headers, json={"price_gold": 99}
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "KEY_PRICE_CHANGED"
    invalid_price = await client.post(
        f"/keys/market/{listing_id}/buy", headers=headers, json={"price_gold": True}
    )
    assert invalid_price.status_code == 422
    assert (await client.get("/keys/me", headers=headers)).json()["keys"] == []
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None
        key.state = "deprecated"
        output = key.payload["action"]["outputs"][0]["item_id"]
        session.commit()
    for filters, count in [
        ({}, 1),
        ({"realm_id": "missing"}, 0),
        ({"item_id": output}, 1),
        ({"item_id": "missing"}, 0),
        ({"class": content.item(output).classes[0]}, 1),
        ({"class": "missing"}, 0),
        ({"kind": "gather"}, 1),
        ({"kind": "combat"}, 0),
    ]:
        response = await client.get("/keys/market", headers=headers, params=filters)
        assert response.status_code == 200, response.text
        assert len(response.json()["listings"]) == count
        if count:
            row = response.json()["listings"][0]
            assert "discovered_by_character_id" not in row["key"]
            assert row["key"]["discovered_by_name"] == "Action Hero"
            assert row["deprecated"] is True
            assert row["key"]["payload"] and row["key"]["uses_remaining"] > 0
    with factory() as session:
        original = session.get(ItemInstance, uuid.UUID(identifier))
        assert original is not None
        owner = session.get(Character, original.discovered_by_character_id)
        assert owner is not None
        combat_key = make_key(session, owner, content)
        combat_key.payload = dict(key_state(content, combat=True).payload)
        session.commit()
        combat_id = str(combat_key.id)
    response = await client.post(
        "/keys/market",
        headers=headers,
        json={"instance_id": combat_id, "price_gold": 10},
    )
    assert response.status_code == 201, response.text
    combatant = content.combatants[0]
    drop_id = combatant.drops[0].item_id
    response = await client.get(
        "/keys/market",
        headers=headers,
        params={
            "kind": "combat",
            "item_id": drop_id,
            "class": content.item(drop_id).classes[0],
        },
    )
    assert [row["key"]["id"] for row in response.json()["listings"]] == [combat_id]
    assert (await client.get("/keys/market")).status_code == 401
    # Cancellation remains available without access, as on the commodity book.
    monkeypatch.setattr(app.state, "content", exploration_content())
    response = await client.post(f"/keys/market/{listing_id}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    assert len((await client.get("/keys/me", headers=headers)).json()["keys"]) == 1
    response = await client.delete(f"/keys/{identifier}", headers=headers)
    assert response.status_code == 204
    with factory() as session:
        assert session.get(KeyListing, uuid.UUID(listing_id)) is None


def test_key_buy_access_funds_and_cancel_ownership(realm_session: Session) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 2000, NOW, content)
    realm_session.commit()
    for operation, settings, code in [
        ("buy", exploration_content(), "NO_MARKET_ACCESS"),
        ("buy", content, "INSUFFICIENT_GOLD"),
        ("cancel", content, "UNKNOWN_KEY_LISTING"),
    ]:
        with pytest.raises(HTTPException) as error:
            transfer_listing(realm_session, buyer, listing.id, operation, NOW, settings)
        assert cast(dict[str, Any], error.value.detail)["error"]["code"] == code
        realm_session.rollback()
        assert listing.status == "open" and key.holder_character_id is None
        assert wallet(realm_session, buyer.id) == 1000


def test_new_listing_invalidation_in_same_transaction(realm_session: Session) -> None:
    """Preloaded relationship state must retain newly created listing custody."""
    from app.services.keys import invalidate_keys, realm_keys

    seller, realm = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, content)
    invalidate_keys(realm_keys(realm_session, realm.id), NOW)
    realm_session.flush()
    assert listing.status == "cancelled"
    assert key.holder_character_id == seller.id


def test_stale_sale_id_cannot_buy_a_relisted_key(realm_session: Session) -> None:
    """A sale at 100 and its resale at 900 are different buyer intents."""
    seller, _ = seed(realm_session)
    first_buyer, _ = seed(realm_session)
    stale_buyer, _ = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    original = list_key(realm_session, seller, key.id, 100, NOW, content)
    original_id = original.id
    realm_session.commit()
    transfer_listing(realm_session, first_buyer, original_id, "buy", NOW, content)
    realm_session.commit()
    resale = list_key(realm_session, first_buyer, key.id, 900, NOW, content)
    realm_session.commit()
    assert resale.id != original_id
    with pytest.raises(HTTPException) as error:
        transfer_listing(realm_session, stale_buyer, original_id, "buy", NOW, content)
    assert error.value.status_code == 404
    assert wallet(realm_session, stale_buyer.id) == 1000
    assert resale.status == "open" and key.holder_character_id is None
    with pytest.raises(HTTPException) as error:
        transfer_listing(
            realm_session,
            stale_buyer,
            resale.id,
            "buy",
            NOW,
            content,
            expected_price_gold=100,
        )
    assert (
        cast(dict[str, Any], error.value.detail)["error"]["code"] == "KEY_PRICE_CHANGED"
    )
    assert wallet(realm_session, stale_buyer.id) == 1000
    transfer_listing(
        realm_session,
        stale_buyer,
        resale.id,
        "buy",
        NOW,
        content,
        expected_price_gold=900,
    )
    realm_session.commit()
    assert wallet(realm_session, stale_buyer.id) == 100
    assert key.holder_character_id == stale_buyer.id


def test_self_purchase_costs_exactly_the_tax(realm_session: Session) -> None:
    seller, realm = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 101, NOW, content)
    realm_session.commit()
    treasury = realm.treasury
    transfer_listing(
        realm_session, seller, listing.id, "buy", NOW, content, expected_price_gold=101
    )
    realm_session.commit()
    # Default 5% seller tax is ceiled: 101 * .05 => 6 whole gold.
    assert wallet(realm_session, seller.id) == 994
    assert realm.treasury == treasury + 6
    assert listing.status == "sold" and key.holder_character_id == seller.id


@pytest.mark.parametrize("count", [1, 4])
def test_tick_listing_invalidation_issues_no_selects(
    realm_session: Session, count: int
) -> None:
    seller, realm = seed(realm_session)
    content = market_content()
    content = replace(
        content, caps=content.caps.model_copy(update={"key_listings": count})
    )
    for _ in range(count):
        key = make_key(realm_session, seller, content)
        realm_session.commit()
        list_key(realm_session, seller, key.id, 100, NOW, content)
        realm_session.commit()
    realm_id, seller_id = realm.id, seller.id
    start_transition(realm, realm.current_node_id, "upgrade", NOW, content)
    realm_session.commit()
    # Drop warm identity-map relationships so a missing eager load really queries.
    realm_session.expunge_all()
    reloaded_realm = realm_session.get(RealmState, realm_id)
    assert reloaded_realm is not None
    context = load_context(realm_session, reloaded_realm, None, content)
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
        complete_tick_transition(
            context,
            reloaded_realm,
            NOW + timedelta(days=content.economy.transition.duration_days),
            content,
        )
    finally:
        event.remove(engine, "before_cursor_execute", record)
    queries = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT")
    ]
    assert queries == []
    assert len(context.keys) == count
    assert all(key.holder_character_id == seller_id for key in context.keys)
    assert all(
        key.listing is not None and key.listing.status == "cancelled"
        for key in context.keys
    )


def test_postgres_buy_waits_for_seller_wallet_mutation(realm_session: Session) -> None:
    """Seller serialization precedes realm locks and prevents lost wallet updates."""
    from test_estates import _wait_for_postgres_blocker

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    seller, realm = seed(realm_session)
    buyer, _ = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, content)
    realm_session.commit()
    seller_id, buyer_id, listing_id, realm_id = (
        seller.id,
        buyer.id,
        listing.id,
        realm.id,
    )
    realm_session.rollback()
    factory = sessionmaker(bind=realm_session.get_bind())
    started = Event()
    worker_pids: list[int] = []

    def buy() -> None:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            worker_pids.append(
                session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            buyer = session.get(Character, buyer_id)
            assert buyer is not None
            started.set()
            transfer_listing(session, buyer, listing_id, "buy", NOW, content)
            session.commit()

    with ThreadPoolExecutor(max_workers=1) as pool, factory() as blocker:
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        lock_character_and_load_action(blocker, seller_id)
        future = pool.submit(buy)
        try:
            assert started.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pids[0], blocker_pid)
            # A buyer must wait on the seller before acquiring ANY realm lock.
            with factory() as probe:
                assert (
                    probe.scalar(
                        select(RealmState)
                        .where(RealmState.id == realm_id)
                        .with_for_update(nowait=True)
                    )
                    is not None
                )
            balance = blocker.get(Currency, seller_id)
            assert balance is not None
            balance.gold += 37
            blocker.commit()
        finally:
            blocker.rollback()
        future.result(timeout=10)
    realm_session.expire_all()
    assert wallet(realm_session, seller_id) == 1132
    assert wallet(realm_session, buyer_id) == 900


@pytest.mark.anyio
async def test_browse_cursor_filters_and_removed_content(
    action_client: ApiFixture,
) -> None:
    """Sparse content filters fill pages, skip removed ids and seek through ties."""
    client, factory, _, headers = action_client
    content = exploration_content()
    expected: list[str] = []
    with factory() as session:
        owner = session.scalar(select(Character))
        assert owner is not None
        good = key_state(content).payload["action"]["outputs"][0]["item_id"]
        other_good = next(
            item.id for item in content.items if item.id != good and not item.instanced
        )
        for number in range(1, 9):
            key = make_key(session, owner, content)
            action = dict(key.payload["action"])
            if number == 7:
                action["combatant_id"] = "removed.combatant"
            else:
                outputs = [dict(output) for output in action["outputs"]]
                outputs[0]["item_id"] = (
                    "removed.item"
                    if number == 6
                    else (other_good if number % 2 == 0 else good)
                )
                action["outputs"] = outputs
            key.payload = {"action": action}
            key.holder_character_id = None
            key.realm_id = (
                "realm.ashen_reach" if number == 8 else owner.current_realm_id
            )
            identifier = uuid.UUID(int=number)
            session.add(
                KeyListing(
                    id=identifier,
                    instance_id=key.id,
                    seller_character_id=owner.id,
                    price_gold=100,
                    realm_id="realm.ashen_reach",
                    status="open",
                    created_at=NOW,
                )
            )
            if number in {1, 3, 5}:
                expected.append(str(identifier))
        session.commit()
        discovery_realm = owner.current_realm_id
    queries: list[str] = []

    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        queries.append(statement)

    engine = factory.kw["bind"]
    event.listen(engine, "before_cursor_execute", record)
    try:
        seen: list[str] = []
        before: str | None = None
        for _ in expected:
            params = {
                "realm_id": discovery_realm,
                "item_id": good,
                "kind": "gather",
                "limit": "1",
            }
            if before is not None:
                params["before"] = before
            response = await client.get("/keys/market", headers=headers, params=params)
            assert response.status_code == 200, response.text
            rows = response.json()["listings"]
            assert len(rows) == 1
            seen.append(rows[0]["id"])
            before = response.json()["next_cursor"]
        assert seen == list(reversed(expected))
        assert before is None
    finally:
        event.remove(engine, "before_cursor_execute", record)
    listing_queries = [query for query in queries if "FROM key_listings" in query]
    assert listing_queries
    assert all(
        "item_instances.realm_id =" in query and "LIMIT" in query
        for query in listing_queries
    )
    # realm_id means discovery realm, even though every listing was placed elsewhere.
    response = await client.get(
        "/keys/market", headers=headers, params={"realm_id": "realm.ashen_reach"}
    )
    assert [row["id"] for row in response.json()["listings"]] == [str(uuid.UUID(int=8))]
    for params in [
        {"kind": "unknown"},
        {"limit": "0"},
        {"limit": "201"},
        {"before": "bad"},
    ]:
        response = await client.get("/keys/market", headers=headers, params=params)
        assert response.status_code == 422


@pytest.mark.anyio
async def test_due_transition_cancel_commits_return(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancel commits a due transition that returns the seller's invalid trophy."""
    client, factory, clock, headers = action_client
    identifier = await discover_api(action_client, monkeypatch)
    content = replace(app.state.content, _nodes_by_id=market_content()._nodes_by_id)
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "transition": content.economy.transition.model_copy(
                    update={"duration_days": 0}
                )
            }
        ),
    )
    monkeypatch.setattr(app.state, "content", content)
    response = await client.post(
        "/keys/market",
        headers=headers,
        json={"instance_id": identifier, "price_gold": 100},
    )
    assert response.status_code == 201, response.text
    listing_id = response.json()["id"]
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None
        realm = session.get(RealmState, key.realm_id)
        assert realm is not None
        start_transition(realm, realm.current_node_id, "upgrade", clock.now, content)
        session.commit()
    content = replace(
        content, caps=content.caps.model_copy(update={"inventory_slots": 1})
    )
    monkeypatch.setattr(app.state, "content", content)
    response = await client.post(f"/keys/market/{listing_id}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert response.json()["key"]["state"] == "invalid"
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None and key.holder_character_id is not None
        realm = session.get(RealmState, key.realm_id)
        assert realm is not None and realm.pending_transition is None
        assert realm.transition_history


def test_unavailable_settlement_has_neutral_error(realm_session: Session) -> None:
    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    content = market_content()
    key = make_key(realm_session, seller, content)
    balance = realm_session.get(Currency, seller.id)
    assert balance is not None
    balance.gold = 2**63 - 1
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, content)
    realm_session.commit()
    with pytest.raises(HTTPException) as error:
        transfer_listing(realm_session, buyer, listing.id, "buy", NOW, content)
    assert cast(dict[str, Any], error.value.detail) == {
        "error": {
            "code": "MARKET_UNAVAILABLE",
            "message": "The purchase cannot be completed",
        }
    }
    assert listing.status == "open" and key.holder_character_id is None
    assert wallet(realm_session, buyer.id) == 1000
