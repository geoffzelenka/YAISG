"""Pure tag activation shared by facilities, bonuses, caps and inertness."""

from collections.abc import Iterable
from dataclasses import dataclass

from app.content.schemas import DecayStage, Tag


@dataclass(frozen=True)
class TagHolder:
    """Resolved emissions and the content-defined weakening factor."""

    tags: tuple[Tag, ...]
    faltering_factor: float


def active_tags(holder: TagHolder, stage: DecayStage) -> tuple[tuple[Tag, float], ...]:
    """Suspend facilities and weaken numeric modifiers, preserving access."""
    weakened = stage not in (DecayStage.FED, DecayStage.STRAINED)
    return tuple(
        (
            tag,
            holder.faltering_factor
            if weakened and tag.kind in {"bonus", "malus"}
            else 1.0,
        )
        for tag in holder.tags
        if not (weakened and tag.kind == "facility")
    )


def tags_present(required: Iterable[str], actual: Iterable[str]) -> bool:
    """Require every declared tag; an empty requirement is unrestricted."""
    return set(required).issubset(actual)


def economy_tags(holder: TagHolder, stage: DecayStage) -> tuple[Tag, ...]:
    """Apply activation and numeric effect weakening to economy consumers."""
    return tuple(
        tag.model_copy(
            update={
                "effects": tag.effects.model_copy(
                    update={
                        "reserve_days_delta": tag.effects.reserve_days_delta * factor,
                        "edge_loss_reduction_pct": tag.effects.edge_loss_reduction_pct
                        * factor,
                    }
                )
            }
        )
        for tag, factor in active_tags(holder, stage)
    )
