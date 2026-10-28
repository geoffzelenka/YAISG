"""Authenticated departure from the private island."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from app.api.actions import get_character
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.services.actions import resolve_character
from app.services.tutorial import depart, instance_id

router = APIRouter(prefix="/tutorial", tags=["tutorial"])


class DepartureRequest(BaseModel):
    """A server-validated arrival realm choice."""

    model_config = ConfigDict(extra="forbid")
    destination_realm_id: str


@router.post("/depart")
def departure(
    body: DepartureRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, str]:
    """Resolve island work and destroy its gold in one departure transaction."""
    content = request.app.state.content
    character = get_character(session, player.id)
    realm_ids = {
        instance_id(t, character.id)
        for t in (content.tutorial.realm_1, content.tutorial.realm_2)
    }
    if body.destination_realm_id in content.tutorial.arrival_realms:
        realm_ids.add(body.destination_realm_id)
    resolve_character(session, character.id, now, content, realm_ids)
    depart(session, character, player.kind, body.destination_realm_id, content, now)
    session.commit()
    return {"current_realm_id": character.current_realm_id}
