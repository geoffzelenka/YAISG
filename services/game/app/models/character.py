"""Character and profile persistence models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Character(Base):
    """A player's single v1 game character."""

    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    name_normalized: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    realm_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CharacterSkill(Base):
    """Mutable progression for one content-defined skill."""

    __tablename__ = "character_skills"

    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (
        CheckConstraint("xp >= 0", name="ck_character_skills_xp_nonnegative"),
        CheckConstraint("level >= 1", name="ck_character_skills_level_positive"),
    )


class Currency(Base):
    """Character currency balances; premium is reserved and unused in v1."""

    __tablename__ = "currency"

    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    gold: Mapped[int] = mapped_column(Integer, nullable=False)
    premium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint("gold >= 0", name="ck_currency_gold_nonnegative"),
        CheckConstraint("premium >= 0", name="ck_currency_premium_nonnegative"),
    )


class Estate(Base):
    """A persistent estate located in a realm."""

    __tablename__ = "estates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    realm_id: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    upgrade_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class EstateUpgrade(Base):
    """An upgrade installed in one estate slot."""

    __tablename__ = "estate_upgrades"

    estate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("estates.id", ondelete="CASCADE"), primary_key=True
    )
    slot_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    upgrade_id: Mapped[str] = mapped_column(String(128), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Inventory(Base):
    """One item stack in a character inventory."""

    __tablename__ = "inventories"

    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_inventories_quantity_positive"),
    )
