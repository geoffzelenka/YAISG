"""Secret ballots: only aggregate choices and public participation persist."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RealmVote(Base):
    """One upgrade ballot with no individual choices."""

    __tablename__ = "realm_votes"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    realm_id: Mapped[str] = mapped_column(ForeignKey("realm_state.id"))
    upgrade_id: Mapped[str] = mapped_column(String(128))
    called_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("characters.id"))
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="open")
    yes_weight: Mapped[int] = mapped_column(BigInteger, default=0)
    no_weight: Mapped[int] = mapped_column(BigInteger, default=0)
    eligible_weight: Mapped[int] = mapped_column(BigInteger)
    fee_gold: Mapped[int] = mapped_column(BigInteger)
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'passed', 'failed')", name="ck_vote_status"
        ),
        CheckConstraint(
            "yes_weight >= 0 AND no_weight >= 0 AND fee_gold >= 0 AND "
            "eligible_weight > 0 AND yes_weight + no_weight <= eligible_weight",
            name="ck_vote_weights",
        ),
        Index(
            "uq_open_realm_vote",
            "realm_id",
            unique=True,
            sqlite_where=text("status = 'open'"),
            postgresql_where=text("status = 'open'"),
        ),
    )


class RealmVoteEligibility(Base):
    """Immutable eligibility and weight, plus participation, never a choice."""

    __tablename__ = "realm_vote_eligibility"
    vote_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("realm_votes.id"), primary_key=True
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id"), primary_key=True
    )
    weight: Mapped[int] = mapped_column(BigInteger)
    voted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("weight > 0", name="ck_vote_eligibility_weight"),)
