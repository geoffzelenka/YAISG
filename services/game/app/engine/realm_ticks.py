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


def consume_value(
    stock: dict[str, int], selector: Selector, amount: int, content: ContentIndex
) -> int:
    """Consume at most a reference-value milli-budget, cheapest goods first.

    A remainder smaller than one milli-unit of the next good stays unmet rather
    than overdrawing the tick's authored appetite.
    """
    consumed = 0
    for item_id in sorted(stock, key=lambda i: (content.item(i).reference_price, i)):
        item = content.item(item_id)
        if not selector.matches(item):
            continue
        quantity = min(stock[item_id], (amount - consumed) // item.reference_price)
        stock[item_id] -= quantity
        consumed += quantity * item.reference_price
    return consumed


def coinage(consumed_value_milli: int, multiple: float) -> int:
    """Floor this tick's minted gold using exact content-decimal arithmetic."""
    from fractions import Fraction

    return int(Fraction(consumed_value_milli, 1000) * Fraction(str(multiple)))
