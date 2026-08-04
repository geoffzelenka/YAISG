"""Character creation and profile endpoints."""

import logging
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth import CurrentPlayer, DatabaseSession
from app.config import STARTING_GOLD
from app.content.loader import ContentIndex
from app.content.schemas import Modifier
from app.engine.levels import level_for_xp, xp_progress
from app.errors import api_error
from app.models import (
    Character,
    CharacterSkill,
    Currency,
    Estate,
    EstateUpgrade,
    Inventory,
)

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
    realm_id: str
    created_at: datetime


class SkillSummary(BaseModel):
    """Skill level and server-derived progress values."""

    id: str
    name: str
    xp: int
    level: int
    xp_into_level: int
    xp_to_next: int


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
    level: int
    upgrade_slots: int
    installed_upgrades: list[InstalledUpgrade]


class ProfileResponse(BaseModel):
    """Complete character profile response."""

    character: CharacterSummary
    skills: list[SkillSummary]
    gold: int
    realm: RealmSummary
    estate: EstateSummary


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

    now = datetime.now(UTC)
    character = Character(
        id=uuid.uuid4(),
        player_id=player.id,
        name=name,
        name_normalized=name.casefold(),
        realm_id=body.realm_id,
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
    session.add(Currency(character_id=character.id, gold=STARTING_GOLD, premium=0))
    session.add(
        Estate(
            character_id=character.id,
            realm_id=body.realm_id,
            level=1,
            upgrade_slots=content.caps.estate_upgrade_slots,
            data={},
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
    estate = session.scalar(select(Estate).where(Estate.character_id == character.id))
    if currency is None or estate is None:
        raise RuntimeError(f"character {character.id} has incomplete profile state")
    realm = content.realm(character.realm_id)
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
        skills.append(
            SkillSummary(
                id=definition.id,
                name=definition.name,
                xp=stored.xp,
                level=derived_level,
                xp_into_level=xp_into_level,
                xp_to_next=xp_to_next,
            )
        )
    if profile_changed:
        session.commit()
    upgrades = session.scalars(
        select(EstateUpgrade)
        .where(EstateUpgrade.estate_id == estate.id)
        .order_by(EstateUpgrade.slot_index)
    )
    return ProfileResponse(
        character=CharacterSummary.model_validate(character, from_attributes=True),
        skills=skills,
        gold=currency.gold,
        realm=RealmSummary(
            id=realm.id,
            name=realm.name,
            tags=realm.tags,
            active_modifiers=realm.modifiers,
        ),
        estate=EstateSummary(
            id=estate.id,
            level=estate.level,
            upgrade_slots=estate.upgrade_slots,
            installed_upgrades=[
                InstalledUpgrade(
                    slot_index=upgrade.slot_index, upgrade_id=upgrade.upgrade_id
                )
                for upgrade in upgrades
            ],
        ),
    )


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    request: Request, player: CurrentPlayer, session: DatabaseSession
) -> ProfileResponse:
    """Return the caller's character profile."""
    character = _character_for_player(session, player.id)
    return _profile(session, _content(request), character)


@router.get("/me/inventory", response_model=InventoryResponse)
async def get_inventory(
    player: CurrentPlayer, session: DatabaseSession
) -> InventoryResponse:
    """Return all item stacks owned by the caller's character."""
    character = _character_for_player(session, player.id)
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
