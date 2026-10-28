"""Pure consumable stack transfers and reactive trigger validation."""

from app.content.loader import ContentIndex
from app.engine.core import CharacterState, resolve_caps
from app.engine.equipment import EquipmentError
from app.engine.inventory import inventory_fits


def belt_capacity(
    state: CharacterState, belt_item: str | None, content: ContentIndex
) -> int:
    """Add the equipped belt's physical positions to the resolved cap."""
    equip = content.item(belt_item).equip if belt_item is not None else None
    positions = equip.belt_slots or 0 if equip is not None else 0
    return resolve_caps(state, content).belt_slots + positions


def transfer_stack(
    state: CharacterState,
    previous: tuple[str, int] | None,
    item_id: str | None,
    quantity: int,
    content: ContentIndex,
) -> dict[str, int]:
    """Return an atomic inventory plan using the §7.5 over-cap rule."""
    inventory = dict(state.inventory)
    if previous is not None:
        old_item, old_quantity = previous
        inventory[old_item] = inventory.get(old_item, 0) + old_quantity
    if item_id is not None:
        if inventory.get(item_id, 0) < quantity:
            raise EquipmentError(
                "MISSING_INPUTS", "Insufficient consumables in inventory"
            )
        inventory[item_id] -= quantity
        if not inventory[item_id]:
            del inventory[item_id]
    limit = resolve_caps(state, content).inventory_slots
    if not inventory_fits(state, inventory, limit, content):
        raise EquipmentError(
            "INVENTORY_FULL", "Inventory cannot hold the returned stack"
        )
    return inventory


def validate_consumable(
    item_id: str, trigger: dict[str, float | bool] | None, content: ContentIndex
) -> None:
    """Require utility items in utility and matching heal/buff belt triggers."""
    try:
        item = content.item(item_id)
    except KeyError:
        raise EquipmentError("UNKNOWN_ITEM", "The item does not exist") from None
    consumable = item.consumable
    if consumable is None or item.instanced:
        raise EquipmentError(
            "INVALID_CONSUMABLE", "The item is not a stackable consumable"
        )
    if trigger is None:
        valid = consumable.utility_for is not None
    else:
        valid = (
            consumable.heal is not None
            and set(trigger) == {"hp_below_pct"}
            and type(trigger["hp_below_pct"]) in (int, float)
            and 0 < trigger["hp_below_pct"] <= 100
        ) or (
            consumable.buff is not None
            and trigger == {"buff_missing": True}
            and type(trigger["buff_missing"]) is bool
        )
    if not valid:
        raise EquipmentError(
            "INVALID_CONSUMABLE", "Consumable kind and holder/trigger do not match"
        )


def change_consumable(
    state: CharacterState,
    previous: tuple[str, int] | None,
    item_id: str | None,
    quantity: int,
    content: ContentIndex,
    *,
    belt_slot: int | None = None,
    belt_item: str | None = None,
    trigger: dict[str, float | bool] | None = None,
) -> dict[str, int]:
    """Validate a setup intent and plan its complete physical transfer."""
    capacity = belt_capacity(state, belt_item, content)
    # Capacity loss never destroys stacks or prevents their return to inventory.
    if belt_slot is not None and (
        belt_slot < 0 or (belt_slot >= capacity and item_id is not None)
    ):
        raise EquipmentError("INVALID_BELT_SLOT", "Belt position exceeds capacity")
    if quantity < 0 or (item_id is None) != (quantity == 0):
        raise EquipmentError("INVALID_CONSUMABLE", "Invalid setup quantity")
    if item_id is not None:
        if belt_slot is not None and trigger is None:
            raise EquipmentError(
                "INVALID_CONSUMABLE", "Belt assignment needs a trigger"
            )
        validate_consumable(item_id, trigger, content)
        if quantity > content.item(item_id).stack_limit:
            raise EquipmentError("INVALID_CONSUMABLE", "Assignment exceeds stack limit")
    elif trigger is not None:
        raise EquipmentError("INVALID_CONSUMABLE", "An empty position has no trigger")
    return transfer_stack(state, previous, item_id, quantity, content)
