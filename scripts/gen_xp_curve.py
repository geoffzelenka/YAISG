"""Generate the exact v0.8 per-level XP costs using Decimal search."""

import json
from decimal import Decimal, localcontext
from pathlib import Path


def build_curve() -> list[int]:
    """Find an amplitude whose floored costs total exactly ten million."""
    with localcontext() as context:
        context.prec = 100
        ratio = Decimal(2) ** (Decimal(1) / 7)
        powers = [ratio**level for level in range(1, 100)]
        low, high = Decimal(0), Decimal(10_000_000)
        for _ in range(400):
            amplitude = (low + high) / 2
            costs = [int(amplitude * power) for power in powers]
            total = sum(costs)
            if total == 10_000_000:
                return costs
            if total < 10_000_000:
                low = amplitude
            else:
                high = amplitude
    raise RuntimeError("No exact XP curve found at the search precision")


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "content" / "xp_curve.json"
    output.write_text(json.dumps(build_curve(), indent=2) + "\n", encoding="utf-8")
