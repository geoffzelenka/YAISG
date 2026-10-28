"""Browse and trade fixed-price resource keys."""

import base64
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import and_, or_, select

from app.api.actions import get_character
from app.api.keys import KeyResponse
from app.api.market import parse_history_cursor
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.content.loader import ContentIndex
from app.content.schemas import Drop
from app.models import ItemInstance, KeyListing
from app.services.actions import as_utc
from app.services.key_market import list_key, transfer_listing

router = APIRouter(prefix="/keys/market", tags=["keys"])


class ListingRequest(BaseModel):
    """A whole-gold fixed price for one held instance."""

    model_config = ConfigDict(extra="forbid")
    instance_id: uuid.UUID
    price_gold: int = Field(gt=0, le=2**63 - 1, strict=True)


class BuyRequest(BaseModel):
    """Optionally pin the price seen by the buyer before submitting intent."""

    model_config = ConfigDict(extra="forbid")
    price_gold: int | None = Field(default=None, gt=0, le=2**63 - 1, strict=True)


def listing_response(listing: KeyListing, key: ItemInstance) -> dict[str, object]:
    """Expose rolled values and explicit deprecation without hidden realm balances."""
    return {
        "id": listing.id,
        "price_gold": listing.price_gold,
        "realm_id": listing.realm_id,
        "status": listing.status,
        "deprecated": key.state == "deprecated",
        "key": KeyResponse.model_validate(key, from_attributes=True).model_dump(
            exclude={"discovered_by_character_id"}
        ),
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
    body: BuyRequest | None = None,
) -> dict[str, object]:
    """Buy directly into inventory or cancel back to the seller."""
    character = get_character(session, player.id)
    listing = transfer_listing(
        session,
        character,
        identifier,
        operation,
        now,
        request.app.state.content,
        expected_price_gold=body.price_gold if body is not None else None,
    )
    key = session.get(ItemInstance, listing.instance_id)
    assert key is not None
    response = listing_response(listing, key)
    session.commit()
    return response


def listing_cursor(listing: KeyListing) -> str:
    """Encode the descending creation-time/UUID boundary, as market history does."""
    value = f"{as_utc(listing.created_at).isoformat()}|{listing.id}"
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def resource_goods(
    key: ItemInstance, content: ContentIndex
) -> tuple[str, list[str]] | None:
    """Normalize stored gathering outputs and authored combat drops explicitly.

    Removed content makes a listing unbrowseable rather than failing the whole
    page; the seller can still cancel it and recover the physical key.
    """
    try:
        action = key.payload["action"]
        if action.get("combatant_id"):
            kind = "combat"
            drops = content.combatant(action["combatant_id"]).drops
        else:
            kind = "gather"
            drops = tuple(
                Drop.model_validate(output) for output in action.get("outputs", ())
            )
        goods = [drop.item_id for drop in drops]
        for identifier in goods:
            content.item(identifier)
        return kind, goods
    except (KeyError, ValidationError):
        return None


@router.get("")
async def browse(
    request: Request,
    player: CurrentPlayer,
    session: DatabaseSession,
    realm_id: str | None = None,
    item_id: str | None = None,
    goods_class: Annotated[str | None, Query(alias="class")] = None,
    kind: Literal["gather", "combat"] | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before: Annotated[str | None, Query(max_length=256)] = None,
) -> dict[str, object]:
    """Page open listings by discovery realm and resource outputs, newest first."""
    content = request.app.state.content
    statement = (
        select(KeyListing, ItemInstance)
        .join(ItemInstance, KeyListing.instance_id == ItemInstance.id)
        .where(KeyListing.status == "open")
    )
    if realm_id is not None:
        statement = statement.where(ItemInstance.realm_id == realm_id)
    boundary = parse_history_cursor(before) if before is not None else None
    matches: list[tuple[KeyListing, ItemInstance]] = []
    # Content-dependent filters are applied after SQL, in bounded batches. Seek
    # through nonmatching rows so sparse filters still fill the requested page.
    while len(matches) <= limit:
        batch_statement = statement
        if boundary is not None:
            at, identifier = boundary
            batch_statement = batch_statement.where(
                or_(
                    KeyListing.created_at < at,
                    and_(KeyListing.created_at == at, KeyListing.id < identifier),
                )
            )
        rows = session.execute(
            batch_statement.order_by(
                KeyListing.created_at.desc(), KeyListing.id.desc()
            ).limit(limit + 1)
        ).all()
        if not rows:
            break
        for listing, key in rows:
            resource = resource_goods(key, content)
            if resource is None:
                continue
            resource_kind, goods = resource
            if kind is not None and resource_kind != kind:
                continue
            if item_id is not None and item_id not in goods:
                continue
            if goods_class is not None and not any(
                goods_class in content.item(good).classes for good in goods
            ):
                continue
            matches.append((listing, key))
            if len(matches) > limit:
                break
        last_listing = rows[-1][0]
        boundary = as_utc(last_listing.created_at), last_listing.id
    page = matches[:limit]
    return {
        "listings": [listing_response(listing, key) for listing, key in page],
        "next_cursor": listing_cursor(page[-1][0]) if len(matches) > limit else None,
    }
