"""Active skilling action endpoints and reward feed."""

import uuid
from dataclasses import replace
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas import RewardsResponse, rewards_response
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.engine import ErrorCode, ResolveResult, can_start, effective_cycle_time
from app.engine.core import input_payment
from app.errors import api_error
from app.models import ActiveActionRecord, Character
from app.services.actions import (
    as_utc,
    claim_rewards,
    clear_active_action,
    load_character_state,
    resolve_character,
)

router = APIRouter(prefix="/characters/me", tags=["actions"])


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


class ActionFeedResponse(BaseModel):
    """Active action plus rewards produced by this request."""

    active: ActionSummary | None
    since_last: RewardsResponse
    stop_reason: str | None


class AvailableAction(BaseModel):
    """Content action annotated with current start eligibility."""

    action_id: str
    name: str
    unlock_level: int
    cycle_ms: int
    startable: bool
    blocked_by: list[str]


class AvailableSkillGroup(BaseModel):
    """Actions belonging to one skill, in content order."""

    skill_id: str
    name: str
    actions: list[AvailableAction]


class AvailableActionsResponse(BaseModel):
    """All realm-visible actions grouped by skill."""

    skills: list[AvailableSkillGroup]


def _content(request: Request) -> ContentIndex:
    return request.app.state.content  # type: ignore[no-any-return]


def _character(session: Session, player_id: uuid.UUID) -> Character:
    character = session.scalar(
        select(Character).where(Character.player_id == player_id)
    )
    if character is None:
        raise api_error(404, "NO_CHARACTER", "Create a character to continue")
    return character


def _realm_matches(required: tuple[str, ...], realm_tags: set[str]) -> bool:
    return "*" in required or bool(set(required) & realm_tags)


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
    )


@router.get("/actions/available", response_model=AvailableActionsResponse)
async def available_actions(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> AvailableActionsResponse:
    """Return every action permitted by the realm with start blockers."""
    character = _character(session, player.id)
    content = _content(request)
    resolve_character(session, character.id, now, content)
    session.commit()
    state = load_character_state(session, character.id)
    realm_tags = set(content.development_node(state.realm_node_id).tags)
    groups: list[AvailableSkillGroup] = []
    for skill in content.skills:
        actions: list[AvailableAction] = []
        for action in skill.actions:
            if action.requires.realm_tags and not _realm_matches(
                action.requires.realm_tags, realm_tags
            ):
                continue
            blocked: list[str] = []
            if state.skill_levels.get(action.skill_id, 1) < action.unlock_level:
                blocked.append(ErrorCode.INSUFFICIENT_LEVEL.value)
            if input_payment(state.inventory, action, content) is None:
                blocked.append(ErrorCode.MISSING_INPUTS.value)
            actions.append(
                AvailableAction(
                    action_id=action.id,
                    name=action.name,
                    unlock_level=action.unlock_level,
                    cycle_ms=effective_cycle_time(action, state, content),
                    startable=not blocked,
                    blocked_by=blocked,
                )
            )
        groups.append(
            AvailableSkillGroup(skill_id=skill.id, name=skill.name, actions=actions)
        )
    return AvailableActionsResponse(skills=groups)


@router.post("/action", response_model=StartedActionResponse)
async def start_action(
    body: StartActionRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> StartedActionResponse:
    """Resolve the prior action and atomically replace it with a validated one."""
    character = _character(session, player.id)
    content = _content(request)
    resolve_character(session, character.id, now, content)
    state = load_character_state(session, character.id)
    try:
        action = content.action(body.action_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_ACTION", "The action does not exist") from None
    validation = can_start(action.id, state, content)
    if isinstance(validation, ErrorCode):
        raise api_error(409, validation.value, "The action cannot currently be started")
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
        cycle_ms=effective_cycle_time(action, state, content),
        started_at=now,
    )


@router.get("/action", response_model=ActionFeedResponse)
async def get_action(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ActionFeedResponse:
    """Resolve the active action and return this request's reward feed."""
    character = _character(session, player.id)
    content = _content(request)
    resolution = resolve_character(session, character.id, now, content)
    state = load_character_state(session, character.id)
    cycle_ms = None
    if resolution.active is not None:
        cycle_ms = effective_cycle_time(
            content.action(resolution.active.action_id),
            state,
            content,
        )
    feed = claim_rewards(session, character.id, now)
    feed = _prefer_current_stop_reason(feed, resolution.result)
    session.commit()
    return ActionFeedResponse(
        active=_active_summary(resolution.active, cycle_ms),
        since_last=_rewards(feed),
        stop_reason=feed.stop_reason,
    )


@router.delete("/action", response_model=ActionFeedResponse)
async def stop_action(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ActionFeedResponse:
    """Resolve final rewards, then stop the current action."""
    character = _character(session, player.id)
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
