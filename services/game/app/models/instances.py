"""Individually held, finite private resource access."""

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


class ItemInstance(Base):
    """One nonfungible inventory slot, including depleted and invalid trophies."""

    __tablename__ = "item_instances"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="key")
    template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    holder_character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id"), index=True
    )
    discovered_by_character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    discovered_by_name: Mapped[str] = mapped_column(String(20), nullable=False)
    realm_id: Mapped[str] = mapped_column(ForeignKey("realm_state.id"), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    uses_total: Mapped[int] = mapped_column(Integer, nullable=False)
    uses_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    bound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    __table_args__ = (
        CheckConstraint(
            "uses_total > 0 AND uses_remaining >= 0 AND uses_remaining <= uses_total",
            name="ck_instances_uses",
        ),
        CheckConstraint(
            "state IN ('active', 'deprecated', 'invalid', 'depleted')",
            name="ck_instances_state",
        ),
    )
