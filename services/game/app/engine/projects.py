"""Pure project progress arithmetic in integer milli-units."""

from datetime import datetime, timedelta
from fractions import Fraction
from math import ceil

from app.content.schemas import ProjectConfig


def erode_project(
    required: list[int],
    contributed: list[int],
    last_contribution_at: datetime,
    tick_at: datetime,
    settings: ProjectConfig,
    per_day: int,
) -> list[int]:
    """Remove the tick's exact share, carrying fractional rounding by tick index."""
    grace_end = last_contribution_at + timedelta(days=settings.idle_grace_days)
    if tick_at <= grace_end:
        return list(contributed)
    elapsed = Fraction((tick_at - grace_end) // timedelta(microseconds=1), 86400000000)
    index = ceil(elapsed * per_day) - 1
    rate = Fraction(str(settings.erosion_pct_per_day)) / (100 * per_day)
    return [
        max(0, held - (int(need * rate * (index + 1)) - int(need * rate * index)))
        for need, held in zip(required, contributed, strict=True)
    ]
