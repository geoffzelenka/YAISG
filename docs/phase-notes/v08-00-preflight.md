## Built

- Audited baseline `697dd2d6005ff7c616617c3d014e18760a87d7da` on
  `v08/00-preflight`; read AGENTS.md, CLAUDE.md, design v0.8 and the vision.
- Added `docs/v08/baseline-audit.md`: 102 evidence rows, with 94 OK, 6 DRIFT,
  1 MISSING and 1 PARTIAL. Every non-OK row names its absorbing prompt.
  No FIX-HERE or BLOCKER findings; no runtime, content or test changes.
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
- §3 versus §23.2: recorded the absent scheduler as shipped-label drift absorbed
  by 14-realm-tick, which explicitly introduces the scheduled job. Did not add
  a scheduler in a documentation-only prompt.

## Deviations

- Build 2 / both-database definition of done: no independent green PostgreSQL
  run was possible in this sandbox. The attempted run and permission probe are
  recorded; PostgreSQL acceptance evidence is the orchestrator's supplied green
  baseline, as explicitly permitted by the task's environment notes.
- §6.3: existing resolve loops per cycle, although the document calls it
  closed-form. Preserved behavior and assigned resolver work to 06.
- §6.4: no requirements-lost stop exists; assigned to 05-tags.
- §23.1: active-action locking substitutes for a character lock when an action
  exists, and relocation finalization locks the estate before realm locks.
  Assigned coordinated transaction work to 06-resolver-presence; not a small
  isolated FIX-HERE correction.
- §4.1: schemas forbid extras and are frozen but permit Pydantic coercion and
  have shallow nested-dictionary immutability. Recorded strict-type ambiguity
  as drift for 02-content-model to resolve with schema work.
- §27: retired market_tax_pct survives in the schema/client types and display
  labels, with no active tax engine behavior. Assigned removal to 03-bonus-model.

## Ratification needed

None. No finding requires a new design decision before 01-foundation. The
strict-schema interpretation should be made explicit in 02's phase note.

## Hand-offs

- 01-foundation: existing curve has 99 cumulative entries, SQL Integer XP,
  default 100 STARTING_GOLD; db-reset does not yet exist. Preserve the already
  tested offline-cap and reward-claim semantics while resetting the schema.
- 02-content-model: explicitly settle strict type coercion and nested frozen
  schema expectations; old Skill has no category; old Project has targets and
  awards, not project tiers. Current table is realm_edge_progress, not
  realm_edges. See map before assuming names from design shorthand.
- 03-bonus-model: remove retired market_tax_pct across schema and client, and
  replace additive cycle_time_pct stacking; preserve inert-upgrade exclusion.
- 05-tags: add requirements-lost stopping when revalidating active actions;
  existing upgrade restriction field is realm_tags, not requires_realm_tags.
- 06-resolver-presence: establish character → sorted realms → estate locking
  across existing mutation paths, replace reward-strategy seam as required,
  and account for the old per-cycle resolver and old character-scoped action
  routes when wiring the consolidated API.
- 07-travel: remove relocation fields/routes/path-cost mechanics end to end.
- 09-development-graph / 10-project-runs: replace edge awards and old project
  totals; remove realm market_offers during template remodel.
- 11-estate-forms / 12-estate-ownership: preserve decoupled ownership/history
  and upgrade/transform error contracts while replacing relocation and slots.
- 14-realm-tick: add the scheduler from scratch; dependency addition still
  needs human approval under AGENTS.md. No dependency was added here.
- 28-combat-model / 29-combat-resolver: replace the empty combat-monsters skill
  and future-combat reward seam; no combat mechanics currently exist.
- Every later prompt: read the audit's individual absorbing-prompt column;
  PostgreSQL fixtures drop metadata in the dedicated test database, and only
  action/estate fixtures select TEST_DATABASE_URL. Do not claim that all tests
  or auth fixtures run against PostgreSQL when setting that variable.

## New error codes

None.
