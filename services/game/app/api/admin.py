"""Operator-only economy accounting."""

from fastapi import APIRouter
from sqlalchemy import func, literal, select, union_all

from app import config
from app.auth import DatabaseSession, Identity
from app.errors import api_error
from app.models import Currency, GoldLedger, MarketOrder, MetricDelta, RealmState
from app.services.metrics import COUNTERS

router = APIRouter()


@router.get("/admin/economy")
def economy(identity: Identity, session: DatabaseSession) -> dict[str, dict[str, int]]:
    """Report holdings and signed ledger totals in one database snapshot."""
    if identity.auth_user_id not in config.OPERATOR_AUTH_USER_IDS:
        raise api_error(403, "OPERATOR_REQUIRED", "Operator access is required")
    # A single statement keeps the holder and ledger totals in the same snapshot
    # on PostgreSQL's default READ COMMITTED isolation level.
    rows = session.execute(
        union_all(
            select(GoldLedger.cause, func.sum(GoldLedger.amount)).group_by(
                GoldLedger.cause
            ),
            select(
                literal("order_escrow"),
                func.coalesce(func.sum(MarketOrder.escrow_gold_remaining), 0),
            ),
            select(
                literal("order_slots"),
                func.coalesce(func.sum(MarketOrder.fill_gold), 0),
            ),
            select(literal("wallets"), func.coalesce(func.sum(Currency.gold), 0)),
            select(
                literal("treasuries"), func.coalesce(func.sum(RealmState.treasury), 0)
            ),
        )
    ).all()
    totals = {str(cause): int(amount) for cause, amount in rows}
    return {
        "holders": {
            key: totals.pop(key)
            for key in ("wallets", "treasuries", "order_escrow", "order_slots")
        },
        "ledger": totals,
    }


@router.get("/admin/metrics")
def metrics(identity: Identity, session: DatabaseSession) -> dict[str, object]:
    """Expose durable event totals and private holder gauges to operators only."""
    accounting = economy(identity, session)
    counters = dict.fromkeys(COUNTERS, 0)
    counters.update(
        (name, int(amount))
        for name, amount in session.execute(
            select(MetricDelta.name, func.sum(MetricDelta.amount)).group_by(
                MetricDelta.name
            )
        )
    )
    counters["gold_minted"] = accounting["ledger"].get("mint", 0)
    return {"counters": counters, "gold_by_holder": accounting["holders"]}
