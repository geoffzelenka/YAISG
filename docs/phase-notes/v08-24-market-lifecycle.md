## Built

- Added a separate expiry/retention job to the existing APScheduler instance.
  Cadence and retention are strict economy.market content settings. The driver
  acquires a PostgreSQL transaction advisory lock, then the same sorted realm
  serialization as market mutations before locking eligible order rows.
  SQLite starts with writer intent. One transaction expires and purges a pass;
  failures roll back and the scheduled callback logs the traceback.
- Expiry reuses cancel_order: remaining sell goods and buy gold move into their
  collectable slots alongside existing fills, without inventory/wallet credit.
  Closed rows are removed only strictly past retention. Collectable balances
  never expire or purge. Repeated passes are idempotent; no match rows are deleted.
- Added authenticated GET /market/history/me from durable buyer/seller match
  identities, independent of retained order rows or current market access.
  Executions sort newest first, with descending match UUID for timestamp ties.
  Self-matches appear once. Match projections include both participant ids.
- Added the deadline-free, deterministic Hypothesis world conservation suite.
  It uses the TEST_DATABASE_URL API fixture and real realm trades, gifts,
  project kickoff/contribution, larder deposits, estate transform/build/buy/
  surrender, caravan dispatch/arrival, mint and realm ticks, order placement,
  matching, cancellation, collection and lifecycle passes. A mandatory prefix
  executes each flow before generated interleavings, including persistent slots.
- Gold compares /admin/economy sum(holders) minus sum(ledger) after each
  operation, including nonzero tax and caravan-fee burns and mint creation.
  Per-item goods accounting uses milli-items across inventories, sell escrow,
  slot fills, realm stores, larders and only in_transit arriving cargo. Historical
  shipments contribute their sent-minus-arriving road loss, never another holder.
  Authorized production, recipe inputs/outputs, construction/project consumption,
  upkeep, mint bullion, spoilage and cap losses are counted separately. The
  mandatory prefix asserts sources/losses and both burn ledger causes occur.
- Picked up Prompt 17's additional hand-off: test_trade_errors_are_atomic now
  checks holdings after the exception and before rollback, covering buy-side
  PRICE_MOVED and physical limits as well as sell-side failures. The world
  property spans two realms and multiple items. Prompt 18's single-snapshot
  accounting and Prompt 20's shipment status rule remain intact.
- Added test_expiry_preserves_escrow_and_purge_only_old_closed,
  test_history_private_remote_and_durable_after_purge,
  test_lifecycle_races_collection_without_losing_escrow,
  test_postgres_lifecycle_advisory_exclusion,
  test_scheduled_lifecycle_callback_and_failure_logging,
  test_failed_expiry_rolls_back_the_whole_pass, and
  test_random_world_operations_conserve_goods_and_gold. Extended the existing
  scheduler cadence test to verify both registered jobs and shutdown.
- Mutation checks: temporarily withdrew one extra sell good during escrow;
  the world property failed its per-item total by 1,000 milli-items. Temporarily
  withdrew one extra buy gold; it failed its endpoint gold invariant by one.
  Both mutations were restored immediately. No mutation remains in runtime code.

- Validation: PATH=$PWD/.venv/bin:$PATH make ci passes on SQLite: auth 15,
  game 612 with 20 database-specific skips, client 76. Ruff formatting/lint,
  strict mypy, TypeScript, ESLint, Vitest, production build, scripts and content
  lint pass. The strengthened failed-trade atomicity cases also pass separately.
  A disposable two-service SQLite db-reset, subsequent game upgrade to head
  and alembic check succeed with no schema drift. git diff --check is clean.

## Removed

None. No existing tests or gameplay behavior removed.

## Design ambiguities resolved

- §17.2 / §23.2: the retention duration and exact few-minute interval are
  unspecified. Added market.retention_days (30) and
  market.lifecycle_interval_seconds (300), authored in the placeholder economy
  pack. Existing market.order_days remains 14. Retention uses closed_at and
  a strict less-than cutoff; expiry includes expires_at equal to now.
- §17.3: history returns {matches: [...]} with the same execution fields as
  immediate fills, plus durable buyer/seller character ids. Newest first is
  convenient for the upcoming history UI; UUID breaks otherwise equal times.
- §23.1: lifecycle changes no character holdings or realm simulation state, so
  it takes sorted realm locks directly before order locks, without resolving
  characters or realms. The transaction advisory guard needs no manual unlock
  and releases automatically on commit, rollback or connection failure.
- §17.6: the goods oracle lives in tests, observing explicit tick payment
  results and calculating permitted production/spoilage/cap losses independently
  of final world totals. No persistent goods ledger or new runtime API is added.

## Deviations

None.

## Ratification needed

No new questions. Prompt 23's unresolved self-matching question remains with
its existing behavior unchanged; history includes those executions once.

## Hand-offs

- 25-client-global-market: consume GET /market/history/me's matches array;
  rows survive order purge and include buyer_character_id and
  seller_character_id for side presentation. The same fields now appear in
  immediate execution projections. Add the market retention/cadence fields to
  client content types alongside Prompt 23's pending tax/duration fields.
- 26-equipment / 27-consumables-hp: extend tests/world_accounting.py holders
  with equipped and belt/utility stacks and exercise their transfers/consumption
  in the world property when those models exist.
- 36-hardening: lifecycle retains coarse sorted realm serialization, matching
  Prompt 23's market strategy. Preserve its exclusion, order and transaction
  guarantees when narrowing locks; evaluate expiry/closed_at indexes if actual
  order volumes justify them. No per-character loop was introduced.

## New error codes

None. No dependencies added.
