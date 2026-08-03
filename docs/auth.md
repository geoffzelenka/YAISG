# Auth service operations

The auth service issues 15-minute RS256 access tokens and publishes its public key
at `/.well-known/jwks.json`. Refresh tokens are opaque, rotate on every refresh,
and are stored only as SHA-256 hashes. The browser cookie is HTTP-only,
`SameSite=Lax`, scoped to `/auth`, and expires after 30 days.

Set `AUTH_KEYS_DIR` to persistent, access-controlled storage. On first boot the
service creates `private.pem` (mode `0600`) and `public.pem` there. Set
`AUTH_COOKIE_SECURE=true` for an HTTPS deployment; local Compose leaves it false
so browsers can use the cookie over localhost HTTP.

When the service runs behind a reverse proxy, set `AUTH_TRUSTED_PROXY_IPS` to a
comma-separated list of proxy addresses. `X-Forwarded-For` is honored only when
the immediate peer is in this allowlist; otherwise rate limiting uses the socket
peer address. Configure the proxy to replace, rather than append to, untrusted
forwarding headers.

## Manual key rotation

Rotation requires a brief maintenance window because the service publishes one
active key and previously issued access tokens will no longer verify.

1. Stop the auth service and retain a protected backup of the current key files.
2. Remove `private.pem` and `public.pem` from `AUTH_KEYS_DIR`.
3. Start the auth service. It generates a new RSA pair and derives a new `kid`.
4. Confirm the new key appears at `/.well-known/jwks.json`, then refresh or restart
   JWT verifiers so they do not retain the old JWKS until their normal cache TTL.
5. Require clients to refresh or log in again. Existing access tokens expire in at
   most 15 minutes, while refresh tokens remain valid and issue tokens signed by
   the new key.
6. After verification, securely destroy the backup according to the deployment's
   secret-retention policy.

Never replace only one of the PEM files. The private key is authoritative and the
public file is an operational artifact generated alongside it.
