"""Fixed-price custody for individually rolled keys."""

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


class KeyListing(Base):
    """One immutable sale identity per physical instance in market custody."""

    __tablename__ = "key_listings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item_instances.id", ondelete="CASCADE"), unique=True
    )
    seller_character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id"))
    price_gold: Mapped[int] = mapped_column(BigInteger)
    realm_id: Mapped[str] = mapped_column(ForeignKey("realm_state.id"))
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    buyer_character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id")
    )
    __table_args__ = (
        Index("ix_key_listings_seller_status", "seller_character_id", "status"),
        Index("ix_key_listings_status", "status"),
        CheckConstraint("price_gold > 0", name="ck_key_listing_price"),
        CheckConstraint(
            "status IN ('open', 'sold', 'cancelled')", name="ck_key_listing_status"
        ),
    )
