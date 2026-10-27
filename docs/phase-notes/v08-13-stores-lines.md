## Built

- Added migration v08_0008_stores, RealmStore holdings in milli-units,
  materialized RealmLine demand, and the singleton WorldState seed marker.
  Existing migration tests cover schema parity, downgrade and fresh rebuild.
- Pure engine/stores.py supplies due(d, n, T), selector grouping, most-specific
  membership, ordinary/value-measured weights, reserve/cap derivation and the
  no-line warehouse cap. Derivation uses decimal-to-Fraction conversion and
  deterministic selector ordering, with no database, clock or global state.
- Demand sums node and active tag upkeep, every estate's full form upkeep,
  and the funding attempt's remaining snapshot requirements divided by the
  project's realm_completion_days. Larder balances never reduce draw. The mint
  provider is empty; in_transit and budget_gold are zero.
- Added one recompute_lines adapter plus replace_lines for persisting a pure
  derivation. Realm detail/list reads recompute under their existing realm locks
  and expose lines with below_reserve flags, without treasury or bid budgets.
- Boot rejects ordinary upkeep class selectors with mixed reference prices,
  invalid seed references, duplicate seed goods/realms, missing world realms,
  isolated seed templates, and cap settings that cannot cover maximum reserve.
  Warning-only upkeep overlap lint is included in content-lint text output.
- Private strict world_seed participates in the overall version hash but is not
  served. create_world claims its singleton with a conflict-safe insert and
  creates all world realms, treasuries, stores and null-owner estates in one
  transaction. Boot, make world-create, character creation and virgin-realm
  first touch share this path. Isolated templates never create shared state.
- Extended public client content types and fixtures for economy settings and
  item warehouse caps. Existing character/action/estate fixtures explicitly seed
  an empty world to keep their test holdings independent of the placeholder
  seed. Their behavioral assertions remain; the first-character race counts
  its selected realm rather than assuming the world contains only one realm.
- Added test_due_sums_to_daily_rate (Hypothesis),
  test_due_rejects_invalid_inputs,
  test_line_grouping_specificity_and_value_units,
  test_reserve_delta_transition_node_override_and_no_line_cap,
  test_validator_rejects_mixed_price_upkeep_class,
  test_upkeep_overlap_warning, test_world_creation_twice_creates_once,
  test_funding_overlay_uses_run_snapshot_and_full_estate_upkeep,
  test_postgres_concurrent_world_creation_once,
  test_world_seed_validation, test_world_seed_is_private_but_versioned,
  test_cap_validation_includes_transition_and_tag_delta,
  test_pending_reserve_uses_full_recorded_transition,
  test_world_creation_rollback_allows_retry,
  test_realm_lines_below_reserve_and_private_seed and test_boot_seeds_world_once.
  Database fixtures honor TEST_DATABASE_URL; the PostgreSQL contention test
  checks a real blocking relationship and skips on SQLite.

- Validation: PATH=$PWD/.venv/bin:$PATH make ci passes on SQLite: auth 15,
  game 358 with nine database-specific skips, client 41. Formatting, Ruff,
  strict mypy, TypeScript, eslint, Vitest, build, scripts and warning-only
  content lint pass. A disposable make db-reset, subsequent alembic upgrade
  head, make world-create twice and alembic check all succeed. git diff --check
  is clean. No dependencies added.

## Removed

- Separate first-touch zero-treasury realm inserts in character creation and
  the realm-lock adapter, replaced by shared world creation. No tests removed.
- The placeholder workshop's mixed-price fake_plant upkeep selector is narrowed
  to item.fake_sprig. Its build payment still accepts the original class.

## Design ambiguities resolved

- §14.1–14.4: stored and public demand amounts use integer milli-line-units.
  Daily fractional contributions are summed exactly per selector, then floored
  once to milli precision; reserve and cap multiply that daily draw and floor
  once. This preserves integer arithmetic and matches the stores representation.
- §14.2: equally specific overlapping class selectors break ties by canonical
  selector JSON key. The specified item/tiered-class/class precedence wins first;
  stock is assigned to exactly one line. Overlap is a lint warning, not rejection.
- §14.3: schema defaults remain reserve_days 3 and cap_days 10; the fake economy
  authors cap_days 11 so it exceeds 3 + 7 transition days. Cap validation uses a
  conservative bound: positive deltas from the node's inherent, offered-project
  and carried tags, including the full transition duration. Pending reserves use the recorded
  started_at/completes_at window, so a later content edit cannot shrink it.
- §14.3: warehouse_value_cap has no prescribed numeric default; the fake pack
  authors 10000. Item warehouse_cap is an optional whole-unit override.
- §14.9 / §21: seed stores use the existing positive whole-unit ItemQuantity
  schema and are multiplied by 1000 at creation. Estate lists may repeat forms
  because they describe distinct estates. last_caravan_pass starts at seeded_at.
- §14.9: if pre-release state already has realm rows but no world marker, seed
  treasuries are installed on those rows; normal fresh-world creation starts
  empty. Retries after a committed marker never restore any holdings.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 14-realm-tick: integrate derive_lines with preloaded RealmTickContext and
  persist through replace_lines once after catch-up; do not call the querying
  recompute_lines adapter inside a per-tick loop. Add stores/estate/tag inputs
  to the batched context and preserve 10a's bounded-query test. due accepts a
  daily milli-rate and a nonnegative absolute tick index. Funding overlay uses
  run.required snapshots and run.contributed, never current project.cost.
- 14-realm-tick / 15-decay: tick consumption, spoilage, cap loss and decay are
  deliberately absent. warehouse_cap returns milli-units for unmatched goods
  with zero reserve. The fake seed is scaffolding; exercise and tune it when
  seed-check becomes executable in 15, including estate production/upkeep.
- 16-realm-pricing: populate budget_gold and pricing/visibility fields. Current
  recomputation writes budget_gold zero; integrate allocation without resetting
  spent budgets on reads. Public lines currently omit budget_gold.
- 17-realm-trade / 20-caravans: update derived lines under held realm locks when
  stores move; trades remain whole units. Replace zero in_transit in 20 and
  use world_state.last_caravan_pass as the one-time pass cursor.
- 18-mint-gold: implement mint_demands from active mint tags with value-measured
  units and record seed treasury creation in the gold ledger inside create_world.
- 21-client-realm-estate / 22-client-realm-market: public realm lines expose
  selector, value_measured, draw_per_day, reserve, cap, stock, in_transit and
  below_reserve. All quantities are milli-line-units; no raw treasury is exposed.
- 34-tutorial: isolated templates are excluded from seeds and rejected as normal
  character starting realms with UNKNOWN_REALM. Create owned instances through
  the tutorial lifecycle; never initialize a shared isolated template row.

## New error codes

None. Reused UNKNOWN_REALM for isolated template selection; invalid content
raises ContentError and invalid pure inputs raise ValueError. No dependencies
added.
