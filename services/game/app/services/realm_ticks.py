"""Ordered realm tick extension points (design §14.5). Caller holds realm lock."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.content.loader import ContentIndex
from app.engine.projects import erode_project
from app.models import RealmProjectRun, RealmState
from app.services.realms import as_utc


@dataclass
class RealmTickContext:
    """Preloaded mutable tick state; load before catch-up and flush after it.

    Steps must use this state without issuing queries. Future stores, estates,
    and demand lines belong here so database work stays independent of ticks.
    """

    active_run: RealmProjectRun | None


def step_0_arrivals(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 20: receive due caravan shipments; isolated realms have no caravans."""
    if realm.isolated:
        return


def step_1_production(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: add estate production."""


def step_2_larder_upkeep(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: consume estate larders; isolated realms have no upkeep."""
    if realm.isolated:
        return


def step_3_estate_upkeep(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: share upkeep above reserve; isolated realms have no upkeep."""
    if realm.isolated:
        return


def step_4_realm_upkeep(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14/18: consume upkeep and coin bullion; skip isolated realm upkeep."""
    if realm.isolated:
        return


def step_5_projects(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Erode idle funding; Prompt 14 adds realm contributions before erosion."""
    run = context.active_run
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
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: spoil stores and larders."""


def step_7_caps(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 14: discard excess stock."""


def step_8_gauges(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 15: update deficit gauges; isolated realms have no upkeep or decay."""
    if realm.isolated:
        return


def step_9_decay(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
) -> None:
    """Prompt 15: advance or recover decay; isolated realms have no decay."""
    if realm.isolated:
        return


def step_10_lines(
    context: RealmTickContext, realm: RealmState, now: datetime, content: ContentIndex
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
