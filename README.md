# Yet Another Idle Skilling Game

YAISG is a multiplayer idle skilling game under active development. The current
Phase 0 implementation is the project skeleton only: two health-check APIs and a
small status page. It does not yet contain authentication or game logic.

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

Then visit <http://localhost:5173>. The page should show both services as healthy.
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

Both services currently have empty Alembic baseline migrations. Apply them from
their respective service directories:

```bash
cd services/game
alembic upgrade head

cd ../auth
alembic upgrade head
```

No application tables are created in Phase 0.

## Configuration

| Variable | Used by | Default |
| --- | --- | --- |
| `GAME_DATABASE_URL` | Game API | `sqlite:///./data/game.db` |
| `AUTH_DATABASE_URL` | Auth API | `sqlite:///./data/auth.db` |
| `CORS_ORIGINS` | Both APIs | `http://localhost:5173` |
| `GIT_SHA` | Both APIs | `dev` |
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
services/auth/   FastAPI authentication service skeleton
services/game/   FastAPI game service skeleton and reserved engine packages
content/         Future data-driven content packs
client/          React status client
design/          Technical design document
docs/            Phase notes and project documentation
```

See [the technical design](design/design.md) and
[Phase 0 notes](docs/phase-notes/0.1.md) for scope and implementation decisions.
