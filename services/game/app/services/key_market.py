"""Atomic key custody and direct wallet settlement."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.core import resolve_caps
from app.engine.order_book import seller_tax
from app.errors import api_error
from app.models import (
    Character,
    Currency,
    GoldLedger,
    ItemInstance,
    KeyListing,
    RealmState,
)
from app.services.actions import load_character_state, lock_character_and_load_action
from app.services.keys import held_key
from app.services.order_book import prepare_market, require_access


def require_room(session: Session, character: Character, content: ContentIndex) -> None:
    """Require one distinct slot for an incoming physical instance."""
    state = load_character_state(session, character.id, content)
    if (
        len(state.inventory) + len(state.instances)
        >= resolve_caps(state, content).inventory_slots
    ):
        raise api_error(409, "INVENTORY_FULL", "The key needs a free inventory slot")


def list_key(
    session: Session,
    character: Character,
    identifier: uuid.UUID,
    price: int,
    now: datetime,
    content: ContentIndex,
) -> KeyListing:
    """Remove an unused active key from inventory into listing custody."""
    prepare_market(session, character, now, content)
    require_access(session, character, content)
    key = held_key(session, identifier, character.id)
    if (
        key.kind != "key"
        or key.state != "active"
        or key.bound_at is not None
        or key.uses_remaining != key.uses_total
    ):
        raise api_error(
            409, "KEY_UNAVAILABLE", "Only active unused unbound keys may be listed"
        )
    used = (
        session.scalar(
            select(func.count())
            .select_from(KeyListing)
            .where(
                KeyListing.seller_character_id == character.id,
                KeyListing.status == "open",
            )
        )
        or 0
    )
    state = load_character_state(session, character.id, content)
    if used >= resolve_caps(state, content).key_listings:
        raise api_error(
            409, "NO_KEY_LISTING_SLOT", "All key listing slots are occupied"
        )
    previous = session.scalar(
        select(KeyListing).where(KeyListing.instance_id == identifier).with_for_update()
    )
    if previous is not None:
        # The unique instance constraint permits one row, but a buyer's stale
        # intent must never address a later sale at a different price.
        session.delete(previous)
        session.flush()
    listing = KeyListing(
        instance_id=identifier,
        seller_character_id=character.id,
        price_gold=price,
        realm_id=character.current_realm_id,
        status="open",
        created_at=now,
    )
    session.add(listing)
    key.listing = listing
    key.holder_character_id = None
    session.flush()
    return listing


def transfer_listing(
    session: Session,
    character: Character,
    identifier: uuid.UUID,
    operation: str,
    now: datetime,
    content: ContentIndex,
    expected_price_gold: int | None = None,
) -> KeyListing:
    """Lock participants before realms, then revalidate listing custody exactly once."""
    # This is only an identity hint. The authoritative row is refreshed after locks.
    hint = session.get(KeyListing, identifier)
    if hint is None:
        raise api_error(404, "UNKNOWN_KEY_LISTING", "The listing does not exist")
    seller_id = hint.seller_character_id
    for character_id in sorted({character.id, seller_id}, key=str):
        lock_character_and_load_action(session, character_id)
    locked = prepare_market(session, character, now, content)
    listing = session.scalar(
        select(KeyListing)
        .where(KeyListing.id == identifier)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if listing is None:
        raise api_error(404, "UNKNOWN_KEY_LISTING", "The listing does not exist")
    if listing.seller_character_id != seller_id or listing.realm_id not in locked:
        raise api_error(
            409, "MARKET_RETRY", "The listing changed; retry in a fresh transaction"
        )
    if operation == "cancel" and seller_id != character.id:
        raise api_error(404, "UNKNOWN_KEY_LISTING", "The listing does not exist")
    key = session.get(ItemInstance, listing.instance_id)
    assert key is not None
    if (
        operation == "cancel"
        and listing.status == "cancelled"
        and key.state == "invalid"
        and key.holder_character_id == character.id
    ):
        # prepare_market completed the transition and returned this trophy.
        # Report that successful return so the HTTP layer commits the completion.
        return listing
    if listing.status != "open":
        raise api_error(409, "KEY_LISTING_CLOSED", "The listing is no longer open")
    assert key.holder_character_id is None
    if operation == "cancel":
        require_room(session, character, content)
        listing.status = "cancelled"
    else:
        if (
            expected_price_gold is not None
            and expected_price_gold != listing.price_gold
        ):
            raise api_error(
                409,
                "KEY_PRICE_CHANGED",
                "The listing price differs from the expected price",
            )
        require_access(session, character, content)
        require_room(session, character, content)
        _settle_purchase(session, character, listing, now, content)
        listing.status = "sold"
        listing.sold_at = now
        listing.buyer_character_id = character.id
    key.holder_character_id = character.id
    session.flush()
    return listing


def _settle_purchase(
    session: Session,
    character: Character,
    listing: KeyListing,
    now: datetime,
    content: ContentIndex,
) -> None:
    """Move whole gold between the two locked wallets and listing realm."""
    buyer = session.get(Currency, character.id)
    seller = session.get(Currency, listing.seller_character_id)
    realm = session.get(RealmState, listing.realm_id)
    assert buyer is not None and seller is not None and realm is not None
    tax, burned = seller_tax(listing.price_gold, content.economy.market)
    if buyer.gold < listing.price_gold:
        raise api_error(409, "INSUFFICIENT_GOLD", "You do not have enough gold")
    if (
        listing.seller_character_id != character.id
        and seller.gold + listing.price_gold - tax > 2**63 - 1
    ):
        raise api_error(409, "MARKET_UNAVAILABLE", "The purchase cannot be completed")
    buyer.gold -= listing.price_gold
    seller.gold += listing.price_gold - tax
    realm.treasury += tax - burned
    if burned:
        session.add(
            GoldLedger(
                cause="tax_burn",
                amount=-burned,
                realm_id=realm.id,
                character_id=listing.seller_character_id,
                at=now,
            )
        )
