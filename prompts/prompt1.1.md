Implement the auth service per §2, §5.7, and §6.1 of the attached design doc. The game service is untouched in this prompt.

Requirements:

Tables via Alembic migration: users(id, email UNIQUE, password_hash, created_at, status) and refresh_tokens(id, user_id FK, token_hash, expires_at, revoked_at NULL). UTC timezone-aware timestamps; integer or UUID PKs — pick UUIDs and use them consistently across the project.
Endpoints:
POST /auth/register {email, password} → 201, creates user (argon2 password hashing via argon2-cffi), auto-logs-in (same response shape as login). Reject duplicate email with the standard error envelope ({"error": {"code": "EMAIL_TAKEN", ...}}, §5).
POST /auth/login {email, password} → sets an httpOnly, SameSite=Lax refresh_token cookie (30-day expiry, rotating) and returns {access_token, expires_in} in the body. Access token: RS256 JWT, 15-minute expiry, claims: sub (user id), iat, exp, iss="yaisg-auth".
POST /auth/refresh → reads cookie, validates against stored hash + expiry + not revoked, rotates it (revoke old, issue new), returns a fresh access token. Reuse of a revoked token revokes the whole user's token family and returns 401.
POST /auth/logout → revokes current refresh token, clears cookie.
GET /.well-known/jwks.json → public key(s) in JWKS format.
RSA keypair: generated at first boot if absent, loaded from AUTH_KEYS_DIR; document key rotation as a manual procedure in docs/auth.md (implementation of rotation itself not required).
Basic per-IP rate limiting on register/login (e.g., 5/min) using an in-process limiter.
Password policy: minimum 10 characters; return WEAK_PASSWORD code otherwise. Nothing fancier.

Tests (pytest + httpx): register→login→refresh→logout happy path; duplicate email; wrong password; expired access token rejected by a sample verifier; refresh rotation; refresh reuse triggers family revocation; JWKS endpoint validates issued tokens.

Out of scope: email verification, password reset, OAuth, account deletion.
