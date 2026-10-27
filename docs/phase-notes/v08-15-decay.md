## Built

- Files changed: `Makefile`, `content/economy.json`, `content/estate_forms.json`,
  `docs/v08/progress.md`, `docs/phase-notes/v08-15-decay.md`;
  `services/game/app/api/estates.py`, `services/game/app/api/realms.py`,
  `services/game/app/content/schemas.py`, `services/game/app/engine/core.py`,
  `services/game/app/engine/decay.py`, `services/game/app/engine/tags.py`,
  `services/game/app/services/actions.py`, `services/game/app/services/realm_ticks.py`,
  `services/game/app/services/realms.py`, `services/game/app/services/stores.py`,
  `services/game/app/services/seed_check.py`;
  `services/game/tests/test_actions.py`, `services/game/tests/test_decay.py`,
  `services/game/tests/test_estates.py`, `services/game/tests/test_projects.py`,
  `services/game/tests/test_realms.py`.
- Filled tick steps 8–9 with reference-value-weighted realm and estate gauges,
  content-owned thresholds, recovery, bounded hunger, live stages, current-node
  tag shedding, regression transitions and estate upgrade/form loss. Realm hunger
  excludes estate upkeep. Isolated realms and estates without tick profiles keep
  their existing exemptions. Fed and Strained have identical mechanics.
- Added pure `engine/decay.py` arithmetic and strict `economy.gauge` / `economy.shed`
  settings, wiring live stages into bonus/tag consumers. Shared pure economy_tags
  serves both materialized lines and tick contexts.
- Preload upgrades, owners and ownership intervals once. Tick steps issue no
  queries or flushes; final persistence batches losses and replacement creation.
  Extended the statement-count regression from 9/11 to 12/14 statements for
  nonpaying/paying worlds, equally for two ticks and maximum catch-up.
- Destroyed estates retain unowned, inactive tombstones for ownership history.
  History intervals close, and a player receives a new
  basic mobile estate with a new acquisition interval in their current realm.
  The next locked character resolve follows the replacement link before loading
  gameplay state. Realm ticks never update or lock character rows after realms.
- Character serialization uses PostgreSQL FOR NO KEY UPDATE: concurrent character
  mutations remain exclusive, while replacement estate/history foreign-key checks
  can take KEY SHARE without deadlocking an owner waiting for the realm lock.
- Catch-up completes newly scheduled build/transition events at exact timestamps,
  sorting by due time and completing builds first on ties. Regression restamps
  survivors only at completion and clears gauges/progress. Lost tags and credits
  remain separate: completed runs and contributions are retained.
- Exposed gauge days on map nodes and estate responses/lists; realm detail already
  carries the gauge. Strained remains visible to owners and on public lists.
- Added `make seed-check`, simulating thirty days on in-memory SQLite created
  with metadata.create_all, tracking even transient Faltering and printing private
  operator holdings. It never touches the configured DB. A failing check stops at
  the first Faltering; healthy checks still simulate all thirty days. Tests use
  daily cadence for the same thirty-day scenario; check_seed also accepts days. Fake workshop production is now
  two sprigs/day against its one-sprig upkeep, keeping the placeholder seed healthy.
  Both realms finish with gauge 0, treasury 1000 and 11000 milli-sprigs.
- Added tests in `tests/test_decay.py`:
  `test_strained_has_no_engine_effect`, `test_strained_has_no_realm_tick_effect`,
  `test_stage_boundaries`, `test_recovery_cancels_hunger_day_for_day`,
  `test_reference_weighting_and_estate_independence`,
  `test_shed_order_rate_transition_pause_and_recovery`,
  `test_d4_upgrade_survivors_regress_and_restamp`,
  `test_estate_chain_and_replacement_retains_history`,
  `test_live_faltering_production_and_strained_equality`,
  `test_seed_check_healthy_and_starving_fixture`,
  `test_decay_catchup_matches_split_and_is_idempotent`,
  `test_no_tick_profile_and_isolation_exemptions`,
  `test_barren_root_remains_failing`,
  `test_postgres_decay_and_owner_resolve_do_not_deadlock`,
  `test_seed_check_cli_exit_and_report`,
  `test_fractional_ticks_do_not_cross_stage_boundaries_early`, and
  `test_catchup_build_precedes_transition_and_keeps_credits`, and
  `test_faltering_weakens_numeric_economy_tag_effects`.
  Added `test_decay_gauge_visible_on_map_realm_and_estates` and
  `test_destroyed_estate_is_hidden_and_cannot_be_bought` in `test_estates.py`.
  Recovery and split/idempotence coverage use Hypothesis. The PostgreSQL-only
  contention test uses independent sessions, bounded waits and pg_blocking_pids
  to prove the owner is waiting on the realm before decay creates a replacement.

- Validation: `PATH=$PWD/.venv/bin:$PATH make ci` passes on SQLite: auth 15,
  game 413 passed / 11 skipped, client 41. Ruff lint/format, strict mypy,
  TypeScript, eslint, prettier, Vitest, production build, scripts checks and
  content lint are green. Migration/reset tests rebuild both services. The
  placeholder `make seed-check` passes and `git diff --check` is clean.


- Round 1: capped empty-node shed progress at one; strengthened both regression
  restamping paths and larder-loss assertions; retained mobile-estate tombstones
  and ownership history on build/buy. Cached reference weights by demand-line key,
  added `test_gauge_weights_are_cached_until_line_membership_changes`, and extended
  the statement bound to decaying estates (15/17 statements versus baseline 12/14,
  equally at two and maximum catch-up ticks). Seed-check now stops on first
  Faltering and its thirty-day daily-cadence regression test takes 0.37 seconds.
  Mutations removing the clamp, either restamp, or larder loss all fail their
  corresponding assertions. SQLite `make ci` passes: auth 15, game 419 passed /
  11 skipped, client 41; all lint, formatting, typing and builds pass. The default
  thirty-day hourly `make seed-check` also passes. No dependencies added.

## Removed

- Replaced the gauge/decay stubs and production-factor hook. No tests deleted.
  Updated existing API expectations for gauge visibility and Faltering estate
  bonus scaling. The transition-only boundary test now sets last_tick_at at its
  boundary so it continues testing transition preservation without fed recovery.

## Design ambiguities resolved

- §14.6: the interval from zero through the Strained threshold is Fed. Thresholds
  use strict greater-than comparisons. Gauge boundaries and integral shed progress
  are snapped within 1e-12 to avoid floating-point accumulation triggering a stage
  early or delaying a loss at hourly cadence; this is numerical error handling.
- §14.7 / §13.7: an empty current-node stack or empty upgrade list advances to
  regression immediately while Failing; the shed rate gates asset removals, not
  an extra wait after the last loss. A barren root remains Failing. Progress can
  drain during a pending transition when the realm is rescued; hunger continues.
- §14.7: the design specifies a default base of one tag per two days but does not
  give numeric acceleration/recovery defaults. Authored placeholder settings use
  base 0.5/day, acceleration 0.5 per gauge-day/day and recovery 1/day.
- §13.1 / §13.7 / §23.1: retain destroyed estate rows as history tombstones rather
  than cascading history away. home_estate_id is repaired lazily under the owner
  lock, following the tombstone replacement link. Ownership of the replacement
  transfers immediately in the decay transaction; all gameplay reads resolve
  the pointer before use. This preserves character-before-realm locking without
  locking every resident character for scheduled realm work.
- §23.1: FOR NO KEY UPDATE supplies the required character serialization without
  excluding foreign-key reads. No character key is changed by ordinary gameplay.

- §14.7: when a Failing node has no current-node tag to shed, retain at most
  one pending loss (shed_progress ≤ 1). Banking unbounded loss at an empty node
  would bypass the slow shed rate when tags are rebuilt or a node is upgraded.
  Rescue drains this bounded remainder at the ordinary recovery rate.
- §13.7 / §13.6: destroying an estate also destroys its remaining larder goods.
  The larder is prepaid upkeep, not refundable inventory; destruction is an
  explicit decay loss rather than a transfer back to the owner or realm stores.
- §13.1 / §13.4: the same unowned tombstone policy applies when build/buy retires
  a mobile estate. Close its open ownership interval, retain all history, and
  discard installed upgrades and larder goods; the new estate has its own interval.
- §14.6 / §13.7: numeric reserve_days_delta and edge_loss_reduction_pct effects
  of bonus/malus tags scale by faltering_factor like their numeric modifiers.
  Access effects and maintenance costs retain their authored values. Numeric tag
  cap bonuses and direct estate cap bonuses also scale. For integer-valued caps,
  add all scaled bonuses to the base and floor the final nonnegative total once
  (int); do not floor individual bonuses. offline_hours retains fractional hours.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 16-realm-pricing: extend seed-check with the funded tier-one bid clause and
  step 10 with market budgets. `SeedReport` includes operator holdings only;
  public realm/map/estate responses still exclude raw treasury balances.
- 18-mint-gold: supply value-measured due/unmet amounts for bullion. Step 8 uses
  weight 1 for value-measured lines and item reference value for ordinary lines.
- 21-client-realm-estate / 22-client-realm-market: render live decay_stage and
  gauge days from map, realm, estate detail and estate lists; Strained stays
  cosmetic. No new client UI is introduced in this server prompt.
- 31-keys: transition start/finalization hooks must cover both the existing
  session-backed path and in-context complete_tick_transition for events created
  during catch-up. Keep build-before-transition ordering on simultaneous events.
- 36-hardening: operator purge/inspection must distinguish destroyed history
  tombstones from active estates and retain replacement links until the owning
  character's home pointer has been resolved. No per-character job is necessary.

## New error codes

None. No dependencies added.
