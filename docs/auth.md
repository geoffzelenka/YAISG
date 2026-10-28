# Auth service operations

The auth service issues 15-minute RS256 access tokens and publishes its public key
at `/.well-known/jwks.json`. Refresh tokens are opaque, rotate on every refresh,
and are stored only as SHA-256 hashes. The browser cookie is HTTP-only,
`SameSite=Lax`, scoped to `/auth`. Full-account refresh sessions last 30 days;
guest sessions have the shorter cap described below.

Set `AUTH_KEYS_DIR` to persistent, access-controlled storage. On first signing-key use the
service creates `private.pem` (mode `0600`) and `public.pem` there. Set
`AUTH_COOKIE_SECURE=true` for an HTTPS deployment; local Compose leaves it false
so browsers can use the cookie over localhost HTTP.

When the service runs behind a reverse proxy, set `AUTH_TRUSTED_PROXY_IPS` to a
comma-separated list of proxy addresses. `X-Forwarded-For` is honored only when
the immediate peer is in this allowlist; otherwise rate limiting uses the socket
peer address. The limiter normalizes IP literals (including equivalent IPv6
spellings) and walks the forwarded list from right to left while hops remain
trusted, selecting the rightmost untrusted hop. An unparsable nonempty hop stops
the walk and becomes the limiter key; an empty hop stops it with a fallback to
the socket peer. If every hop is trusted, the socket peer is used. Configure the
proxy to replace untrusted forwarding headers.

## Guest accounts and upgrades

`POST /auth/guest` takes no credentials and creates an active guest identity,
returning HTTP 201 with an access token and the normal rotating refresh cookie.
It shares the credential endpoint IP limiter. Access tokens carry a `kind`
claim of `guest` or `full`; both have the same 15-minute lifetime. The game
verifier requires `kind` and rejects missing or other kind values. Opaque
refresh tokens are not JWTs; their current user's kind determines the access
token issued on refresh.

`POST /auth/upgrade` requires a valid, unexpired bearer access token plus JSON
`email` and `password`. It verifies signature and issuer, locks the user row,
and requires an active guest. Invalid identity returns `UNAUTHORIZED` (401);
an already full account returns `ACCOUNT_ALREADY_FULL` (409). Passwords need at
least ten characters (`WEAK_PASSWORD`, 422) and have a 1,024-character request
limit. Email is normalized and validated; an invalid email returns
`INVALID_EMAIL` (422), and an existing email returns `EMAIL_TAKEN` (409).
This endpoint also shares the credential IP limiter. The UUID is preserved,
credentials are attached in place, and a new full access/refresh session is
issued. It does not require the caller's refresh cookie.

After upgrade, the client **must call `GET /players/me` with the new token**
before retrying departure. This promotes the game-owned player to `full`;
upgrading auth alone does not synchronously update the game database. The
existing client retains a pending promotion confirmation so it can retry that
read if necessary, and refreshes an expired access token once before retrying
an upgrade.

## Guest retention and activity

Both services load `content/auth.json`: `auth.guest_ttl_days` is currently **14**
and `auth.activity_write_interval_minutes` is **60** (these are content settings,
not environment variables). Each service independently deletes guests whose
last activity, or creation time if absent, is older than the TTL. Auth deletes
refresh sessions and identities; game cleanup disposes of guest-owned state,
handles market custody and estates, and removes isolated tutorial realms.
Full accounts are excluded. Each purge rechecks eligibility under locks and
uses a PostgreSQL transaction advisory lock to exclude overlapping workers.

Auth runs its purge at startup and every 24 hours; the game's scheduler runs it
daily. Game activity writes are throttled to the configured interval, with
promotion from guest to full written immediately. Auth stamps activity whenever
it issues a session, including refresh; game reads do not directly update auth
activity. Keep both services on the same auth content settings.

Every newly issued guest refresh token and cookie has a lifetime of
`min(30 days, guest_ttl_days)`, currently 14 days. Rotation renews from issuance;
this is a per-session lifetime cap, not a fixed deadline since guest creation.

## Manual key rotation

Rotation requires a brief maintenance window because the service publishes one
active key and previously issued access tokens will no longer verify.

1. Stop the auth service and retain a protected backup of the current key files.
2. Remove `private.pem` and `public.pem` from `AUTH_KEYS_DIR`.
3. Start the auth service and request `/.well-known/jwks.json`. This lazily
   generates a new RSA pair and derives a new `kid`.
4. Confirm the new key appears at `/.well-known/jwks.json`, then refresh or restart
   JWT verifiers so they do not retain the old JWKS until their normal cache TTL.
5. Require clients to refresh or log in again. Existing access tokens expire in at
   most 15 minutes, while refresh tokens remain valid and issue tokens signed by
   the new key.
6. After verification, securely destroy the backup according to the deployment's
   secret-retention policy.

Never replace only one of the PEM files. The private key is authoritative and the
public file is an operational artifact generated alongside it.
