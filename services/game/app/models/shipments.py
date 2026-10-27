"""Durable caravan goods and expected road losses."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RealmShipment(Base):
    """Whole goods dispatched once and credited at a due realm tick."""

    __tablename__ = "realm_shipments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    from_realm_id: Mapped[str] = mapped_column(ForeignKey("realm_state.id"))
    to_realm_id: Mapped[str] = mapped_column(ForeignKey("realm_state.id"), index=True)
    item_id: Mapped[str] = mapped_column(String(128))
    quantity_sent: Mapped[int] = mapped_column(BigInteger)
    quantity_arriving: Mapped[int] = mapped_column(BigInteger)
    goods_gold: Mapped[int] = mapped_column(BigInteger)
    fee_gold: Mapped[int] = mapped_column(BigInteger)
    dispatched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arrives_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="in_transit")
    __table_args__ = (
        CheckConstraint(
            "quantity_sent > 0 AND quantity_arriving >= 0 "
            "AND quantity_arriving <= quantity_sent",
            name="ck_shipment_goods",
        ),
        CheckConstraint("goods_gold >= 0 AND fee_gold >= 0", name="ck_shipment_gold"),
        CheckConstraint(
            "status IN ('in_transit', 'arrived')", name="ck_shipment_status"
        ),
    )
