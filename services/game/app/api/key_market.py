"""Browse and trade fixed-price resource keys."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.actions import get_character
from app.api.keys import KeyResponse
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.models import ItemInstance, KeyListing
from app.services.key_market import list_key, transfer_listing

router = APIRouter(prefix="/keys/market", tags=["keys"])


class ListingRequest(BaseModel):
    """A whole-gold fixed price for one held instance."""

    model_config = ConfigDict(extra="forbid")
    instance_id: uuid.UUID
    price_gold: int = Field(gt=0, le=2**63 - 1, strict=True)


def listing_response(listing: KeyListing, key: ItemInstance) -> dict[str, object]:
    """Expose rolled values and explicit deprecation without hidden realm balances."""
    return {
        "id": listing.id,
        "price_gold": listing.price_gold,
        "realm_id": listing.realm_id,
        "status": listing.status,
        "deprecated": key.state == "deprecated",
        "key": KeyResponse.model_validate(key, from_attributes=True),
    }


@router.post("", status_code=201)
async def create(
    body: ListingRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, object]:
    """List one active unbound key with market access."""
    character = get_character(session, player.id)
    listing = list_key(
        session,
        character,
        body.instance_id,
        body.price_gold,
        now,
        request.app.state.content,
    )
    key = session.get(ItemInstance, listing.instance_id)
    assert key is not None
    response = listing_response(listing, key)
    session.commit()
    return response


@router.post("/{identifier}/{operation}")
async def transfer(
    identifier: uuid.UUID,
    operation: Literal["buy", "cancel"],
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, object]:
    """Buy directly into inventory or cancel back to the seller."""
    character = get_character(session, player.id)
    listing = transfer_listing(
        session, character, identifier, operation, now, request.app.state.content
    )
    key = session.get(ItemInstance, listing.instance_id)
    assert key is not None
    response = listing_response(listing, key)
    session.commit()
    return response


@router.get("")
async def browse(
    request: Request,
    player: CurrentPlayer,
    session: DatabaseSession,
    realm_id: str | None = None,
    item_id: str | None = None,
    goods_class: Annotated[str | None, Query(alias="class")] = None,
    kind: str | None = None,
) -> dict[str, object]:
    """Read open listings remotely, matching goods against resource outputs."""
    content = request.app.state.content
    rows = session.execute(
        select(KeyListing, ItemInstance)
        .join(ItemInstance, KeyListing.instance_id == ItemInstance.id)
        .where(KeyListing.status == "open")
        .order_by(KeyListing.created_at, KeyListing.id)
    )
    result = []
    for listing, key in rows:
        action = key.payload["action"]
        resource_kind = "combat" if action.get("combatant_id") else "gather"
        if realm_id is not None and key.realm_id != realm_id:
            continue
        if kind is not None and resource_kind != kind:
            continue
        outputs = (
            content.combatant(action["combatant_id"]).drops
            if resource_kind == "combat"
            else action.get("outputs", ())
        )
        goods = [
            output.item_id if hasattr(output, "item_id") else output["item_id"]
            for output in outputs
        ]
        if item_id is not None and item_id not in goods:
            continue
        if goods_class is not None and not any(
            goods_class in content.item(good).classes for good in goods
        ):
            continue
        result.append(listing_response(listing, key))
    return {"listings": result}
