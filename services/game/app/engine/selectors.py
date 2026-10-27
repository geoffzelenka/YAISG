"""Deterministic, atomic selector payment for any goods holding."""

from collections.abc import Mapping
from dataclasses import dataclass

from app.content.loader import ContentIndex
from app.content.schemas import Selector


@dataclass(frozen=True)
class Shortfall:
    """Unpaid quantity; no withdrawals are made on failure."""

    quantity: int


def pay_selector(
    holding: Mapping[str, int], selector: Selector, quantity: int, content: ContentIndex
) -> dict[str, int] | Shortfall:
    """Return a complete payment, cheapest first, without mutating the holding."""
    if quantity < 0 or any(value < 0 for value in holding.values()):
        raise ValueError("payment and holding quantities must be nonnegative")
    remaining = quantity
    withdrawals: dict[str, int] = {}
    candidates = sorted(
        (item for item in content.items if selector.matches(item)),
        key=lambda item: (item.reference_price, item.id),
    )
    for item in candidates:
        taken = min(holding.get(item.id, 0), remaining)
        if taken:
            withdrawals[item.id] = taken
            remaining -= taken
        if not remaining:
            break
    return Shortfall(remaining) if remaining else withdrawals
