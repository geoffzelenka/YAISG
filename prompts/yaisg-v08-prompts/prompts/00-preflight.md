## Prompt 00 — Baseline alignment audit

**ID:** `00-preflight` · **Needs:** nothing · **Design:** §0, §2, §3, §21, §22, §27 · **Changes behaviour:** no

### Goal

Before any v0.8 work, establish that the repository is the v0.5 baseline that design v0.8 assumes, and write down where everything lives so every later prompt starts from facts instead of guesses. This prompt audits and documents. It does not implement any [CHANGE] or [NEW] item.

### Build

1. **Inputs present.** Confirm `design/design.md` is v0.8 (its header says so) and `design/the-vision.md` exists. If either is missing or older, stop and record a `BLOCKER`.
2. **Green baseline.** Run `make ci` on SQLite and PostgreSQL 16. Record the commit, test counts and timings. Any failure is a finding.
3. **Audit every [SHIPPED] claim** in the design against the code, with evidence (file path and symbol, or test name). At minimum:
   - §3: two FastAPI services, separate databases and Alembic histories; RS256, JWKS, rotating hashed refresh tokens, reuse revokes all; SQLite + PostgreSQL in CI; Makefile as single source of checks; error envelope.
   - §4.1: strict frozen Pydantic packs, cross-pack checks, canonical SHA-256 hashing, manifest, strong ETags, unauthenticated content endpoints.
   - §6.4 unchanged behaviours: lazy resolve with partial cycle kept, segmentation at level-ups, offline cap ending the action, stop reasons and overflow precedence, CSPRNG seeding per resolve, backwards clock no-op, at-most-once reward feed.
   - §7.4 inert upgrades derived per resolve and never stored.
   - §9.1 inventory semantics; §13.1 ownership decoupled (`owner_character_id`, ownership history, `home_estate_id`); §13.3 upgrade and transform endpoints with their error codes and the last-slot row lock.
   - §23.1 locking (`FOR UPDATE` on PostgreSQL, immediate writer transaction on SQLite, two realms in id order); §23.4 existing property, statistics and contention tests; §23.6 JSON logs with request ids; §24 client shell (4 Hz clock, boundary-aligned polling with jitter, welcome-back modal, toasts).
4. **Audit every [CHANGE] item is still in its pre-change form**, so later prompts know their starting point. Record the current shape of each: XP curve (cumulative `floor(100·1.12^(L−2))`, max 99); additive modifier stacking and `cycle_time_pct`; `CycleRewardStrategy`; `characters.realm_id`; estate relocation columns, `level`, `upgrade_slots`; `realm_edges`, `realm_projects`, `award_edge_progress`, `finalize_realm`; `market_offers` on realms; the nine served packs; the `market_listings` cap; starting gold grant; `POST /characters {name, realm_id}`; relocation endpoints and `relocation_cost`/`path_cost`.
5. **Audit that no [NEW] item partially exists** (for example a half-built order book, stores table, or combat code). Any partial [NEW] code is a finding stating which prompt will replace it.
6. **Write `docs/v08/baseline-audit.md`**: one table, one row per item audited, columns `§ref | mark | status (OK / DRIFT / MISSING / PARTIAL) | evidence | absorbing prompt | severity (INFO / FIX-HERE / BLOCKER)`. `BLOCKER` means a later prompt's stated starting point is false in a way that prompt cannot absorb.
7. **Write `docs/v08/codebase-map.md`**: where the engine, content schemas, loader, routes, services, migrations, scheduler (if any), client routes and stores live; how to add a pack, a migration, an endpoint, a client panel; test layout, fixtures and factories; how the clock and RNG are injected; how to run each check locally on each database.
8. **Create `docs/v08/progress.md`** with one row per prompt from the README sequence, all `pending` except this one.
9. **Fix only `FIX-HERE` drift**: a [SHIPPED] behaviour that is a small bug against the design, fixed with a regression test. Everything else is recorded, not changed.

### Tests

- Any regression test added under item 9.
- No other code changes.

### Acceptance

- Both audit documents exist, every row has evidence, and `make ci` is green on both databases.
- Every `PARTIAL`, `DRIFT` and `MISSING` row names an absorbing prompt from the sequence, or is a `BLOCKER`.

### Out of scope

Any [CHANGE] or [NEW] implementation; content changes; refactors.

### Review focus

Evidence, not assertion: spot-check at least ten rows by opening the cited files. Confirm severity is honest; a `BLOCKER` must stop the pipeline.

