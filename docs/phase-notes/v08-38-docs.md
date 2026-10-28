## Built

- Refreshed README for v0.8 capabilities, name-only Tutorial Island creation,
  guest upgrade/departure, SQLite Compose, PostgreSQL 16 runtime/test URLs,
  independent migration ownership, disposable reset, all nine Make targets,
  scheduler cadences/locks, maintenance, repository layout, and current links.
  Preserved the configuration table and operational hardening section.
- Expanded auth operations with guest/upgrade routes, guards and errors, token
  kinds, refresh lifetime cap, separate inactivity purges, activity throttling,
  game promotion confirmation, and normalized trusted-proxy traversal. Clarified
  that key generation occurs lazily on signing-key use.
- Updated CLAUDE architecture, commands and layout while retaining its structure,
  role descriptions and Orchestrator section. Reviewed AGENTS.md: its standards
  and Python 3.12+ target remain accurate, so no edit was needed.
- Added historical-snapshot banners to the two prompt-00 reports, refreshed the
  progress introduction, and added 38-docs as ready for review. Kept the reports'
  original bodies intact. Updated the reward-feed reference to v0.8 §6.4 and
  confirmed toast grouping is still open after the combat/key client phases.
- Checked commands and targets against Makefile, scripts/db_reset.py,
  scripts/load_pipeline.py, service pyproject.toml files, client/package.json,
  docker-compose.yml, Dockerfiles, and .github/workflows/ci.yml. Confirmed
  service directories, migrations, scripts, client panels and documentation
  links exist. Checked all environment reads in services/*/app (getenv and
  environ.get) against the configuration table; none were missing. Verified
  Vite URLs in client/src/api/http.ts and the load token setting in the script.
- Checked auth guest/upgrade/refresh and email/password guards in auth api.py,
  schemas.py and security.py; proxy behavior in rate_limit.py; guest settings
  against content/auth.json; retention and locks in both guest_purge.py modules;
  game activity/promotion in game auth.py; /players/me and name-only creation in
  API modules; client upgrade confirmation/retry in api/http.ts and departure
  in TutorialBanner.tsx. Checked health/logging and admin/rate-limit claims in
  both applications and their logging modules, game admin.py and rate_limit.py.
- Checked hourly ticks, six-tick caravan passes, five-minute order lifecycle,
  30-day closed-slot retention, metric compaction, daily guest cleanup and lock
  scope against scheduler.py, caravans.py, market_lifecycle.py, metrics.py,
  auth main.py, both guest purges, and content/economy.json. Checked boot/CLI
  seeding in game main.py/world.py, warning-only content lint and fatal seed
  check in their CLI entry points. Verified reward aggregation/claiming and
  toast text against services/actions.py, engine/core.py, ActionExperience.tsx,
  ResolverDetails.tsx, actionStore.ts and their existing tests.
- No tests added: this is documentation only. No existing tests changed.
- SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passed with the external
  `PYTHONPATH=/tmp/yaisg-asyncio-wakeup` sandbox workaround already described
  in phases 36/37. The initial unshimmed run stalled in game action tests and
  was interrupted. Ruff, strict mypy, pytest, client lint/format/typecheck/
  Vitest/build, script checks, content lint and fatal seed-check all passed.
  `git diff --check`, environment-name coverage, link existence, exact note
  headings and preservation of protected documentation sections also passed.

## Removed

- Removed stale Phase 3 capability/future-work claims, selected-starting-realm
  walkthrough, obsolete table inventory, and Phase 3.1/3.2 README links.
- No code, behavior, routes, content or dependencies removed.

## Design ambiguities resolved

- None. Documentation follows the code; known differences from the design link
  to docs/v08/conformance.md rather than implying full conformance.

## Deviations

- None. Documentation-only scope; design, prompts, conformance, human
  ratifications and existing phase notes were not modified.

## Ratification needed

- None introduced. Existing questions remain in docs/v08/conformance.md.

## Hand-offs

- No earlier hand-off explicitly names 38-docs. Existing conformance Q1–Q9 and
  follow-ups F1–F8 remain the reference for future behavior changes; this refresh
  neither resolves nor implements them.

## New error codes

- None. No new dependencies.

## Orchestrator verification and review hand-offs

- Verified at c784c20 (docs only): SQLite make ci green; PostgreSQL game 887 / 2 skipped, auth 40; boot 200.
- Review round 1: APPROVE; the reviewer checked 31 factual claims against the code, and all match. Non-blocking hand-offs:
  - **Code/CI gap, needs human approval:** `services/auth/pyproject.toml` doesn't list `psycopg`. The GitHub `auth (postgres)` matrix job installs only `services/auth[dev]`, so a `postgresql+psycopg://` URL can't import its driver there, nor in the auth Docker image. Local runs pass only because the shared venv also installs the game service. Fix: add `psycopg[binary]>=3.2,<4` (already approved for game) to auth's dependencies.
  - README: running `TEST_DATABASE_URL=... make ci` against one database runs both suites against it in turn. That appears safe, but per-service `make auth-ci` / `make game-ci` would mirror CI.
  - docs/auth.md: any authenticated game request promotes an upgraded player, not only `GET /players/me`.
