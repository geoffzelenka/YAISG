"""Authenticated journey previews and starts."""

from dataclasses import replace
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.actions import ActionFeedResponse, _active_summary, get_character
from app.api.schemas import rewards_response
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import DecayStage
from app.engine import CharacterState
from app.engine.travel import complete_step, route, step_cost, travel_profile
from app.errors import api_error
from app.models import ActiveActionRecord, RealmState
from app.services.actions import (
    claim_rewards,
    clear_active_action,
    load_character_state,
    resolve_character,
)
from app.services.realms import stack_tags

router = APIRouter(prefix="/travel", tags=["travel"])


class TravelRequest(BaseModel):
    """Destination and movement mode, never client-calculated prices."""

    model_config = ConfigDict(extra="forbid")
    destination_realm_id: str
    mode: Literal["visit", "relocate"]


def _route(
    state: CharacterState, destination: str, mode: str, content: ContentIndex
) -> list[dict[str, str]]:
    if ":" in state.current_realm_id and destination in {
        content.tutorial.realm_1,
        content.tutorial.realm_2,
    }:
        destination = f"{destination}:{state.current_realm_id.partition(':')[2]}"
    try:
        content.realm(destination)
    except KeyError:
        raise api_error(
            404, "UNKNOWN_REALM", "The destination does not exist"
        ) from None
    if destination == state.current_realm_id:
        raise api_error(409, "ALREADY_THERE", "You are already in that realm")
    if mode == "relocate":
        if content.estate_form(state.estate_form_id).mobility != "mobile":
            raise api_error(409, "ESTATE_FIXED", "A fixed estate cannot relocate")
        if state.estate_realm_id != state.current_realm_id:
            raise api_error(409, "ESTATE_NOT_HERE", "Your estate is in another realm")
    try:
        return route(
            state.current_realm_id,
            destination,
            travel_profile(state, mode, content),
            state.skill_levels.get("travel", 1),
            content,
        )
    except ValueError:
        raise api_error(
            409, "NO_ROUTE", "No usable route reaches the destination"
        ) from None


@router.get("/preview")
async def preview(
    destination_realm_id: str,
    mode: Literal["visit", "relocate"],
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, object]:
    """Resolve prior work and return current terms without starting travel."""
    content: ContentIndex = request.app.state.content
    character = get_character(session, player.id)
    # Lock all route candidates before the estate, including on first touch.
    resolve_character(
        session,
        character.id,
        now,
        content,
        additional_realm_ids={realm.id for realm in content.realms}
        | {
            row.id
            for row in session.scalars(
                select(RealmState).where(RealmState.owner_character_id == character.id)
            )
        },
    )
    state = load_character_state(session, character.id, content, now)
    steps = _route(state, destination_realm_id, mode, content)
    edges = {edge.id: edge for edge in content.map.edges}
    state = replace(
        state,
        realm_states={
            realm.id: (
                realm.current_node_id,
                DecayStage(realm.decay_stage),
                stack_tags(session, realm.id),
            )
            for realm in session.scalars(select(RealmState))
        },
    )
    profile = travel_profile(state, mode, content)
    terms = []
    for step in steps:
        duration, supplies = step_cost(edges[step["edge_id"]], state, profile, content)
        terms.append({**step, "time_ms": duration, "supplies": supplies})
        state, _ = complete_step(
            state, edges[step["edge_id"]], step["destination_realm_id"], mode, content
        )
    session.commit()
    return {"route": terms}


@router.post("/start", response_model=ActionFeedResponse)
async def start(
    body: TravelRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ActionFeedResponse:
    """Replace prior work with a fixed route and pay the first step immediately."""
    content: ContentIndex = request.app.state.content
    character = get_character(session, player.id)
    resolve_character(
        session,
        character.id,
        now,
        content,
        additional_realm_ids={realm.id for realm in content.realms}
        | {
            row.id
            for row in session.scalars(
                select(RealmState).where(RealmState.owner_character_id == character.id)
            )
        },
    )
    state = load_character_state(session, character.id, content, now)
    steps = _route(state, body.destination_realm_id, body.mode, content)
    action = next(
        a for a in content.actions_for_skill("travel") if a.resolver == "travel"
    )
    clear_active_action(session, character.id)
    session.add(
        ActiveActionRecord(
            character_id=character.id,
            action_id=action.id,
            started_at=now,
            last_resolved_at=now,
            meta={"route": steps, "mode": body.mode},
        )
    )
    session.flush()
    # The character lock is already held; never release SQLite's writer lock.
    from app.services.actions import resolve_locked_character

    resolution = resolve_locked_character(session, character.id, now, content)
    feed = claim_rewards(session, character.id, now)
    active = resolution.active
    cycle_ms = int(active.meta["duration_ms"]) if active else None
    response = ActionFeedResponse(
        active=_active_summary(active, cycle_ms),
        since_last=rewards_response(feed),
        stop_reason=resolution.result.stop_reason,
    )
    session.commit()
    return response
