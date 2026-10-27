"""Global order slots and durable execution history."""

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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MarketOrder(Base):
    """One occupied slot, including escrow and everything awaiting collection."""

    __tablename__ = "market_orders"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id"), index=True
    )
    side: Mapped[str] = mapped_column(String(4))
    item_id: Mapped[str] = mapped_column(String(128))
    unit_price: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(BigInteger)
    quantity_remaining: Mapped[int] = mapped_column(BigInteger)
    escrow_gold_remaining: Mapped[int] = mapped_column(BigInteger, default=0)
    fill_items: Mapped[int] = mapped_column(BigInteger, default=0)
    fill_gold: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(16), default="open")
    realm_id: Mapped[str] = mapped_column(ForeignKey("realm_state.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("side IN ('buy', 'sell')", name="ck_market_order_side"),
        CheckConstraint(
            "status IN ('open', 'collectable', 'closed')", name="ck_market_order_status"
        ),
        CheckConstraint(
            "unit_price > 0 AND quantity > 0 "
            "AND quantity_remaining >= 0 AND quantity_remaining <= quantity",
            name="ck_market_order_quantity",
        ),
        CheckConstraint(
            "escrow_gold_remaining >= 0 AND fill_items >= 0 AND fill_gold >= 0",
            name="ck_market_order_holdings",
        ),
        CheckConstraint(
            "(status = 'open' AND quantity_remaining > 0) OR "
            "(status <> 'open' AND quantity_remaining = 0 "
            "AND escrow_gold_remaining = 0)",
            name="ck_market_order_remainder",
        ),
        CheckConstraint(
            "status <> 'closed' OR (fill_items = 0 AND fill_gold = 0 "
            "AND closed_at IS NOT NULL)",
            name="ck_market_order_closed",
        ),
        Index(
            "ix_market_order_book",
            "item_id",
            "side",
            "status",
            "unit_price",
            "created_at",
            "id",
        ),
    )


class MarketMatch(Base):
    """Execution history survives later order retention purges."""

    __tablename__ = "market_matches"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    maker_order_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    taker_order_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    buyer_character_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    seller_character_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    item_id: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(BigInteger)
    unit_price: Mapped[int] = mapped_column(BigInteger)
    tax_gold: Mapped[int] = mapped_column(BigInteger)
    burned_gold: Mapped[int] = mapped_column(BigInteger)
    tax_realm_id: Mapped[str] = mapped_column(String(128))
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "quantity > 0 AND unit_price > 0 AND tax_gold >= 0 "
            "AND burned_gold >= 0 AND burned_gold <= tax_gold "
            "AND tax_gold <= quantity * unit_price",
            name="ck_market_match_amounts",
        ),
    )
