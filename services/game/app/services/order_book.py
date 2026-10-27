"""Transactional escrow, matching and collection under character/realm locks."""

import uuid
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.core import realm_active_tags, resolve_caps
from app.engine.order_book import seller_tax
from app.errors import api_error
from app.models import (
    Character,
    Currency,
    GoldLedger,
    Inventory,
    MarketMatch,
    MarketOrder,
    RealmState,
)
from app.services.actions import load_character_state, resolve_character


def prepare_market(
    session: Session, character: Character, now: datetime, content: ContentIndex
) -> None:
    """Resolve the character and serialize the book before touching any orders.

    Sorted world realm locks also cover every possible seller tax recipient and
    prevent phantom crossing inserts when the book is empty. This deliberately
    coarse first implementation can later use per-good serialization, provided
    it preserves character -> sorted realms -> estate -> price-time order locks.
    """
    realm_ids = set(session.scalars(select(RealmState.id)))
    resolve_character(
        session, character.id, now, content, additional_realm_ids=realm_ids
    )


def require_access(
    session: Session, character: Character, content: ContentIndex
) -> None:
    """Gate creation and collection on resolved current-realm access tags."""
    state = load_character_state(session, character.id, content)
    if not any(
        tag.effects.market_access for tag, _ in realm_active_tags(state, content)
    ):
        raise api_error(
            409, "NO_MARKET_ACCESS", "The current realm has no market access"
        )


def validate_good(item_id: str, content: ContentIndex) -> None:
    """Accept only known fungible goods on the global book."""
    try:
        item = content.item(item_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_ITEM", "The item does not exist") from None
    if item.instanced:
        raise api_error(
            409, "INSTANCED_ITEM", "Instanced items cannot use the global book"
        )


def create_order(
    session: Session,
    character: Character,
    side: Literal["buy", "sell"],
    item_id: str,
    quantity: int,
    unit_price: int,
    now: datetime,
    content: ContentIndex,
) -> tuple[MarketOrder, list[MarketMatch]]:
    """Escrow the full intent and sweep makers at their resting prices."""
    require_access(session, character, content)
    validate_good(item_id, content)
    if quantity <= 0 or unit_price <= 0 or quantity * unit_price > 2**63 - 1:
        raise api_error(
            422, "INVALID_ORDER", "Positive quantity and price must fit 64-bit gold"
        )
    _check_slots(session, character, content)
    escrow = _escrow(session, character, side, item_id, quantity, unit_price)
    order = MarketOrder(
        character_id=character.id,
        side=side,
        item_id=item_id,
        unit_price=unit_price,
        quantity=quantity,
        quantity_remaining=quantity,
        escrow_gold_remaining=escrow,
        fill_items=0,
        fill_gold=0,
        status="open",
        realm_id=character.current_realm_id,
        created_at=now,
        expires_at=now + timedelta(days=content.economy.market.order_days),
    )
    session.add(order)
    session.flush()
    matches = _sweep(session, order, now, content)
    session.flush()
    return order, matches


def _check_slots(session: Session, character: Character, content: ContentIndex) -> None:
    state = load_character_state(session, character.id, content)
    used = (
        session.scalar(
            select(func.count())
            .select_from(MarketOrder)
            .where(
                MarketOrder.character_id == character.id, MarketOrder.status != "closed"
            )
        )
        or 0
    )
    if used >= resolve_caps(state, content).order_slots:
        raise api_error(409, "NO_ORDER_SLOT", "All order slots are occupied")


def _sweep(
    session: Session, order: MarketOrder, now: datetime, content: ContentIndex
) -> list[MarketMatch]:
    price = MarketOrder.unit_price
    crossing = (
        price <= order.unit_price if order.side == "buy" else price >= order.unit_price
    )
    maker_ids = session.scalars(
        select(MarketOrder.id)
        .where(
            MarketOrder.item_id == order.item_id,
            MarketOrder.side == ("sell" if order.side == "buy" else "buy"),
            MarketOrder.status == "open",
            crossing,
        )
        .order_by(
            price.asc() if order.side == "buy" else price.desc(),
            MarketOrder.created_at,
            MarketOrder.id,
        )
    ).all()
    matches = []
    for maker_id in maker_ids:
        if order.quantity_remaining == 0:
            break
        # Realm serialization keeps the candidate list stable. Lock only the
        # makers actually swept, in precisely the price-time order above.
        maker = session.scalar(
            select(MarketOrder)
            .where(MarketOrder.id == maker_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert maker is not None
        matches.append(_match(session, maker, order, now, content))
    return matches


def _escrow(
    session: Session,
    character: Character,
    side: str,
    item_id: str,
    quantity: int,
    price: int,
) -> int:
    if side == "buy":
        wallet = session.get(Currency, character.id)
        assert wallet is not None
        gold = quantity * price
        if wallet.gold < gold:
            raise api_error(409, "INSUFFICIENT_GOLD", "You do not have enough gold")
        wallet.gold -= gold
        return gold
    stack = session.get(Inventory, (character.id, item_id))
    if stack is None or stack.quantity < quantity:
        raise api_error(409, "MISSING_INPUTS", "You do not hold enough of this item")
    stack.quantity -= quantity
    if stack.quantity == 0:
        session.delete(stack)
    return 0


def _match(
    session: Session,
    maker: MarketOrder,
    taker: MarketOrder,
    now: datetime,
    content: ContentIndex,
) -> MarketMatch:
    buy, sell = (taker, maker) if taker.side == "buy" else (maker, taker)
    quantity = min(maker.quantity_remaining, taker.quantity_remaining)
    gross = quantity * maker.unit_price
    tax, burned = seller_tax(gross, content.economy.market)
    buy.escrow_gold_remaining -= quantity * buy.unit_price
    buy.fill_items += quantity
    buy.fill_gold += quantity * buy.unit_price - gross
    sell.fill_gold += gross - tax
    for order in (maker, taker):
        order.quantity_remaining -= quantity
        if order.quantity_remaining == 0:
            order.status = "collectable"
    realm = session.get(RealmState, sell.realm_id)
    assert realm is not None
    realm.treasury += tax - burned
    if burned:
        session.add(
            GoldLedger(
                cause="tax_burn",
                amount=-burned,
                realm_id=sell.realm_id,
                character_id=sell.character_id,
                at=now,
            )
        )
    match = MarketMatch(
        maker_order_id=maker.id,
        taker_order_id=taker.id,
        buyer_character_id=buy.character_id,
        seller_character_id=sell.character_id,
        item_id=maker.item_id,
        quantity=quantity,
        unit_price=maker.unit_price,
        tax_gold=tax,
        burned_gold=burned,
        tax_realm_id=sell.realm_id,
        matched_at=now,
    )
    session.add(match)
    return match


def owned_order(
    session: Session, character: Character, order_id: uuid.UUID
) -> MarketOrder:
    """Lock an owned slot without disclosing somebody else's order."""
    order = session.scalar(
        select(MarketOrder)
        .where(MarketOrder.id == order_id, MarketOrder.character_id == character.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None:
        raise api_error(404, "UNKNOWN_ORDER", "The order does not exist")
    return order


def cancel_order(order: MarketOrder) -> None:
    """Move unfilled escrow into the slot; cancellation never collects."""
    if order.status != "open":
        return
    if order.side == "sell":
        order.fill_items += order.quantity_remaining
    else:
        order.fill_gold += order.escrow_gold_remaining
    order.escrow_gold_remaining = 0
    order.quantity_remaining = 0
    order.status = "collectable"


def collect_order(
    session: Session,
    character: Character,
    order: MarketOrder,
    now: datetime,
    content: ContentIndex,
) -> tuple[int, int]:
    """Collect only what fits; an open order stays open after early collection."""
    require_access(session, character, content)
    state = load_character_state(session, character.id, content)
    stack = session.get(Inventory, (character.id, order.item_id))
    room = max(
        0, content.item(order.item_id).stack_limit - (stack.quantity if stack else 0)
    )
    if (
        stack is None
        and len(state.inventory) >= resolve_caps(state, content).inventory_slots
    ):
        room = 0
    items = min(room, order.fill_items)
    if items:
        if stack is None:
            stack = Inventory(
                character_id=character.id, item_id=order.item_id, quantity=0
            )
            session.add(stack)
        stack.quantity += items
        order.fill_items -= items
    wallet = session.get(Currency, character.id)
    assert wallet is not None
    gold = min(order.fill_gold, 2**63 - 1 - wallet.gold)
    wallet.gold += gold
    order.fill_gold -= gold
    if order.status == "collectable" and order.fill_items == order.fill_gold == 0:
        order.status = "closed"
        order.closed_at = now
    session.flush()
    return items, gold
