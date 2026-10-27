"""Persistent realm holdings, derived appetite, and singleton seed marker."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RealmStore(Base):
    """One good held by a realm in milli-units."""

    __tablename__ = "realm_stores"
    realm_id: Mapped[str] = mapped_column(
        ForeignKey("realm_state.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    quantity_milli: Mapped[int] = mapped_column(BigInteger)
    __table_args__ = (
        CheckConstraint("quantity_milli >= 0", name="ck_realm_stores_nonnegative"),
    )


class RealmLine(Base):
    """Materialized demand; amounts use milli-line-units."""

    __tablename__ = "realm_lines"
    realm_id: Mapped[str] = mapped_column(
        ForeignKey("realm_state.id", ondelete="CASCADE"), primary_key=True
    )
    line_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    selector: Mapped[dict[str, Any]] = mapped_column(JSON)
    value_measured: Mapped[bool]
    draw_per_day: Mapped[int] = mapped_column(BigInteger)
    reserve: Mapped[int] = mapped_column(BigInteger)
    cap: Mapped[int] = mapped_column(BigInteger)
    stock: Mapped[int] = mapped_column(BigInteger)
    in_transit: Mapped[int] = mapped_column(BigInteger, default=0)
    budget_gold: Mapped[int] = mapped_column(BigInteger, default=0)


class WorldState(Base):
    """The one-time world creation marker."""

    __tablename__ = "world_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seeded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_caravan_pass: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_version: Mapped[str] = mapped_column(String(64))
    __table_args__ = (CheckConstraint("id = 1", name="ck_world_state_singleton"),)
