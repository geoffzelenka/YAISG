"""World setup for tests that isolate character and estate behavior."""

import uuid
from dataclasses import replace
from datetime import datetime

from httpx import AsyncClient, Response
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from app.content.loader import ContentIndex
from app.main import app
from app.models import Character, Estate, RealmState
from app.services.world import create_world


def create_empty_world(session: Session, content: ContentIndex, now: datetime) -> None:
    """Use an explicit empty seed so unrelated tests own all their test holdings."""
    seed = content.world_seed.model_copy(
        update={
            "realms": tuple(
                realm.model_copy(update={"treasury": 0, "stores": (), "estates": ()})
                for realm in content.world_seed.realms
            )
        }
    )
    create_world(session, replace(content, world_seed=seed), now)
    session.commit()


async def create_world_character(
    client: AsyncClient,
    factory: sessionmaker[Session],
    *,
    headers: dict[str, str],
    name: str,
    realm_id: str,
) -> Response:
    """Create an API identity, then place an unrelated test directly in the world.

    These fixtures test world mechanics, not the tutorial. No tutorial rewards or
    departure rules are bypassed in production; this is explicit test setup.
    """
    response = await client.post("/characters", headers=headers, json={"name": name})
    if response.status_code != 201:
        return response
    identifier = uuid.UUID(response.json()["character"]["id"])
    with factory() as session:
        character = session.get(Character, identifier)
        assert character is not None
        estate = session.get(Estate, character.home_estate_id)
        assert estate is not None
        character.current_realm_id = realm_id
        character.tutorial_step = None
        estate.realm_id = realm_id
        estate.form_id = app.state.content.progression.basic_mobile_form
        session.flush()
        session.execute(
            delete(RealmState).where(RealmState.owner_character_id == identifier)
        )
        session.commit()
    profile = await client.get("/characters/me", headers=headers)
    assert profile.status_code == 200, profile.text
    return Response(201, json=profile.json())
