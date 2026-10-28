"""Persistence of validated equipment transfers under the character lock."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CharacterEquipment, Inventory


def persist_equipment(
    session: Session,
    character_id: uuid.UUID,
    inventory: dict[str, int],
    equipment: dict[str, str],
) -> None:
    """Apply only changed holdings; leave unrelated inventory and slots intact."""
    stacks = {
        row.item_id: row
        for row in session.scalars(
            select(Inventory).where(Inventory.character_id == character_id)
        )
    }
    for item_id, row in stacks.items():
        quantity = inventory.get(item_id, 0)
        if quantity == 0:
            session.delete(row)
        elif quantity != row.quantity:
            row.quantity = quantity
    for item_id, quantity in inventory.items():
        if item_id not in stacks:
            session.add(
                Inventory(character_id=character_id, item_id=item_id, quantity=quantity)
            )
    slots = {
        row.slot: row
        for row in session.scalars(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character_id
            )
        )
    }
    for slot, equipped_row in slots.items():
        replacement = equipment.get(slot)
        if replacement is None:
            session.delete(equipped_row)
        elif replacement != equipped_row.item_id:
            equipped_row.item_id = replacement
    for slot, item_id in equipment.items():
        if slot not in slots:
            session.add(
                CharacterEquipment(
                    character_id=character_id, slot=slot, item_id=item_id, quantity=1
                )
            )
