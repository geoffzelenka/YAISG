You are implementing Phase 0 of the attached design document for a multiplayer idle skilling game. Build the project skeleton only — no game logic.

Create:

The monorepo layout exactly as specified in §3.1: services/auth, services/game, content/, client/, docs/.
services/auth and services/game: FastAPI apps with only a GET /healthz endpoint returning {"status": "ok", "service": "<name>", "version": "<git sha or 'dev'>"}. Each service has its own pyproject.toml (Python 3.12), with ruff, mypy, pytest, httpx configured. Shared lint/type settings; strict mypy.
services/game: SQLAlchemy 2.x + Alembic wired up with an empty baseline migration. Database URL from env var GAME_DATABASE_URL, defaulting to a SQLite file at ./data/game.db with WAL mode enabled on connect. Same pattern for auth with AUTH_DATABASE_URL.
client/: Vite + React 18 + TypeScript + Tailwind. Render a single page showing the app name and live health status of both services (fetch both /healthz on load). ESLint + prettier configured.
docker-compose.yml: three services (auth on :8001, game on :8000, client dev server on :5173) with hot reload, SQLite files on a mounted ./data volume. Env vars for service URLs so the client knows where auth and game live (VITE_AUTH_URL, VITE_GAME_URL).
CI (GitHub Actions): one workflow that lints, typechecks, and tests both Python services and the client. Structure the test job with a database matrix placeholder (sqlite now; postgres to be added later per §6.4).
Structured JSON logging middleware in both services: every request logs method, path, status, duration, and a generated request id (also returned as X-Request-Id).

Acceptance criteria:

docker-compose up → visiting :5173 shows both services healthy.
pytest passes in both services (write at least a healthz test each).
CI workflow file is valid and all steps would pass locally via a make ci (provide the Makefile).

Out of scope: auth logic, any DB tables, any game endpoints.

