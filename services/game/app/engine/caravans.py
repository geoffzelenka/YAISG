"""Pure routes, expected losses and exhaustive integral shipment selection."""

from dataclasses import dataclass
from fractions import Fraction
from math import ceil

from app.content.schemas import CaravanConfig, MapEdge, MapPack
from app.engine.market import QuoteContext, total


@dataclass(frozen=True)
class Route:
    """Cheapest base-time route, retaining edges for current road effects."""

    hours: Fraction
    edges: tuple[MapEdge, ...]


def remoteness(pack: MapPack) -> dict[tuple[str, str], Route]:
    """Compute directed all-pairs shortest paths with deterministic edge ties."""
    routes: dict[tuple[str, str], Route] = {}
    nodes = sorted({n for e in pack.edges for n in (e.a, e.b)})
    for edge in sorted(pack.edges, key=lambda e: e.id):
        if edge.min_travel_level != 1:
            continue
        for a, b in (
            ((edge.a, edge.b),)
            if edge.one_way
            else ((edge.a, edge.b), (edge.b, edge.a))
        ):
            route = Route(Fraction(str(edge.base_time_s)) / 3600, (edge,))
            if (a, b) not in routes or route.hours < routes[a, b].hours:
                routes[a, b] = route
    for k in nodes:
        for a in nodes:
            for b in nodes:
                if a == b or (a, k) not in routes or (k, b) not in routes:
                    continue
                left, right = routes[a, k], routes[k, b]
                hours = left.hours + right.hours
                if (a, b) not in routes or hours < routes[a, b].hours:
                    routes[a, b] = Route(hours, left.edges + right.edges)
    return routes


def survival(route: Route, reductions: dict[str, Fraction]) -> Fraction:
    """Multiply edge survival after both endpoints' capped road reductions."""
    result = Fraction(1)
    for edge in route.edges:
        reduction = min(
            Fraction(100),
            reductions.get(edge.a, Fraction(0)) + reductions.get(edge.b, Fraction(0)),
        )
        result *= 1 - Fraction(str(edge.base_loss_pct)) / 100 * (1 - reduction / 100)
    return result


@dataclass(frozen=True)
class Candidate:
    """Largest feasible whole shipment for a seller and item."""

    sent: int
    delivered: int
    goods: int
    fee: int

    @property
    def unit_cost(self) -> Fraction:
        """Compare delivered prices without floating point ties."""
        return Fraction(self.goods + self.fee, self.delivered)


def candidate(
    seller: QuoteContext,
    buyer: QuoteContext,
    need: int,
    capacity: int,
    route: Route,
    retained: Fraction,
    settings: CaravanConfig,
) -> Candidate | None:
    """Search downward: floor delivery and ceil fees need not be monotonic.

    Exhaustive selection preserves the largest-q requirement even around
    rounding discontinuities where a binary feasibility search is invalid.
    """
    if retained <= 0 or need <= 0:
        return None
    # floor(q * retained) <= whole need iff q * retained < whole need + 1.
    delivery_limit = ceil(Fraction(need // (buyer.w * 1000) + 1) / retained) - 1
    maximum = min(
        delivery_limit,
        seller.available,
        int((seller.stock - seller.reserve) / seller.w),
        capacity // seller.reference_price,
    )
    for q in range(maximum, 0, -1):
        delivered = int(q * retained)
        if delivered <= 0 or delivered * buyer.w * 1000 > need:
            continue
        goods = total(seller, "buy", q)
        fee = ceil(
            q
            * seller.reference_price
            * Fraction(str(settings.fee_pct_per_hour))
            * route.hours
            / 100
        )
        if goods + fee <= min(buyer.treasury, total(buyer, "sell", delivered)):
            return Candidate(q, delivered, goods, fee)
    return None
