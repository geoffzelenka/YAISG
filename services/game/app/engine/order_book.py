"""Exact whole-gold seller tax arithmetic for the global book."""

from fractions import Fraction
from math import ceil

from app.content.schemas import MarketConfig


def seller_tax(gross: int, market: MarketConfig) -> tuple[int, int]:
    """Ceil the seller's tax and floor its destroyed share without float drift."""
    tax = ceil(gross * Fraction(str(market.tax_pct)) / 100)
    burned = tax * Fraction(str(market.tax_burn_pct)) // 100
    return tax, burned
