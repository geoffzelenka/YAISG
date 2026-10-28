"""Authenticated permanent-equipment changes."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from app.api.actions import get_character
from app.api.characters import BeltStack, EquippedStack
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import EquipmentSlot
from app.engine.consumables import change_consumable
from app.engine.core import action_definition, effective_cycle_time
from app.engine.equipment import EquipmentError, change_equipment
from app.errors import api_error
from app.models import CharacterBelt, CharacterEquipment
from app.services.actions import (
    as_utc,
    load_character_state,
    regenerate_character_hp,
    resolve_character,
    resolve_locked_character,
)
from app.services.equipment import persist_consumable, persist_equipment

router = APIRouter(prefix="/equipment", tags=["equipment"])


class UnequipRequest(BaseModel):
    """A concrete slot to empty."""

    model_config = ConfigDict(extra="forbid")
    slot: EquipmentSlot


class EquipRequest(UnequipRequest):
    """An inventory item and concrete destination slot."""

    item_id: str


class EquipmentResponse(BaseModel):
    """The authoritative permanent equipment layout."""

    equipment: dict[str, EquippedStack]


def _change(
    body: UnequipRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> EquipmentResponse:
    character = get_character(session, player.id)
    content: ContentIndex = request.app.state.content
    resolution = resolve_character(session, character.id, now, content)
    active = resolution.active
    if (
        active is not None
        and action_definition(active.action_id, active.meta, content).resolver
        == "combat"
    ):
        raise api_error(
            409, "EQUIPMENT_IN_COMBAT", "Equipment cannot change during combat"
        )
    state = load_character_state(session, character.id, content, now)
    equipped = {
        row.slot: row.item_id
        for row in session.scalars(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id
            )
        )
    }
    try:
        inventory, equipment = change_equipment(
            state,
            equipped,
            body.slot,
            body.item_id if isinstance(body, EquipRequest) else None,
            content,
        )
    except EquipmentError as exc:
        raise api_error(
            404 if exc.code == "UNKNOWN_ITEM" else 409, exc.code, str(exc)
        ) from None
    persist_equipment(session, character.id, inventory, equipment)
    session.flush()
    regenerate_character_hp(session, character, now, content)
    changed_state = load_character_state(session, character.id, content, now)
    if (
        active is not None
        and action_definition(active.action_id, active.meta, content).resolver
        == "uniform"
        and now >= as_utc(active.last_resolved_at)
    ):
        # Preserve fractional cycle progress, without applying the new speed to
        # wall time already spent under the old gear. Journeys snapshot paid edges.
        action = action_definition(active.action_id, active.meta, content)
        old_cycle = effective_cycle_time(action, state, content)
        new_cycle = effective_cycle_time(action, changed_state, content)
        fraction = (
            (now - as_utc(active.last_resolved_at)).total_seconds() * 1000 / old_cycle
        )
        active.last_resolved_at = now - timedelta(milliseconds=fraction * new_cycle)
    if active is not None:
        required_tool = action_definition(
            active.action_id, active.meta, content
        ).requires.tool_class
        if (
            required_tool is not None
            and required_tool != changed_state.right_hand_tool_class
        ):
            # The equipment mutation is the detection boundary for a lost tool;
            # do not accrue another interval of work without the required item.
            resolve_locked_character(session, character.id, now, content, record=active)
    session.commit()
    return EquipmentResponse(
        equipment={
            row.slot: EquippedStack(item_id=row.item_id, quantity=row.quantity)
            for row in session.scalars(
                select(CharacterEquipment).where(
                    CharacterEquipment.character_id == character.id
                )
            )
        }
    )


@router.post("/equip")
async def equip(
    body: EquipRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> EquipmentResponse:
    """Resolve elapsed work and move one inventory item into equipment."""
    return _change(body, request, now, player, session)


@router.post("/unequip")
async def unequip(
    body: UnequipRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> EquipmentResponse:
    """Resolve elapsed work and return one equipped item to inventory."""
    return _change(body, request, now, player, session)


class StackRequest(BaseModel):
    """Replace a setup stack; null item and zero quantity empty the holder."""

    model_config = ConfigDict(extra="forbid", strict=True)
    item_id: str | None = None
    quantity: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_stack(self) -> "StackRequest":
        """Reject partial or inconsistent stack intents."""
        if (self.item_id is None) != (self.quantity == 0):
            raise ValueError(
                "item_id requires positive quantity; empty stacks require null item"
            )
        return self


class BeltRequest(StackRequest):
    """A belt assignment with one matching reactive trigger."""

    trigger: dict[str, float | bool] | None = None


class ConsumablesResponse(EquipmentResponse):
    """All physical equipment and belt holders after a setup transfer."""

    belt: dict[int, BeltStack]


def _setup_stack(
    body: StackRequest,
    slot: int | None,
    request: Request,
    now: datetime,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ConsumablesResponse:
    character = get_character(session, player.id)
    content: ContentIndex = request.app.state.content
    resolution = resolve_character(session, character.id, now, content)
    if (
        resolution.active is not None
        and action_definition(
            resolution.active.action_id, resolution.active.meta, content
        ).resolver
        == "combat"
    ):
        raise api_error(
            409, "EQUIPMENT_IN_COMBAT", "Consumable setup cannot change during combat"
        )
    state = load_character_state(session, character.id, content, now)
    equipment = {
        row.slot: row
        for row in session.scalars(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id
            )
        )
    }
    belt = {
        row.slot: row
        for row in session.scalars(
            select(CharacterBelt).where(CharacterBelt.character_id == character.id)
        )
    }
    previous = equipment.get("utility") if slot is None else belt.get(slot)
    trigger = body.trigger if isinstance(body, BeltRequest) else None
    try:
        inventory = change_consumable(
            state,
            (previous.item_id, previous.quantity) if previous else None,
            body.item_id,
            body.quantity,
            content,
            belt_slot=slot,
            belt_item=equipment["belt"].item_id if "belt" in equipment else None,
            trigger=trigger,
        )
    except EquipmentError as exc:
        raise api_error(
            404 if exc.code == "UNKNOWN_ITEM" else 409, exc.code, str(exc)
        ) from None
    persist_equipment(
        session,
        character.id,
        inventory,
        {key: row.item_id for key, row in equipment.items()},
    )
    persist_consumable(
        session, character.id, previous, slot, body.item_id, body.quantity, trigger
    )
    session.flush()
    response = ConsumablesResponse(
        equipment={
            row.slot: EquippedStack(item_id=row.item_id, quantity=row.quantity)
            for row in session.scalars(
                select(CharacterEquipment).where(
                    CharacterEquipment.character_id == character.id
                )
            )
        },
        belt={
            row.slot: BeltStack(
                item_id=row.item_id, quantity=row.quantity, trigger=row.trigger
            )
            for row in session.scalars(
                select(CharacterBelt).where(CharacterBelt.character_id == character.id)
            )
        },
    )
    session.commit()
    return response


@router.put("/utility")
async def setup_utility(
    body: StackRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ConsumablesResponse:
    """Move a per-cycle utility stack between inventory and equipment."""
    return _setup_stack(body, None, request, now, player, session)


@router.put("/belt/{slot}")
async def setup_belt(
    slot: int,
    body: BeltRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> ConsumablesResponse:
    """Assign or empty one zero-based reactive belt position."""
    return _setup_stack(body, slot, request, now, player, session)
