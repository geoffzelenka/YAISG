"""Operator-only economy accounting."""

from fastapi import APIRouter
from sqlalchemy import func, literal, select, union_all

from app import config
from app.auth import DatabaseSession, Identity
from app.errors import api_error
from app.models import Currency, GoldLedger, RealmState

router = APIRouter()


@router.get("/admin/economy")
async def economy(
    identity: Identity, session: DatabaseSession
) -> dict[str, dict[str, int]]:
    """Report holdings and signed ledger totals in one database snapshot."""
    if str(identity.auth_user_id) not in config.OPERATOR_AUTH_USER_IDS:
        raise api_error(403, "OPERATOR_REQUIRED", "Operator access is required")
    # A single statement keeps the holder and ledger totals in the same snapshot
    # on PostgreSQL's default READ COMMITTED isolation level.
    rows = session.execute(
        union_all(
            select(GoldLedger.cause, func.sum(GoldLedger.amount)).group_by(
                GoldLedger.cause
            ),
            select(literal("wallets"), func.coalesce(func.sum(Currency.gold), 0)),
            select(
                literal("treasuries"), func.coalesce(func.sum(RealmState.treasury), 0)
            ),
        )
    ).all()
    totals = {str(cause): int(amount) for cause, amount in rows}
    return {
        "holders": {key: totals.pop(key) for key in ("wallets", "treasuries")},
        "ledger": totals,
    }
