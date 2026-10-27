"""Ordered realm tick extension points (design §14.5). Caller holds realm lock."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.projects import erode_project
from app.models import RealmState
from app.services.projects import active_run
from app.services.realms import as_utc


def step_0_arrivals(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 20: receive due caravan shipments; isolated realms have no caravans."""
    if realm.isolated:
        return


def step_1_production(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: add estate production."""


def step_2_larder_upkeep(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: consume estate larders; isolated realms have no upkeep."""
    if realm.isolated:
        return


def step_3_estate_upkeep(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: share upkeep above reserve; isolated realms have no upkeep."""
    if realm.isolated:
        return


def step_4_realm_upkeep(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14/18: consume upkeep and coin bullion; skip isolated realm upkeep."""
    if realm.isolated:
        return


def step_5_projects(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Erode idle funding; Prompt 14 adds realm contributions before erosion."""
    run = active_run(session, realm.id)
    if run is None or run.status != "funding":
        return
    run.contributed = erode_project(
        [line["quantity"] * 1000 for line in run.required],
        run.contributed,
        as_utc(run.last_contribution_at),
        now,
        content.economy.project,
        content.economy.tick.per_day,
    )
    if now > as_utc(run.last_contribution_at) + timedelta(
        days=content.economy.project.idle_grace_days
    ) and not any(run.contributed):
        run.status = "failed"
        run.failed_at = now


def step_6_spoilage(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: spoil stores and larders."""


def step_7_caps(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: discard excess stock."""


def step_8_gauges(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 15: update deficit gauges; isolated realms have no upkeep or decay."""
    if realm.isolated:
        return


def step_9_decay(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 15: advance or recover decay; isolated realms have no decay."""
    if realm.isolated:
        return


def step_10_lines(
    session: Session, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14/16: recompute lines, including isolated realms' project lines.

    Skip only market budgets, treasury bands and tax work for isolated realms.
    """


TICK_STEPS = (
    step_0_arrivals,
    step_1_production,
    step_2_larder_upkeep,
    step_3_estate_upkeep,
    step_4_realm_upkeep,
    step_5_projects,
    step_6_spoilage,
    step_7_caps,
    step_8_gauges,
    step_9_decay,
    step_10_lines,
)
