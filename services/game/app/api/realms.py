"""Public realm identities and map, with lazy transition completion."""

import uuid
from datetime import datetime, timedelta
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.actions import get_character
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import CapBonus, DecayStage, Modifier
from app.engine.estates import sale_price
from app.engine.market import quote
from app.engine.tags import TagHolder, active_tags
from app.errors import api_error
from app.models import (
    Estate,
    RealmContribution,
    RealmProjectRun,
    RealmState,
    RealmTag,
    RealmVote,
    RealmVoteEligibility,
)
from app.services.actions import resolve_character
from app.services.estates import estate_ask_provider, persisted_estate_value
from app.services.market import market_contexts, market_view
from app.services.projects import (
    active_run,
    contribute_character,
    kickoff,
    validate_kickoff,
)
from app.services.realms import (
    as_utc,
    finalize_realm,
    finalize_realms,
    prepare_sqlite_write,
)
from app.services.stores import recompute_lines
from app.services.trade import gift, trade
from app.services.votes import call_vote, cast_vote, open_vote

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


class DemandLineResponse(BaseModel):
    """Public demand in milli-line-units; no private treasury information."""

    line_key: str
    selector: dict[str, object]
    value_measured: bool
    draw_per_day: int
    reserve: int
    cap: int
    stock: int
    in_transit: int
    below_reserve: bool


class VoteParticipation(BaseModel):
    """Public eligibility and participation snapshot."""

    character_id: uuid.UUID
    weight: int
    voted_at: datetime | None


class VoteResponse(BaseModel):
    """Public ballot; aggregate totals remain hidden until close."""

    id: uuid.UUID
    upgrade_id: str
    called_by: uuid.UUID | None
    called_at: datetime
    closes_at: datetime
    status: str
    eligible_weight: int
    fee_gold: int
    yes_weight: int | None
    no_weight: int | None
    participation: list[VoteParticipation]


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
    open_vote: VoteResponse | None
    lines: list[DemandLineResponse]
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
    vote = open_vote(session, realm_id)
    lines = recompute_lines(session, state, content) if state else []
    return RealmResponse(
        lines=[
            DemandLineResponse(
                line_key=line.line_key,
                selector=line.selector,
                value_measured=line.value_measured,
                draw_per_day=line.draw_per_day,
                reserve=line.reserve,
                cap=line.cap,
                stock=line.stock,
                in_transit=line.in_transit,
                below_reserve=line.stock < line.reserve,
            )
            for line in lines
        ],
        active_run=_run_response(run, now, content) if run else None,
        open_vote=_vote_response(session, vote) if vote else None,
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
def get_realms(
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


def _private_realm_access(
    session: DatabaseSession,
    content: ContentIndex,
    realm_id: str,
    player: CurrentPlayer,
) -> None:
    """Hide templates and reject every non-owner reference to private instances."""
    state = session.get(RealmState, realm_id)
    if state is not None and state.isolated:
        character = get_character(session, player.id)
        if state.owner_character_id != character.id:
            raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    elif state is None:
        try:
            isolated = content.realm(realm_id).isolated
        except KeyError:
            return
        if isolated:
            raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")


@router.get("/realms/{realm_id}", response_model=RealmResponse)
def get_realm(
    realm_id: str,
    request: Request,
    now: ServerNow,
    session: DatabaseSession,
    player: CurrentPlayer,
) -> RealmResponse:
    """Return a realm's public identity and acquired tag stack."""
    content = _content(request)
    _private_realm_access(session, content, realm_id, player)
    state = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    try:
        content.realm(state.template_id if state else realm_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist") from None
    response = _realm_response(session, content, realm_id, state, now)
    session.commit()
    return response


@router.get("/map")
def get_map(
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
                "gauge": state.gauge if state else 0,
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


@router.get("/realms/{realm_id}/projects/availability")
def project_availability(
    realm_id: str,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, dict[str, str] | None]:
    """Expose kickoff gate reasons without paying or starting a project."""
    content = _content(request)
    character = get_character(session, player.id)
    _check_realm_id(session, content, realm_id)
    resolve_character(session, character.id, now, content, {realm_id})
    realm = _project_realm(session, realm_id)
    result: dict[str, dict[str, str] | None] = {}
    for project_id in content.development_node(realm.current_node_id).projects:
        try:
            validate_kickoff(session, character, realm, project_id, now, content)
        except HTTPException as exc:
            result[project_id] = cast(dict[str, dict[str, str]], exc.detail)["error"]
        else:
            result[project_id] = None
    session.commit()
    return result


@router.post("/realms/{realm_id}/projects/{project_id}/kickoff")
def kickoff_project(
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
def contribute_project(
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
def tag_credits(
    realm_id: str,
    tag_id: str,
    request: Request,
    now: ServerNow,
    session: DatabaseSession,
    player: CurrentPlayer,
) -> TagCreditsResponse:
    """Return credits from the attempt that granted the currently held tag."""
    content = _content(request)
    _private_realm_access(session, content, realm_id, player)
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
    gauge: float
    sale_price: int | None = None


@router.get("/realms/{realm_id}/estates", response_model=list[RealmEstateResponse])
def get_realm_estates(
    realm_id: str,
    request: Request,
    now: ServerNow,
    session: DatabaseSession,
    player: CurrentPlayer,
) -> list[RealmEstateResponse]:
    """List player and realm estates after resolving the realm lazily."""
    content = _content(request)
    _private_realm_access(session, content, realm_id, player)
    state = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    if state is None and realm_id not in {realm.id for realm in content.realms}:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    unit_ask = estate_ask_provider(session, state, content)
    result = [
        RealmEstateResponse(
            id=estate.id,
            owner=estate.owner_character_id or "realm-owned",
            sale_price=sale_price(
                persisted_estate_value(session, estate, content, unit_ask).value,
                content.economy.estate.sale_markup_pct,
            )
            if estate.owner_character_id is None
            and content.estate_form(estate.form_id).mobility == "fixed"
            else None,
            form=estate.form_id,
            decay_stage=estate.decay_stage,
            gauge=estate.gauge,
        )
        for estate in session.scalars(
            select(Estate)
            .where(Estate.realm_id == realm_id, Estate.status == "active")
            .order_by(Estate.id)
        )
    ]
    session.commit()
    return result


class MarketMemberResponse(BaseModel):
    """One alternative item bid sharing the line budget."""

    item_id: str
    spot_bid: str | None
    funded_quantity: int
    funded_total: int


class MarketLineResponse(BaseModel):
    """Demand and its best funded member, in milli-line-units."""

    line_key: str
    selector: dict[str, object]
    stock: int
    reserve: int
    cap: int
    draw_per_day: int
    spot_bid: str | None
    funded_quantity: int
    funded_total: int
    days_of_cover: float | None
    members: list[MarketMemberResponse]


class MarketSaleResponse(BaseModel):
    """Whole items offered from surplus stores."""

    item_id: str
    quantity: int
    spot_ask: int


class MarketShortfallResponse(BaseModel):
    """Unfunded reserve deficit in milli-line-units."""

    line_key: str
    missing_milli: int


class MarketResponse(BaseModel):
    """Public market projection, excluding private balances and budgets."""

    lines: list[MarketLineResponse]
    for_sale: list[MarketSaleResponse]
    shortfalls: list[MarketShortfallResponse]
    decay_stage: str
    gauge_days: float
    treasury_band: str | None


class MarketQuoteResponse(BaseModel):
    """Integrated gold total and current physical/funding limit."""

    gold: int
    max_quantity: int


@router.get("/realms/{realm_id}/market", response_model=MarketResponse)
def get_market(
    realm_id: str,
    request: Request,
    now: ServerNow,
    session: DatabaseSession,
    player: CurrentPlayer,
) -> MarketResponse:
    """Inspect any realm market from any location."""
    content = _content(request)
    _private_realm_access(session, content, realm_id, player)
    realm = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    if realm is None:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    if realm.isolated:
        raise api_error(409, "NO_MARKET_ACCESS", "Isolated realms have no market")
    recompute_lines(session, realm, content)
    session.flush()
    result = MarketResponse.model_validate(market_view(session, realm, content))
    session.commit()
    return result


@router.get("/realms/{realm_id}/market/quote", response_model=MarketQuoteResponse)
def get_market_quote(
    realm_id: str,
    item_id: str,
    side: Literal["buy", "sell"],
    request: Request,
    now: ServerNow,
    session: DatabaseSession,
    player: CurrentPlayer,
    quantity: int = Query(gt=0),
) -> MarketQuoteResponse:
    """Return an integrated quote and the currently executable maximum."""
    content = _content(request)
    _private_realm_access(session, content, realm_id, player)
    realm = finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    if realm is None:
        raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    if realm.isolated:
        raise api_error(409, "NO_MARKET_ACCESS", "Isolated realms have no market")
    recompute_lines(session, realm, content)
    session.flush()
    contexts = market_contexts(session, realm, content)
    if item_id not in contexts:
        raise api_error(404, "UNKNOWN_ITEM", "The item does not exist")
    line, ctx = contexts[item_id]
    if side == "sell" and line is None:
        raise api_error(400, "NO_DEMAND", "The realm has no demand for this item")
    result = quote(ctx, item_id, side, quantity)
    session.commit()
    return MarketQuoteResponse(gold=result.gold, max_quantity=result.max_quantity)


class TradeRequest(BaseModel):
    """Whole-item intent with an all-or-nothing gold limit."""

    model_config = ConfigDict(extra="forbid")
    item_id: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0, strict=True)
    limit_gold: int = Field(ge=0, strict=True)


class GiftRequest(BaseModel):
    """Positive integral gold to transfer to a realm."""

    model_config = ConfigDict(extra="forbid")
    gold: int = Field(gt=0, strict=True)


@router.post("/realms/{realm_id}/market/trade", response_model=MarketQuoteResponse)
def trade_market(
    realm_id: str,
    body: TradeRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> MarketQuoteResponse:
    """Resolve and serialize holdings before executing a whole trade."""
    content = _content(request)
    character = get_character(session, player.id)
    _check_realm_id(session, content, realm_id)
    resolve_character(session, character.id, now, content, {realm_id})
    gold = trade(
        session,
        character,
        _project_realm(session, realm_id),
        content,
        body.item_id,
        body.side,
        body.quantity,
        body.limit_gold,
    )
    session.commit()
    return MarketQuoteResponse(gold=gold, max_quantity=body.quantity)


@router.post("/realms/{realm_id}/treasury/gift", status_code=204)
def gift_treasury(
    realm_id: str,
    body: GiftRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> None:
    """Give gold to the realm where the resolved character is present."""
    content = _content(request)
    character = get_character(session, player.id)
    _check_realm_id(session, content, realm_id)
    resolve_character(session, character.id, now, content, {realm_id})
    gift(session, character, _project_realm(session, realm_id), body.gold)
    session.commit()


class VoteRequest(BaseModel):
    """An ephemeral ballot choice, never recorded against a character."""

    model_config = ConfigDict(extra="forbid")
    choice: Literal["yes", "no"]


def _vote_response(session: DatabaseSession, vote: RealmVote) -> VoteResponse:
    return VoteResponse(
        id=vote.id,
        upgrade_id=vote.upgrade_id,
        called_by=vote.called_by,
        called_at=vote.called_at,
        closes_at=vote.closes_at,
        status=vote.status,
        eligible_weight=vote.eligible_weight,
        fee_gold=vote.fee_gold,
        yes_weight=vote.yes_weight if vote.status != "open" else None,
        no_weight=vote.no_weight if vote.status != "open" else None,
        participation=[
            VoteParticipation(
                character_id=e.character_id, weight=e.weight, voted_at=e.voted_at
            )
            for e in session.scalars(
                select(RealmVoteEligibility)
                .where(RealmVoteEligibility.vote_id == vote.id)
                .order_by(RealmVoteEligibility.character_id)
            )
        ],
    )


@router.post("/realms/{realm_id}/upgrades/{upgrade_id}/call")
def call_upgrade_vote(
    realm_id: str,
    upgrade_id: str,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> VoteResponse:
    """Resolve and lock the realm before paying and snapshotting eligibility."""
    content = _content(request)
    character = get_character(session, player.id)
    _check_realm_id(session, content, realm_id)
    resolve_character(session, character.id, now, content, {realm_id})
    vote = call_vote(
        session, character, _project_realm(session, realm_id), upgrade_id, now, content
    )
    response = _vote_response(session, vote)
    session.commit()
    return response


@router.post("/realms/{realm_id}/vote")
def submit_vote(
    realm_id: str,
    body: VoteRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> VoteResponse:
    """Add aggregate weight once, without logging or retaining the choice."""
    content = _content(request)
    character = get_character(session, player.id)
    _check_realm_id(session, content, realm_id)
    resolve_character(session, character.id, now, content, {realm_id})
    vote = cast_vote(
        session, character, _project_realm(session, realm_id), body.choice, now, content
    )
    response = _vote_response(session, vote)
    session.commit()
    return response


@router.get("/realms/{realm_id}/vote")
def get_vote(
    realm_id: str,
    request: Request,
    now: ServerNow,
    session: DatabaseSession,
) -> VoteResponse | None:
    """Read the current or most recently called ballot after lazy close."""
    content = _content(request)
    _check_realm_id(session, content, realm_id)
    finalize_realm(session, realm_id, now, content, prepare_sqlite=True)
    vote = session.scalar(
        select(RealmVote)
        .where(RealmVote.realm_id == realm_id)
        .order_by(RealmVote.called_at.desc(), RealmVote.id.desc())
        .limit(1)
    )
    response = _vote_response(session, vote) if vote is not None else None
    session.commit()
    return response
