"""Pure, fixed-precision realm pricing in whole line units and gold."""

from dataclasses import dataclass, replace
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from typing import Literal

from app.content.loader import ContentIndex
from app.content.schemas import MarketConfig
from app.engine.stores import Line

D = Decimal
PRECISION = 50


@dataclass(frozen=True)
class QuoteContext:
    """Explicit holdings, limits and curve settings for one item."""

    reference_price: int
    w: int
    stock: Decimal
    cap: Decimal
    reserve: Decimal
    settings: MarketConfig
    margin_pct: Decimal
    budget: int
    treasury: int
    available: int = 0


@dataclass(frozen=True)
class Quote:
    """Requested total and the largest currently executable whole quantity."""

    gold: int
    max_quantity: int


def multiplier(stock: Decimal, cap: Decimal, settings: MarketConfig) -> Decimal:
    """Return the spot bid multiple, clamped at full stores."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        if cap <= 0:
            return D(str(settings.f))
        return (
            D(str(settings.f))
            + (D(str(settings.c)) - D(str(settings.f)))
            * (1 - min(stock, cap) / cap) ** settings.k
        )


def integral(a: Decimal, b: Decimal, cap: Decimal, settings: MarketConfig) -> Decimal:
    """Integrate nonnegative stock, pricing any above-cap stretch at the floor."""
    if not 0 <= a <= b:
        raise ValueError("pricing interval must satisfy 0 <= a <= b")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        f, c = D(str(settings.f)), D(str(settings.c))
        if cap <= 0:
            return f * (b - a)
        excess = f * max(D(0), b - max(a, cap))
        a, b = min(a, cap), min(b, cap)
        power = settings.k + 1
        return (
            excess
            + f * (b - a)
            + (c - f) * cap / power * ((1 - a / cap) ** power - (1 - b / cap) ** power)
        )


def total(ctx: QuoteContext, side: Literal["buy", "sell"], quantity: int) -> int:
    """Round a valid integrated trade in the realm's favour."""
    with localcontext() as precision:
        precision.prec = PRECISION
        delta = D(quantity * ctx.w)
        a, b = (
            (ctx.stock, ctx.stock + delta)
            if side == "sell"
            else (ctx.stock - delta, ctx.stock)
        )
        value = D(ctx.reference_price) / ctx.w * integral(a, b, ctx.cap, ctx.settings)
        if side == "buy":
            value *= 1 + ctx.margin_pct / 100
        return int(
            value.to_integral_value(
                rounding=ROUND_FLOOR if side == "sell" else ROUND_CEILING
            )
        )


def quote(
    ctx: QuoteContext, item: str, side: Literal["buy", "sell"], quantity: int
) -> Quote:
    """Quote a request and bisect the largest funded quantity without mutation.

    Requests beyond physical limits are priced only up to those limits. The
    returned maximum lets callers reject an all-or-nothing trade explicitly.
    """
    with localcontext() as precision:
        precision.prec = PRECISION
        return _quote(ctx, item, side, quantity)


def _quote(
    ctx: QuoteContext, item: str, side: Literal["buy", "sell"], quantity: int
) -> Quote:
    if quantity <= 0 or ctx.w <= 0 or side not in ("buy", "sell"):
        raise ValueError(f"invalid quote request for {item}")
    physical = max(
        0,
        int(
            (ctx.cap - ctx.stock if side == "sell" else ctx.stock - ctx.reserve) / ctx.w
        ),
    )
    if side == "buy":
        physical = min(physical, ctx.available)
    lo, hi = 0, physical
    if side == "sell":
        if min(ctx.budget, ctx.treasury) <= 0:
            hi = 0
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if total(ctx, side, mid) <= min(ctx.budget, ctx.treasury):
                lo = mid
            else:
                hi = mid - 1
    else:
        lo = hi
    return Quote(total(ctx, side, min(quantity, physical)) if physical else 0, lo)


def allocate_budgets(
    lines: tuple[Line, ...],
    treasury: int,
    content: ContentIndex,
    unit_values: dict[str, int] | None = None,
) -> tuple[Line, ...]:
    """Divide the treasury by unmet reference value; discard fractional gold."""
    weights = [
        max(0, line.cap - line.stock)
        * (
            unit_values[line.key]
            if unit_values is not None
            else 1
            if line.value_measured
            else next(
                i.reference_price for i in content.items if line.selector.matches(i)
            )
        )
        * (2 if line.stock < line.reserve else 1)
        for line in lines
    ]
    denominator = sum(weights)
    return tuple(
        replace(
            line, budget_gold=treasury * weight // denominator if denominator else 0
        )
        for line, weight in zip(lines, weights, strict=True)
    )


def treasury_band(days: Decimal, previous: str | None, settings: MarketConfig) -> str:
    """Apply symmetric hysteresis to the four content-authored boundaries."""
    boundaries = [D(str(n)) for n in settings.band_days]
    band = (
        int(previous)
        if previous in {"0", "1", "2", "3", "4"}
        else sum(days >= b for b in boundaries)
    )
    hysteresis = D(str(settings.band_hysteresis_pct)) / 100
    while band < 4 and days >= boundaries[band] * (1 + hysteresis):
        band += 1
    while band > 0 and days < boundaries[band - 1] * (1 - hysteresis):
        band -= 1
    return str(band)


def spot_bid(ctx: QuoteContext) -> str:
    """Publish a spot bid with eight fixed decimal places."""
    with localcontext() as precision:
        precision.prec = PRECISION
        value = ctx.reference_price * multiplier(ctx.stock, ctx.cap, ctx.settings)
        return format(value.quantize(D("0.00000001"), rounding=ROUND_HALF_EVEN), "f")


def band_from_upkeep(
    treasury: int, upkeep: Decimal, previous: str | None, settings: MarketConfig
) -> str:
    """An empty treasury has no cover, including when upkeep is zero."""
    with localcontext() as precision:
        precision.prec = PRECISION
        if treasury == 0:
            return "0"
        days = D(treasury) / upkeep if upkeep else D("Infinity")
        return treasury_band(days, previous, settings)
