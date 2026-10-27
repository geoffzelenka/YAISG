"""Realm development, map, project contribution, and relocation endpoints."""

import uuid
from datetime import datetime, timedelta
from typing import cast

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.schemas import RewardsResponse, rewards_response
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import CapBonus, ItemQuantity, MapCost, Modifier
from app.engine import path_cost, relocation_cost
from app.errors import api_error
from app.models import (
    Character,
    Currency,
    Estate,
    Inventory,
    RealmContribution,
    RealmEdgeProgress,
    RealmProject,
    RealmState,
)
from app.services.actions import claim_rewards, clear_active_action, resolve_character
from app.services.realms import (
    award_edge_progress,
    finalize_realm,
    finalize_realms,
    finalize_relocation,
    prepare_sqlite_write,
)

router = APIRouter(tags=["realms"])


class NodeIdentity(BaseModel):
    """A realm's current development-node identity."""

    id: str
    name: str
    tags: tuple[str, ...]
    modifiers: tuple[Modifier, ...]
    cap_bonuses: tuple[CapBonus, ...]


class PendingTransition(BaseModel):
    """A visible realm transition window."""

    to_node_id: str
    completes_at: datetime


class ProjectProgress(BaseModel):
    """An active project and contribution totals by target."""

    project_id: str
    name: str
    targets: tuple[ItemQuantity, ...]
    contribution_totals: dict[str, int]


class EdgeProgress(BaseModel):
    """Progress toward one outgoing development edge."""

    edge_id: str
    progress: int
    target: int


class RealmResponse(BaseModel):
    """Current public gameplay state for one realm."""

    id: str
    name: str
    node: NodeIdentity
    pending_transition: PendingTransition | None
    active_projects: list[ProjectProgress]
    outgoing_edges: list[EdgeProgress]


class ContributionRequest(BaseModel):
    """Requested project input contribution."""

    item_id: str
    quantity: int


class ContributionResponse(BaseModel):
    """Accepted contribution and resulting project state."""

    accepted_quantity: int
    project: ProjectProgress
    completed: bool


class RelocateRequest(BaseModel):
    """Requested destination realm."""

    realm_id: str


class RelocateResponse(BaseModel):
    """Charged relocation and any rewards resolved before departure."""

    realm_id: str
    relocating_to_realm_id: str | None
    relocation_completes_at: datetime | None
    cost: MapCost
    final_rewards: RewardsResponse


class RelocationPreviewResponse(BaseModel):
    """Computed relocation terms without changing character state."""

    realm_id: str
    destination_realm_id: str
    cost: MapCost


def _content(request: Request) -> ContentIndex:
    return cast(ContentIndex, request.app.state.content)


def _character(session: DatabaseSession, player_id: uuid.UUID) -> Character:
    character = session.scalar(
        select(Character).where(Character.player_id == player_id)
    )
    if character is None:
        raise api_error(404, "NO_CHARACTER", "Create a character to continue")
    return character


def _relocation_cost_for(
    content: ContentIndex, estate: Estate, destination_realm_id: str
) -> MapCost:
    """Validate a destination and compute the estate's path-based cost."""
    try:
        content.realm(destination_realm_id)
    except KeyError:
        raise api_error(
            404, "UNKNOWN_REALM", "The destination does not exist"
        ) from None
    if destination_realm_id == estate.realm_id:
        raise api_error(409, "ALREADY_THERE", "The estate is already in that realm")
    if estate.status != "active" or estate.relocating_to_realm_id is not None:
        raise api_error(409, "ESTATE_BUSY", "The estate is not active")
    try:
        route = path_cost(estate.realm_id, destination_realm_id, content)
    except ValueError:
        raise api_error(
            409, "UNREACHABLE", "No route reaches the destination"
        ) from None
    return relocation_cost(route, content.estate_form(estate.form_id), content)


def _get_or_create_realm_state(
    session: DatabaseSession, content: ContentIndex, realm_id: str
) -> RealmState:
    """Create first-touch realm state while tolerating a concurrent creator."""
    state = session.get(RealmState, realm_id)
    if state is not None:
        return state
    state = RealmState(
        realm_id=realm_id,
        node_id=content.realm(realm_id).starting_node_id,
        treasury=0,
        data={},
    )
    try:
        with session.begin_nested():
            session.add(state)
            session.flush()
    except IntegrityError:
        statement = select(RealmState).where(RealmState.realm_id == realm_id)
        if session.get_bind().dialect.name != "sqlite":
            statement = statement.with_for_update()
        existing = session.scalar(statement)
        if existing is None:
            raise
        return existing
    return state


def _realm_response(
    session: DatabaseSession,
    content: ContentIndex,
    realm_id: str,
    state: RealmState | None,
) -> RealmResponse:
    realm = content.realm(realm_id)
    node_id = state.node_id if state is not None else realm.starting_node_id
    node = content.development_node(node_id)
    stored_projects = {
        value.project_id: value
        for value in session.scalars(
            select(RealmProject).where(RealmProject.realm_id == realm_id)
        )
    }
    projects = []
    for project_id in node.projects:
        stored = stored_projects.get(project_id)
        if stored is not None and stored.status != "active":
            continue
        definition = content.project(project_id)
        projects.append(
            ProjectProgress(
                project_id=project_id,
                name=definition.name,
                targets=definition.targets,
                contribution_totals=dict(stored.contribution_totals) if stored else {},
            )
        )
    stored_edges = {
        value.edge_id: value.progress
        for value in session.scalars(
            select(RealmEdgeProgress).where(RealmEdgeProgress.realm_id == realm_id)
        )
    }
    outgoing = [
        EdgeProgress(
            edge_id=edge.id,
            progress=stored_edges.get(edge.id, 0),
            target=edge.progress_target,
        )
        for edge in content.development_edges
        if edge.from_node == node_id and edge.kind == "development"
    ]
    pending = None
    if state is not None and state.transition_to_node_id is not None:
        assert state.transition_completes_at is not None
        pending = PendingTransition(
            to_node_id=state.transition_to_node_id,
            completes_at=state.transition_completes_at,
        )
    return RealmResponse(
        id=realm.id,
        name=realm.name,
        node=NodeIdentity(
            id=node.id,
            name=node.name,
            tags=node.tags,
            modifiers=node.modifiers,
            cap_bonuses=node.cap_bonuses,
        ),
        pending_transition=pending,
        active_projects=projects,
        outgoing_edges=outgoing,
    )


@router.get("/realms", response_model=list[RealmResponse])
async def get_realms(
    request: Request, now: ServerNow, session: DatabaseSession
) -> list[RealmResponse]:
    """Return all realms after lazily finalizing due transitions."""
    content = _content(request)
    prepare_sqlite_write(session)
    states = finalize_realms(
        session, {realm.id for realm in content.realms}, now, content
    )
    result = []
    for realm in content.realms:
        result.append(_realm_response(session, content, realm.id, states[realm.id]))
    session.commit()
    return result


@router.get("/realms/{realm_id}", response_model=RealmResponse)
async def get_realm(
    realm_id: str, request: Request, now: ServerNow, session: DatabaseSession
) -> RealmResponse:
    """Return one realm after lazily finalizing its transition."""
    content = _content(request)
    try:
        content.realm(realm_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist") from None
    state = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    response = _realm_response(session, content, realm_id, state)
    session.commit()
    return response


@router.get("/map")
async def get_map(request: Request) -> dict[str, object]:
    """Return the content-defined realm graph without requiring authentication."""
    content = _content(request)
    return {
        "nodes": [
            {
                "realm_id": realm.id,
                "name": realm.name,
                "position": content.map.positions.get(realm.id),
            }
            for realm in content.realms
        ],
        "edges": list(content.map.edges),
    }


@router.post(
    "/realms/{realm_id}/projects/{project_id}/contribute",
    response_model=ContributionResponse,
)
async def contribute(
    realm_id: str,
    project_id: str,
    body: ContributionRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ContributionResponse:
    """Consume inventory and atomically advance one offered realm project."""
    content = _content(request)
    try:
        content.realm(realm_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist") from None
    character = _character(session, player.id)
    resolve_character(
        session,
        character.id,
        now,
        content,
        additional_realm_ids={realm_id},
    )
    state = _get_or_create_realm_state(session, content, realm_id)
    if state.transition_to_node_id is not None:
        raise api_error(
            409,
            "REALM_TRANSITIONING",
            "The realm is already transitioning to another node",
        )
    node = content.development_node(state.node_id)
    if project_id not in node.projects:
        raise api_error(404, "UNKNOWN_PROJECT", "The project is not available")
    definition = content.project(project_id)
    target = next((v for v in definition.targets if v.item_id == body.item_id), None)
    if body.quantity <= 0 or target is None:
        raise api_error(409, "INVALID_CONTRIBUTION", "The contribution is invalid")
    statement = select(RealmProject).where(
        RealmProject.realm_id == realm_id,
        RealmProject.project_id == project_id,
    )
    if session.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    project = session.scalar(statement)
    if project is None:
        project = RealmProject(
            realm_id=realm_id,
            project_id=project_id,
            contribution_totals={},
            status="active",
        )
        session.add(project)
        session.flush()
    if project.status != "active":
        raise api_error(404, "UNKNOWN_PROJECT", "The project is not available")
    totals = dict(project.contribution_totals)
    remaining = target.qty - totals.get(body.item_id, 0)
    if remaining <= 0:
        raise api_error(409, "INVALID_CONTRIBUTION", "That target is already filled")
    accepted = min(body.quantity, remaining)
    stack = session.get(Inventory, (character.id, body.item_id))
    if stack is None or stack.quantity < accepted:
        raise api_error(409, "MISSING_INPUTS", "The contribution is not affordable")
    stack.quantity -= accepted
    if stack.quantity == 0:
        session.delete(stack)
    totals[body.item_id] = totals.get(body.item_id, 0) + accepted
    project.contribution_totals = totals
    session.add(
        RealmContribution(
            realm_id=realm_id,
            project_id=project_id,
            character_id=character.id,
            item_id=body.item_id,
            quantity=accepted,
            contributed_at=now,
        )
    )
    completed = all(
        totals.get(value.item_id, 0) >= value.qty for value in definition.targets
    )
    if completed:
        project.status = "completed"
        project.completed_at = now
        for award in definition.awards:
            award_edge_progress(
                session,
                realm_id,
                award.edge_id,
                award.progress,
                f"project:{project_id}",
                now,
                content,
            )
            # A filled award starts departure immediately. Later awards in the
            # same project are skipped under the same rule that rejects all
            # further awards while a transition is pending.
            if state.transition_to_node_id is not None:
                break
    session.commit()
    return ContributionResponse(
        accepted_quantity=accepted,
        project=ProjectProgress(
            project_id=project_id,
            name=definition.name,
            targets=definition.targets,
            contribution_totals=totals,
        ),
        completed=completed,
    )


@router.post("/characters/me/relocate", response_model=RelocateResponse)
async def relocate(
    body: RelocateRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> RelocateResponse:
    """Stop active work, charge path cost, and move the home estate."""
    content = _content(request)
    character = _character(session, player.id)
    resolution = resolve_character(session, character.id, now, content)
    rewards = claim_rewards(session, character.id, now)
    clear_active_action(session, character.id)
    estate = session.get(Estate, character.home_estate_id)
    currency = session.get(Currency, character.id)
    if estate is None or currency is None:
        raise RuntimeError(f"character {character.id} has incomplete relocation state")
    cost = _relocation_cost_for(content, estate, body.realm_id)
    relocation_stacks: dict[str, Inventory] = {}
    for entry in cost.items:
        stack = session.get(Inventory, (character.id, entry.item_id))
        if stack is None or stack.quantity < entry.qty:
            raise api_error(409, "MISSING_INPUTS", "Relocation items are missing")
        relocation_stacks[entry.item_id] = stack
    if currency.gold < cost.gold:
        raise api_error(409, "INSUFFICIENT_GOLD", "Relocation gold is insufficient")
    currency.gold -= cost.gold
    for entry in cost.items:
        stack = relocation_stacks[entry.item_id]
        stack.quantity -= entry.qty
        if stack.quantity == 0:
            session.delete(stack)
    completes_at = None
    if cost.time_ms == 0:
        estate.realm_id = body.realm_id
        character.realm_id = body.realm_id
    else:
        completes_at = now + timedelta(milliseconds=cost.time_ms)
        estate.status = "relocating"
        estate.relocating_to_realm_id = body.realm_id
        estate.relocation_completes_at = completes_at
    final_rewards = rewards_response(rewards)
    if final_rewards.stop_reason is None:
        final_rewards.stop_reason = resolution.result.stop_reason
    session.commit()
    return RelocateResponse(
        realm_id=estate.realm_id,
        relocating_to_realm_id=estate.relocating_to_realm_id,
        relocation_completes_at=completes_at,
        cost=cost,
        final_rewards=final_rewards,
    )


@router.get("/characters/me/relocate/preview", response_model=RelocationPreviewResponse)
async def preview_relocation(
    realm_id: str,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> RelocationPreviewResponse:
    """Lazily finalize arrival, then return terms without starting a new move."""
    content = _content(request)
    character = _character(session, player.id)
    estate = finalize_relocation(session, character, now, prepare_sqlite=True)
    cost = _relocation_cost_for(content, estate, realm_id)
    session.commit()
    return RelocationPreviewResponse(
        realm_id=estate.realm_id,
        destination_realm_id=realm_id,
        cost=cost,
    )
