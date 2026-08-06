"""Response models shared by game API modules."""

from pydantic import BaseModel

from app.engine import ResolveResult


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
