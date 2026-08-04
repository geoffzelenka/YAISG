"""Pure skill-level calculations."""

from collections.abc import Sequence

from app.content.schemas import XpLevel


def level_for_xp(xp: int, curve: Sequence[XpLevel]) -> int:
    """Return the highest level whose cumulative XP requirement is met."""
    if xp < 0:
        raise ValueError("xp cannot be negative")
    for entry in reversed(curve):
        if xp >= entry.xp:
            return entry.level
    raise ValueError("XP curve must include a level reachable at zero XP")


def xp_progress(xp: int, curve: Sequence[XpLevel]) -> tuple[int, int]:
    """Return in-level and remaining XP for a contiguous, level-ordered curve."""
    level = level_for_xp(xp, curve)
    current_requirement = curve[level - 1].xp
    if level == curve[-1].level:
        return xp - current_requirement, 0
    next_requirement = curve[level].xp
    return xp - current_requirement, next_requirement - xp
