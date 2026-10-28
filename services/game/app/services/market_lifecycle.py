"""Idempotent expiry and retention under the market's realm serialization."""

from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.content.loader import ContentIndex
from app.models import MarketOrder, RealmState
from app.services.metrics import compact_deltas
from app.services.order_book import cancel_order
from app.services.realms import prepare_sqlite_write

# Application lock identity, independent of authored content.
MARKET_LIFECYCLE_LOCK = 1497453384


def run_market_lifecycle(
    factory: sessionmaker[Session], content: ContentIndex, now: datetime
) -> bool:
    """Expire escrow into slots and purge only empty, sufficiently old slots.

    Realm locks serialize against matching, cancellation and collection. No
    character state is read or credited, so no character lock is needed.
    """
    with factory() as session:
        prepare_sqlite_write(session)
        if session.get_bind().dialect.name == "postgresql" and not session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": MARKET_LIFECYCLE_LOCK},
        ):
            return False
        for realm_id in sorted(session.scalars(select(RealmState.id))):
            session.scalar(
                select(RealmState).where(RealmState.id == realm_id).with_for_update()
            )
        cutoff = now - timedelta(days=content.economy.market.retention_days)
        orders = session.scalars(
            select(MarketOrder)
            .where(
                ((MarketOrder.status == "open") & (MarketOrder.expires_at <= now))
                | ((MarketOrder.status == "closed") & (MarketOrder.closed_at < cutoff))
            )
            .order_by(MarketOrder.unit_price, MarketOrder.created_at, MarketOrder.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        for order in orders:
            if order.status == "open":
                cancel_order(order)
            else:
                session.delete(order)
        compact_deltas(session)
        session.commit()
    return True
