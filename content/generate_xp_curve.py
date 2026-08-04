"""Generate the checked-in level 1-99 placeholder XP table.

Each level after 1 adds ``floor(100 * 1.12 ** (level - 2))`` XP to the
cumulative requirement. This is intentionally conventional scaffolding, not
game balance.
"""

import json
import math
from pathlib import Path

FORMULA = "level 1 = 0; each next level adds floor(100 * 1.12 ** (level - 2))"


def build_curve() -> dict[str, object]:
    """Return the deterministic XP curve document."""
    cumulative_xp = 0
    levels: list[dict[str, int]] = []
    for level in range(1, 100):
        if level > 1:
            cumulative_xp += math.floor(100 * 1.12 ** (level - 2))
        levels.append({"level": level, "xp": cumulative_xp})
    return {"formula": FORMULA, "levels": levels}


if __name__ == "__main__":
    output = Path(__file__).with_name("xp_curve.json")
    output.write_text(json.dumps(build_curve(), indent=2) + "\n", encoding="utf-8")
