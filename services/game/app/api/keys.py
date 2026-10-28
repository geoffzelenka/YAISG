"""Private key inventory and explicit trophy disposal."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.api.actions import get_character
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.models import ActiveActionRecord, ItemInstance, KeyListing
from app.services.actions import as_utc, clear_active_action, resolve_character
from app.services.keys import held_key

router = APIRouter(prefix="/keys", tags=["keys"])


class KeyResponse(BaseModel):
    """The holder-visible rolled resource, provenance and remaining access."""

    id: uuid.UUID
    kind: str
    template_id: str
    discovered_by_character_id: uuid.UUID | None
    discovered_by_name: str
    realm_id: str
    payload: dict[str, Any]
    uses_total: int
    uses_remaining: int
    state: str
    invalidated_at: datetime | None
    bound_at: datetime | None
    created_at: datetime

    @field_validator("created_at", "bound_at", "invalidated_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        """Restore the timezone omitted by SQLite's datetime adapter."""
        return as_utc(value) if value is not None else None


class KeysResponse(BaseModel):
    """Every held instance, including trophies."""

    keys: list[KeyResponse]


@router.get("/me")
async def get_keys(
    request: Request, now: ServerNow, player: CurrentPlayer, session: DatabaseSession
) -> KeysResponse:
    """Resolve progress before returning the caller's private holdings."""
    character = get_character(session, player.id)
    resolve_character(session, character.id, now, request.app.state.content)
    keys = list(
        session.scalars(
            select(ItemInstance)
            .where(ItemInstance.holder_character_id == character.id)
            .order_by(ItemInstance.created_at, ItemInstance.id)
        )
    )
    response = KeysResponse(
        keys=[KeyResponse.model_validate(key, from_attributes=True) for key in keys]
    )
    session.commit()
    return response


@router.delete("/{identifier}", status_code=204)
async def delete_key(
    identifier: uuid.UUID,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> Response:
    """Dispose of any held key, stopping its action after final resolution."""
    character = get_character(session, player.id)
    resolve_character(session, character.id, now, request.app.state.content)
    key = held_key(session, identifier, character.id)
    active = session.get(ActiveActionRecord, character.id)
    if active is not None and active.key_instance_id == identifier:
        clear_active_action(session, character.id)
    listing = session.scalar(
        select(KeyListing).where(KeyListing.instance_id == identifier).with_for_update()
    )
    if listing is not None:
        session.delete(listing)
        session.flush()
    session.delete(key)
    session.commit()
    return Response(status_code=204)
