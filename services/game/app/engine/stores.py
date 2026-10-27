"""Pure demand derivation; all amounts are integer milli-line-units."""

import json
from dataclasses import dataclass, replace
from fractions import Fraction

from app.content.loader import ContentIndex
from app.content.schemas import (
    ActionInput,
    DevelopmentNode,
    EstateForm,
    Item,
    Selector,
    Tag,
)


def due(d: int, n: int, T: int) -> int:
    """Return one tick's share of a nonnegative daily milli-rate without drift."""
    if d < 0 or n < 0 or T <= 0:
        raise ValueError("daily rate and tick index must be nonnegative; T positive")
    return d * (n + 1) // T - d * n // T


@dataclass(frozen=True)
class Demand:
    """One source's daily demand in milli-line-units."""

    selector: Selector
    daily_milli: Fraction
    value_measured: bool = False


@dataclass(frozen=True)
class Line:
    """Derived appetite and assigned stock in milli-line-units."""

    key: str
    selector: Selector
    draw_per_day: int
    reserve: int
    cap: int
    stock: int
    value_measured: bool
    in_transit: int = 0
    budget_gold: int = 0


def line_key(selector: Selector) -> str:
    """Return the canonical, stable selector identity."""
    return json.dumps(selector.model_dump(), sort_keys=True, separators=(",", ":"))


def membership(item: Item, lines: tuple[Line, ...]) -> Line | None:
    """Choose the most specific match, breaking equal-specificity ties by key."""
    matches = [line for line in lines if line.selector.matches(item)]
    return min(
        matches,
        key=lambda line: (
            0 if line.selector.item else 1 if line.selector.tier else 2,
            line.key,
        ),
        default=None,
    )


def line_weight(item: Item, line: Line) -> int:
    """Return line units contributed by one item unit."""
    return item.reference_price if line.value_measured else 1


def project_demands(
    required: tuple[ActionInput, ...],
    contributed: tuple[int, ...],
    completion_days: float,
) -> tuple[Demand, ...]:
    """Derive a funding overlay from its snapshotted cost and milli-progress."""
    days = Fraction(str(completion_days))
    if days <= 0:
        raise ValueError("project completion days must be positive")
    return tuple(
        Demand(line.selector, Fraction(max(0, line.quantity * 1000 - paid)) / days)
        for line, paid in zip(required, contributed, strict=True)
    )


def mint_demands() -> tuple[Demand, ...]:
    """Prompt 18 supplies value-measured mint appetite here."""
    return ()


def derive_lines(
    node: DevelopmentNode,
    tags: tuple[Tag, ...],
    estates: tuple[EstateForm, ...],
    overlay: tuple[Demand, ...],
    stores: dict[str, int],
    content: ContentIndex,
    transition_days: Fraction = Fraction(0),
    mint: tuple[Demand, ...] = (),
) -> tuple[Line, ...]:
    """Group source demand and assign each stored item exactly once."""
    holders: tuple[DevelopmentNode | Tag | EstateForm, ...] = (node, *tags, *estates)
    demands = [
        Demand(line.selector, Fraction(str(line.per_day)) * 1000)
        for holder in holders
        for line in holder.upkeep
    ]
    demands.extend((*overlay, *mint))
    grouped: dict[str, Demand] = {}
    for demand in demands:
        key = line_key(demand.selector)
        prior = grouped.get(key)
        if prior and prior.value_measured != demand.value_measured:
            raise ValueError(f"incompatible units on line {key}")
        grouped[key] = Demand(
            demand.selector,
            demand.daily_milli + (prior.daily_milli if prior else 0),
            demand.value_measured,
        )
    reserve_days = Fraction(
        str(
            content.economy.reserve_days
            if node.reserve_days is None
            else node.reserve_days
        )
    ) + sum((Fraction(str(t.effects.reserve_days_delta)) for t in tags), Fraction(0))
    reserve_days += transition_days
    cap_days = Fraction(
        str(content.economy.cap_days if node.cap_days is None else node.cap_days)
    )
    lines = tuple(
        Line(
            key,
            d.selector,
            int(d.daily_milli),
            int(int(d.daily_milli) * reserve_days),
            int(int(d.daily_milli) * cap_days),
            0,
            d.value_measured,
        )
        for key, d in sorted(grouped.items())
        if d.daily_milli > 0
    )
    stocks = dict.fromkeys((line.key for line in lines), 0)
    for item_id, quantity in stores.items():
        item = content.item(item_id)
        line = membership(item, lines)
        if line:
            stocks[line.key] += quantity * line_weight(item, line)
    return tuple(replace(line, stock=stocks[line.key]) for line in lines)


def warehouse_cap(item: Item, content: ContentIndex) -> int:
    """Return the hard cap for an unassigned item in milli-units (reserve zero)."""
    if item.warehouse_cap is not None:
        return item.warehouse_cap * 1000
    return content.economy.warehouse_value_cap * 1000 // item.reference_price
