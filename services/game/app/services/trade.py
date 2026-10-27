"""Atomic player transfers under the caller's character and realm locks."""

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.core import resolve_caps
from app.engine.market import quote, total
from app.errors import api_error
from app.models import Character, Currency, Inventory, RealmLine, RealmState, RealmStore
from app.services.actions import load_character_state
from app.services.market import market_contexts
from app.services.stores import recompute_lines


def present(character: Character, realm: RealmState) -> None:
    """Require resolved presence, equally for residents and visitors."""
    if character.current_realm_id != realm.id:
        raise api_error(409, "NOT_PRESENT", "You must be in the realm")


def gift(session: Session, character: Character, realm: RealmState, gold: int) -> None:
    """Transfer wallet gold without making it spendable in this tick's budgets."""
    present(character, realm)
    wallet = session.get(Currency, character.id)
    assert wallet is not None
    if wallet.gold < gold:
        raise api_error(409, "INSUFFICIENT_GOLD", "You do not have enough gold")
    wallet.gold -= gold
    realm.treasury += gold


def trade(
    session: Session,
    character: Character,
    realm: RealmState,
    content: ContentIndex,
    item_id: str,
    side: Literal["buy", "sell"],
    quantity: int,
    limit_gold: int,
) -> int:
    """Validate a complete trade before moving either named holder's holdings."""
    present(character, realm)
    recompute_lines(session, realm, content)
    session.flush()
    contexts = market_contexts(session, realm, content)
    if item_id not in contexts:
        raise api_error(404, "UNKNOWN_ITEM", "The item does not exist")
    line, ctx = contexts[item_id]
    stack = session.get(Inventory, (character.id, item_id))
    wallet = session.get(Currency, character.id)
    assert wallet is not None
    if side == "sell":
        if line is None or line.draw_per_day <= 0:
            raise api_error(409, "NO_DEMAND", "The realm has no demand for this item")
        if quantity * ctx.w * 1000 > line.cap - line.stock:
            raise api_error(409, "STORES_FULL", "The trade exceeds the line cap")
        maximum = quote(ctx, item_id, side, quantity).max_quantity
        if quantity > maximum:
            raise api_error(
                409,
                "UNFUNDED_DEMAND",
                "The realm cannot fund the trade",
                extra={"max_quantity": maximum},
            )
        if stack is None or stack.quantity < quantity:
            raise api_error(
                409, "MISSING_INPUTS", "You do not hold enough of this item"
            )
    elif quantity > quote(ctx, item_id, side, quantity).max_quantity:
        raise api_error(409, "NOT_FOR_SALE", "The requested stock is not for sale")
    gold = total(ctx, side, quantity)
    if (side == "sell" and gold < limit_gold) or (side == "buy" and gold > limit_gold):
        raise api_error(409, "PRICE_MOVED", "The quote is worse than your limit")
    if side == "buy":
        if wallet.gold < gold:
            raise api_error(409, "INSUFFICIENT_GOLD", "You do not have enough gold")
        state = load_character_state(session, character.id, content)
        if (stack.quantity if stack else 0) + quantity > content.item(
            item_id
        ).stack_limit or (
            stack is None
            and len(state.inventory) >= resolve_caps(state, content).inventory_slots
        ):
            raise api_error(
                409, "INVENTORY_FULL", "The trade does not fit your inventory"
            )
    direction = 1 if side == "sell" else -1
    store = session.get(RealmStore, (realm.id, item_id))
    if store is None:
        store = RealmStore(realm_id=realm.id, item_id=item_id, quantity_milli=0)
        session.add(store)
    store.quantity_milli += direction * quantity * 1000
    if stack is None:
        stack = Inventory(character_id=character.id, item_id=item_id, quantity=0)
        session.add(stack)
    stack.quantity -= direction * quantity
    if stack.quantity == 0:
        session.delete(stack)
    wallet.gold += direction * gold
    realm.treasury -= direction * gold
    if side == "sell":
        assert line is not None
        row = session.scalar(
            select(RealmLine).where(
                RealmLine.realm_id == realm.id, RealmLine.line_key == line.key
            )
        )
        assert row is not None
        row.budget_gold -= gold
    session.flush()
    recompute_lines(session, realm, content)
    return gold
