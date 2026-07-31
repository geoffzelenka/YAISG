Prompt 3.2 — Skilling API: active action endpoints + persistence

Expose the engine over HTTP per §4.3, §5.3, and §8.2. Engine from Prompt 3.1 is complete and must not be modified except to fix bugs its tests missed (note any such fixes in phase notes).

Requirements:

Migrations: active_actions(character_id PK, action_id, started_at, last_resolved_at, meta JSON) and reward_log(id, character_id, action_id, cycles, xp JSON, items JSON, resolved_at) (§6.2).
A resolve_character(session, character_id, now) service function: loads state, runs engine resolve, persists state deltas + a reward_log row (only when cycles > 0), all within the caller's transaction. Per §8.2, acquire the character's active-action row with a write intent first so concurrent resolves serialize (use SELECT ... FOR UPDATE guarded by dialect — on SQLite rely on the writer lock; structure the code so the Postgres path is a one-line difference).
Wire lazy resolution into existing reads per §4.2's rule: GET /characters/me, GET /characters/me/inventory now resolve first.
Endpoints (§5.3):
GET /characters/me/actions/available — grouped by skill; every action the character's realm allows, annotated {startable: bool, blocked_by: [error codes]} so the client can show locked entries. Combat group returns empty in this phase.
POST /characters/me/action {action_id} — resolve current action if any, validate via engine can_start, replace atomically, return {action_id, cycle_ms (effective), started_at}.
GET /characters/me/action — resolve, then return {active: {...} | null, since_last: ResolveResult-shaped rewards, stop_reason}. This response is the client's reward feed.
DELETE /characters/me/action — resolve then clear; returns final since_last.
RNG: seed per resolve call from secrets (§8.1); wrap in the engine's rng interface.
Server clock only: now = datetime.now(UTC) injected at the route layer (single utility, easy to freeze in tests).

Tests (integration, httpx + test DB): start→poll→poll→stop happy path with a fake clock advancing between calls, asserting xp/inventory/reward_log line up with engine expectations; switching actions mid-cycle resolves the old one; offline catch-up (jump clock 20h, one poll → capped rewards + stop_reason); available reflects level/realm gating; two concurrent polls produce no double rewards (run against SQLite; add the Postgres service to the CI matrix now per §6.4 and make this test meaningful there).

