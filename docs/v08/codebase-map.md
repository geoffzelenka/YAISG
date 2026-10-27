# v0.8 codebase map

Verified at `697dd2d6005ff7c616617c3d014e18760a87d7da`, 2026-10-26.
Read alongside [baseline-audit.md](baseline-audit.md). This describes existing
v0.5 code, not the intended v0.8 architecture. No scheduler currently exists.

| Area | Location and entry points |
|---|---|
| Service boot | `services/auth/app/main.py`, `services/game/app/main.py`: FastAPI app, routers, CORS, error handlers, request middleware; game attaches loaded content to app.state |
| Auth | `services/auth/app/api.py`: register/login/refresh/logout/JWKS; `security.py`: Argon2, RS256 keys, SHA-256 refresh hashes; `models.py`: User/RefreshToken; `rate_limit.py`: IpRateLimiter |
| Game authentication | `services/game/app/auth.py`: JWKS cache, verify_access_token, current player; `api/players.py`: player identity bootstrap |
| Pure engine | `services/game/app/engine/core.py`: immutable state/action/result dataclasses, resolve, can_start, effective bonuses, caps, path_cost/relocation_cost, reward strategy protocol; `engine/levels.py`: level_for_xp/xp_progress |
| Content schemas | `services/game/app/content/schemas.py`: ContentModel (frozen, unknown fields forbidden; no strict type-coercion setting), pack and record models |
| Content loading | `services/game/app/content/loader.py`: load_content, ContentIndex lookups/with_overrides, cross-reference validation, canonical serialization and hashes, PUBLIC_PACKS; `runtime.py`: process CONTENT; `content/*.json` plus private xp_curve and generator |
| Content HTTP | `services/game/app/api/content.py`: manifest, pack bytes, ETag/304; main.py exempts exact public pack paths from JWT checks |
| Game routes | `services/game/app/api/characters.py`: create/profile/inventory; `actions.py`: available/start/poll/stop; `estates.py`: home estate/install upgrade/transform; `realms.py`: list/detail/map/contribute/relocation and preview; `api/schemas.py`: shared action payloads |
| Transaction adapters | `services/game/app/services/actions.py`: resolve_character, state load/persist, reward claims, serialization; `services/realms.py`: sorted realm locks, transition finalization, edge awards, relocation finalization. Some orchestration remains in routers |
| Models | `services/game/app/models/player.py`, `models/character.py`, exported in `models/__init__.py`; character, skills, currency, estate/history/upgrades, realm state/edge progress/projects/contributions, inventory, active action, reward log |
| Database setup | Each service owns `app/db.py`, config, Alembic ini/env and metadata; game SQLite dialect hooks implement WAL and explicit BEGIN/BEGIN IMMEDIATE; PostgreSQL locks use SQLAlchemy with_for_update |
| Migration histories | `services/auth/migrations/versions/0001_baseline.py` through `0002_auth_tables.py`; game `0001_baseline.py` through `0006_realm_estate_v05.py`; `0005_reward_feed_tracking.py` adds reward claim tracking |
| Scheduler | None; no APScheduler dependency or lifespan job. Prompt 14 introduces it; later prompts add caravans, order expiry/purge and guest purge |
| Client entry/routes | `client/src/main.tsx`, `App.tsx`: auth guard, character creation, shared sidebar/action strip; skills, profile, estate, realm and map panels under `features/` |
| Client data/state | `client/src/api/http.ts`: authenticated transport/refresh; `api/content.tsx`: typed content context/cache; other `api/*.ts`: TanStack Query hooks; `features/auth/AuthProvider.tsx`: session; `features/actions/actionStore.ts`: shared Zustand cosmetic clock and polling math |
| Action presentation | `features/actions/ActionExperience.tsx`: server polling, action strip, welcome modal/reward toasts; `rewardPresentation.ts`; `features/realm/Countdown.tsx` and countdownMath.ts for realm/relocation timers |
| Observability | Both `app/logging.py`: JSON request logs and X-Request-Id including safe INTERNAL_ERROR; estate router emits audit records. No economy counters |
| Checks/deployment | `Makefile` is check source; `.github/workflows/ci.yml` runs service targets, PostgreSQL migrations, client target; `docker-compose.yml` boots auth/game with Alembic and Vite client; README.md configuration |

To add a pack, define records and a pack model in `content/schemas.py`, add its
JSON under `content/`, wire `loader.py:load_content` and cross-pack validation,
and extend ContentIndex and its test override support where required. Add served
packs to PUBLIC_PACKS (private packs still participate in the version hash).
The content router and exact-path public allowlist derive from PUBLIC_PACKS.
Update client content types/loading and the content validation, hashing, public
route and ETag tests. Follow v0.8 ownership: later prompts create only packs
they need; `world_seed` is private. No new pack was created by this audit.

To add a migration, work in the owning service, register model imports in its
metadata, then use `alembic revision --autogenerate -m 'description'` or write an
explicit revision. Review generated SQL/types/constraints and the revision
chain. Set AUTH_DATABASE_URL or GAME_DATABASE_URL for Alembic (TEST_DATABASE_URL
only selects supported test fixtures). Check upgrade/current/check against
SQLite and PostgreSQL. Prompt 01 replaces the game baseline destructively and
adds db-reset; that target does not exist yet.

To add an endpoint, define typed boundary/response schemas and stable error
codes with `api_error`, add the route in the appropriate router, and register
new routers in main.py. Inject ServerNow and DatabaseSession. Put pure rules
in engine functions and persistence in services. Establish character → sorted
realms → estate locks before reads/mutations and commit the response's state
and reward claims atomically. The baseline lock order is not universally this
order (see audit); copying it blindly would carry drift forward. Add API tests
using dependency overrides, and run lock-sensitive tests on PostgreSQL.

To add a client panel, add typed API methods/query hooks in `client/src/api`,
a feature component under `features/<area>`, and a route/sidebar link in App.tsx.
Use server values as truth and the shared cosmetic clock for timers; invalidate
relevant query keys after mutations. Co-locate Vitest/Testing Library tests,
using mocked transport/content/auth and fake timers when testing time.

Tests live in each service's `tests/`; there is no shared conftest or factory
package. Auth `test_auth.py` uses temporary SQLite, temporary signing keys,
HTTPX ASGITransport and dependency overrides. Game `test_engine.py` provides
`make_state`, `make_active`, `with_action` and loaded content; immutable content
can be varied using ContentIndex.with_overrides or model_copy. Hypothesis checks
resolve associativity and recipe conservation; a seeded drop-statistics test
checks the declared distribution. `test_levels.py` checks table boundaries.
`test_content.py` copies content into tmp_path and tests invalid definitions,
hash changes, ETags and public access. `test_migrations.py` upgrades a temporary
SQLite database with legacy data and tests downgrade.

Game `test_actions.py:action_client` and `test_estates.py:estate_client` select
TEST_DATABASE_URL or a temporary SQLite file, configure SQLite writer behavior,
create/drop game metadata, issue test JWTs, replace JWKS lookup, and override
get_db/utc_now. `_give` in estate tests seeds inventory. These fixtures **drop
all tables in the selected database**: use only the dedicated disposable test
database and run them sequentially. Other game API and realm-unit fixtures
remain SQLite even during a PostgreSQL matrix run. The concurrency tests use
separate sessions/threads and events; the estate last-slot test has a real
PostgreSQL handler-contention branch and an SQLite outcome-only branch.

Clock/RNG injection: `app/clock.py:utc_now` is the FastAPI ServerNow dependency;
API fixtures override it with FakeClock or a mutable fixed-time mapping. Pure
`engine/core.py:resolve` takes explicit now and RandomSource; engine tests pass
seeded random.Random values. Production `services/actions.py:resolve_character`
seeds a fresh RNG from secrets.randbits(256). Realm finalizers accept explicit
now; legacy award_edge_progress also has a wall-clock fallback outside engine.
Client clock tests use Vitest fake timers and polling math accepts injected
randomness. Never put database, wall clock or global runtime state in engine.

Run from the repository root using its virtualenv (the default shell Python
belongs to another project):

```bash
PATH=$PWD/.venv/bin:$PATH make ci
PATH=$PWD/.venv/bin:$PATH make auth-ci
PATH=$PWD/.venv/bin:$PATH make game-ci
PATH=$PWD/.venv/bin:$PATH make client-ci
PATH=$PWD/.venv/bin:$PATH TEST_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_test make ci
```

Each Python target runs Ruff lint, Ruff format --check, strict mypy, then pytest.
client-ci runs eslint, prettier --check, tsc -b --pretty false, vitest and a production
TypeScript/Vite build. To run an individual check, prefix PATH at the repo
root (or export it once before changing directories), then run the corresponding
Makefile command in its service directory; e.g. `python -m pytest
 tests/test_engine.py -k offline_cap`, `python -m mypy app tests`, or
`python -m ruff check .`. Client checks are the npm scripts in package.json.

The orchestrator provisioned PostgreSQL 16 at localhost:5432, user/password
`yaisg` and database `yaisg_test`, matching the CI container. Docker Compose
itself configures SQLite, not this PostgreSQL test service. To check migrations
locally after exporting the repo PATH, use:

```bash
cd services/game
GAME_DATABASE_URL=sqlite:////tmp/yaisg-preflight-game.db alembic upgrade head
GAME_DATABASE_URL=sqlite:////tmp/yaisg-preflight-game.db alembic check
GAME_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_test alembic upgrade head
GAME_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_test alembic current
GAME_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_test alembic check
```

Use auth's own directory/AUTH_DATABASE_URL for its separate history. Do not
interleave Alembic checks with metadata-dropping test fixtures. The matrix only
runs the game suite on PostgreSQL; setting TEST_DATABASE_URL does not move the
auth tests to PostgreSQL. If mypy crashes with an INTERNAL ERROR in zipimport.pyi,
the orchestrator observed a stale game .mypy_cache; deleting that generated
cache restored checks. See the audit for measured runs and sandbox limits.
