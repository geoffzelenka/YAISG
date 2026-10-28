"""Daily cleanup of expired, inactive guest identities."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import prepare_sqlite_write
from app.guest_settings import GuestSettings
from app.models import RefreshToken, User


def purge_guests(session: Session, settings: GuestSettings, now: datetime) -> int:
    """Delete guests whose last activity is older than the authored TTL."""
    prepare_sqlite_write(session)
    cutoff = now - timedelta(days=settings.guest_ttl_days)
    users = session.scalars(
        select(User)
        .where(
            User.kind == "guest",
            func.coalesce(User.last_activity_at, User.created_at) < cutoff,
        )
        .order_by(User.id)
        .with_for_update()
    )
    count = 0
    for user in users:
        try:
            with session.begin_nested():
                session.execute(
                    delete(RefreshToken).where(RefreshToken.user_id == user.id)
                )
                session.delete(user)
                session.flush()
            count += 1
        except Exception:
            logging.getLogger(__name__).exception(
                "Auth guest purge failed: user_id=%s", user.id
            )
    return count


def run_guest_purge(
    factory: sessionmaker[Session], settings: GuestSettings, now: datetime
) -> None:
    """Roll back and log failures without terminating the daily job."""
    try:
        with factory() as session:
            if session.get_bind().dialect.name == "postgresql" and not session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": 1497453386},
            ):
                return
            purge_guests(session, settings, now)
            session.commit()
    except Exception:
        logging.getLogger(__name__).exception("Auth guest purge failed")
