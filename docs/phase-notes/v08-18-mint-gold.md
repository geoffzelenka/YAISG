## Built

- Validated equivalence of item.bullion and the bullion class. Added the global
  economy.coinage_multiple setting (default and placeholder value 1.2), a fake
  bullion drop on an existing gathering action, an access mint tag and project,
  and an existing node offering that action and project.
- The largest active mint supplies one value-measured bullion line. Both read
  recomputation and tick derivation include its draw, reserves, cap, market
  funding and treasury coverage. Reads retain spent budgets. Weighted cap loss
  now uses reference value for bullion while ordinary lines retain item units.
- Step 4 consumes bullion below reserve in reference-price / item-id order,
  coins floor(consumed reference value * multiple) to the treasury, and records
  the same signed amount in gold_ledger. Bullion due and unmet reference value
  feed the ordinary gauge. Access mint tags remain active while Faltering.
- Added GoldLedger and migration v08_0009_gold. The six specified causes have
  database checks for cause and creation/destruction sign. World seeding records
  each treasury in its existing atomic, conflict-safe creation transaction.
  Catch-up accumulates entries in memory and inserts them in one batch after
  ticks; tick steps issue no queries. Existing seed concurrency coverage now
  also verifies exactly one set of ledger entries.
- Widened currency.gold to BIGINT, matching treasury and ledger amounts; added
  a 2**40 wallet round-trip regression. The migration supports downgrade and
  fresh reset through the existing schema-parity/reset tests.
- Added GET /admin/economy, gated by the configuration allowlist
  GAME_OPERATOR_AUTH_USER_IDS (comma-separated auth user UUIDs, empty by
  default). A single SQL statement reports wallet/treasury holdings and signed
  ledger totals from one snapshot. README documents the setting. Client content
  types and fixtures include coinage_multiple; no new client UI was added.
- Extended api_error with extra payload fields and routed UNFUNDED_DEMAND
  through it, preserving error.max_quantity. Updated the existing synthetic
  weighted trade test for mint_demands' active-tag argument without weakening it.
- Added test_bullion_flag_matches_class,
  test_largest_mint_line_caps_gauge_and_faltering,
  test_coinage_per_tick_and_day,
  test_scarce_bullion_drains_treasury_until_mint_stops,
  test_seed_ledger_once_and_atomic_rollback,
  test_admin_economy_operator_only,
  test_random_gold_operations_match_ledger (deterministic Hypothesis sequences
  exercising real build, transform, buy/surrender, kickoff, trade, gift and mint
  operations), test_mint_catchup_batches_ledger_and_is_idempotent,
  test_postgres_concurrent_mint_resolves_once,
  test_coinage_fractional_bullion_and_value_remainder, and
  test_wallet_retains_64_bit_gold. Database fixtures honor TEST_DATABASE_URL;
  the PostgreSQL-only contention test skips on SQLite.

- Validation: repository-virtualenv `make ci` passes on SQLite: auth 15, game
  470 passed / 14 database-specific skips, client 41. Formatting, lint, strict
  typing, migration/reset/schema checks, client build and content lint pass.
  `git diff --check` is clean. No dependencies added.

## Removed

- Empty mint-demand stub and the inline UNFUNDED_DEMAND envelope. No tests,
  routes or content fields were removed.

## Design ambiguities resolved

- §14.1 / §14.8: bullion consumption uses existing item milli-units. A remaining
  value allowance smaller than one milli-unit of a matching good stays unmet;
  consumption never exceeds the tick allowance. Coinage floors each tick, as
  specified, without carrying sub-gold fractions into subsequent ticks. Exact
  rational arithmetic interprets authored decimal multipliers without binary
  float rounding. Cap loss rounds item milli-units upward only as necessary to
  leave reference-value stock at or below cap.
- §18 / §21: ledger amounts are signed gold deltas; creation is nonnegative and
  destruction nonpositive. Holder identifiers are nullable durable references,
  without cascading foreign keys, so later tutorial deletion cannot erase its
  audit trail. Zero-valued world seeds still receive an entry; zero coinage
  does not create redundant entries.
- §18: the report includes currently implemented holder types (wallets and
  treasuries), including isolated holders. It reports persisted holdings without
  triggering gameplay ticks. One unioned aggregate query gives consistent
  holder and ledger totals under PostgreSQL READ COMMITTED.
- §18 / Prompt 12 hand-off: player wallets use 64-bit integers because transfers
  from a 64-bit treasury must not fail at the former 32-bit wallet boundary.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 20-caravans / 23-global-market: add negative caravan_fee_burn / tax_burn
  entries in the same transaction as their actual burns. Transfers alone need
  no ledger entry. Both burn shares remain outside this prompt.
- 23-global-market / 24-market-lifecycle: extend /admin/economy holder totals
  with escrow and gold held in slots when those tables exist. Preserve its
  single-snapshot accounting and extend the gold conservation property.
- 34-tutorial: write tutorial_seed / tutorial_destroy signed entries atomically
  with grants and all gold removed during isolated-instance deletion. Retain
  ledger records after deleting their referenced ephemeral holders.
- 36-hardening: use mint ledger deltas for minted-gold counters; no metrics
  dependency was introduced here.

## New error codes

- OPERATOR_REQUIRED (403): the authenticated auth user is not in the operator
  allowlist. Existing authentication and validation envelopes are unchanged.
