"""Public realm identities and map, with lazy transition completion."""

from datetime import datetime
from typing import Literal, cast

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import CapBonus, DecayStage, Modifier
from app.engine.tags import TagHolder, active_tags
from app.errors import api_error
from app.models import RealmState, RealmTag
from app.services.realms import finalize_realm, finalize_realms, prepare_sqlite_write

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


class RealmResponse(BaseModel):
    """Public gameplay state; never includes treasury."""

    id: str
    name: str
    node: NodeIdentity
    tags: list[StackTag]
    active_tags: tuple[str, ...]
    decay_stage: str
    gauge: float
    pending_transition: PendingTransition | None


def _content(request: Request) -> ContentIndex:
    return cast(ContentIndex, request.app.state.content)


def _realm_response(
    session: DatabaseSession,
    content: ContentIndex,
    realm_id: str,
    state: RealmState | None,
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
    return RealmResponse(
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
        _realm_response(session, content, r.id, states[r.id])
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
    response = _realm_response(session, content, realm_id, state)
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
