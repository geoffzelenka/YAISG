"""Key validation and transition hooks under the existing realm locks."""

import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.content.schemas import Action
from app.errors import api_error
from app.models import ItemInstance


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
        session.scalars(
            select(ItemInstance)
            .options(joinedload(ItemInstance.listing))
            .where(ItemInstance.realm_id == realm_id)
        )
    )


def deprecate_keys(keys: list[ItemInstance]) -> None:
    """Keep existing resources usable throughout a pending transition."""
    for key in keys:
        if key.state == "active":
            key.state = "deprecated"


def invalidate_keys(keys: list[ItemInstance], at: datetime) -> None:
    """Record the first access cutoff without touching any character action.

    Holders resolve earned work lazily under their own character lock. Repeated
    transitions must never extend a key's original access window.
    """
    for key in keys:
        if key.listing is not None and key.listing.status == "open":
            key.listing.status = "cancelled"
            key.holder_character_id = key.listing.seller_character_id
        key.state = "invalid"
        if key.invalidated_at is None:
            key.invalidated_at = at
