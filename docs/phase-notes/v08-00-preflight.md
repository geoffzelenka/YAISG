## Built

- Audited baseline `697dd2d6005ff7c616617c3d014e18760a87d7da` on
  `v08/00-preflight`; read AGENTS.md, CLAUDE.md, design v0.8 and the vision.
- Added `docs/v08/baseline-audit.md`: 102 evidence rows, with 94 OK, 6 DRIFT,
  1 MISSING and 1 PARTIAL. Every non-OK row names its absorbing prompt.
  One FIX-HERE finding fixed; no BLOCKER findings or content changes.
  Counts describe baseline findings: DRIFT includes the fixed lock-order bug;
  the sandbox PostgreSQL limitation is OK with an environment note.
- Fixed §23.1 shipped GET /realms lock ordering (review B1): call
  finalize_realms to acquire locks in id order, then return content order.
  Added test_get_realms_locks_in_id_order: PostgreSQL confirms the request is
  blocked on the lower realm via pg_blocking_pids; a third session acquires
  the higher realm NOWAIT. The old route fails this check. Bounded waits and
  a statement timeout prevent hangs; SQLite skips this PostgreSQL-only test.
- Round 1 SQLite `PATH=$PWD/.venv/bin:$PATH make game-ci` passed Ruff lint,
  format check, strict mypy and pytest: 99 passed, 1 skipped, three existing
  datetime-adapter warnings, pytest 6.73s. Orchestrator ran PostgreSQL 16
  `make game-ci` at 786e5bf: 100 passed. With only the old `get_realms`
  restored, `test_get_realms_locks_in_id_order` fails with LockNotAvailable.
- Added `docs/v08/codebase-map.md`: service/engine/content/client locations,
  extension recipes, fixtures, clock/RNG injection, database setup and checks.
- Added `docs/v08/progress.md`: all 38 prompts; 00 ready for review, others
  pending. Merge commit remains unset until the orchestrator merges.
- Local SQLite `make ci` passed: auth 15 (3.25s), game 99 (6.56s), client 22
  (7.60s); all formatting, lint, strict mypy, TypeScript and build checks green.
  Vite build 4.83s; total wall time not instrumented. Three game warnings are
  SQLite datetime-adapter deprecations.
- Local PostgreSQL `make ci` attempted: auth 15 passed (5.89s), game 74 passed
  and 25 fixture setup errors (18.54s), total 27.826s, client not reached.
  Direct localhost:5432 socket probe raises PermissionError (errno 1,
  Operation not permitted); this sandbox cannot reach PostgreSQL. Relying on
  orchestrator results as authorized: SQLite make ci green (15/99/22, ~67s)
  and PostgreSQL 16 game-ci green (99, ~15s), both at 697dd2d.
- Recorded the orchestrator's stale game .mypy_cache / zipimport.pyi INTERNAL
  ERROR and successful cache removal. No source fix was needed.

## Removed

Nothing. No tests were deleted or weakened. Untracked orchestration material
under `prompts/yaisg-v08-prompts/` was left untouched and excluded from staging.

## Design ambiguities resolved

- §0, §4.2 and §23.2: NEW/OK means absent as expected. Nullable estate ownership,
  treasury fields and dormant upkeep profiles are shipped prerequisites, not
  implemented realm-economy mechanics; the empty combat skill is explicitly
  recorded as PARTIAL because later combat work must replace it.
- §5.1, §2.1 R1: the baseline generator accumulates each exponential step into
  cumulative thresholds. Recorded its actual formula instead of interpreting
  the reconciliation table's shorthand as a direct cumulative exponential.

## Deviations

- Build 2 / both-database definition of done: no independent green PostgreSQL
  run was possible in this sandbox. The attempted run and permission probe are
  recorded; PostgreSQL acceptance evidence is the orchestrator's supplied green
  baseline, as explicitly permitted by the task's environment notes.

## Ratification needed

None. No finding requires a new design decision before 01-foundation. The
strict-schema interpretation should be made explicit in 02's phase note.

## Hand-offs

- 01-foundation: existing curve has 99 cumulative entries, SQL Integer XP,
  default 100 STARTING_GOLD; db-reset does not yet exist. Preserve the already
  tested offline-cap and reward-claim semantics while resetting the schema.
- 02-content-model: explicitly settle strict type coercion and nested frozen
  schema expectations; old Skill has no category; old Project has targets and
  awards, not project tiers. Remove the empty combat-monsters skill in 02.
  `test_get_realms_locks_in_id_order` only detects content-order locking
  because content lists realms out of id order (verdant_vale before
  ashen_reach); if realm content changes, keep the realms out of id order in
  that test (e.g. via content overrides) and use first/last sorted ids.
  Current table is realm_edge_progress, not realm_edges. See map before assuming names from design shorthand.
- 03-bonus-model: remove retired market_tax_pct across schema and client, and
  replace additive cycle_time_pct stacking; preserve inert-upgrade exclusion.
- 05-tags: add requirements-lost stopping when revalidating active actions;
  existing upgrade restriction field is realm_tags, not requires_realm_tags.
- 06-resolver-presence: replace active-action serialization with consistent
  character locking and remove CycleRewardStrategy as required; the shipped
  resolver loops per cycle despite §6.3 calling it closed-form. Also
  account for the old character-scoped action routes when wiring the
  consolidated API.
- 07-travel / 12-estate-ownership: address the estate-before-realm lock drift.
  07 removes finalize_relocation and relocation fields/routes/path-cost
  mechanics; 12 Build 7 establishes character → realm → estate locking.
- 09-development-graph / 10-project-runs: replace edge awards and old project
  totals; remove realm market_offers during template remodel.
- 11-estate-forms / 12-estate-ownership: preserve decoupled ownership/history
  and upgrade/transform error contracts while replacing relocation and slots.
- 14-realm-tick: add the scheduler from scratch. §3 labels it shipped, but
  §23.2 correctly treats it as new; no scheduler exists in the baseline.
  Dependency addition still needs human approval under AGENTS.md. No
  dependency was added here.
- 28-combat-model / 29-combat-resolver: build combat mechanics after 02 removes
  the placeholder skill and 06 removes the reward-strategy seam; no combat
  mechanics currently exist.
- Every later prompt: read the audit's individual absorbing-prompt column;
  PostgreSQL fixtures drop metadata in the dedicated test database, and only
  action/estate fixtures select TEST_DATABASE_URL. Do not claim that all tests
  or auth fixtures run against PostgreSQL when setting that variable.

## New error codes

None.
