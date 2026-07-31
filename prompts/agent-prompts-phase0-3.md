# Coding Agent Prompts — Phases 0–3

Companion to `idle-skilling-game-design.md` (v0.3). Run prompts **in order**; each assumes all previous prompts are complete and their acceptance criteria pass. Every prompt should be given to the agent along with the full design doc as attached context.

**Conventions used in every prompt:**
- "Design doc" = `idle-skilling-game-design.md`. Section references (§) point into it.
- Definition of done for *every* prompt: code compiles/lints clean (ruff + mypy for Python, tsc + eslint for TS), all new and existing tests pass, `docker-compose up` yields a working stack, and a short `docs/phase-notes/<prompt-id>.md` summarizes what was built and any deviations.
- The agent must not build anything listed in §10 (non-goals) and must not invent game content beyond the placeholder pack.

---

## Prompt 0.1 — Repository skeleton and dev stack

You are implementing Phase 0 of the attached design document for a multiplayer idle skilling game. Build the project skeleton only — no game logic.

**Create:**

1. The monorepo layout exactly as specified in §3.1: `services/auth`, `services/game`, `content/`, `client/`, `docs/`.
2. `services/auth` and `services/game`: FastAPI apps with only a `GET /healthz` endpoint returning `{"status": "ok", "service": "<name>", "version": "<git sha or 'dev'>"}`. Each service has its own `pyproject.toml` (Python 3.12), with ruff, mypy, pytest, httpx configured. Shared lint/type settings; strict mypy.
3. `services/game`: SQLAlchemy 2.x + Alembic wired up with an empty baseline migration. Database URL from env var `GAME_DATABASE_URL`, defaulting to a SQLite file at `./data/game.db` with WAL mode enabled on connect. Same pattern for auth with `AUTH_DATABASE_URL`.
4. `client/`: Vite + React 18 + TypeScript + Tailwind. Render a single page showing the app name and live health status of both services (fetch both `/healthz` on load). ESLint + prettier configured.
5. `docker-compose.yml`: three services (auth on :8001, game on :8000, client dev server on :5173) with hot reload, SQLite files on a mounted `./data` volume. Env vars for service URLs so the client knows where auth and game live (`VITE_AUTH_URL`, `VITE_GAME_URL`).
6. CI (GitHub Actions): one workflow that lints, typechecks, and tests both Python services and the client. Structure the test job with a database matrix placeholder (sqlite now; postgres to be added later per §6.4).
7. Structured JSON logging middleware in both services: every request logs method, path, status, duration, and a generated request id (also returned as `X-Request-Id`).

**Acceptance criteria:**
- `docker-compose up` → visiting :5173 shows both services healthy.
- `pytest` passes in both services (write at least a healthz test each).
- CI workflow file is valid and all steps would pass locally via a `make ci` (provide the Makefile).

**Out of scope:** auth logic, any DB tables, any game endpoints.

---

## Prompt 1.1 — Auth service: registration, login, JWT issuance

Implement the auth service per §2, §5.7, and §6.1 of the attached design doc. The game service is untouched in this prompt.

**Requirements:**

1. Tables via Alembic migration: `users(id, email UNIQUE, password_hash, created_at, status)` and `refresh_tokens(id, user_id FK, token_hash, expires_at, revoked_at NULL)`. UTC timezone-aware timestamps; integer or UUID PKs — pick UUIDs and use them consistently across the project.
2. Endpoints:
   - `POST /auth/register` `{email, password}` → 201, creates user (argon2 password hashing via `argon2-cffi`), auto-logs-in (same response shape as login). Reject duplicate email with the standard error envelope (`{"error": {"code": "EMAIL_TAKEN", ...}}`, §5).
   - `POST /auth/login` `{email, password}` → sets an httpOnly, SameSite=Lax `refresh_token` cookie (30-day expiry, rotating) and returns `{access_token, expires_in}` in the body. Access token: **RS256 JWT, 15-minute expiry**, claims: `sub` (user id), `iat`, `exp`, `iss="yaisg-auth"`.
   - `POST /auth/refresh` → reads cookie, validates against stored hash + expiry + not revoked, **rotates** it (revoke old, issue new), returns a fresh access token. Reuse of a revoked token revokes the whole user's token family and returns 401.
   - `POST /auth/logout` → revokes current refresh token, clears cookie.
   - `GET /.well-known/jwks.json` → public key(s) in JWKS format.
3. RSA keypair: generated at first boot if absent, loaded from `AUTH_KEYS_DIR`; document key rotation as a manual procedure in `docs/auth.md` (implementation of rotation itself not required).
4. Basic per-IP rate limiting on register/login (e.g., 5/min) using an in-process limiter.
5. Password policy: minimum 10 characters; return `WEAK_PASSWORD` code otherwise. Nothing fancier.

**Tests (pytest + httpx):** register→login→refresh→logout happy path; duplicate email; wrong password; expired access token rejected by a sample verifier; refresh rotation; refresh reuse triggers family revocation; JWKS endpoint validates issued tokens.

**Out of scope:** email verification, password reset, OAuth, account deletion.

---

## Prompt 1.2 — Game API auth middleware + client auth flow

Wire authentication end-to-end per §3 and §5.7. Auth service from Prompt 1.1 is complete.

**Game service requirements:**

1. JWT verification middleware/dependency: fetch + cache JWKS from the auth service (`AUTH_JWKS_URL` env var, cache with TTL and refetch on unknown-kid), verify RS256 signature, `iss`, `exp`. Reject with 401 + error envelope on any failure. Apply to all routes except `/healthz`.
2. Alembic migration for `players(id, auth_user_id UNIQUE, created_at)` (§6.2).
3. Auto-provisioning: a dependency that maps the verified `sub` claim to a `players` row, creating it on first authenticated request. Expose `GET /players/me` returning the player row (temporary endpoint; character profile replaces its role in Phase 2).
4. Uniform error envelope helper used by all future endpoints.

**Client requirements:**

5. Auth screens: register and login forms (email/password), calling the auth service with `credentials: 'include'` so the refresh cookie works cross-port in dev (configure CORS on both services accordingly: allow the client origin, allow credentials).
6. Token handling: access token kept in memory only. An API layer wrapper attaches `Authorization: Bearer`, and on 401 transparently calls `/auth/refresh` once and retries; if refresh fails, route to login. Silent refresh on app load (try refresh before showing login).
7. Authenticated shell: after login, show a placeholder authenticated layout (sidebar skeleton per §9.1 with static section labels, all panels "coming soon") and a logout button. Use React Router; unauthenticated users are redirected to login.
8. Set up TanStack Query as the only server-state mechanism (§9.2); `GET /players/me` displayed somewhere in the shell as proof of end-to-end auth.

**Tests:** game-service middleware unit tests (valid, expired, bad-issuer, bad-signature tokens — mint test tokens with a test keypair); auto-provisioning idempotency; a client-side test (vitest) for the retry-on-401 wrapper.

**Acceptance criteria:** full flow in the browser — register, land in shell, hard-refresh stays logged in via silent refresh, logout returns to login; `players` row created exactly once.

---

## Prompt 2.1 — Content pipeline and placeholder pack

Implement the content system per §1.1 (pillar 2), §5.1, and §6.3. This is server-side only plus a small client cache.

**Requirements:**

1. Pydantic schemas (in `services/game/app/content/`) for content files: skills (with nested actions), items, realms, estate upgrades, realm projects, and an XP curve. Follow the shapes implied by §6.3 and §7, with these engine-facing fields required:
   - Action: `id`, `name`, `skill_id`, `level_required`, `cycle_ms`, `inputs: [{item_id, qty}]`, `xp`, `drops: [{item_id, qty: [min,max], chance}]`, `realm_tags: [str]`.
   - Item: `id`, `name`, `stack_limit` (use a large default), `tags`.
   - Realm: `id`, `name`, `tags: [str]`, `modifiers: [{type, value}]` (types per §7), `market_offers` (leave schema minimal: `{item_id, buy_price, sell_price}`), `project` (contribution targets + tier modifier sets).
   - Estate upgrade: `id`, `name`, `cost: [{item_id, qty}]`, `modifiers` and/or `cap_bonuses: [{cap, value}]` (§7.1), `realm_tags`.
   - Caps config: base values for `offline_hours` (12), `inventory_slots`, `market_listings`, `estate_upgrade_slots`.
2. Loader: reads all JSON under `/content` at startup, validates, cross-checks referential integrity (every `item_id`/`skill_id`/tag reference must resolve; duplicate ids are fatal), computes a manifest `{version: <hash of canonical content>, packs: {...hashes}}`, and exposes an immutable in-memory `ContentIndex` with typed lookup helpers (`action(id)`, `actions_for_skill(skill_id)`, `item(id)`, etc.). Startup fails loudly on invalid content.
3. Endpoints (§5.1): `GET /content/manifest` and `GET /content/{pack}` for packs `skills`, `items`, `realms`, `upgrades`, `caps`. Drop rates are included (§5.1 decision). Strong ETags from pack hashes; support `If-None-Match` → 304.
4. **Placeholder content pack** in `/content` (this is scaffolding, not game design — keep it obviously fake):
   - 4 skills: gathering, refining, crafting, combat-monsters (combat content shape only; not used until Phase 6). Exploration: none (§10).
   - Gathering: 3 actions at levels 1/10/25, no inputs. Refining: 2 actions consuming gathering outputs. Crafting: 2 actions consuming refining outputs. This creates a real dependency chain for testing.
   - ~10 items covering the chain; one currency-adjacent junk item.
   - 2 realms ("Verdant Vale", "Ashen Reach") with different tags so at least one gathering action is exclusive to each, and small distinct modifiers (e.g., ±10% cycle time on one skill).
   - 2 estate upgrades (one grants `xp_pct`, one grants `offline_hours` cap bonus) and 1 realm project per realm with a tier-1 modifier.
   - XP curve: standard exponential table to level 99 generated by a checked-in script; document the formula.
5. Client: fetch manifest on app load; if version differs from the cached one, fetch packs and store in localStorage keyed by version. Provide a typed `useContent()` hook. No UI beyond wiring.

**Tests:** loader accepts the placeholder pack; rejects (parameterized) broken fixtures — unknown item ref, duplicate id, bad modifier type, missing cap; ETag/304 behavior; manifest hash changes when content changes.

---

## Prompt 2.2 — Character creation and profile

Implement §5.2 (minus inventory display polish) on top of the content system.

**Server requirements:**

1. Migrations for `characters`, `character_skills`, `currency` (gold + premium columns, premium untouched), `estates`, `inventories` per §6.2 — including the estate-table shape with its own UUID PK and `upgrade_slots`.
2. `POST /characters` `{name, realm_id}`:
   - Validate: player has no character (v1 one-character rule, §6.2), name 3–20 chars alphanumeric + spaces, globally unique (case-insensitive), realm exists in content.
   - Create character, one `character_skills` row per content skill at level 1 / 0 XP, currency row (starting gold from a config constant), and an estate in the chosen realm at level 1 with base `estate_upgrade_slots` from caps config.
   - Error codes: `CHARACTER_EXISTS`, `NAME_TAKEN`, `INVALID_NAME`, `UNKNOWN_REALM`.
3. `GET /characters/me` — profile: character, skills (xp, level, xp-to-next from the curve), gold, realm summary (id, name, tags, active modifiers), estate summary (level, slots, installed upgrades — empty for now). Returns 404 `NO_CHARACTER` if none, which the client uses to route to creation.
4. `GET /characters/me/inventory` — item stacks with quantities (empty for now).
5. Level derivation: single engine function `level_for_xp(xp, curve)`; `character_skills.level` is a cached value always written through this function. Property test: monotonic, consistent with the table.

**Client requirements:**

6. Post-login routing: no character → character creation screen (name field + realm picker rendering realm names, tags, and modifiers from content); has character → main shell.
7. Profile panel (first real sidebar section, §9.1): character name, realm info, gold, and a skill list with level + XP progress bars computed from server-provided xp-to-next.
8. Sidebar: sections from §9.1 with dividers; Profile is live; all others remain "coming soon"; Exploration rendered disabled.

**Tests:** creation happy path; each error code; one-character enforcement under concurrent double-submit (two simultaneous requests → exactly one character); profile math for xp-to-next.

---

## Prompt 3.1 — Engine core: lazy resolution loop (test-first)

Implement the pure engine at the heart of the game, per §4 and §7. **No API endpoints, no SQLAlchemy imports in `engine/` — pure functions + dataclasses only.** Write tests before implementation where practical; this prompt is judged primarily on its test suite.

**Engine API to implement (in `services/game/app/engine/`):**

1. Value types: `CharacterState` (skills xp/levels, inventory as dict, gold, realm id, installed upgrades, caps), `ActiveAction` (action id, started_at, last_resolved_at), `ResolveResult` (cycles completed, xp gained per skill, items consumed, items gained, level-ups, stop_reason: None | 'inputs_exhausted' | 'offline_cap' | 'inventory_full').
2. `effective_cycle_time(action, state, content) -> int` and `effective_xp(...)`, `effective_drops(...)`: apply modifier stacking per §7 — sum all `cycle_time_pct`/`xp_pct`/`extra_drop_chance_pct` from realm + realm tier + installed (non-inert) estate upgrades, additive within type, applied once. Inert upgrade rule per §7 (realm_tags mismatch → contributes nothing).
3. `resolve(state, active, content, now, rng) -> (state', active', ResolveResult)` implementing §4.2 exactly:
   - Full cycles only; preserve partial-cycle remainder in `last_resolved_at`.
   - Cap cycles by: remaining offline budget (from `offline_hours` cap, measured against elapsed since `last_resolved_at`), input availability, and inventory capacity (`inventory_slots` cap counts distinct stacks; overflow rule per §7.1 v1: drops beyond capacity are discarded and recorded in the result as `overflowed_items` — consuming inputs may free slots, account for ordering per cycle).
   - Consume inputs and roll drops per cycle via the injected `rng` (interface: `rng.random() -> float`, `rng.randint(a,b)`); grant xp; recompute levels; if a level-up occurs, recompute effective values **from the next cycle onward** (segmented resolution per §4.2's note — implement the segmented version, not the snapshot simplification, since we're doing it test-first anyway).
   - A `stop_reason` other than None means the action ends; `active'` is None.
4. `can_start(action_id, state, content) -> Ok | ErrorCode` checking level, realm tags, and inputs for at least one cycle (`INSUFFICIENT_LEVEL`, `WRONG_REALM`, `MISSING_INPUTS`).
5. `resolve_caps(state, content) -> Caps` — base caps + `cap_bonuses` from installed upgrades and realm tier (§7.1).

**Required tests (pytest + hypothesis):**
- Exact-cycle and partial-cycle timestamp math (property: repeated resolve with increasing `now` is equivalent to one big resolve — idempotence/associativity from §8.4).
- Offline cap: 13h elapsed with 12h cap → exactly 12h of cycles, correct stop_reason, and `last_resolved_at` advanced only by resolved cycles.
- Input exhaustion mid-batch; inventory overflow with the discard rule; interaction of the two.
- Level-up mid-batch changes subsequent cycle output (construct content where level affects an effective value via a level-gated modifier or verify xp accrual boundary behavior — at minimum, verify segmentation produces different results than naive whole-batch math in a crafted case).
- Modifier stacking: additive within type, multiple sources, inert-upgrade exclusion.
- Drop statistics: with a seeded RNG over 10k cycles, observed drop frequency within tolerance of `chance`.
- Conservation property: for input-consuming actions, `consumed inputs per recipe × cycles` exact.

**Out of scope:** persistence, HTTP, combat cycle logic (framework must not preclude it — the per-cycle reward step should be a strategy function so Phase 6 can swap in a combat resolver).

---

## Prompt 3.2 — Skilling API: active action endpoints + persistence

Expose the engine over HTTP per §4.3, §5.3, and §8.2. Engine from Prompt 3.1 is complete and must not be modified except to fix bugs its tests missed (note any such fixes in phase notes).

**Requirements:**

1. Migrations: `active_actions(character_id PK, action_id, started_at, last_resolved_at, meta JSON)` and `reward_log(id, character_id, action_id, cycles, xp JSON, items JSON, resolved_at)` (§6.2).
2. A `resolve_character(session, character_id, now)` service function: loads state, runs engine `resolve`, persists state deltas + a `reward_log` row (only when cycles > 0), all within the caller's transaction. Per §8.2, acquire the character's active-action row with a write intent first so concurrent resolves serialize (use `SELECT ... FOR UPDATE` guarded by dialect — on SQLite rely on the writer lock; structure the code so the Postgres path is a one-line difference).
3. Wire lazy resolution into existing reads per §4.2's rule: `GET /characters/me`, `GET /characters/me/inventory` now resolve first.
4. Endpoints (§5.3):
   - `GET /characters/me/actions/available` — grouped by skill; every action the character's realm allows, annotated `{startable: bool, blocked_by: [error codes]}` so the client can show locked entries. Combat group returns empty in this phase.
   - `POST /characters/me/action` `{action_id}` — resolve current action if any, validate via engine `can_start`, replace atomically, return `{action_id, cycle_ms (effective), started_at}`.
   - `GET /characters/me/action` — resolve, then return `{active: {...} | null, since_last: ResolveResult-shaped rewards, stop_reason}`. This response is the client's reward feed.
   - `DELETE /characters/me/action` — resolve then clear; returns final `since_last`.
5. RNG: seed per resolve call from `secrets` (§8.1); wrap in the engine's rng interface.
6. Server clock only: `now = datetime.now(UTC)` injected at the route layer (single utility, easy to freeze in tests).

**Tests (integration, httpx + test DB):** start→poll→poll→stop happy path with a fake clock advancing between calls, asserting xp/inventory/reward_log line up with engine expectations; switching actions mid-cycle resolves the old one; offline catch-up (jump clock 20h, one poll → capped rewards + stop_reason); `available` reflects level/realm gating; two concurrent polls produce no double rewards (run against SQLite; add the Postgres service to the CI matrix now per §6.4 and make this test meaningful there).

---

## Prompt 3.3 — Client: skill panels and the global action strip

Implement the skilling UI per §9. Server from Prompt 3.2 is complete.

**Requirements:**

1. Skill sections (Gathering, Refining, Crafting) become live routes. Each lists its actions from `GET /characters/me/actions/available` + content: name, level requirement, inputs, outputs (drop items + rates — exposed per design), effective cycle time. Locked actions render with their `blocked_by` reason. A Start button per startable action.
2. Global **active-action strip** (§9.1) visible on every route: current action name + icon placeholder, an animated progress bar, and a stop button. Progress animates client-side from `started_at` and effective `cycle_ms` (single 4-times-per-second interval store — zustand — driving all timers; no per-component intervals).
3. Polling: TanStack Query refetches `GET /characters/me/action` aligned to cycle boundaries with ±10% jitter, plus on window refocus and on network reconnect. On response: merge rewards into a **reward feed** (toast stack + a scrollback list in the strip's expandable drawer), and invalidate profile/inventory queries only when the response shows changes.
4. Offline catch-up UX: when a response's `since_last` spans many cycles (threshold: > 5), show a "Welcome back" summary modal (cycles, xp per skill, items, and stop_reason if capped) instead of toast spam.
5. Inventory panel: add a simple inventory grid to the Profile section (item name, quantity) fed by the inventory endpoint; shows stack count vs `inventory_slots` cap.
6. Stop reasons: when the server reports the action ended (`inputs_exhausted`, `offline_cap`, `inventory_full`), clear the strip and surface the reason in the feed.
7. Keep §9.2's rules: no client-computed rewards displayed as authoritative; the progress bar is explicitly cosmetic (if a poll reveals the server has less/more progress, snap to server truth).

**Tests (vitest + testing-library):** action list renders locked/unlocked states from fixture data; strip progress math from `started_at`; welcome-back modal triggers on large `since_last`; poll scheduling honors cycle boundaries (fake timers).

**Acceptance criteria (manual, in browser):** create character → start a gathering action → watch two cycles complete with reward toasts → start a refining action that consumes the gathered items → stop it → close the tab for a few minutes → reopen → welcome-back summary shows offline gains; profile XP bars and inventory reflect everything.

---

## Suggested prompt-to-agent packaging

For each run, provide: (1) the design doc, (2) this file's single relevant prompt, (3) the current repo state. After each prompt, review the phase notes and diff before proceeding — Prompt 3.1's test suite in particular deserves human review, since every later phase trusts the engine's math.
