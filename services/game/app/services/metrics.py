"""Transactional counters; engine code never knows about instrumentation."""

from typing import cast

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models import MetricDelta

COUNTERS = (
    "ticks_run",
    "tick_duration_ns",
    "matches",
    "tax_gold",
    "realm_trades",
    "caravan_shipments",
    "caravan_losses",
    "tags_shed",
    "regressions",
    "keys_discovered",
)


def record(session: Session, **amounts: int) -> None:
    """Stage counter increments, combining unflushed samples into one batch.

    Deltas survive holder deletion, but roll back with failed game transactions.
    Duration is total wall time in nanoseconds for completed realm tick batches.
    """
    pending = cast(
        dict[str, MetricDelta], session.info.setdefault("metric_deltas_pending", {})
    )
    for name, amount in amounts.items():
        if name not in COUNTERS or amount < 0:
            raise ValueError(f"Invalid operational counter {name}={amount}")
        if not amount:
            continue
        row = pending.get(name)
        # Flushing makes a row persistent; rollback removes newly added rows.
        # Check only this cached row so both cases start a fresh delta without
        # scanning unrelated pending game objects or retaining rollback state.
        if row is not None and inspect(row).pending and inspect(row).session is session:
            row.amount += amount
            continue
        row = MetricDelta(name=name, amount=amount)
        session.add(row)
        pending[name] = row


def compact_deltas(session: Session, batch_size: int = 1000) -> int:
    """Replace a bounded locked batch with equivalent sums in this transaction.

    PostgreSQL skips rows held by another compactor; gameplay only inserts new
    deltas. Readers therefore see the old or new sums atomically, and rollback
    restores the original rows. The caller owns writer intent on SQLite.
    """
    if batch_size < 2:
        raise ValueError("Metric compaction batch_size must be at least two")
    session.flush()
    rows = list(
        session.scalars(
            select(MetricDelta)
            .order_by(MetricDelta.name, MetricDelta.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    )
    amounts: dict[str, int] = {}
    for row in rows:
        amounts[row.name] = amounts.get(row.name, 0) + row.amount
    if len(rows) <= len(amounts):
        return 0
    for row in rows:
        session.delete(row)
    session.add_all(
        MetricDelta(name=name, amount=amount) for name, amount in amounts.items()
    )
    session.flush()
    return len(rows) - len(amounts)
