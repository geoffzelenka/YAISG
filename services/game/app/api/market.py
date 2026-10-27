"""Global player market reads and atomic slot mutations."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.api.actions import get_character
from app.auth import CurrentPlayer, DatabaseSession
from app.clock import ServerNow
from app.models import MarketMatch, MarketOrder
from app.services.order_book import (
    cancel_order,
    collect_order,
    create_order,
    owned_order,
    prepare_market,
    validate_good,
)

router = APIRouter(prefix="/market", tags=["market"])


class OrderRequest(BaseModel):
    """Whole-unit limit order intent; the server computes every transfer."""

    model_config = ConfigDict(extra="forbid")
    side: Literal["buy", "sell"]
    item_id: str = Field(min_length=1)
    quantity: int = Field(gt=0, le=2**63 - 1, strict=True)
    unit_price: int = Field(gt=0, le=2**63 - 1, strict=True)


def order_response(order: MarketOrder) -> dict[str, object]:
    """Project an owned slot including its uncollected holdings."""
    return {
        name: getattr(order, name)
        for name in (
            "id",
            "side",
            "item_id",
            "unit_price",
            "quantity",
            "quantity_remaining",
            "escrow_gold_remaining",
            "fill_items",
            "fill_gold",
            "status",
            "realm_id",
            "created_at",
            "expires_at",
            "closed_at",
        )
    }


def match_response(match: MarketMatch) -> dict[str, object]:
    """Report immediate executions at actual maker prices."""
    return {
        name: getattr(match, name)
        for name in (
            "id",
            "maker_order_id",
            "taker_order_id",
            "item_id",
            "quantity",
            "unit_price",
            "tax_gold",
            "burned_gold",
            "tax_realm_id",
            "matched_at",
        )
    }


@router.post("/orders", status_code=201)
async def place_order(
    body: OrderRequest,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, object]:
    """Place one fully escrowed order and return its immediate fills."""
    character = get_character(session, player.id)
    content = request.app.state.content
    prepare_market(session, character, now, content)
    order, matches = create_order(
        session,
        character,
        body.side,
        body.item_id,
        body.quantity,
        body.unit_price,
        now,
        content,
    )
    response: dict[str, object] = {
        "order": order_response(order),
        "fills": [match_response(m) for m in matches],
    }
    session.commit()
    return response


@router.get("/orders/me")
async def own_orders(
    player: CurrentPlayer, session: DatabaseSession
) -> dict[str, object]:
    """Read all owned slots from any location, including retained closed rows."""
    character = get_character(session, player.id)
    orders = session.scalars(
        select(MarketOrder)
        .where(MarketOrder.character_id == character.id)
        .order_by(MarketOrder.created_at, MarketOrder.id)
    )
    return {"orders": [order_response(o) for o in orders]}


@router.get("/book/{item_id}")
async def book(
    item_id: str,
    request: Request,
    session: DatabaseSession,
    depth: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    """Aggregate each side by price; access and presence do not gate reads."""
    validate_good(item_id, request.app.state.content)
    levels: dict[str, object] = {}
    for side in ("buy", "sell"):
        price = MarketOrder.unit_price
        rows = session.execute(
            select(price, func.sum(MarketOrder.quantity_remaining))
            .where(
                MarketOrder.item_id == item_id,
                MarketOrder.side == side,
                MarketOrder.status == "open",
            )
            .group_by(price)
            .order_by(price.desc() if side == "buy" else price.asc())
            .limit(depth)
        )
        # PostgreSQL SUM(bigint) returns Decimal; normalize at the API boundary
        # just as the economy report does, preserving integer JSON on both DBs.
        levels[side] = [{"unit_price": int(p), "quantity": int(q)} for p, q in rows]
    return {"item_id": item_id, **levels}


@router.post("/orders/{order_id}/cancel")
async def cancel(
    order_id: uuid.UUID,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, object]:
    """Cancel without market access, leaving every holding in the slot."""
    character = get_character(session, player.id)
    prepare_market(session, character, now, request.app.state.content)
    order = owned_order(session, character, order_id)
    cancel_order(order)
    response = order_response(order)
    session.commit()
    return {"order": response}


@router.post("/orders/{order_id}/collect")
async def collect(
    order_id: uuid.UUID,
    request: Request,
    now: ServerNow,
    player: CurrentPlayer,
    session: DatabaseSession,
) -> dict[str, object]:
    """Move available proceeds into a wallet and inventory within current caps."""
    character = get_character(session, player.id)
    content = request.app.state.content
    prepare_market(session, character, now, content)
    order = owned_order(session, character, order_id)
    items, gold = collect_order(session, character, order, now, content)
    response: dict[str, object] = {
        "order": order_response(order),
        "collected": {"items": items, "gold": gold},
    }
    session.commit()
    return response
