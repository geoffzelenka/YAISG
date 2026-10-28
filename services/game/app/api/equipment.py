"""Authenticated permanent-equipment changes."""

from datetime import timedelta

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.actions import get_character
from app.api.characters import EquippedStack
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import EquipmentSlot
from app.engine.core import effective_cycle_time
from app.engine.equipment import EquipmentError, change_equipment
from app.errors import api_error
from app.models import CharacterEquipment
from app.services.actions import (
    as_utc,
    load_character_state,
    resolve_character,
    resolve_locked_character,
)
from app.services.equipment import persist_equipment

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
    if active is not None and content.action(active.action_id).resolver == "combat":
        raise api_error(
            409, "EQUIPMENT_IN_COMBAT", "Equipment cannot change during combat"
        )
    state = load_character_state(session, character.id, content)
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
    changed_state = load_character_state(session, character.id, content)
    if (
        active is not None
        and content.action(active.action_id).resolver == "uniform"
        and now >= as_utc(active.last_resolved_at)
    ):
        # Preserve fractional cycle progress, without applying the new speed to
        # wall time already spent under the old gear. Journeys snapshot paid edges.
        action = content.action(active.action_id)
        old_cycle = effective_cycle_time(action, state, content)
        new_cycle = effective_cycle_time(action, changed_state, content)
        fraction = (
            (now - as_utc(active.last_resolved_at)).total_seconds() * 1000 / old_cycle
        )
        active.last_resolved_at = now - timedelta(milliseconds=fraction * new_cycle)
    if active is not None:
        required_tool = content.action(active.action_id).requires.tool_class
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
            slot: EquippedStack(item_id=item, quantity=1)
            for slot, item in equipment.items()
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
