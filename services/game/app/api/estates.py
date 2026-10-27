"""Home-estate queries, upgrades, and form transformations."""

import json
import logging
import uuid
from collections.abc import Sequence
from dataclasses import replace

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func, select

from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import (
    BuildCost,
    CapBonus,
    DecayStage,
    ItemQuantity,
    Modifier,
    TravelProfile,
)
from app.engine import Shortfall, pay_selector, resolve_caps
from app.engine.core import realm_active_tags
from app.engine.tags import tags_present
from app.errors import api_error
from app.models import Character, Currency, Estate, EstateUpgrade, Inventory, RealmState
from app.services.actions import load_character_state, resolve_character
from app.services.realms import stack_tags

router = APIRouter(prefix="/estates", tags=["estates"])
audit_logger = logging.getLogger("yaisg.audit")


class EstateFormSummary(BaseModel):
    """Resolved content definition for an estate form."""

    id: str
    name: str
    tags: tuple[str, ...]
    tier: int
    upgrade_slots: int
    mobility: str
    travel_profile: TravelProfile | None
    cap_bonuses: tuple[CapBonus, ...]
    modifiers: tuple[Modifier, ...]


class InstalledUpgradeSummary(BaseModel):
    """One installed upgrade and its current applicability."""

    slot_index: int
    upgrade_id: str
    name: str
    status: str
    inert_reason: str | None


class EstateResponse(BaseModel):
    """The authenticated character's home estate."""

    id: uuid.UUID
    form: EstateFormSummary
    realm_id: str
    tier: int
    mobility: str
    tags: tuple[str, ...]
    decay_stage: str
    status: str
    upgrade_slots: int
    installed_upgrades: list[InstalledUpgradeSummary]


class TransformRequest(BaseModel):
    """Requested destination form."""

    form_id: str


def _content(request: Request) -> ContentIndex:
    return request.app.state.content  # type: ignore[no-any-return]


def _character(session: DatabaseSession, player_id: uuid.UUID) -> Character:
    character = session.scalar(
        select(Character).where(Character.player_id == player_id)
    )
    if character is None:
        raise api_error(404, "NO_CHARACTER", "Create a character to continue")
    return character


def _home_estate(
    session: DatabaseSession, character: Character, *, lock: bool = False
) -> Estate:
    statement = select(Estate).where(Estate.id == character.home_estate_id)
    if lock and session.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    estate = session.scalar(statement)
    if estate is None:
        raise api_error(
            500,
            "INCOMPLETE_CHARACTER_STATE",
            f"Character {character.id} has no home estate",
        )
    return estate


def _upgrade_inert_reason(
    content: ContentIndex, realm_tags: set[str], upgrade_id: str
) -> str | None:
    upgrade = content.upgrade(upgrade_id)
    if not tags_present(upgrade.requires_realm_tags, realm_tags):
        return "realm requirements not met"
    return None


def _estate_response(
    session: DatabaseSession,
    content: ContentIndex,
    character: Character,
    estate: Estate,
) -> EstateResponse:
    installed = list(
        session.scalars(
            select(EstateUpgrade)
            .where(EstateUpgrade.estate_id == estate.id)
            .order_by(EstateUpgrade.slot_index)
        )
    )
    state = load_character_state(session, character.id)
    slots = resolve_caps(state, content).estate_upgrade_slots
    realm = session.get(RealmState, estate.realm_id)
    estate_realm_state = replace(
        state,
        current_realm_id=estate.realm_id,
        realm_node_id=realm.current_node_id
        if realm
        else content.realm(estate.realm_id).starting_node_id,
        realm_stage=DecayStage(realm.decay_stage) if realm else DecayStage.FED,
        realm_stack_tags=stack_tags(session, estate.realm_id),
    )
    realm_tags = {tag.id for tag, _ in realm_active_tags(estate_realm_state, content)}
    form = content.estate_form(estate.form_id)
    summaries: list[InstalledUpgradeSummary] = []
    for record in installed:
        upgrade = content.upgrade(record.upgrade_id)
        reason = _upgrade_inert_reason(content, realm_tags, upgrade.id)
        summaries.append(
            InstalledUpgradeSummary(
                slot_index=record.slot_index,
                upgrade_id=upgrade.id,
                name=upgrade.name,
                status="inert" if reason else "active",
                inert_reason=reason,
            )
        )
    return EstateResponse(
        id=estate.id,
        form=EstateFormSummary(
            id=form.id,
            name=form.name,
            tags=form.tags,
            tier=form.tier,
            upgrade_slots=form.upgrade_slots,
            mobility=form.mobility,
            travel_profile=form.travel_profile,
            cap_bonuses=form.cap_bonuses,
            modifiers=form.modifiers,
        ),
        realm_id=estate.realm_id,
        tier=form.tier,
        mobility=form.mobility,
        tags=form.tags,
        decay_stage=estate.decay_stage,
        status=estate.status,
        upgrade_slots=slots,
        installed_upgrades=summaries,
    )


def _consume_items(
    session: DatabaseSession,
    character_id: uuid.UUID,
    costs: Sequence[ItemQuantity],
) -> bool:
    # Check affordability before applying any withdrawals.
    entries = tuple(costs)
    stacks = {
        stack.item_id: stack
        for stack in session.scalars(
            select(Inventory).where(
                Inventory.character_id == character_id,
                Inventory.item_id.in_([entry.item_id for entry in entries]),
            )
        )
    }
    if any(
        stacks.get(entry.item_id) is None or stacks[entry.item_id].quantity < entry.qty
        for entry in entries
    ):
        return False
    for entry in entries:
        stack = stacks[entry.item_id]
        stack.quantity -= entry.qty
        if stack.quantity == 0:
            session.delete(stack)
    return True


def _require_owner_present(character: Character, estate: Estate) -> None:
    if estate.owner_character_id != character.id:
        raise api_error(403, "NOT_ESTATE_OWNER", "You do not own this estate")
    if character.current_realm_id != estate.realm_id:
        raise api_error(409, "NOT_PRESENT", "You must be in the estate's realm")


def _pay_build_cost(
    session: DatabaseSession,
    character: Character,
    estate: Estate,
    cost: BuildCost,
    content: ContentIndex,
) -> None:
    """Plan all selector payments before transferring goods and gold atomically."""
    currency = session.get(Currency, character.id)
    realm = session.get(RealmState, estate.realm_id)
    if currency is None or realm is None:
        raise api_error(500, "INCOMPLETE_CHARACTER_STATE", "Missing currency or realm")
    stacks = list(
        session.scalars(select(Inventory).where(Inventory.character_id == character.id))
    )
    remaining = {stack.item_id: stack.quantity for stack in stacks}
    if currency.gold < cost.gold:
        raise api_error(409, "MISSING_INPUTS", "The build cost is not affordable")
    for line in cost.goods:
        payment = pay_selector(remaining, line.selector, line.quantity, content)
        if isinstance(payment, Shortfall):
            raise api_error(409, "MISSING_INPUTS", "The build cost is not affordable")
        for item_id, quantity in payment.items():
            remaining[item_id] -= quantity
    for stack in stacks:
        stack.quantity = remaining[stack.item_id]
        if stack.quantity == 0:
            session.delete(stack)
    currency.gold -= cost.gold
    realm.treasury += cost.gold


def _audit(change: str, character: Character, estate: Estate, **details: str) -> None:
    audit_logger.info(
        json.dumps(
            {
                "event": "estate_changed",
                "change": change,
                "character_id": str(character.id),
                "estate_id": str(estate.id),
                **details,
            },
            sort_keys=True,
        )
    )


@router.get("/me", response_model=EstateResponse)
async def get_estate(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> EstateResponse:
    """Resolve active work and return the caller's home estate."""
    character = _character(session, player.id)
    content = _content(request)
    resolve_character(session, character.id, now, content)
    estate = _home_estate(session, character)
    response = _estate_response(session, content, character, estate)
    session.commit()
    return response


@router.post("/me/upgrades/{upgrade_id}", response_model=EstateResponse)
async def purchase_upgrade(
    upgrade_id: str,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> EstateResponse:
    """Resolve work, charge item inputs, and install an estate upgrade."""
    character = _character(session, player.id)
    content = _content(request)
    resolve_character(session, character.id, now, content)
    # On SQLite, resolve_character has already acquired BEGIN IMMEDIATE. This
    # ordering is the SQLite equivalent of the estate row lock below.
    estate = _home_estate(session, character, lock=True)
    _require_owner_present(character, estate)
    try:
        upgrade = content.upgrade(upgrade_id)
    except KeyError:
        raise api_error(404, "UNKNOWN_UPGRADE", "The upgrade does not exist") from None
    installed = list(
        session.scalars(
            select(EstateUpgrade)
            .where(EstateUpgrade.estate_id == estate.id)
            .order_by(EstateUpgrade.slot_index)
        )
    )
    if any(record.upgrade_id == upgrade.id for record in installed):
        raise api_error(409, "ALREADY_INSTALLED", "The upgrade is already installed")
    cap = resolve_caps(
        load_character_state(session, character.id), content
    ).estate_upgrade_slots
    used_slots = {record.slot_index for record in installed}
    free_slot = next((slot for slot in range(cap) if slot not in used_slots), None)
    if free_slot is None:
        raise api_error(409, "NO_FREE_SLOT", "The estate has no free upgrade slot")
    if not _consume_items(session, character.id, upgrade.cost):
        raise api_error(409, "MISSING_INPUTS", "The upgrade cost is not affordable")
    session.add(
        EstateUpgrade(
            estate_id=estate.id,
            slot_index=free_slot,
            upgrade_id=upgrade.id,
            purchased_at=now,
        )
    )
    response = _estate_response(session, content, character, estate)
    session.commit()
    _audit("upgrade_installed", character, estate, upgrade_id=upgrade.id)
    return response


@router.post("/me/transform", response_model=EstateResponse)
async def transform_estate(
    body: TransformRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> EstateResponse:
    """Resolve work, charge a transformation edge, and change estate form."""
    character = _character(session, player.id)
    content = _content(request)
    resolution = resolve_character(session, character.id, now, content)
    # On SQLite, resolve_character has already acquired BEGIN IMMEDIATE. This
    # ordering is the SQLite equivalent of the estate row lock below.
    estate = _home_estate(session, character, lock=True)
    if (
        resolution.active is not None
        and content.action(resolution.active.action_id).resolver == "travel"
        and resolution.active.meta.get("mode") == "relocate"
    ):
        raise api_error(409, "ESTATE_BUSY", "The estate is on a journey")
    if estate.status != "active":
        raise api_error(409, "ESTATE_BUSY", "The estate is not active")
    _require_owner_present(character, estate)
    source = content.estate_form(estate.form_id)
    try:
        destination = content.estate_form(body.form_id)
    except KeyError:
        raise api_error(
            409, "INVALID_TRANSFORMATION", "No transformation edge exists"
        ) from None
    if (
        body.form_id not in source.transforms_to
        or destination.mobility != source.mobility
    ):
        raise api_error(409, "INVALID_TRANSFORMATION", "No transformation edge exists")
    state = load_character_state(session, character.id)
    installed_count = session.scalar(
        select(func.count())
        .select_from(EstateUpgrade)
        .where(EstateUpgrade.estate_id == estate.id)
    )
    destination_slots = destination.upgrade_slots
    if (installed_count or 0) > destination_slots:
        raise api_error(
            409,
            "WOULD_ORPHAN_UPGRADES",
            "The destination form has too few upgrade slots",
        )
    realm_tags = {tag.id for tag, _ in realm_active_tags(state, content)}
    if not tags_present(destination.requires_realm_tags, realm_tags):
        raise api_error(
            409, "MISSING_REALM_TAGS", "The destination form requires realm tags"
        )
    _pay_build_cost(session, character, estate, destination.build_cost, content)
    previous_form = estate.form_id
    estate.form_id = body.form_id
    response = _estate_response(session, content, character, estate)
    session.commit()
    _audit(
        "form_transformed",
        character,
        estate,
        from_form_id=previous_form,
        to_form_id=body.form_id,
    )
    return response
