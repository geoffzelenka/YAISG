# Yet Another Idle Skilling Game

YAISG v0.8 is a multiplayer idle skilling game under active development, with
two FastAPI services and a React client. Progress is server-authoritative and
resolved lazily from timestamps. Known gaps and unresolved design questions are
tracked in [the conformance report](docs/v08/conformance.md).

## Current capabilities

- Guest play, registration, and in-place account upgrade.
- Tutorial Island, guided steps, and departure after upgrading a guest account.
- Skills, tiers, proficiency, XP taper, and offline rewards.
- Travel and multi-edge journeys.
- Realm development, projects, tags, upgrade votes, and transitions.
- Realm stores, demand lines, ticks, decay, and minting.
- Realm markets, treasury gifts, and caravans.
- A global commodity order book with escrow, slots, and history.
- Estate forms, building, buying, surrendering, upgrades, and larder deposits.
- Equipment, consumable belts, buffs, and hit points.
- Combat, stances, and encounter rewards.
- Exploration, instanced keys, and the key market.
- Mutation rate limits and operator metrics.

The content pack is deliberately synthetic scaffolding. It does not establish final
game names, balance, or content.

## Current services

| Service | Technology | Local URL |
| --- | --- | --- |
| Game API | FastAPI | <http://localhost:8000/healthz> |
| Auth API | FastAPI | <http://localhost:8001/healthz> |
| Client | React and Vite | <http://localhost:5173> |

Each API health endpoint returns its service name, status, and build version. It
also returns an `X-Request-Id` response header and writes a structured JSON request
log.

## Run with Docker Compose

Docker Compose is the simplest way to start the full development stack.

Requirements:

- Docker Engine
- Docker Compose v2 (`docker compose`)

From the repository root, run:

```bash
docker compose up --build
```

Then visit <http://localhost:5173>. Choose **Play now** for a guest session, or
register an account. Create a character by name only; it starts on a private
Tutorial Island. Follow the tutorial hints to build the raft and depart. Guests
must upgrade to an account before departure; the client offers that form when
departure is blocked. The global action strip stays visible across routes.
Source directories are mounted into their containers, so the development servers
reload when files change. SQLite databases are stored in the ignored local `data/`
directory. Compose uses SQLite for both services.

Stop the stack with `Ctrl+C`, or from another terminal:

```bash
docker compose down
```

To include a Git commit in the health response, set `GIT_SHA` before building:

```bash
GIT_SHA=$(git rev-parse HEAD) docker compose up --build
```

Without this variable, the reported version is `dev`.

## Run locally without Docker

### Python services

Python 3.12 or newer is required. Create a virtual environment and install both
services with their development tools:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e "services/auth[dev]" -e "services/game[dev]"
```

Before starting either API, apply both migration chains from the repository root:

```bash
(cd services/game && alembic upgrade head)
(cd services/auth && alembic upgrade head)
```

The game API creates the world during boot and requires a migrated database.
For disposable development data, `make db-reset` rebuilds both databases.

Start the game API:

```bash
cd services/game
uvicorn app.main:app --reload --port 8000
```

In a second terminal with the same virtual environment activated, start the auth
API:

```bash
cd services/auth
uvicorn app.main:app --reload --port 8001
```

The default databases are `services/game/data/game.db` and
`services/auth/data/auth.db`, depending on the service's working directory.

### PostgreSQL 16

Both APIs also support PostgreSQL 16. Provision separate databases for runtime
auth and game state, with a role allowed to migrate them, then export these in
each API terminal before running the migration and startup commands above:

```bash
export GAME_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_game
export AUTH_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_auth
```

For tests, use a separate disposable database, as the PostgreSQL 16 matrix in
`.github/workflows/ci.yml` does. The test fixtures recreate tables; never point
`TEST_DATABASE_URL` at a runtime database. From the repository root:

```bash
TEST_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_test make ci
```

The runtime URL variables select the databases for migrations and the APIs;
`TEST_DATABASE_URL` selects the database for the Python tests. Without it, tests
use SQLite. Docker Compose continues to use SQLite.

### Client

Node.js 20 and npm are required. In another terminal:

```bash
cd client
npm ci
npm run dev
```

Open <http://localhost:5173> after both APIs are running.

## Database migrations

Each service owns an independent Alembic chain and database. Auth owns identities,
credentials, activity timestamps, and rotating refresh sessions. Game owns players,
characters and progression, actions and rewards, realms and development, estates,
economy and markets, equipment and combat state, keys, tutorials, and operational
counters and rate allowances. Apply each chain from its service directory using
`alembic upgrade head`, as shown above. Docker Compose does this before startup.

Development data is disposable. From the repository root, `make db-reset`
destructively recreates both configured databases and migrates them to head.
PostgreSQL reset requires permission to terminate connections and drop/create the
two dedicated databases; the auth and game targets must be distinct.

## Configuration

| Variable | Used by | Default |
| --- | --- | --- |
| `GAME_DATABASE_URL` | Game API | `sqlite:///./data/game.db` |
| `GAME_OPERATOR_AUTH_USER_IDS` | Game API | Empty (comma-separated auth user UUIDs allowed to call `GET /admin/economy` and `GET /admin/metrics`) |
| `GAME_MUTATION_LIMIT` | Game API | `120` mutation attempts per character/account per window |
| `GAME_MUTATION_WINDOW_SECONDS` | Game API | `60` (fixed UTC windows; positive integer) |
| `AUTH_DATABASE_URL` | Auth API | `sqlite:///./data/auth.db` |
| `CORS_ORIGINS` | Both APIs | `http://localhost:5173` |
| `GIT_SHA` | Both APIs | `dev` |
| `CONTENT_DIR` | Auth and Game APIs | Repository `content/` directory locally; set to the mounted shared content directory in API images |
| `AUTH_JWKS_URL` | Game API | `http://localhost:8001/.well-known/jwks.json` |
| `AUTH_JWKS_TTL_SECONDS` | Game API | `300` |
| `JWT_ISSUER` | Game API | `yaisg-auth` |
| `AUTH_KEYS_DIR` | Auth API | `./data/keys` |
| `AUTH_COOKIE_SECURE` | Auth API | `false` |
| `AUTH_TRUSTED_PROXY_IPS` | Auth API | Empty (comma-separated proxy IPs; forwarded chains use the rightmost untrusted hop) |
| `VITE_GAME_URL` | Client | `http://localhost:8000` |
| `VITE_AUTH_URL` | Client | `http://localhost:8001` |

Multiple CORS origins can be supplied as a comma-separated list.

## Checks and tests

After installing the Python and client dependencies, run every local CI check from
the repository root:

```bash
make ci
```

This runs Ruff formatting and linting, strict mypy, and pytest for both Python
services, followed by ESLint, Prettier, TypeScript checking, Vitest, and the client
production build, script checks, content lint and the fatal thirty-day seed check.

| Target | Purpose |
| --- | --- |
| `ci` | All service, client, script, content-lint, and seed checks. |
| `auth-ci` | Auth Ruff lint/format, strict mypy, and pytest. |
| `game-ci` | Game Ruff lint/format, strict mypy, and pytest. |
| `client-ci` | ESLint, Prettier, TypeScript, Vitest, and production build. |
| `scripts-ci` | Ruff lint/format and mypy for `scripts/`. |
| `db-reset` | Destructively recreate both development databases and migrate. |
| `content-lint` | Warning-only XP-rate and combat content report; balance warnings do not fail CI. |
| `seed-check` | Thirty-day world sustainability simulation; failures are fatal in CI. |
| `world-create` | Seed the migrated game database once; also performed on API boot. |

## Background jobs

The game lifespan starts an in-process APScheduler. With the current
`content/economy.json`, the realm driver runs hourly (`86400 / tick.per_day`
seconds). It advances shared realms and invokes the caravan pass; caravan
boundaries occur every six ticks (`caravan.pass_every_ticks`), currently six
hours. Requests also resolve state lazily.

The market lifecycle job runs every 300 seconds
(`market.lifecycle_interval_seconds`): open orders expire into their slots,
closed empty slots older than the 30-day retention are purged, and a bounded
metric-delta batch is compacted without changing totals. The game guest purge
runs daily. Auth has a separate cleanup thread that runs on startup and then
every 24 hours. Both purges use the shared guest inactivity settings described
in [auth operations](docs/auth.md).

For multiple processes, PostgreSQL advisory locks exclude overlapping realm
(and associated caravan) drivers, market lifecycle passes, and each service's
guest purge passes. Realm ticks use a dedicated connection's session lock;
lifecycle and guest purges use transaction locks. SQLite uses serialized writes
and idempotent replay. There is no mutation-allowance pruning job.

## Repository layout

```text
services/auth/   FastAPI authentication service and auth-owned database
services/game/   FastAPI game API, content loader, models, and pure engine functions
content/         Validated placeholder content packs and generated XP curve
client/          React auth/tutorial, skills/travel, realms/estates/markets,
                 equipment/combat, keys, inventory, and reward UI
scripts/         Database reset, XP-curve generation, and HTTP load tooling
design/          Technical design and vision
docs/            Auth operations, tech debt, and phase notes
docs/v08/        Pipeline progress, baseline snapshots, and conformance report
```

See [the technical design](design/design.md), [pipeline progress](docs/v08/progress.md),
[known conformance gaps](docs/v08/conformance.md), [auth operations](docs/auth.md),
and [phase notes](docs/phase-notes/).

## Operational hardening

Game mutations share a database-backed allowance across routes and workers.
The key is the verified account UUID: each account owns at most one character,
so creation and later mutations share the same allowance. Failed intents count;
GET polling and lazy reads do not. A refusal returns 429, `RATE_LIMITED`, and
`Retry-After`. Fixed windows permit a burst on either side of a boundary.

Operators can read `/admin/metrics` for durable event counters and gold by holder
(wallets, treasuries, order escrow and slots). `tick_duration_ns` is cumulative
wall time for completed realm tick batches, including loading/persistence;
`caravan_losses` counts whole goods lost on dispatch, and `keys_discovered`
counts persisted keys. Mint totals come from the signed gold ledger. Counter
deltas commit with game changes and survive history/holder deletion. Keep SQL
statement/parameter logging disabled in production to preserve secret ballots;
request logs contain neither bodies nor vote choices.

Run a mixed HTTP load against a **disposable** deployment with stock, market
access and free order slots. Set `YAISG_LOAD_TOKENS` to a JSON array of valid
bearer tokens, then run:

```bash
PATH=$PWD/.venv/bin:$PATH python scripts/load_pipeline.py \
  --base-url http://localhost:8000 --realm REALM_ID --item ITEM_ID \
  --workers 4 --rounds 10
```

Each worker polls, reads a realm, inserts a sell order, cancels and collects it.
Each round makes **3 mutations** against the default **120 per account per minute**.
Provide enough tokens for distinct accounts or raise `GAME_MUTATION_LIMIT` for
higher load. Workers sharing a token share its allowance: the example above
uses all 120 attempts if its four workers share one token and finish in a minute.
Leave headroom for setup and other game mutations.
Use an empty book to avoid unintended fills; errors (including rate limits)
count as failures and cause a nonzero exit. Tokens are never printed. The
reproducible local ASGI baseline and its limits are recorded in
`docs/phase-notes/v08-36-hardening.md`.
