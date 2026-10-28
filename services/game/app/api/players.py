"""Player API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import CurrentPlayer

router = APIRouter(prefix="/players", tags=["players"])


class PlayerResponse(BaseModel):
    """Public player identity."""

    id: uuid.UUID
    auth_user_id: uuid.UUID
    kind: str
    created_at: datetime


@router.get("/me", response_model=PlayerResponse)
def get_me(player: CurrentPlayer) -> PlayerResponse:
    """Return the caller's auto-provisioned player record."""
    return PlayerResponse.model_validate(player, from_attributes=True)
