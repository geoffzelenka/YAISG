Prompt 1.2 — Game API auth middleware + client auth flow

Wire authentication end-to-end per §3 and §5.7. Auth service from Prompt 1.1 is complete.

Game service requirements:

JWT verification middleware/dependency: fetch + cache JWKS from the auth service (AUTH_JWKS_URL env var, cache with TTL and refetch on unknown-kid), verify RS256 signature, iss, exp. Reject with 401 + error envelope on any failure. Apply to all routes except /healthz.
Alembic migration for players(id, auth_user_id UNIQUE, created_at) (§6.2).
Auto-provisioning: a dependency that maps the verified sub claim to a players row, creating it on first authenticated request. Expose GET /players/me returning the player row (temporary endpoint; character profile replaces its role in Phase 2).
Uniform error envelope helper used by all future endpoints.

Client requirements:

Auth screens: register and login forms (email/password), calling the auth service with credentials: 'include' so the refresh cookie works cross-port in dev (configure CORS on both services accordingly: allow the client origin, allow credentials).
Token handling: access token kept in memory only. An API layer wrapper attaches Authorization: Bearer, and on 401 transparently calls /auth/refresh once and retries; if refresh fails, route to login. Silent refresh on app load (try refresh before showing login).
Authenticated shell: after login, show a placeholder authenticated layout (sidebar skeleton per §9.1 with static section labels, all panels "coming soon") and a logout button. Use React Router; unauthenticated users are redirected to login.
Set up TanStack Query as the only server-state mechanism (§9.2); GET /players/me displayed somewhere in the shell as proof of end-to-end auth.

Tests: game-service middleware unit tests (valid, expired, bad-issuer, bad-signature tokens — mint test tokens with a test keypair); auto-provisioning idempotency; a client-side test (vitest) for the retry-on-401 wrapper.

Acceptance criteria: full flow in the browser — register, land in shell, hard-refresh stays logged in via silent refresh, logout returns to login; players row created exactly once.
