"""Scheduled liveness driver; requests remain authoritative lazy resolvers."""

import logging
from datetime import UTC, datetime
from typing import Protocol, cast

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.content.loader import ContentIndex
from app.models import RealmState
from app.services.caravans import run_caravan_pass
from app.services.guest_purge import run_guest_purge
from app.services.market_lifecycle import run_market_lifecycle
from app.services.realms import finalize_realm, prepare_sqlite_write

# Stable application lock key, unrelated to content ids or tunable game rules.
REALM_TICK_LOCK = 1497453383


def run_realm_ticks(
    factory: sessionmaker[Session], content: ContentIndex, now: datetime
) -> bool:
    """Advance all shared realms once, excluding concurrent PostgreSQL drivers."""
    # A dedicated connection holds a session lock across per-realm transactions.
    # Always unlock before returning the connection to the pool.
    with factory() as guard:
        connection = guard.connection()
        postgres = connection.dialect.name == "postgresql"
        if postgres and not connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": REALM_TICK_LOCK}
        ):
            return False
        try:
            realm_ids = list(
                connection.scalars(
                    select(RealmState.id)
                    .where(RealmState.isolated.is_(False))
                    .order_by(RealmState.id)
                )
            )
            for realm_id in realm_ids:
                try:
                    with factory() as session:
                        prepare_sqlite_write(session)
                        finalize_realm(session, realm_id, now, content)
                        session.commit()
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Realm tick failed: realm_id=%s", realm_id
                    )
            try:
                with factory() as session:
                    run_caravan_pass(session, content, now)
                    session.commit()
            except Exception:
                logging.getLogger(__name__).exception("Caravan pass failed")
        finally:
            if postgres:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": REALM_TICK_LOCK}
                )
        return True


class Scheduler(Protocol):
    """Lifecycle surface supplied by APScheduler."""

    def shutdown(self, wait: bool = True) -> None:
        """Stop accepting jobs and wait for active work."""


def start_scheduler(factory: sessionmaker[Session], content: ContentIndex) -> Scheduler:
    """Start one APScheduler instance; lifespan owns its shutdown."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="UTC")

    def advance() -> None:
        run_realm_ticks(factory, content, datetime.now(UTC))

    scheduler.add_job(
        advance,
        "interval",
        seconds=86400 / content.economy.tick.per_day,
        id="realm_tick",
        coalesce=True,
        max_instances=1,
    )

    def expire_orders() -> None:
        try:
            run_market_lifecycle(factory, content, datetime.now(UTC))
        except Exception:
            logging.getLogger(__name__).exception("Market lifecycle failed")

    scheduler.add_job(
        expire_orders,
        "interval",
        seconds=content.economy.market.lifecycle_interval_seconds,
        id="market_lifecycle",
        coalesce=True,
        max_instances=1,
    )
    guest_settings = content.auth

    def purge_inactive_guests() -> None:
        run_guest_purge(factory, content, guest_settings, datetime.now(UTC))

    scheduler.add_job(
        purge_inactive_guests,
        "interval",
        days=1,
        id="guest_purge",
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    return cast(Scheduler, scheduler)
