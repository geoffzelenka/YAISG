"""Pure estate rules shared by voting and lifecycle callers."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.content.loader import ContentIndex
from app.content.schemas import EstateForm


def vote_weight(estate: EstateForm) -> int:
    """Return the vote weight determined by the estate's resolved form."""
    return 1 if estate.mobility == "mobile" else 9 + estate.tier


UnitAsk = Callable[[str, str], int | None]


def not_selling(realm_id: str, item_id: str) -> None:
    """Placeholder unit-ask provider until realm pricing is available."""
    return None


@dataclass(frozen=True)
class Valuation:
    """Rebuild value and the cheapest authored tier-one path used."""

    value: int
    path: tuple[str, ...]


def estate_value(
    form_id: str,
    upgrades: Sequence[str],
    realm_id: str,
    content: ContentIndex,
    unit_ask: UnitAsk = not_selling,
) -> Valuation:
    """Price every simple tier-one rebuild path; break ties by form ids."""

    def price(item_id: str) -> int:
        reference = content.item(item_id).reference_price
        ask = unit_ask(realm_id, item_id)
        return reference if ask is None else min(reference, ask)

    def form_cost(form: EstateForm) -> int:
        return form.build_cost.gold + sum(
            line.quantity
            * min(
                price(item.id) for item in content.items if line.selector.matches(item)
            )
            for line in form.build_cost.goods
        )

    candidates: list[Valuation] = []

    def visit(form: EstateForm, path: tuple[str, ...], value: int) -> None:
        if form.id in path:
            return
        path = (*path, form.id)
        value += form_cost(form)
        if form.id == form_id:
            candidates.append(Valuation(value, path))
            return
        for target in form.transforms_to:
            visit(content.estate_form(target), path, value)

    for form in content.estate_forms:
        if form.tier == 1:
            visit(form, (), 0)
    if not candidates:
        raise ValueError(f"Estate form {form_id} has no tier-one rebuild path")
    best = min(candidates, key=lambda candidate: (candidate.value, candidate.path))
    upgrade_value = sum(
        entry.qty * price(entry.item_id)
        for upgrade_id in upgrades
        for entry in content.upgrade(upgrade_id).cost
    )
    return Valuation(best.value + upgrade_value, best.path)


def sale_price(value: int, markup_pct: int) -> int:
    """Round a marked-up integral gold valuation upward exactly."""
    return (value * (100 + markup_pct) + 99) // 100
