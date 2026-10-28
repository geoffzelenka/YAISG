"""Simulate a disposable player-less world, never touching the configured DB."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import DecayStage
from app.db import Base
from app.engine.market import quote
from app.models import RealmState, RealmStore
from app.services.market import market_contexts
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
    arrival_bids_check: str = "passed"


def check_seed(content: ContentIndex, *, days: int = 30) -> list[SeedReport]:
    """Simulate the requested days, stopping at the first failing health check."""
    if days <= 0:
        raise ValueError("seed-check days must be positive")
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            start = datetime(2026, 1, 1, tzinfo=UTC)
            create_world(session, content, start)
            realms = list(session.scalars(select(RealmState).order_by(RealmState.id)))
            unhealthy: set[str] = set()
            unfunded: set[str] = set()
            interval = timedelta(days=1) / content.economy.tick.per_day
            for tick in range(1, days * content.economy.tick.per_day + 1):
                for realm in realms:
                    resolve_realm(session, realm, start + tick * interval, content)
                    if realm.id in content.tutorial.arrival_realms:
                        contexts = market_contexts(session, realm, content)
                        if not any(
                            content.item(item_id).tier == 1
                            and quote(context, item_id, "sell", 1).max_quantity > 0
                            for item_id, (_, context) in contexts.items()
                        ):
                            unfunded.add(realm.id)
                    if realm.decay_stage not in (DecayStage.FED, DecayStage.STRAINED):
                        unhealthy.add(realm.id)
                        break
                if unhealthy:
                    break
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
                    "failed" if realm.id in unfunded else "passed",
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
            f"treasury={report.treasury} stores_milli={report.stores} "
            f"arrival_bids={report.arrival_bids_check}"
        )
    if any(report.arrival_bids_check == "failed" for report in reports):
        raise SystemExit("Seed check failed: an arrival realm lacks funded tier 1 bids")
    if any(report.reached_faltering for report in reports):
        raise SystemExit("Seed check failed: a realm reached Faltering")


if __name__ == "__main__":
    main()
