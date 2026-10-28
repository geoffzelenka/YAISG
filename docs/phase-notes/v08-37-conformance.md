## Built

- Audited all 28 §28 vision traceability rows, §2.1 R1–R17, each §23.4
  required test behavior, §21 tables and §22 endpoints. Wrote
  docs/v08/conformance.md with actual code locations and executable test names,
  consolidated outstanding questions, authoritative human rulings, removal
  inventory and scoped follow-up prompts. Read all earlier notes including 10a.
- Added the missing §22 open_vote to realm list/detail using the existing
  VoteResponse projection. Open aggregates remain hidden, participation stays
  public, and closed votes disappear from this field. Extended the existing
  ballot secrecy regression to check both projections and closure.
- Added bounded transactional metric-delta compaction to the existing periodic
  market lifecycle pass. Locked samples become equivalent summed delta rows in
  the same transaction; PostgreSQL skips samples locked by another compactor.
  Concurrent gameplay appends are preserved. No new table, job or dependency.
- Picked up 36's deferred client polish: equipment requirements show met/unmet
  and current levels, missing skills default to level one, the equipment doll
  has a group role, and belt positions have fieldsets and legends. Added direct
  combat unequip/assigned-stack return assertions and missing-skill coverage.
- New tests in services/game/tests/test_conformance.py:
  test_consolidated_action_routes_replace_aliases;
  test_removed_action_aliases_return_not_found;
  test_design_tables_and_endpoints_exist_without_retired_schema;
  test_metric_compaction_preserves_totals_rollback_and_future_events;
  test_lifecycle_compacts_committed_metrics;
  test_postgres_metric_compaction_skips_locked_rows_and_keeps_new_events.
- New client tests in EquipmentPanel.test.tsx:
  “keeps unequip and assigned stack returns disabled during combat”;
  “shows unmet equipment requirements with the default level for a missing skill”.
- Final repository-virtualenv SQLite make ci passes: auth 39 passed / 1 skipped,
  game 855 passed / 34 skipped, client 124 passed. Ruff formatting/lint, strict
  mypy, ESLint, Prettier, TypeScript, production build, scripts, content lint
  and fatal thirty-day seed-check pass. Checks used the existing external
  /tmp/yaisg-asyncio-wakeup sandbox shim documented by phase 36; no shim ships.
- Disposable SQLite make db-reset, subsequent game alembic upgrade head and
  alembic check succeed. App lifespan starts/stops the scheduler and serves the
  content manifest with HTTP 200. git diff --check passes. Report citations
  were checked against AST definitions; the 28 vision and 17 reconciliation
  rows and exact phase-note headings were checked independently.

## Removed

- Removed the four legacy character-scoped action route registrations per 06's
  explicit 37 hand-off. Migrated their existing tests to /actions/available,
  /actions/start, /actions/poll and /actions/stop without removing assertions.
  Authenticated requests to the retired URLs now return 404.
- Removed the unused mutation_windows.window index through reversible migration
  v08_0023_conformance. Request allowance upserts use the primary key. No pruning
  job needs the index today; a future pruning prompt should introduce its own
  justified index together with the job and concurrency tests.
- No tests deleted or weakened. No design or prompt files edited.

## Design ambiguities resolved

- §23.6 / 36 hand-off: roll-up uses equivalent aggregate rows in metric_deltas
  rather than a second totals table. Operator SUM queries keep their existing
  atomic snapshot semantics. One lifecycle pass examines at most 1,000 rows;
  this operational batch bound is independent of gameplay content. Rollback
  restores the original samples. It compacts rather than discards counters.
- §22: open_vote is the same typed public projection as GET vote, limited to
  currently open ballots. The dedicated endpoint still returns the latest
  closed ballot. This fills the consolidated projection requirement without
  changing ballot rules or exposing individual choices.

## Deviations

- §6.3: inherited uniform resolution remains per-cycle, despite closed-form
  wording. Follow-up F3 records the gap and compatibility requirements rather
  than attempting a large seeded reward algorithm rewrite during this audit.
- §21: inherited belt slot and ownership interval column spellings differ from
  the consolidated sketch; the report names the exact retained spellings.
- Remaining client polish and scaling/retention work from 36 are explicitly
  scoped in conformance.md F1–F8. This audit does not assert unconditional full
  conformance while these gaps and human questions remain.

## Ratification needed

- Consolidated human list Q1–Q9 in docs/v08/conformance.md: estate payment
  destination; zero-valued fixed forms; geometric project overlay; treasury
  inference through funded totals; failed-vote conflict precedence; NO_DEMAND
  status split; commodity self-matching; zero-HP regeneration/defeat (including
  dependent defensive-XP-at-zero behavior); combat XP multipliers and cap.
- These are inherited questions, unchanged here. Resolved vote-stock gates,
  upfront short raft construction, httpx/asyncio load generation, plain JSON
  metrics and the approved APScheduler dependency are listed separately under
  “Human rulings already given”. No new gameplay ruling was invented.

## Hand-offs

- Follow-up F1: optional mutation allowance pruning must be an independent,
  bounded maintenance transaction with PostgreSQL SKIP LOCKED, a stale-window
  recheck and live-mutation races. Never reintroduce cross-account request-path
  deletion. Measure metric ingestion against compaction capacity before tuning.
- Follow-ups F2–F8: replacement lock/dependency protocols, uniform batching,
  safe key-history watermark, remaining client polish/tests, content/lint
  projections, scalable read/cursor policies, and reset/migration isolation.
  conformance.md records origins and acceptance constraints for each.
- Human: rule on Q1–Q9 before follow-up work changes disputed gameplay. In
  particular the overlay completion promise and default defeat reachability
  cannot be honestly certified until their conflicting requirements are settled.

## New error codes

None. No new dependencies.
