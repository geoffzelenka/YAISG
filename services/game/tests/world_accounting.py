"""Test-only world accounting independent of persisted transfer implementations."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from fractions import Fraction
from functools import wraps

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import Selector
from app.engine.realm_ticks import (
    consume_value as original_value,
)
from app.engine.realm_ticks import (
    take as original_take,
)
from app.engine.stores import Line, line_weight, membership, warehouse_cap
from app.models import (
    CharacterEquipment,
    EstateLarder,
    Inventory,
    MarketOrder,
    RealmShipment,
    RealmState,
    RealmStore,
)
from app.services import realm_ticks
from app.services.realm_ticks import RealmTickContext, daily_share, production_factor


def goods(session: Session) -> Counter[str]:
    """Count each physical holder in milli-items, never audit/history rows."""
    result: Counter[str] = Counter()
    for equipped in session.scalars(select(CharacterEquipment)):
        result[equipped.item_id] += equipped.quantity * 1000
    for row in session.scalars(select(Inventory)):
        result[row.item_id] += row.quantity * 1000
    for store in session.scalars(select(RealmStore)):
        result[store.item_id] += store.quantity_milli
    for larder in session.scalars(select(EstateLarder)):
        result[larder.item_id] += larder.quantity_milli
    for order in session.scalars(select(MarketOrder)):
        result[order.item_id] += 1000 * (
            order.fill_items + (order.quantity_remaining if order.side == "sell" else 0)
        )
    for shipment in session.scalars(
        select(RealmShipment).where(RealmShipment.status == "in_transit")
    ):
        result[shipment.item_id] += shipment.quantity_arriving * 1000
    return result


@dataclass
class GoodsAccounting:
    """Record only authorized production and destruction, by item and cause.

    Transfers never adjust this oracle. Tick withdrawals count explicit payment
    results rather than inferring losses from changes in world totals.
    """

    changes: dict[str, Counter[str]] = field(default_factory=dict)
    context: RealmTickContext | None = None
    cause: str = ""

    def add(self, cause: str, item: str, amount: int) -> None:
        """Record a signed milli-item source or sink."""
        self.changes.setdefault(cause, Counter())[item] += amount

    def expected(self, baseline: Counter[str]) -> Counter[str]:
        """Preserve signed deltas; Counter addition would discard negatives."""
        expected = baseline.copy()
        for amounts in self.changes.values():
            expected.update(amounts)
        return expected

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Observe tick payments and independently calculate authored losses."""

        def take(
            stock: dict[str, int],
            selector: Selector,
            amount: int,
            content: ContentIndex,
            lines: tuple[Line, ...] = (),
        ) -> dict[str, int]:
            paid = original_take(stock, selector, amount, content, lines)
            context = self.context
            if context is not None and (
                stock is context.stores
                or any(stock is larder for larder in context.larders.values())
            ):
                for item, amount in paid.items():
                    self.add(self.cause, item, -amount)
            return paid

        def consume_value(
            stock: dict[str, int],
            selector: Selector,
            amount: int,
            content: ContentIndex,
        ) -> int:
            # Mint consumes reference value, while conservation counts items.
            remaining = amount
            for item in sorted(content.items, key=lambda i: (i.reference_price, i.id)):
                if selector.matches(item):
                    paid = min(stock.get(item.id, 0), remaining // item.reference_price)
                    self.add("mint_bullion", item.id, -paid)
                    remaining -= paid * item.reference_price
            return original_value(stock, selector, amount, content)

        monkeypatch.setattr(realm_ticks, "take", take)
        monkeypatch.setattr(realm_ticks, "consume_value", consume_value)
        monkeypatch.setattr(
            realm_ticks,
            "TICK_STEPS",
            tuple(self.observe(step) for step in realm_ticks.TICK_STEPS),
        )

    def observe(self, step: Callable[..., None]) -> Callable[..., None]:
        """Calculate permitted source/sink amounts before running a tick step."""

        @wraps(step)
        def observed(
            context: RealmTickContext,
            realm: RealmState,
            now: datetime,
            content: ContentIndex,
        ) -> None:
            self.context = context
            self.cause = step.__name__
            if step.__name__ == "step_1_production":
                for estate in context.estates:
                    form = content.estate_form(estate.form_id)
                    if set(form.requires_realm_tags) <= {t.id for t in context.tags}:
                        for output in form.production:
                            self.add(
                                "production",
                                output.item_id,
                                int(
                                    daily_share(output.per_day, now, content)
                                    * production_factor(estate, content)
                                ),
                            )
            elif step.__name__ == "step_6_spoilage":
                for stock in (context.stores, *context.larders.values()):
                    for item, amount in stock.items():
                        rate = Fraction(str(content.item(item).spoilage_pct_per_day))
                        self.add(
                            "spoilage",
                            item,
                            -int(amount * rate / (100 * content.economy.tick.per_day)),
                        )
            elif step.__name__ == "step_7_caps":
                self.cap_losses(context, content)
            try:
                step(context, realm, now, content)
            finally:
                self.context = None

        return observed

    def cap_losses(self, context: RealmTickContext, content: ContentIndex) -> None:
        """Predict discarded quantities using the specified plentiful-first rule."""
        for line in context.lines:
            items = [
                i
                for i in context.stores
                if membership(content.item(i), context.lines) == line
            ]
            excess = max(
                0,
                sum(
                    context.stores[i] * line_weight(content.item(i), line)
                    for i in items
                )
                - line.cap,
            )
            for item in sorted(items, key=lambda i: (-context.stores[i], i)):
                weight = line_weight(content.item(item), line)
                lost = min(context.stores[item], (excess + weight - 1) // weight)
                self.add("cap", item, -lost)
                excess = max(0, excess - lost * weight)
        for item, amount in context.stores.items():
            if membership(content.item(item), context.lines) is None:
                self.add(
                    "cap",
                    item,
                    -max(0, amount - warehouse_cap(content.item(item), content)),
                )
