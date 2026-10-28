# CLAUDE.md

Guidance for Claude Code when working in this repository.

YAISG (Yet Another Idle Skilling Game) is a multiplayer idle skilling game under
active development. It is a monorepo of two FastAPI services and a React client.

## How Claude is used here

Claude works in two primary roles in this repo. Pick the one that matches the task.

### Code reviewer

Reviews changes for correctness, security, and maintainability. It **critiques
only — it never writes or edits files.**

- Invoke the `code-reviewer` subagent, or switch to the `reviewer` output style
  (`.claude/output-styles/reviewer.md`) for a review-only session.
- Every finding must cite `file:line`, explain why it matters, and include a
  concrete fix suggestion — but leave applying the fix to the author.
- Flag missing tests, unclear naming, and violations of the conventions in
  `AGENTS.md` and this file.

### Debugger

Investigates and diagnoses reported issues — reproduce, isolate root cause, then
propose the minimal fix.

- Invoke the `debugger` subagent for a focused diagnosis.
- Reproduce first: write or run a failing test or command that demonstrates the
  bug before theorizing about causes.
- Trace to the actual root cause rather than patching the symptom; explain the
  causal chain from trigger to observed failure.
- Keep the fix minimal and covered by a test that fails before it and passes after.

### Orchestrator
Manages coding agent and debugging agent and orchestrates communication between the two.

- Invoke a Codex coding agent via `codex exec --sandbox workspace-write --json < $prompt`
- Run verification and tests
- Invoke a Claude in reviewer role to review coding agent output
- Resume a Codex coding agent session via `codex exec resume <SESSION_ID> "Address review findings"`
- The Claude reviewer should be invoked no more than 3 times.  If a agreement between the reviewer and coding agents has not been met, then stop and wait for human intervention.


## Architecture

Three deployable pieces, coordinated by `docker-compose.yml`:

| Piece | Path | Stack | Local URL |
| --- | --- | --- | --- |
| Auth API | `services/auth/` | FastAPI, SQLite or PostgreSQL 16, Alembic | `http://localhost:8001` |
| Game API | `services/game/` | FastAPI, SQLite or PostgreSQL 16, Alembic | `http://localhost:8000` |
| Client | `client/` | React, Vite, TypeScript, Tailwind | `http://localhost:5173` |

- The **auth service** issues RS256 JWTs and serves a JWKS endpoint. The game
  service verifies tokens against that JWKS. Each service owns its own database
  and Alembic migration chain — they never share tables.
- The **game service** is layered: `app/api/` (routers) → `app/services/`
  (orchestration) → `app/engine/` (pure action resolvers and game math) and
  `app/models/` (SQLAlchemy). Keep `app/engine/` pure and deterministic — it is
  the most heavily tested part and must stay easy to reason about.
- Game content (including skills, realms, economy, combat, and tutorial) lives
  as validated, versioned JSON in `content/`, loaded via `app/content/loader.py`.
  It is deliberately synthetic placeholder scaffolding — not final game data.

Design and phase context: `design/design.md`, `docs/`.

## Commands

Run all CI checks (Ruff format + lint, strict mypy, pytest, then client
lint/format/typecheck/test/build, script checks, content lint, and seed-check)
from the repo root:

```bash
make ci
```

Per-piece targets: `make auth-ci`, `make game-ci`, `make client-ci`, `make scripts-ci`.

Run a single Python service's tests directly (venv activated):

```bash
cd services/game                              # or services/auth
python -m pytest
python -m pytest tests/test_engine.py           # game service only
```

Client tests: `cd client && npm test`.

Full stack for manual testing: `docker compose up --build` (see `README.md` for
running without Docker, and the env vars in the README's Configuration table).

## Conventions

`AGENTS.md` holds the full coding standards — read it. Highlights:

- Python 3.12+, PEP 8, type hints on public APIs, modern generics (`list[str]`).
- Priorities in order: correctness, readability, simplicity, then performance.
- Prefer the standard library; **a human must approve any new dependency.**
- When you change behavior, update or add tests in the same change.
- Before considering work done: formatted, lint clean, mypy clean, tests pass,
  no debug or commented-out code, no unused imports.

## Repo layout

```text
services/auth/   Auth service (users, refresh tokens, JWKS) + its database
services/game/   Game API: routers, services, pure engine, models, content loader
content/         Validated placeholder content packs + generated XP curve
client/          React auth/tutorial, skills/travel, realm/estate/markets, equipment/combat, keys UI
design/          Technical design document
scripts/         Database reset, XP-curve generation, and load tooling
docs/            Phase notes, auth operations, tech debt, and v0.8 conformance
```
