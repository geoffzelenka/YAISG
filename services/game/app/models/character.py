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
    text,
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
    # Cache of the residence-defining home estate's realm (§7.5).
    home_estate_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
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
    owner_character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    realm_id: Mapped[str] = mapped_column(String(128), nullable=False)
    form_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    relocating_to_realm_id: Mapped[str | None] = mapped_column(String(128))
    relocation_completes_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    upgrade_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class EstateOwnershipHistory(Base):
    """Historied ownership interval for an estate."""

    __tablename__ = "estate_ownership_history"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    estate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("estates.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id"), nullable=False
    )
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    relinquished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RealmState(Base):
    """Current development identity for a realm."""

    __tablename__ = "realm_state"
    realm_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    transition_to_node_id: Mapped[str | None] = mapped_column(String(128))
    transition_completes_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    treasury: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RealmEdgeProgress(Base):
    """Per-realm progress on a development edge."""

    __tablename__ = "realm_edge_progress"
    realm_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    edge_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class RealmProject(Base):
    """Per-realm communal project state."""

    __tablename__ = "realm_projects"
    realm_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contribution_totals: Mapped[dict[str, int]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RealmContribution(Base):
    """Audit record for a project contribution."""

    __tablename__ = "realm_contributions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    realm_id: Mapped[str] = mapped_column(String(128), nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    contributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


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


class ActiveActionRecord(Base):
    """The single repeating action currently assigned to a character."""

    __tablename__ = "active_actions"

    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    action_id: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RewardLog(Base):
    """An immutable summary of one productive action resolution."""

    __tablename__ = "reward_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cycles: Mapped[int] = mapped_column(Integer, nullable=False)
    xp: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    items: Mapped[dict[str, dict[str, int]]] = mapped_column(JSON, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'")
    )
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        CheckConstraint("cycles > 0", name="ck_reward_log_cycles_positive"),
    )
