# Yet Another Idle Skilling Game

YAISG is a multiplayer idle skilling game under active development. The current
Phase 3 server implementation includes authentication, validated and versioned
placeholder content, character creation, the pure skilling engine, and persistent
active-action APIs. The client includes live skilling routes, inventory display,
and a persistent active-action experience. Markets, estate upgrades, and combat
remain future phases.

## Current capabilities

- Register, log in, refresh, and log out through the RS256/JWKS auth service.
- Load validated placeholder skills, items, realms, upgrades, and caps through
  versioned public content endpoints.
- Create one character per account with a globally unique, case-insensitive name
  and an estate in the selected realm.
- View character skills and XP progress, gold, realm modifiers, and estate summary.
- List realm-available skilling actions with level and input blockers.
- Start, poll, switch, and stop one server-authoritative active action per character.
- Resolve online and offline progress lazily, including XP, inventory changes,
  offline caps, and a durable reward feed.
- Route authenticated accounts without a character to creation and established
  characters to the main profile shell.
- Browse Gathering, Refining, and Manufacturing actions with requirements, recipes,
  drop rates, server-calculated cycle times, and start blockers.
- Track and stop the global active action with a cosmetic progress timer, receive
  authoritative reward notifications, and review offline gains in a catch-up
  summary.
- View named inventory stacks and base inventory-slot usage on the Profile route.

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

Then visit <http://localhost:5173>. Register an account, choose a character name and
realm, and use the skill routes in the sidebar to start an action. The global
action strip remains visible while navigating between routes.
Source directories are mounted into their containers, so the development servers
reload when files change. SQLite databases are stored in the ignored local `data/`
directory.

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

### Client

Node.js 20 and npm are required. In another terminal:

```bash
cd client
npm ci
npm run dev
```

Open <http://localhost:5173> after both APIs are running.

## Database migrations

Both services own Alembic migrations. The auth migrations create users and rotating
refresh tokens; the game migrations create players, characters, skill progression,
currency, estates, installed estate upgrades, inventory stacks, active actions, and
the reward log/feed state. Apply them from their respective service directories:

```bash
cd services/game
alembic upgrade head

cd ../auth
alembic upgrade head
```

Docker Compose applies both migration chains automatically before starting the APIs.

## Configuration

| Variable | Used by | Default |
| --- | --- | --- |
| `GAME_DATABASE_URL` | Game API | `sqlite:///./data/game.db` |
| `GAME_OPERATOR_AUTH_USER_IDS` | Game API | Empty (comma-separated auth user UUIDs allowed to call `GET /admin/economy`) |
| `AUTH_DATABASE_URL` | Auth API | `sqlite:///./data/auth.db` |
| `CORS_ORIGINS` | Both APIs | `http://localhost:5173` |
| `GIT_SHA` | Both APIs | `dev` |
| `CONTENT_DIR` | Auth and Game APIs | Repository `content/` directory locally; set to the mounted shared content directory in API images |
| `AUTH_JWKS_URL` | Game API | `http://localhost:8001/.well-known/jwks.json` |
| `AUTH_JWKS_TTL_SECONDS` | Game API | `300` |
| `JWT_ISSUER` | Game API | `yaisg-auth` |
| `AUTH_KEYS_DIR` | Auth API | `./data/keys` |
| `AUTH_COOKIE_SECURE` | Auth API | `false` |
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
production build.

Individual targets are also available:

```bash
make auth-ci
make game-ci
make client-ci
```

## Repository layout

```text
services/auth/   FastAPI authentication service and auth-owned database
services/game/   FastAPI game API, content loader, models, and pure engine functions
content/         Validated placeholder content packs and generated XP curve
client/          React authentication, character creation, and profile client
design/          Technical design document
docs/            Phase notes and project documentation
```

See [the technical design](design/design.md), [Phase 3.1 notes](docs/phase-notes/3.1.md),
and [Phase 3.2 notes](docs/phase-notes/3.2.md) for scope and implementation decisions.
