"""Pure equipment transfers and slot validation."""

from dataclasses import replace

from app.content.loader import ContentIndex
from app.content.schemas import EquipmentSlot
from app.engine.core import CharacterState, resolve_caps


class EquipmentError(ValueError):
    """A rejected equipment intent with a stable public code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def change_equipment(
    state: CharacterState,
    equipped: dict[str, str],
    slot: EquipmentSlot,
    item_id: str | None,
    content: ContentIndex,
) -> tuple[dict[str, int], dict[str, str]]:
    """Plan an atomic permanent-item transfer, including displaced hands."""
    inventory = dict(state.inventory)
    result = dict(equipped)
    if slot == "utility":
        raise EquipmentError(
            "INVALID_EQUIPMENT_SLOT", "Utility stacks use consumable setup"
        )
    displaced = [slot]
    if item_id is not None:
        try:
            equip = content.item(item_id).equip
        except KeyError:
            raise EquipmentError("UNKNOWN_ITEM", "The item does not exist") from None
        if equip is None:
            raise EquipmentError("NOT_EQUIPPABLE", "The item cannot be equipped")
        allowed: set[str] = {equip.slot}
        if equip.slot in {"ring", "arm"}:
            allowed = {f"left_{equip.slot}", f"right_{equip.slot}"}
        if slot not in allowed:
            raise EquipmentError(
                "INVALID_EQUIPMENT_SLOT", "The item does not fit this slot"
            )
        if any(
            state.skill_levels.get(skill, 1) < level
            for skill, level in equip.requires.items()
        ):
            raise EquipmentError(
                "EQUIPMENT_LEVEL_REQUIRED", "Equipment skill requirements are not met"
            )
        right = (
            content.item(result["right_hand"]).equip if "right_hand" in result else None
        )
        if slot == "left_hand" and right is not None and right.two_handed:
            raise EquipmentError(
                "TWO_HANDED_CONFLICT", "The right-hand item blocks the left hand"
            )
        if inventory.get(item_id, 0) < 1:
            raise EquipmentError("MISSING_INPUTS", "The item is not in inventory")
        inventory[item_id] -= 1
        if inventory[item_id] == 0:
            del inventory[item_id]
        if equip.two_handed:
            displaced.append("left_hand")
    elif slot not in result:
        raise EquipmentError("EQUIPMENT_SLOT_EMPTY", "The equipment slot is empty")
    for target in displaced:
        previous = result.pop(target, None)
        if previous is not None:
            inventory[previous] = inventory.get(previous, 0) + 1
    if item_id is not None:
        result[slot] = item_id
    # Check against the resulting gear: removing a capacity item can lower the cap.
    caps = dict(state.cap_bonuses)
    for direction, sources in ((-1, equipped), (1, result)):
        for identifier in sources.values():
            definition = content.item(identifier).equip
            if definition is not None:
                for cap, amount in definition.cap_bonuses.items():
                    caps[cap] = caps.get(cap, 0) + direction * amount
    limit = resolve_caps(replace(state, cap_bonuses=caps), content).inventory_slots
    if (len(inventory) > limit and len(inventory) > len(state.inventory)) or any(
        qty > content.item(identifier).stack_limit
        for identifier, qty in inventory.items()
        if qty > state.inventory.get(identifier, 0)
    ):
        raise EquipmentError(
            "INVENTORY_FULL", "Inventory cannot hold the displaced equipment"
        )
    return inventory, result
