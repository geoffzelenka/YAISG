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


def xp_progress(xp: int, curve: Sequence[XpLevel]) -> tuple[int, int | None]:
    """Return in-level and remaining XP for a contiguous, level-ordered curve."""
    level = level_for_xp(xp, curve)
    current_requirement = curve[level - 1].xp
    if level == curve[-1].level:
        return xp - current_requirement, None
    next_requirement = curve[level].xp
    return xp - current_requirement, next_requirement - xp


def tier_for_level(level: int, thresholds: Sequence[int]) -> int:
    """Return the number of tier thresholds reached."""
    if not 1 <= level <= 100:
        raise ValueError("level must be between 1 and 100")
    return sum(level >= threshold for threshold in thresholds)
