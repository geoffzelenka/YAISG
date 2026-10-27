"""Audit records for gold creation and destruction; transfers need no entry."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GoldLedger(Base):
    """Signed gold delta with durable holder identifiers and event time."""

    __tablename__ = "gold_ledger"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cause: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(BigInteger)
    realm_id: Mapped[str | None] = mapped_column(String(128))
    character_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "cause IN ('world_seed', 'mint', 'tutorial_seed', "
            "'tutorial_destroy', 'tax_burn', 'caravan_fee_burn')",
            name="ck_gold_ledger_cause",
        ),
        CheckConstraint(
            "(cause IN ('world_seed', 'mint', 'tutorial_seed') AND amount >= 0) OR "
            "(cause IN ('tutorial_destroy', 'tax_burn', "
            "'caravan_fee_burn') AND amount <= 0)",
            name="ck_gold_ledger_sign",
        ),
    )
