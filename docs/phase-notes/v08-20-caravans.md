## Built

- Added cached directed all-pairs remoteness over level-one map edges, warmed at
  process boot. Routes retain edges for current active endpoint road reductions.
- Added strict economy.caravan settings and public client content types. The
  synthetic pack authors six-tick passes, 1 percent fee per hour, zero burn,
  time multiplier 2 and reference-value capacity 1000 per realm per pass.
- Added realm_shipments and migration v08_0011_caravans with nonnegative gold,
  bounded delivered quantities, valid statuses and a destination index. Sent
  minus arriving permanently records expected road losses.
- Scheduled passes claim the world cursor atomically with all dispatches. Shared
  realms lock in id order before the singleton. Missed passes are skipped. Buyer
  order is descending gauge then id; lines use descending reference draw then
  canonical key. Candidates compare exact delivered cost, distance, seller id
  and item id. Both sides share their remaining sent reference-value capacity.
- Reused whole-good market integrals and selector membership, including bullion
  value weights, reserve protection, treasury limits and buyer bid constraints.
  Fees transfer to the seller less floor-rounded burn, recorded negatively in
  the existing caravan_fee_burn gold ledger cause.
- Replaced the step-0 hook with preloaded due arrivals, credited once before
  production/upkeep. Current in-transit deliveries follow demand membership on
  recomputation and in tick context. Catch-up has one additional preload query,
  independent of tick count; existing exact statement budgets were extended by
  that one query. No per-tick queries were added.
- Added test_nothing_bought_twice_in_transit_and_arrivals,
  test_missed_passes_not_replayed,
  test_nearer_seller_and_never_cheaper_than_ask,
  test_loss_capacity_and_conservation (Hypothesis),
  test_remoteness_level_gates_direction_and_cheapest_path,
  test_gold_goods_conserved_and_fee_burn,
  test_two_postgres_schedulers_claim_one_pass,
  test_isolated_and_without_access_never_trade,
  test_equal_ask_nearer_seller_wins, and
  test_random_passes_conserve_goods_and_gold (Hypothesis),
  test_multiedge_loss_and_capped_adjoining_road_tags, and
  test_arrival_on_first_due_tick.

- Pre-review fix 1: the shared realm fixture configures SQLite listeners even
  for PostgreSQL. The old begin listener had no dialect guard; the caravan
  service's unconditional write-intent option changed its otherwise accepted
  BEGIN into PostgreSQL-invalid BEGIN IMMEDIATE. Configuration now ignores
  non-SQLite engines, the begin listener independently checks its connection
  dialect. These guards remain unchanged in review round 1. Fixtures
  remain unchanged so they continue exercising this production boundary.
- Added test_transaction_configuration_on_selected_database (ordinary and
  write-intent transactions, honoring TEST_DATABASE_URL) and
  test_non_sqlite_dialect_never_emits_sqlite_begin (guard checked before and
  after listener setup without needing a PostgreSQL server). Both local guard
  cases failed on BEGIN IMMEDIATE before the fix and pass after it. Focused
  database/caravan/scheduler tests pass: 34 passed, two dialect-specific skips.

- Review round 1: an unlocked cursor check skips passes that are not due;
  due passes take sorted realm locks (including isolated map endpoints), then
  the world lock and re-check the cursor with refreshed ORM state. Each locked
  realm is resolved with the standard lazy resolver before selection, including
  retrying a realm whose earlier scheduled attempt failed. The initial cursor
  read uses an ordinary transaction; no SQLite writer intent is taken for a
  pass that is not due. The PostgreSQL/SQLite database guards are unchanged.
- Road reductions now use all actual map endpoint realm ids, including isolated
  endpoints; isolated realms remain excluded from buyers and sellers. Published
  realm_holders replaces the private helper import. Scheduled-pass and test
  imports moved to module scope; boot warms the cached property directly.
- Candidate search additionally bounds q by
  ceil((floor(need / (weight * 1000)) + 1) / retained) - 1, preserving the strict
  upper boundary implied by floor(q * retained). A property compares every
  selected result against an exhaustive physical-range reference search.
- Added test_scheduled_job_dispatches_due_pass_once,
  test_hungriest_buyer_gets_shared_seller_capacity,
  test_largest_reference_draw_gets_single_capacity_allowance,
  test_draw_value_uses_actual_members_and_empty_default,
  test_pass_resolves_stale_seller_before_selection (direct and failed scheduler),
  test_pass_not_due_only_reads_cursor,
  test_isolated_route_endpoint_tags_reduce_loss (with/without roads),
  test_delivery_clamp_preserves_largest_feasible_candidate (Hypothesis), and
  test_remoteness_prefers_cheaper_two_hop_path. Database fixtures honor
  TEST_DATABASE_URL, so scheduled integration covers PostgreSQL advisory locks.
- Strengthened test_equal_ask_nearer_seller_wins with a far seller id sorting
  before the nearer seller and an exact candidate unit-cost tie. Removing the
  hours key fails that test. Reversing buyer order or line order independently
  fails the respective new contention test. Removed the loss tautology and
  assert delivery against the tagged floor formula. Selection fixtures start
  from current realm snapshots; the in-transit test now uses a journey longer
  than the next pass so it tests duplicate buying separately from consumption.
- Existing exact catch-up statement assertions are unchanged: freshness resolves
  are outside the catch-up loop, with no new tick queries or altered budgets.

- Validation: SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passes (auth 15,
  game 572 with 18 database-specific skips, client 41). Lint, formatting,
  strict typing, client build, scripts and content lint pass. A disposable
  SQLite make db-reset, subsequent upgrade to head, alembic check and world
  creation passed during initial implementation; this round changes no schema.

## Removed

- Replaced the arrival stub. No routes, content fields or tests removed.

## Design ambiguities resolved

- §16.3: capacity uses reference value of sent goods on both realms, and each
  realm shares one allowance across buying and selling. This accounts for all
  cargo handled, including expected road loss.
- §16.3: whole-unit candidates delivering zero are ineligible because delivered
  unit cost is undefined. Equal cost and remoteness use seller id then item id
  for deterministic otherwise unspecified ties. Equal line draw uses line key.
- §16.3: pass boundaries are anchored at seeded_at; advance the cursor directly
  to the latest boundary and dispatch at the supplied current time, never backdate
  shipments or replay missed boundaries.
- §16.3: unspecified friction/capacity numbers are synthetic content settings,
  not balance decisions. Fee burn floors the destroyed share, crediting the
  remainder to the seller so no fractional gold appears.
- §16.3: search quantities downward rather than bisecting feasibility: integer
  delivery and fee rounding can make the buyer-integral constraint nonmonotonic.
  Authored capacity bounds this straightforward exact search.
- §16.3: ordinary selector-line draw value uses the minimum reference price of
  items actually assigned to the line after specificity rules. A line with no
  assigned items has value zero; value-measured draw already is reference value
  and keeps weight one. This is independent of content item ordering and avoids
  StopIteration on empty membership.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 21-client-realm-estate / 22-client-realm-market: existing public in_transit
  fields now contain arriving milli-line-units, including weighted bullion.
  Arrival occurs on realm ticks; it is not an immediate store credit.
- 24-market-lifecycle: world conservation must count only in_transit shipments
  as holdings; arrived rows remain audit history. quantity_sent minus
  quantity_arriving records road loss separately from spoilage/cap losses.
- 36-hardening: add shipment/loss counters around dispatch. The pass currently
  locks all shared realms for a consistent selection snapshot; narrow this only
  while preserving global ordering and atomic capacity/selection guarantees.
- Content authoring: existing fake world tags do not grant caravan access;
  author roads through access tags/projects when building actual content. Tests
  inject road access without changing unrelated placeholder world balance.

## New error codes

None. No new dependencies.
