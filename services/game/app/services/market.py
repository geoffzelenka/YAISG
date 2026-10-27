"""Market projections from locked, resolved realm holdings."""

from decimal import ROUND_CEILING, localcontext
from decimal import Decimal as D

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import Selector
from app.engine.market import PRECISION, QuoteContext, multiplier, quote, spot_bid
from app.engine.stores import Line, line_weight, membership, warehouse_cap
from app.models import RealmLine, RealmState, RealmStore


def market_contexts(
    session: Session, realm: RealmState, content: ContentIndex
) -> dict[str, tuple[Line | None, QuoteContext]]:
    """Assign every item to at most one line, preserving its stored budget."""
    with localcontext() as precision:
        precision.prec = PRECISION
        return _market_contexts(session, realm, content)


def _market_contexts(
    session: Session, realm: RealmState, content: ContentIndex
) -> dict[str, tuple[Line | None, QuoteContext]]:
    lines = tuple(
        Line(
            r.line_key,
            Selector.model_validate(r.selector),
            r.draw_per_day,
            r.reserve,
            r.cap,
            r.stock,
            r.value_measured,
            r.in_transit,
            r.budget_gold,
        )
        for r in session.scalars(
            select(RealmLine).where(RealmLine.realm_id == realm.id)
        )
    )
    stores = {
        r.item_id: r.quantity_milli
        for r in session.scalars(
            select(RealmStore).where(RealmStore.realm_id == realm.id)
        )
    }
    node = content.development_node(realm.current_node_id)
    settings = content.economy.market
    margin = (
        D(str(settings.m)) * 100 if node.margin_pct is None else D(str(node.margin_pct))
    )
    result = {}
    for item in sorted(content.items, key=lambda item: (item.reference_price, item.id)):
        line = membership(item, lines)
        stock = line.stock if line else stores.get(item.id, 0)
        cap = line.cap if line else max(stock, warehouse_cap(item, content))
        result[item.id] = (
            line,
            QuoteContext(
                item.reference_price,
                line_weight(item, line) if line else 1,
                D(stock) / 1000,
                D(cap) / 1000,
                D(line.reserve if line else 0) / 1000,
                settings,
                margin,
                line.budget_gold if line else 0,
                realm.treasury,
                stores.get(item.id, 0) // 1000,
            ),
        )
    return result


def spot_ask(ctx: QuoteContext) -> int | None:
    """Return the rounded spot unit ask only when a whole item is for sale."""
    if ctx.available <= 0 or ctx.stock - ctx.reserve < ctx.w:
        return None
    with localcontext() as precision:
        precision.prec = PRECISION
        return int(
            (
                ctx.reference_price
                * multiplier(ctx.stock, ctx.cap, ctx.settings)
                * (1 + ctx.margin_pct / 100)
            ).to_integral_value(rounding=ROUND_CEILING)
        )


def market_view(
    session: Session, realm: RealmState, content: ContentIndex
) -> dict[str, object]:
    """Publish funded appetites and sale inventory without private balances."""
    contexts = market_contexts(session, realm, content)
    grouped: dict[str, dict[str, object]] = {}
    sales = []
    missing_by_line: dict[str, int] = {}
    best_capacity: dict[str, int] = {}
    for item_id, (line, ctx) in contexts.items():
        ask = spot_ask(ctx)
        if ask is not None:
            sales.append(
                {
                    "item_id": item_id,
                    "quantity": min(
                        ctx.available, int((ctx.stock - ctx.reserve) / ctx.w)
                    ),
                    "spot_ask": ask,
                }
            )
        if line is None:
            continue
        funded = quote(ctx, item_id, "sell", max(1, int((ctx.cap - ctx.stock) / ctx.w)))
        member = {
            "item_id": item_id,
            "spot_bid": spot_bid(ctx) if funded.max_quantity else None,
            "funded_quantity": funded.max_quantity,
            "funded_total": quote(ctx, item_id, "sell", funded.max_quantity).gold
            if funded.max_quantity
            else 0,
        }
        if line.key not in grouped:
            grouped[line.key] = {
                "line_key": line.key,
                "selector": line.selector.model_dump(),
                "stock": line.stock,
                "reserve": line.reserve,
                "cap": line.cap,
                "draw_per_day": line.draw_per_day,
                "spot_bid": member["spot_bid"],
                "funded_quantity": funded.max_quantity * ctx.w * 1000,
                "funded_total": member["funded_total"],
                "days_of_cover": line.stock / line.draw_per_day
                if line.draw_per_day
                else None,
                "members": [],
            }
        capacity = funded.max_quantity * ctx.w * 1000
        if capacity > best_capacity.get(line.key, -1):
            best_capacity[line.key] = capacity
            grouped[line.key].update(
                spot_bid=member["spot_bid"],
                funded_quantity=capacity,
                funded_total=member["funded_total"],
            )
        members = grouped[line.key]["members"]
        assert isinstance(members, list)
        members.append(member)
        missing = max(0, line.reserve - line.stock - funded.max_quantity * ctx.w * 1000)
        missing_by_line[line.key] = min(missing_by_line.get(line.key, missing), missing)
    return {
        "lines": list(grouped.values()),
        "for_sale": sales,
        "shortfalls": [
            {"line_key": key, "missing_milli": missing}
            for key, missing in missing_by_line.items()
            if missing
        ],
        "decay_stage": realm.decay_stage,
        "gauge_days": realm.gauge,
        "treasury_band": realm.treasury_band,
    }
