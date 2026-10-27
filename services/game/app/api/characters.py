"""Character creation and profile endpoints."""

import logging
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.schemas import ActionValues, action_values
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import CapType, Modifier
from app.engine import resolve_caps
from app.engine.core import modifier_groups
from app.engine.levels import level_for_xp, tier_for_level, xp_progress
from app.errors import api_error
from app.models import (
    Character,
    CharacterSkill,
    Currency,
    Estate,
    EstateOwnershipHistory,
    EstateUpgrade,
    Inventory,
    RealmState,
)
from app.services.actions import load_character_state, resolve_character

router = APIRouter(prefix="/characters", tags=["characters"])
_VALID_NAME = re.compile(r"^[A-Za-z0-9 ]{3,20}$")
logger = logging.getLogger(__name__)


class CreateCharacterRequest(BaseModel):
    """Character creation fields."""

    name: str
    realm_id: str


class CharacterSummary(BaseModel):
    """Basic character identity."""

    id: uuid.UUID
    name: str
    current_realm_id: str
    created_at: datetime


class SkillSummary(BaseModel):
    """Skill level and server-derived progress values."""

    id: str
    name: str
    xp: int
    level: int
    xp_into_level: int
    xp_to_next: int | None
    tier: int
    tier_title: str


class RealmSummary(BaseModel):
    """Character realm content visible in the profile."""

    id: str
    name: str
    tags: tuple[str, ...]
    active_modifiers: tuple[Modifier, ...]


class InstalledUpgrade(BaseModel):
    """An installed estate upgrade."""

    slot_index: int
    upgrade_id: str


class EstateSummary(BaseModel):
    """Estate progression visible in the profile."""

    id: uuid.UUID
    tier: int
    upgrade_slots: int
    installed_upgrades: list[InstalledUpgrade]


class CapSummary(BaseModel):
    """A global base and character-effective cap value."""

    base: float
    effective: float


class ProfileResponse(BaseModel):
    """Complete character profile response."""

    character: CharacterSummary
    skills: list[SkillSummary]
    gold: int
    realm: RealmSummary
    estate: EstateSummary
    caps: dict[CapType, CapSummary]
    actions: dict[str, ActionValues]


class InventoryStack(BaseModel):
    """One inventory item stack."""

    item_id: str
    quantity: int


class InventoryResponse(BaseModel):
    """Current character inventory."""

    items: list[InventoryStack]


def _content(request: Request) -> ContentIndex:
    return request.app.state.content  # type: ignore[no-any-return]


def _character_for_player(session: DatabaseSession, player_id: uuid.UUID) -> Character:
    character = session.scalar(
        select(Character).where(Character.player_id == player_id)
    )
    if character is None:
        raise api_error(404, "NO_CHARACTER", "Create a character to continue")
    return character


@router.post("", response_model=ProfileResponse, status_code=201)
async def create_character(
    body: CreateCharacterRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ProfileResponse:
    """Atomically create the caller's initial character state."""
    content = _content(request)
    if session.scalar(select(Character.id).where(Character.player_id == player.id)):
        raise api_error(409, "CHARACTER_EXISTS", "This player already has a character")
    name = body.name.strip()
    if _VALID_NAME.fullmatch(name) is None:
        raise api_error(
            422,
            "INVALID_NAME",
            "Name must be 3–20 characters using letters, numbers, and spaces",
        )
    try:
        content.realm(body.realm_id)
    except KeyError:
        raise api_error(
            422, "UNKNOWN_REALM", "The selected realm does not exist"
        ) from None

    realm_state = session.get(RealmState, body.realm_id)
    if realm_state is None:
        try:
            with session.begin_nested():
                session.add(
                    RealmState(
                        id=body.realm_id,
                        template_id=body.realm_id,
                        isolated=content.realm(body.realm_id).isolated,
                        last_tick_at=now,
                        current_node_id=content.realm(body.realm_id).starting_node_id,
                        treasury=0,
                    )
                )
                session.flush()
        except IntegrityError:
            # Another character creation initialized this realm concurrently.
            pass

    estate_id = uuid.uuid4()
    character = Character(
        id=uuid.uuid4(),
        player_id=player.id,
        name=name,
        name_normalized=name.casefold(),
        current_realm_id=body.realm_id,
        home_estate_id=estate_id,
        created_at=now,
    )
    session.add(character)
    for skill in content.skills:
        xp = 0
        session.add(
            CharacterSkill(
                character_id=character.id,
                skill_id=skill.id,
                xp=xp,
                level=level_for_xp(xp, content.xp_curve.levels),
            )
        )
    session.add(Currency(character_id=character.id, gold=0, premium=0))
    session.add(
        Estate(
            id=estate_id,
            owner_character_id=character.id,
            realm_id=body.realm_id,
            form_id=content.progression.basic_mobile_form,
            status="active",
            data={},
        )
    )
    session.add(
        EstateOwnershipHistory(
            estate_id=estate_id,
            character_id=character.id,
            acquired_at=now,
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if session.scalar(select(Character.id).where(Character.player_id == player.id)):
            raise api_error(
                409, "CHARACTER_EXISTS", "This player already has a character"
            ) from None
        raise api_error(
            409, "NAME_TAKEN", "That character name is already taken"
        ) from None
    return _profile(session, content, character)


def _profile(
    session: DatabaseSession, content: ContentIndex, character: Character
) -> ProfileResponse:
    currency = session.get(Currency, character.id)
    estate = session.get(Estate, character.home_estate_id)
    if currency is None or estate is None:
        raise RuntimeError(f"character {character.id} has incomplete profile state")
    realm = content.realm(character.current_realm_id)
    realm_state = session.get(RealmState, character.current_realm_id)
    node = content.development_node(
        realm_state.current_node_id if realm_state else realm.starting_node_id
    )
    stored_skills = {
        skill.skill_id: skill
        for skill in session.scalars(
            select(CharacterSkill).where(CharacterSkill.character_id == character.id)
        )
    }
    skills: list[SkillSummary] = []
    profile_changed = False
    for definition in content.skills:
        stored = stored_skills.get(definition.id)
        if stored is None:
            stored = CharacterSkill(
                character_id=character.id,
                skill_id=definition.id,
                xp=0,
                level=level_for_xp(0, content.xp_curve.levels),
            )
            session.add(stored)
            profile_changed = True
        derived_level = level_for_xp(stored.xp, content.xp_curve.levels)
        if stored.level != derived_level:
            logger.warning(
                "Repairing cached skill level for character %s, skill %s: %s -> %s",
                character.id,
                stored.skill_id,
                stored.level,
                derived_level,
            )
            stored.level = derived_level
            profile_changed = True
        xp_into_level, xp_to_next = xp_progress(stored.xp, content.xp_curve.levels)
        tier = tier_for_level(derived_level, content.progression.tier_thresholds)
        skills.append(
            SkillSummary(
                id=definition.id,
                name=definition.name,
                xp=stored.xp,
                level=derived_level,
                xp_into_level=xp_into_level,
                xp_to_next=xp_to_next,
                tier=tier,
                tier_title=content.progression.tier_titles[tier - 1],
            )
        )
    if profile_changed:
        session.commit()
    upgrades = list(
        session.scalars(
            select(EstateUpgrade)
            .where(EstateUpgrade.estate_id == estate.id)
            .order_by(EstateUpgrade.slot_index)
        )
    )
    state = load_character_state(session, character.id)
    resolved = resolve_caps(state, content)
    active_modifiers = [
        modifier for group in modifier_groups(state, content) for modifier in group
    ]
    effective_caps = {
        CapType.OFFLINE_HOURS: resolved.offline_hours,
        CapType.INVENTORY_SLOTS: resolved.inventory_slots,
        CapType.ORDER_SLOTS: resolved.order_slots,
        CapType.KEY_LISTINGS: resolved.key_listings,
        CapType.BELT_SLOTS: resolved.belt_slots,
        CapType.ESTATE_UPGRADE_SLOTS: resolved.estate_upgrade_slots,
    }
    return ProfileResponse(
        actions={
            action.id: action_values(action, state, content)
            for skill in content.skills
            for action in skill.actions
        },
        character=CharacterSummary.model_validate(character, from_attributes=True),
        skills=skills,
        gold=currency.gold,
        realm=RealmSummary(
            id=realm.id,
            name=realm.name,
            tags=node.inherent_tags,
            active_modifiers=tuple(active_modifiers),
        ),
        estate=EstateSummary(
            id=estate.id,
            tier=content.estate_form(estate.form_id).tier,
            upgrade_slots=resolved.estate_upgrade_slots,
            installed_upgrades=[
                InstalledUpgrade(
                    slot_index=upgrade.slot_index, upgrade_id=upgrade.upgrade_id
                )
                for upgrade in upgrades
            ],
        ),
        caps={
            cap: CapSummary(
                base=float(
                    content.estate_form(estate.form_id).upgrade_slots
                    if cap == CapType.ESTATE_UPGRADE_SLOTS
                    else getattr(content.caps, cap.value)
                ),
                effective=float(value),
            )
            for cap, value in effective_caps.items()
        },
    )


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ProfileResponse:
    """Return the caller's character profile."""
    character = _character_for_player(session, player.id)
    content = _content(request)
    resolve_character(session, character.id, now, content)
    session.commit()
    return _profile(session, content, character)


@router.get("/me/inventory", response_model=InventoryResponse)
async def get_inventory(
    now: ServerNow, player: CurrentPlayer, session: DatabaseSession
) -> InventoryResponse:
    """Return all item stacks owned by the caller's character."""
    character = _character_for_player(session, player.id)
    resolve_character(session, character.id, now)
    session.commit()
    stacks = session.scalars(
        select(Inventory)
        .where(Inventory.character_id == character.id)
        .order_by(Inventory.item_id)
    )
    return InventoryResponse(
        items=[
            InventoryStack.model_validate(stack, from_attributes=True)
            for stack in stacks
        ]
    )
