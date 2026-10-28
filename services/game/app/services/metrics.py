"""Transactional counters; engine code never knows about instrumentation."""

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
    pending = {row.name: row for row in session.new if isinstance(row, MetricDelta)}
    for name, amount in amounts.items():
        if name not in COUNTERS or amount < 0:
            raise ValueError(f"Invalid operational counter {name}={amount}")
        if not amount:
            continue
        if name in pending:
            pending[name].amount += amount
        else:
            row = MetricDelta(name=name, amount=amount)
            session.add(row)
            pending[name] = row
