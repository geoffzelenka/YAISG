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
  History is paginated by (matched_at, id), newest first. Both history and
  immediate fills return the caller's side and omit participant character ids.
  Both identities remain stored in market_matches.
- Reworked the world conservation suite after review round 1, then extended it
  after review round 2. Each of eight deterministic, deadline-free Hypothesis
  examples generates a permutation of 21 operations followed by 2-4 sampled
  operations, allowing adjacent repeats and further state-dependent orderings.
  Every generated intent must succeed; 409s fail the test. A test-local per-op
  counter excludes the mandatory prefix and preparation. Each example asserts
  positive coverage against an independently written specification set rather
  than deriving the requirements from the generator's OPERATIONS list. Requiring
  coverage in every example is stronger than requiring it across the whole run.
- Fresh disposable database state per example supplies two separately
  authenticated characters in two realms. All buy orders belong to one owner
  and sell orders to the other; fills are checked in the receiving owner's slot.
  The world suite does not depend on self-matching.
- Preparation uses real, checked game operations: build before larder/surrender,
  surrender before build/buy, finish active projects through contributions before
  another kickoff, and honor kickoff cooldowns. Seven synthetic project/tag
  definitions let eroded or completed attempts give way to another offered
  project, including up to four additional kickoff attempts in the sampled tail. Realm purchases select an actual above-reserve offer; caravan supply
  comes from the second character's real trades when replenishment is needed.
- The mandatory prefix now expires occupied buy and sell escrow and asserts the
  open-to-collectable transitions. It purges actual closed rows and asserts their
  removal while old collectable slots retain both goods and gold. Generated
  expiry/purge operations make the same assertions. These invoke the job at the
  authored order_days boundary and beyond order_days + retention_days, separately
  from the realm simulation clock. The original suite's lifecycle call did not
  reach expiry or retention; the previous claim that it exercised those flows
  was incorrect and is replaced by these state-changing checks.
- Gold compares /admin/economy sum(holders) minus sum(ledger) after every mutation,
  including preparation. Goods are counted per item in milli-units across
  inventories, sell escrow, slot fills, stores, larders and only in_transit cargo.
  Authorized production, recipe inputs/outputs, construction/project consumption,
  upkeep, mint bullion, spoilage and cap losses are counted separately. Road loss
  is independently calculated as sent - floor(sent * authored edge survival);
  the fixture authors zero road reductions and verifies every delivered amount.
  Mint creation, both nonzero burn ledger causes, and each goods source/loss
  category must actually occur.
- Picked up Prompt 17's additional hand-off: test_trade_errors_are_atomic checks
  holdings after exceptions and before rollback, including buy-side PRICE_MOVED
  and physical limits. Prompt 18's single-snapshot accounting and Prompt 20's
  in-transit-only holder rule remain intact.
- Tests added in this phase: test_expiry_preserves_escrow_and_purge_only_old_closed,
  test_history_private_remote_and_durable_after_purge,
  test_lifecycle_races_collection_without_losing_escrow,
  test_postgres_lifecycle_advisory_exclusion,
  test_scheduled_lifecycle_callback_and_failure_logging,
  test_failed_expiry_rolls_back_the_whole_pass, and
  test_random_world_operations_conserve_goods_and_gold. The scheduler cadence
  test verifies both jobs and shutdown. All database fixtures honor TEST_DATABASE_URL.
- Review round 1 adds
  test_lifecycle_races_cancellation_without_duplicate_refund,
  test_history_cursor_pagination_ties_limits_and_validation, and
  test_immediate_fills_return_caller_side_without_counterparty_identity.
  The collection race now uses a partial fill with price-improvement gold, so
  either serialization moves both goods and gold. The cancellation race retains
  prior sale proceeds and refunds a sell remainder only once. History tests
  cover participant filtering after purge, both sides, self-match deduplication,
  timestamp ties, default/max limits, invalid cursors and bounds, and an execution
  inserted between pages without shifting the remaining results.
- Review round 1 mutation checks: clearing expired sell goods fails the world
  goods invariant; clearing expired buy gold fails its gold invariant; purging
  collectable rows alongside old closed rows fails its gold invariant. All three
  mutations were restored. Earlier extra-withdrawal mutations also failed the
  world goods and gold assertions. No mutation remains in runtime code.
- Review round 1 focused world suite: 8 examples, 168 generated successes, 8 for
  each operation (buy, sell, gift, kickoff, contribute, larder, build, estate_buy,
  surrender, caravan, arrive, order_trade, open_buy, open_sell, collect, cancel,
  tick, expiry, purge, action, transform). The focused SQLite run took 13.32s.

- Review round 1 validation: PATH=$PWD/.venv/bin:$PATH make ci passes on SQLite:
  auth 15, game 615 with 20 database-specific skips, client 76. Formatting,
  lint, strict typing, client build, scripts and content lint pass. The world
  property retains ordinary Hypothesis generation and shrinking settings,
  deadline=None, and deterministic inputs; no scratch mutation profile remains.

- Review round 2: removed the file-writing success_tally fixture. The property
  keeps its own success counter and writes no tally artifact. A scratch mutation
  removed gift only from the generator, leaving the mandatory prefix's gift
  intact: the independent coverage assertion failed with missing {'gift'}.
  The generator was restored. The permutation plus sampled-tail property passed
  on SQLite in 14.47s total (13.40s test call), within the requested roughly
  19.5s budget. PATH=$PWD/.venv/bin:$PATH make ci passes: auth 15, game 615
  with 20 database-specific skips, client 76; formatting, lint, strict typing,
  production build, scripts and content lint pass.

## Removed

- Removed participant character ids from history and immediate-fill projections;
  durable stored identities remain. Replaced the ineffective random tail and
  lifecycle no-op in the world property. Removed the shared temporary tally file
  write and its fixture in review round 2. No existing test behavior was weakened.

## Design ambiguities resolved

- §17.2 / §23.2: retention duration and exact few-minute interval are unspecified.
  Added market.retention_days (30) and market.lifecycle_interval_seconds (300),
  authored in the placeholder economy pack. Existing market.order_days remains
  14. Retention uses closed_at and a strict less-than cutoff; expiry includes
  expires_at equal to now.
- §17.3: history returns {matches: [...], next_cursor: string | null}, with limit
  default 50, minimum 1 and maximum 200. before is an opaque URL-safe base64
  encoding of the UTC matched_at and match UUID. The tuple boundary is exclusive
  in descending order, so equal timestamps and new executions between requests
  cannot shift existing pages. A terminal page has next_cursor null. Invalid
  cursors return INVALID_CURSOR; invalid limit/length bounds use INVALID_REQUEST.
- §17.3: disclose buy/sell side instead of counterparties' character identities,
  for history and immediate fills. The database retains both identities for
  filtering and retention durability. A still-allowed self-match appears once
  in history with side buy; immediate fills use the submitting order's side.
- §23.1: lifecycle changes no character holdings or realm simulation state, so
  it takes sorted realm locks directly before order locks without resolving
  characters or realms. The transaction advisory guard releases automatically
  on commit, rollback or connection failure.
- §17.6: the goods oracle lives in tests, observing explicit tick payment results
  and calculating permitted production/spoilage/cap losses independently of final
  world totals. No persistent goods ledger or new runtime API is added.

## Deviations

None.

## Ratification needed

No new questions. Prompt 23's unresolved self-matching question remains with
matching behavior unchanged. The world property now trades between two owners.

## Hand-offs

- 25-client-global-market: consume history's matches and next_cursor; pass the
  cursor back as before with an optional limit (1-200, default 50). Display the
  returned side for history and immediate fills; participant character ids are
  not exposed. Rows survive order purge. Add retention/cadence fields to client
  content types alongside Prompt 23's pending tax/duration fields.
- 26-equipment / 27-consumables-hp: extend tests/world_accounting.py holders
  with equipped and belt/utility stacks and tests/world_scenario.py operations
  with their transfers/consumption when those models exist. Extend the test's
  independent required-operation set alongside new generator operations.
- 36-hardening: lifecycle retains coarse sorted realm serialization, matching
  Prompt 23's strategy. Preserve exclusion, order and transaction guarantees
  when narrowing locks; evaluate expiry/closed_at and history tuple indexes if
  actual volumes justify them. No per-character runtime loop was introduced.

## New error codes

- INVALID_CURSOR (422): malformed market-history before cursor, including a
  timestamp without a timezone. Query bounds retain INVALID_REQUEST.
- No dependencies added.

## Orchestrator verification and review hand-offs

- Orchestrator on 56dc6f7: SQLite make ci green (auth 15, game 615 / 20
  skipped, client 76); PostgreSQL 16 game-ci 634 / 1 skipped; PG db-reset,
  alembic check and boot green. World suite ~14s SQLite / ~25s PG. Review:
  round 1 CHANGES_REQUESTED (lifecycle no-op and thin interleaving in the
  conservation suite), round 2 APPROVE (nits applied), round 3 APPROVE.
- 26-equipment / 27-consumables-hp: add equipment and belt holders to
  tests/world_scenario.py, extend the hand-written `required` op set and
  OPERATIONS together.
- maker_order_id / taker_order_id are still returned in fills and history;
  revisit if order ids are ever treated as private.
