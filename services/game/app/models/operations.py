"""Durable operational counters and shared mutation-rate windows."""

import uuid

from sqlalchemy import BigInteger, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MetricDelta(Base):
    """Append-only counter deltas committed with the events they describe."""

    __tablename__ = "metric_deltas"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)


class MutationWindow(Base):
    """One shared allowance per account (which owns at most one character)."""

    __tablename__ = "mutation_windows"
    auth_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    window: Mapped[int] = mapped_column(BigInteger, index=True)
    attempts: Mapped[int] = mapped_column(Integer)
