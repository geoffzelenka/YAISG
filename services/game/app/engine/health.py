"""Pure health formulas shared by lazy reads and the future combat resolver."""

from datetime import datetime

from app.content.loader import ContentIndex
from app.engine.core import CharacterState


def maximum_hp(state: CharacterState, armour_hp: float, content: ContentIndex) -> float:
    """Combine the authored Vigor formula and permanent armour contributions."""
    combat = content.progression.combat
    return (
        combat.base_hp
        + state.skill_levels.get("vigor", 1) * combat.hp_per_level
        + armour_hp
    )


def regenerate_hp(
    hp: float, maximum: float, updated_at: datetime, now: datetime, regen_per_min: float
) -> float:
    """Regenerate fractional HP without rounding loss or backwards-clock damage."""
    minutes = max(0.0, (now - updated_at).total_seconds() / 60)
    return min(maximum, max(0.0, hp) + maximum * regen_per_min * minutes)
