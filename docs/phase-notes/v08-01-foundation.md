## Built

- Replaced game Alembic history with `v08_0000_baseline`, creating the current
  schema with BIGINT skill XP on both SQL dialects. Fixed the game revision
  template to emit generated operations (it previously emitted empty bodies).
- Added `make db-reset` and `scripts/db_reset.py`: delete SQLite database and
  sidecars, or drop/recreate configured PostgreSQL databases, then upgrade game
  and auth to head. Auth keeps its independent history. Documented disposable
  development-data policy and invocation in codebase-map.md.
- Added Decimal (100-digit precision) amplitude bisection generator
  `scripts/gen_xp_curve.py`; the search stops only at an exact floored total of
  10,000,000. Checked in 99 integer costs matching every §5.1 reference point.
- Boot validates integer costs, count, strict increase, positive first cost and
  exact total. XP remains private and hashed. Cumulative sums expose levels
  1–100 to the existing engine; XP continues accumulating without new levels.
- Added public strict/extra-forbidden progression pack with thresholds and
  obviously fake titles; pure tier_for_level; profile tier/tier_title and null
  xp_to_next at 100. Updated client content loading/types/cache fixtures and
  maximum-level rendering for the nullable API value.
- New characters receive zero gold. Existing relocation tests explicitly seed
  funds, preserving their charge/rollback assertions. Existing offline-cap and
  reward-claim behavior/tests remain intact.
- Added tests: test_design_curve_reference_points_and_halfway,
  test_every_boundary_and_uncapped_xp, test_tier_boundaries,
  test_generator_reproduces_checked_in_curve,
  test_boot_rejects_invalid_xp_table (3 cases),
  test_boot_rejects_invalid_tier_thresholds (4 cases),
  test_profile_max_level_retains_64_bit_xp,
  test_v08_baseline_upgrade_check_and_downgrade (honors TEST_DATABASE_URL,
  checks schema parity and a 2**40 XP round trip), and
  test_db_reset_rebuilds_both_services (SQLite repeat reset and head upgrade).
- Manually ran make db-reset against disposable SQLite game/auth files; both
  upgraded successfully. Generator/reset scripts pass Ruff and mypy.

- Final `PATH=$PWD/.venv/bin:$PATH make ci` passed on SQLite: auth 15,
  game 112 passed / 1 PostgreSQL-only skip, client 22. Ruff, formatting, strict
  mypy, eslint, prettier, TypeScript, Vitest and production build all green.
  Scripts also pass separate Ruff formatting/lint and strict mypy checks.
  `git diff --check` is clean.

- Round 1 B1/N1–N8: cache immutable cumulative XP thresholds during validation;
  freeze the XP RootModel; isolate XP and tier invariant tests with specific
  error matches; rename baseline file without changing its revision; reject
  shared game/auth reset targets before mutation; include scripts in CI using
  game tool configuration; add the maximum-level UI test; refresh migration
  map and orchestrator verification records.
- Round 1 tests added: test_xp_thresholds_are_cached_and_curve_is_frozen,
  test_db_reset_refuses_shared_database (SQLite path and PostgreSQL identity,
  neither case requires a PostgreSQL connection), and Vitest
  "shows Maximum level when XP to next is null".

- Round 1 final SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passed: auth 15,
  game 115 passed / 1 PostgreSQL-only skip, client 23. All formatting, lint,
  type checks and build passed, including scripts-ci using game configuration.
  Round 1 PostgreSQL execution remains for the orchestrator.

## Removed

- Six historical game migrations, replaced by the new baseline; auth unchanged.
- Old cumulative exponential generator and table representation; replaced old
  curve assertions with exact v0.8 assertions, retaining monotonicity coverage.
- test_v05_backfills_phase3_data_and_downgrades: legacy backfills are explicitly
  retired by destructive baseline reset; replaced with fresh-baseline tests.
- Starting-gold constant/environment setting and README entry; level-99 cap.

## Design ambiguities resolved

- §5.1: preserve the existing engine's cumulative XpLevel interface by summing
  the 99 checked-in costs into 100 thresholds, including zero. Summing costs
  is table reading, not recomputing the exponential formula at boot.
- §5.3: tier titles are an ordered array parallel to thresholds; this is the
  minimal schema needed for this prompt. Unknown fields are forbidden and
  thresholds reject coercion, while JSON arrays load as immutable tuples.
- §18 / preflight economy-pack audit row: zero gold needs no tunable economy
  setting, so no unused economy pack was created. Its first consumer owns it.

## Deviations

- PostgreSQL cannot be reached from this coding sandbox. Orchestrator verification
  on committed baseline a79d26a: PostgreSQL 16 make game-ci passed 113 tests;
  make db-reset passed twice on dedicated yaisg_game_dev/yaisg_auth_dev databases,
  game revision is v08_0000_baseline (head), and alembic check found no drift.
  SQLite db-reset also passed and app GET /content/manifest returned 200.
  Round 1 changes still need orchestrator PostgreSQL verification.

## Ratification needed

None.

## Hand-offs

- 02-content-model: extend progression only as required; action/item tiers
  remain intentionally absent. Action level gates now permit level 100.
- 03-bonus-model / 04-content-lint: progression exists for proficiency/taper
  and rate settings; tier titles are placeholder content, not balance.
- 08-client-skills-travel: tier fields are available in profile API/types;
  full skill/tier UI remains yours. Existing UI supports null at maximum level.
- Orchestrator: run PostgreSQL 16 make ci with TEST_DATABASE_URL. For db-reset,
  set separate GAME_DATABASE_URL and AUTH_DATABASE_URL disposable databases
  (not TEST_DATABASE_URL); the role needs database creation privileges. Then
  run each service's alembic upgrade head and verify content boot. The orchestrator
  committed the initial implementation as a79d26a; round 1 edits remain uncommitted.

## New error codes

None. Boot failures continue using ContentError; pure invalid inputs ValueError.
