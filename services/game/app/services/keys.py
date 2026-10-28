"""Key validation and transition hooks under the existing realm locks."""

import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.schemas import Action
from app.errors import api_error
from app.models import ActiveActionRecord, ItemInstance, RewardLog


def held_key(
    session: Session, identifier: uuid.UUID, character_id: uuid.UUID
) -> ItemInstance:
    """Hide absent and other holders' instance identities behind one error."""
    key = session.get(ItemInstance, identifier)
    if key is None or key.holder_character_id != character_id:
        raise api_error(404, "UNKNOWN_KEY", "The key is not held by this character")
    return key


def key_action(key: ItemInstance, realm_id: str) -> Action:
    """Validate private access before projecting the server-stored inline action."""
    if key.state == "invalid":
        raise api_error(409, "KEY_INVALIDATED", "The key's realm has changed")
    if key.state == "depleted" or key.uses_remaining == 0:
        raise api_error(409, "KEY_DEPLETED", "The key has no uses remaining")
    if key.state not in {"active", "deprecated"}:
        raise api_error(409, "KEY_UNAVAILABLE", "The key cannot be used")
    if key.realm_id != realm_id:
        raise api_error(409, "KEY_WRONG_REALM", "Travel to the key's realm to use it")
    return Action.model_validate_json(json.dumps(key.payload["action"]))


def realm_keys(session: Session, realm_id: str) -> list[ItemInstance]:
    """Load realm instances once under the realm serialization lock."""
    return list(
        session.scalars(select(ItemInstance).where(ItemInstance.realm_id == realm_id))
    )


def deprecate_keys(keys: list[ItemInstance]) -> None:
    """Keep existing resources usable throughout a pending transition."""
    for key in keys:
        if key.state == "active":
            key.state = "deprecated"


def invalidate_keys(
    keys: list[ItemInstance], actions: list[ActiveActionRecord], at: datetime
) -> tuple[list[ActiveActionRecord], list[RewardLog]]:
    """Invalidate access and build stop-only feed entries without character locks.

    Callers hold the realm lock, which every key mutation takes after its
    character lock. No character row is changed by a realm transition.
    """
    identifiers = {key.id for key in keys}
    for key in keys:
        key.state = "invalid"
    stopped = [action for action in actions if action.key_instance_id in identifiers]
    logs = [
        RewardLog(
            character_id=action.character_id,
            action_id=action.action_id,
            cycles=0,
            xp={},
            items={},
            details={"stop_reason": "KEY_INVALIDATED"},
            resolved_at=at,
        )
        for action in stopped
    ]
    return stopped, logs
