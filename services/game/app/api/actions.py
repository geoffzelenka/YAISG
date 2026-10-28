"""Active skilling action endpoints and reward feed."""

import uuid
from dataclasses import replace
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas import (
    ActionValues,
    RewardsResponse,
    action_values,
    rewards_response,
)
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import Action
from app.engine import (
    CharacterState,
    ResolveResult,
    effective_cycle_time,
)
from app.engine.combat import player_stats
from app.engine.core import ACTION_RESOLVERS, unmet_requirements
from app.errors import api_error
from app.models import ActiveActionRecord, Character
from app.services.actions import (
    as_utc,
    claim_rewards,
    clear_active_action,
    load_character_state,
    resolve_character,
)

router = APIRouter(tags=["actions"])


class StartActionRequest(BaseModel):
    """Client intent to begin a content-defined action."""

    action_id: str


class StartedActionResponse(BaseModel):
    """Timing data for a newly started action."""

    action_id: str
    cycle_ms: int
    started_at: datetime


class ActionSummary(BaseModel):
    """Current active action timing data."""

    action_id: str
    cycle_ms: int
    started_at: datetime
    last_resolved_at: datetime
    meta: dict[str, Any]


class ActionFeedResponse(BaseModel):
    """Active action plus rewards produced by this request."""

    active: ActionSummary | None
    since_last: RewardsResponse
    stop_reason: str | None


class AvailableAction(ActionValues):
    """Content action annotated with current start eligibility."""

    action_id: str
    name: str
    unlock_level: int
    startable: bool
    blocked_by: list[str]


class AvailableSkillGroup(BaseModel):
    """Actions belonging to one skill, in content order."""

    skill_id: str
    name: str
    actions: list[AvailableAction]


class AvailableActionsResponse(BaseModel):
    """Every character skill action grouped with unmet requirements."""

    skills: list[AvailableSkillGroup]


def _content(request: Request) -> ContentIndex:
    return request.app.state.content  # type: ignore[no-any-return]


def get_character(session: Session, player_id: uuid.UUID) -> Character:
    """Load the player's character or raise the shared missing-character error."""
    character = session.scalar(
        select(Character).where(Character.player_id == player_id)
    )
    if character is None:
        raise api_error(404, "NO_CHARACTER", "Create a character to continue")
    return character


def _rewards(result: ResolveResult) -> RewardsResponse:
    return rewards_response(result)


def _prefer_current_stop_reason(
    feed: ResolveResult, current: ResolveResult
) -> ResolveResult:
    """Preserve a zero-cycle stop that has no corresponding reward-log row."""
    if current.stop_reason is None:
        return feed
    return replace(feed, stop_reason=current.stop_reason)


def _active_summary(
    record: ActiveActionRecord | None,
    state_cycle_ms: int | None,
) -> ActionSummary | None:
    if record is None or state_cycle_ms is None:
        return None
    return ActionSummary(
        action_id=record.action_id,
        cycle_ms=state_cycle_ms,
        started_at=as_utc(record.started_at),
        last_resolved_at=as_utc(record.last_resolved_at),
        meta={key: value for key, value in record.meta.items() if key != "rng_state"},
    )


def _start_blockers(
    action: Action, state: CharacterState, content: ContentIndex
) -> list[str]:
    """Share generic endpoint gates between the availability report and start."""
    blocked = [code.value for code in unmet_requirements(action, state, content)]
    if action.resolver not in ACTION_RESOLVERS:
        blocked.insert(0, "RESOLVER_UNAVAILABLE")
    if action.resolver == "travel":
        blocked.insert(0, "TRAVEL_DESTINATION_REQUIRED")
    if action.resolver == "combat" and action.combatant_id is not None:
        stats = player_stats(
            state, state.equipment, content.combatant(action.combatant_id), content
        )
        if (
            state.hp is not None
            and state.hp * 100
            < stats.max_hp * content.progression.combat.min_engage_hp_pct
        ):
            blocked.append("INSUFFICIENT_HP")
    return blocked


@router.get("/actions/available", response_model=AvailableActionsResponse)
@router.get("/characters/me/actions/available", response_model=AvailableActionsResponse)
async def available_actions(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> AvailableActionsResponse:
    """Return every character skill action with all current start blockers."""
    character = get_character(session, player.id)
    content = _content(request)
    resolve_character(session, character.id, now, content)
    state = load_character_state(session, character.id, content, now)
    groups: list[AvailableSkillGroup] = []
    for skill in content.skills:
        actions: list[AvailableAction] = []
        for action in skill.actions:
            blocked = _start_blockers(action, state, content)
            actions.append(
                AvailableAction(
                    action_id=action.id,
                    name=action.name,
                    unlock_level=action.unlock_level,
                    **action_values(action, state, content).model_dump(),
                    startable=not blocked,
                    blocked_by=blocked,
                )
            )
        groups.append(
            AvailableSkillGroup(skill_id=skill.id, name=skill.name, actions=actions)
        )
    session.commit()
    return AvailableActionsResponse(skills=groups)


@router.post("/actions/start", response_model=StartedActionResponse)
@router.post("/characters/me/action", response_model=StartedActionResponse)
async def start_action(
    body: StartActionRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> StartedActionResponse:
    """Resolve the prior action and atomically replace it with a validated one."""
    character = get_character(session, player.id)
    content = _content(request)
    resolve_character(session, character.id, now, content)
    state = load_character_state(session, character.id, content, now)
    try:
        action = content.action(body.action_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_ACTION", "The action does not exist") from None
    blocked = _start_blockers(action, state, content)
    if blocked:
        message = (
            "Start a journey through /travel/start"
            if blocked[0] == "TRAVEL_DESTINATION_REQUIRED"
            else "The action cannot currently be started"
        )
        raise api_error(409, blocked[0], message)
    clear_active_action(session, character.id)
    session.add(
        ActiveActionRecord(
            character_id=character.id,
            action_id=action.id,
            started_at=now,
            last_resolved_at=now,
            meta={},
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise api_error(
            409, "ACTION_CONFLICT", "Another action change completed concurrently"
        ) from None
    return StartedActionResponse(
        action_id=action.id,
        cycle_ms=(
            player_stats(
                state, state.equipment, content.combatant(action.combatant_id), content
            ).cycle_ms
            if action.resolver == "combat" and action.combatant_id
            else effective_cycle_time(action, state, content)
        ),
        started_at=now,
    )


@router.get("/actions/poll", response_model=ActionFeedResponse)
@router.get("/characters/me/action", response_model=ActionFeedResponse)
async def get_action(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ActionFeedResponse:
    """Resolve the active action and return this request's reward feed."""
    character = get_character(session, player.id)
    content = _content(request)
    resolution = resolve_character(session, character.id, now, content)
    state = load_character_state(session, character.id, content, now)
    cycle_ms = None
    if resolution.active is not None:
        cycle_ms = effective_cycle_time(
            content.action(resolution.active.action_id),
            state,
            content,
        )
    if (
        resolution.active is not None
        and content.action(resolution.active.action_id).resolver == "travel"
    ):
        cycle_ms = int(resolution.active.meta["duration_ms"])
    if (
        resolution.active is not None
        and content.action(resolution.active.action_id).resolver == "combat"
    ):
        cycle_ms = int(resolution.active.meta.get("cycle_ms", cycle_ms or 0))
    feed = claim_rewards(session, character.id, now)
    feed = _prefer_current_stop_reason(feed, resolution.result)
    session.commit()
    return ActionFeedResponse(
        active=_active_summary(resolution.active, cycle_ms),
        since_last=_rewards(feed),
        stop_reason=feed.stop_reason,
    )


@router.post("/actions/stop", response_model=ActionFeedResponse)
@router.delete("/characters/me/action", response_model=ActionFeedResponse)
async def stop_action(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ActionFeedResponse:
    """Resolve final rewards, then stop the current action."""
    character = get_character(session, player.id)
    resolution = resolve_character(session, character.id, now, _content(request))
    feed = claim_rewards(session, character.id, now)
    feed = _prefer_current_stop_reason(feed, resolution.result)
    clear_active_action(session, character.id)
    session.commit()
    return ActionFeedResponse(
        active=None,
        since_last=_rewards(feed),
        stop_reason=feed.stop_reason,
    )
