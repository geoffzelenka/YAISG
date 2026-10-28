"""Character and profile persistence models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
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
    stance: Mapped[str] = mapped_column(String(128), nullable=False)
    hp: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    hp_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_realm_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Residence is derived from this estate, independently of current presence.
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
    xp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
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
    gold: Mapped[int] = mapped_column(BigInteger, nullable=False)
    premium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint("gold >= 0", name="ck_currency_gold_nonnegative"),
        CheckConstraint("premium >= 0", name="ck_currency_premium_nonnegative"),
    )


class Estate(Base):
    """A persistent estate located in a realm."""

    __tablename__ = "estates"

    decay_stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="fed", server_default="fed"
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    realm_id: Mapped[str] = mapped_column(String(128), nullable=False)
    form_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    gauge: Mapped[float] = mapped_column(
        Float, nullable=False, default=0, server_default="0"
    )
    shed_progress: Mapped[float] = mapped_column(
        Float, nullable=False, default=0, server_default="0"
    )
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
    """A world realm or a character-owned isolated realm instance."""

    __tablename__ = "realm_state"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    isolated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id")
    )
    current_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    treasury: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    pending_transition: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    last_tick_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    gauge: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    decay_stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="fed", server_default="fed"
    )
    shed_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    vote_cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    treasury_band: Mapped[str | None] = mapped_column(String(32))
    tag_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class RealmTag(Base):
    """A project tag, ordered by acquisition and stamped with its D4 node."""

    __tablename__ = "realm_tags"

    realm_id: Mapped[str] = mapped_column(
        ForeignKey("realm_state.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    project_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("realm_project_runs.id")
    )
    __table_args__ = (
        UniqueConstraint("realm_id", "seq", name="uq_realm_tags_seq"),
        CheckConstraint("seq > 0", name="ck_realm_tags_seq_positive"),
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
        CheckConstraint("cycles >= 0", name="ck_reward_log_cycles_nonnegative"),
    )


class RealmProjectRun(Base):
    """One project attempt; progress is stored in integer milli-units per line."""

    __tablename__ = "realm_project_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    realm_id: Mapped[str] = mapped_column(ForeignKey("realm_state.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    kicked_off_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id"))
    kicked_off_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    required: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    contributed: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    last_contribution_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    build_completes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "status IN ('funding', 'building', 'complete', 'failed')",
            name="ck_project_run_status",
        ),
        Index(
            "uq_realm_active_project",
            "realm_id",
            unique=True,
            sqlite_where=text("status IN ('funding', 'building')"),
            postgresql_where=text("status IN ('funding', 'building')"),
        ),
    )


class RealmContribution(Base):
    """Immutable consumed goods, including the realm's own (null) contributor."""

    __tablename__ = "realm_contributions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("realm_project_runs.id"), nullable=False, index=True
    )
    character_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("characters.id"))
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity_milli: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contributed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("quantity_milli > 0", name="ck_contribution_positive"),
    )


class EstateLarder(Base):
    """Goods irreversibly deposited toward estate upkeep."""

    __tablename__ = "estate_larder"
    estate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("estates.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    quantity_milli: Mapped[int] = mapped_column(BigInteger, nullable=False)
    __table_args__ = (
        CheckConstraint("quantity_milli > 0", name="ck_estate_larder_positive"),
    )
