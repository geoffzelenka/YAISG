"""Deterministic integer stock allocation for realm ticks."""

from app.content.loader import ContentIndex
from app.content.schemas import Selector
from app.engine.stores import Line, membership


def take(
    stock: dict[str, int],
    selector: Selector,
    amount: int,
    content: ContentIndex,
    lines: tuple[Line, ...] = (),
) -> dict[str, int]:
    """Consume matching goods in item-id order, respecting assigned reserves."""
    paid: dict[str, int] = {}
    for item_id in sorted(stock, key=lambda i: (content.item(i).reference_price, i)):
        item = content.item(item_id)
        if not selector.matches(item):
            continue
        available = stock[item_id]
        line = membership(item, lines)
        if line is not None:
            held = sum(
                q
                for i, q in stock.items()
                if membership(content.item(i), lines) == line
            )
            available = min(available, max(0, held - line.reserve))
        quantity = min(amount, available)
        if quantity:
            stock[item_id] -= quantity
            paid[item_id] = quantity
            amount -= quantity
        if amount == 0:
            break
    return paid


def shares(owed: list[int], available: int) -> list[int]:
    """Apportion scarce milli-units by largest remainder, ties in input order."""
    total = sum(owed)
    if total <= available:
        return owed.copy()
    result = [amount * available // total for amount in owed]
    order = sorted(range(len(owed)), key=lambda i: (-(owed[i] * available % total), i))
    for i in order[: available - sum(result)]:
        result[i] += 1
    return result
