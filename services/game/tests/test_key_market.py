"""Key listing custody, lifecycle, settlement and concurrent buyouts."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier
from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy import select
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
)
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
    relisted = list_key(realm_session, owner, first.id, 200, NOW, content)
    assert relisted.id == listing.id


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
