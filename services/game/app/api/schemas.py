"""Response models shared by game API modules."""

from pydantic import BaseModel

from app.content.loader import ContentIndex
from app.content.schemas import Action
from app.engine import CharacterState, ResolveResult, effective_cycle_time, effective_xp
from app.engine.core import proficiency_pct, taper_factor, xp_factors


class RewardsResponse(BaseModel):
    """JSON representation of an engine resolve result."""

    cycles_completed: int
    xp_gained: dict[str, int]
    items_consumed: dict[str, int]
    items_gained: dict[str, int]
    overflowed_items: dict[str, int]
    level_ups: dict[str, tuple[int, ...]]
    stop_reason: str | None


def rewards_response(result: ResolveResult) -> RewardsResponse:
    """Convert an engine result to the shared API reward shape."""
    return RewardsResponse(
        cycles_completed=result.cycles_completed,
        xp_gained=dict(result.xp_gained),
        items_consumed=dict(result.items_consumed),
        items_gained=dict(result.items_gained),
        overflowed_items=dict(result.overflowed_items),
        level_ups=dict(result.level_ups),
        stop_reason=result.stop_reason,
    )


class ActionValues(BaseModel):
    """Server-derived action rates; XP multipliers are reported before taper."""

    cycle_ms: int
    xp_per_cycle: int
    xp_bonus_uncapped: float
    xp_bonus_capped: float
    proficiency_pct: float
    taper_factor: float


def action_values(
    action: Action, state: CharacterState, content: ContentIndex
) -> ActionValues:
    """Build the same effective-value report for profile and availability."""
    uncapped, capped = xp_factors(action, state, content)
    return ActionValues(
        cycle_ms=effective_cycle_time(action, state, content),
        xp_per_cycle=effective_xp(action, state, content),
        xp_bonus_uncapped=(uncapped - 1) * 100,
        xp_bonus_capped=(capped - 1) * 100,
        proficiency_pct=proficiency_pct(action, state, content),
        taper_factor=taper_factor(action, state, content),
    )
