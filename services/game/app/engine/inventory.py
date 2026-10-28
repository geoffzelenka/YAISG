"""Shared inventory capacity rules for physical holder transfers."""

from collections.abc import Mapping

from app.content.loader import ContentIndex
from app.engine.core import CharacterState


def inventory_fits(
    state: CharacterState,
    inventory: Mapping[str, int],
    limit: int,
    content: ContentIndex,
) -> bool:
    """Permit over-cap transfers only when usage does not increase (§7.5)."""
    usage = len(inventory) + len(state.instances)
    previous = len(state.inventory) + len(state.instances)
    return not (
        (usage > limit and usage > previous)
        or any(
            amount > content.item(identifier).stack_limit
            for identifier, amount in inventory.items()
            if amount > state.inventory.get(identifier, 0)
        )
    )
