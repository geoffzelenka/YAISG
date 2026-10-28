"""Permanent character equipment holders."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CharacterEquipment(Base):
    """One permanent item in a concrete character slot."""

    __tablename__ = "character_equipment"
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    slot: Mapped[str] = mapped_column(String(16), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint(
            "quantity > 0 AND (slot = 'utility' OR quantity = 1)",
            name="ck_equipment_quantity",
        ),
        CheckConstraint(
            "slot IN ('head','chest','gloves','legs','feet','neck',"
            "'left_arm','right_arm','left_ring','right_ring','belt','cape',"
            "'right_hand','left_hand','utility')",
            name="ck_equipment_slot",
        ),
    )
