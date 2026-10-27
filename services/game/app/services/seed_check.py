"""Simulate a disposable player-less world, never touching the configured DB."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import DecayStage
from app.db import Base
from app.models import RealmState, RealmStore
from app.services.realms import resolve_realm
from app.services.world import create_world


@dataclass(frozen=True)
class SeedReport:
    """Final private operator data and health throughout the simulation."""

    realm_id: str
    gauge: float
    treasury: int
    stores: dict[str, int]
    reached_faltering: bool


def check_seed(content: ContentIndex) -> list[SeedReport]:
    """Run thirty days one tick at a time, detecting even transient starvation."""
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            start = datetime(2026, 1, 1, tzinfo=UTC)
            create_world(session, content, start)
            realms = list(session.scalars(select(RealmState).order_by(RealmState.id)))
            unhealthy: set[str] = set()
            interval = timedelta(days=1) / content.economy.tick.per_day
            for tick in range(1, 30 * content.economy.tick.per_day + 1):
                for realm in realms:
                    resolve_realm(session, realm, start + tick * interval, content)
                    if realm.decay_stage not in (DecayStage.FED, DecayStage.STRAINED):
                        unhealthy.add(realm.id)
            return [
                SeedReport(
                    realm.id,
                    realm.gauge,
                    realm.treasury,
                    {
                        s.item_id: s.quantity_milli
                        for s in session.scalars(
                            select(RealmStore).where(RealmStore.realm_id == realm.id)
                        )
                    },
                    realm.id in unhealthy,
                )
                for realm in realms
            ]
    finally:
        engine.dispose()


def main() -> None:
    """Print operator holdings and return a failing exit status for starvation."""
    from app.content.runtime import CONTENT

    reports = check_seed(CONTENT)
    for report in reports:
        print(
            f"{report.realm_id}: gauge={report.gauge:.6f} "
            f"treasury={report.treasury} stores_milli={report.stores}"
        )
    if any(report.reached_faltering for report in reports):
        raise SystemExit("Seed check failed: a realm reached Faltering")


if __name__ == "__main__":
    main()
