"""Public realm identities and map, with lazy transition completion."""

import uuid
from datetime import datetime, timedelta
from typing import Literal, cast

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.actions import get_character
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import CapBonus, DecayStage, Modifier
from app.engine.tags import TagHolder, active_tags
from app.errors import api_error
from app.models import (
    Estate,
    RealmContribution,
    RealmProjectRun,
    RealmState,
    RealmTag,
)
from app.services.actions import resolve_character
from app.services.projects import active_run, contribute_character, kickoff
from app.services.realms import (
    as_utc,
    finalize_realm,
    finalize_realms,
    prepare_sqlite_write,
)

router = APIRouter(tags=["realms"])


class NodeIdentity(BaseModel):
    """Current mechanical node identity."""

    id: str
    name: str
    realm_type: str
    tier: int
    tags: tuple[str, ...]
    modifiers: tuple[Modifier, ...]
    cap_bonuses: tuple[CapBonus, ...]


class PendingTransition(BaseModel):
    """Public transition timing and cause."""

    to_node: str
    cause: Literal["upgrade", "regression"]
    started_at: datetime
    completes_at: datetime


class StackTag(BaseModel):
    """An acquired tag with its original order and D4 stamp."""

    tag_id: str
    seq: int
    node_id: str


class ProjectRunResponse(BaseModel):
    """Public attempt snapshot; line amounts are expressed in whole-good units."""

    id: uuid.UUID
    project_id: str
    required: list[dict[str, object]]
    contributed: list[float]
    status: str
    stalled: bool
    last_contribution_at: datetime
    build_completes_at: datetime | None


def _run_response(
    run: RealmProjectRun, now: datetime, content: ContentIndex
) -> ProjectRunResponse:
    return ProjectRunResponse(
        id=run.id,
        project_id=run.project_id,
        required=run.required,
        contributed=[amount / 1000 for amount in run.contributed],
        status=run.status,
        stalled=run.status == "funding"
        and as_utc(now)
        > as_utc(run.last_contribution_at)
        + timedelta(days=content.economy.project.idle_grace_days),
        last_contribution_at=run.last_contribution_at,
        build_completes_at=run.build_completes_at,
    )


class RealmResponse(BaseModel):
    """Public gameplay state; never includes treasury."""

    id: str
    name: str
    node: NodeIdentity
    tags: list[StackTag]
    active_tags: tuple[str, ...]
    decay_stage: str
    gauge: float
    active_run: ProjectRunResponse | None
    pending_transition: PendingTransition | None


def _content(request: Request) -> ContentIndex:
    return cast(ContentIndex, request.app.state.content)


def _realm_response(
    session: DatabaseSession,
    content: ContentIndex,
    realm_id: str,
    state: RealmState | None,
    now: datetime,
) -> RealmResponse:
    realm = content.realm(state.template_id if state else realm_id)
    node = content.development_node(
        state.current_node_id if state else realm.starting_node_id
    )
    tags = list(
        session.scalars(
            select(RealmTag).where(RealmTag.realm_id == realm_id).order_by(RealmTag.seq)
        )
    )
    stage = DecayStage(state.decay_stage) if state else DecayStage.FED
    ids = set(node.inherent_tags) | {tag.tag_id for tag in tags}
    active = active_tags(
        TagHolder(
            tuple(t for t in content.tags if t.id in ids),
            content.economy.decay.faltering_factor,
        ),
        stage,
    )
    run = active_run(session, realm_id)
    return RealmResponse(
        active_run=_run_response(run, now, content) if run else None,
        id=realm_id,
        name=realm.name,
        node=NodeIdentity(
            id=node.id,
            name=node.name,
            realm_type=node.realm_type,
            tier=node.tier,
            tags=node.inherent_tags,
            modifiers=node.modifiers,
            cap_bonuses=node.cap_bonuses,
        ),
        tags=[StackTag(tag_id=t.tag_id, seq=t.seq, node_id=t.node_id) for t in tags],
        active_tags=tuple(t.id for t, _ in active),
        decay_stage=stage.value,
        gauge=state.gauge if state else 0,
        pending_transition=PendingTransition.model_validate(state.pending_transition)
        if state and state.pending_transition
        else None,
    )


def _world_ids(session: DatabaseSession, content: ContentIndex) -> set[str]:
    isolated = set(
        session.scalars(select(RealmState.id).where(RealmState.isolated.is_(True)))
    )
    return {r.id for r in content.realms if not r.isolated and r.id not in isolated}


@router.get("/realms", response_model=list[RealmResponse])
async def get_realms(
    request: Request, now: ServerNow, session: DatabaseSession
) -> list[RealmResponse]:
    """Return world realms after finalizing transitions in sorted lock order."""
    content = _content(request)
    prepare_sqlite_write(session)
    ids = _world_ids(session, content)
    states = finalize_realms(session, ids, now, content)
    result = [
        _realm_response(session, content, r.id, states[r.id], now)
        for r in content.realms
        if r.id in ids
    ]
    session.commit()
    return result


@router.get("/realms/{realm_id}", response_model=RealmResponse)
async def get_realm(
    realm_id: str, request: Request, now: ServerNow, session: DatabaseSession
) -> RealmResponse:
    """Return a realm's public identity and acquired tag stack."""
    content = _content(request)
    state = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    try:
        content.realm(state.template_id if state else realm_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist") from None
    response = _realm_response(session, content, realm_id, state, now)
    session.commit()
    return response


@router.get("/map")
async def get_map(
    request: Request, now: ServerNow, session: DatabaseSession
) -> dict[str, object]:
    """Return only world realms and edges joining visible realms."""
    content = _content(request)
    prepare_sqlite_write(session)
    ids = _world_ids(session, content)
    states = finalize_realms(session, ids, now, content)
    nodes = []
    for realm in content.realms:
        if realm.id not in ids:
            continue
        state = states[realm.id]
        node_id = state.current_node_id if state else realm.starting_node_id
        nodes.append(
            {
                "realm_id": realm.id,
                "name": realm.name,
                "position": content.map.positions.get(realm.id),
                "node": node_id,
                "tier": content.development_node(node_id).tier,
                "decay_stage": state.decay_stage if state else "fed",
                "treasury_band": state.treasury_band if state else None,
                "transition_pending": bool(state and state.pending_transition),
            }
        )
    result: dict[str, object] = {
        "nodes": nodes,
        "edges": [e for e in content.map.edges if e.a in ids and e.b in ids],
    }
    session.commit()
    return result


class ContributionRequest(BaseModel):
    """A whole-good payment intent."""

    model_config = ConfigDict(extra="forbid")
    item_id: str
    quantity: int = Field(gt=0, strict=True)


def _project_realm(session: DatabaseSession, realm_id: str) -> RealmState:
    state = session.get(RealmState, realm_id)
    if state is None:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    return state


def _check_realm_id(
    session: DatabaseSession, content: ContentIndex, realm_id: str
) -> None:
    if (
        realm_id not in {realm.id for realm in content.realms}
        and session.get(RealmState, realm_id) is None
    ):
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")


@router.post("/realms/{realm_id}/projects/{project_id}/kickoff")
async def kickoff_project(
    realm_id: str,
    project_id: str,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ProjectRunResponse:
    """Start an attempt after resolving presence and locking realms in id order."""
    content = _content(request)
    character = get_character(session, player.id)
    _check_realm_id(session, content, realm_id)
    resolve_character(session, character.id, now, content, {realm_id})
    realm = _project_realm(session, realm_id)
    run = kickoff(session, character, realm, project_id, now, content)
    response = _run_response(run, now, content)
    session.commit()
    return response


@router.post("/realms/{realm_id}/project/contribute")
async def contribute_project(
    realm_id: str,
    body: ContributionRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ProjectRunResponse:
    """Consume a clamped payment and record one immutable credit per call."""
    content = _content(request)
    character = get_character(session, player.id)
    _check_realm_id(session, content, realm_id)
    resolve_character(session, character.id, now, content, {realm_id})
    realm = _project_realm(session, realm_id)
    run = contribute_character(
        session,
        character,
        realm,
        body.item_id,
        body.quantity,
        now,
        content,
    )
    response = _run_response(run, now, content)
    session.commit()
    return response


class TagCreditsResponse(BaseModel):
    """Kickoff and consumed contribution credits for a currently held tag."""

    tag_id: str
    project_run_id: uuid.UUID | None
    kicked_off_by: uuid.UUID | None
    contributions: dict[str, float]
    realm_share: float


@router.get("/realms/{realm_id}/tags/{tag_id}", response_model=TagCreditsResponse)
async def tag_credits(
    realm_id: str,
    tag_id: str,
    request: Request,
    now: ServerNow,
    session: DatabaseSession,
) -> TagCreditsResponse:
    """Return credits from the attempt that granted the currently held tag."""
    content = _content(request)
    state = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    if state is None and realm_id not in {realm.id for realm in content.realms}:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    tag = session.get(RealmTag, (realm_id, tag_id))
    if tag is None:
        raise api_error(404, "UNKNOWN_REALM_TAG", "The realm does not hold this tag")
    run = (
        session.get(RealmProjectRun, tag.project_run_id) if tag.project_run_id else None
    )
    totals: dict[str, int] = {}
    realm_share = 0
    if run is not None:
        for row in session.scalars(
            select(RealmContribution).where(RealmContribution.run_id == run.id)
        ):
            if row.character_id is None:
                realm_share += row.quantity_milli
            else:
                key = str(row.character_id)
                totals[key] = totals.get(key, 0) + row.quantity_milli
    response = TagCreditsResponse(
        tag_id=tag_id,
        project_run_id=run.id if run else None,
        kicked_off_by=run.kicked_off_by if run else None,
        contributions={key: value / 1000 for key, value in totals.items()},
        realm_share=realm_share / 1000,
    )
    session.commit()
    return response


class RealmEstateResponse(BaseModel):
    """Public estate ownership and condition without private holdings."""

    id: uuid.UUID
    owner: uuid.UUID | Literal["realm-owned"]
    form: str
    decay_stage: str


@router.get("/realms/{realm_id}/estates", response_model=list[RealmEstateResponse])
async def get_realm_estates(
    realm_id: str, request: Request, now: ServerNow, session: DatabaseSession
) -> list[RealmEstateResponse]:
    """List player and realm estates after resolving the realm lazily."""
    content = _content(request)
    state = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    if state is None and realm_id not in {realm.id for realm in content.realms}:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    result = [
        RealmEstateResponse(
            id=estate.id,
            owner=estate.owner_character_id or "realm-owned",
            form=estate.form_id,
            decay_stage=estate.decay_stage,
        )
        for estate in session.scalars(
            select(Estate).where(Estate.realm_id == realm_id).order_by(Estate.id)
        )
    ]
    session.commit()
    return result
