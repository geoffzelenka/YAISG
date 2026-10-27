"""Scheduled liveness driver; requests remain authoritative lazy resolvers."""

from datetime import UTC, datetime
from typing import Protocol, cast

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.content.loader import ContentIndex
from app.models import RealmState
from app.services.realms import finalize_realm, prepare_sqlite_write

# Stable application lock key, unrelated to content ids or tunable game rules.
REALM_TICK_LOCK = 1497453383


def run_realm_ticks(
    factory: sessionmaker[Session], content: ContentIndex, now: datetime
) -> bool:
    """Advance all shared realms once, excluding concurrent PostgreSQL drivers."""
    with factory() as session:
        if session.get_bind().dialect.name == "postgresql":
            acquired = session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": REALM_TICK_LOCK},
            )
            if not acquired:
                return False
        else:
            prepare_sqlite_write(session)
        realm_ids = list(
            session.scalars(
                select(RealmState.id)
                .where(RealmState.isolated.is_(False))
                .order_by(RealmState.id)
            )
        )
        for realm_id in realm_ids:
            finalize_realm(session, realm_id, now, content)
        session.commit()
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
    scheduler.start()
    return cast(Scheduler, scheduler)
