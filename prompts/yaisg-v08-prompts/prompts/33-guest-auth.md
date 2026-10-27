## Prompt 33 — Guest accounts

**ID:** `33-guest-auth` · **Workstream:** P · **Needs:** 32 · **Design:** §20.1, §23.2 (guest purge) · **Vision:** V§12.1

### Build

1. **Auth service**: `users.kind` (`guest` | `full`), nullable email and password. `POST /auth/guest` returns the usual tokens with a `kind` claim; rate-limited per IP by the existing limiter. `POST /auth/upgrade {email, password}` turns the same user into a full account (id unchanged; existing email and password rules).
2. **Game service** records `kind` from the token claim and the player's last activity.
3. **Guest purge** (daily, both services, same `auth.guest_ttl_days`, *default* 14): auth deletes inactive guest users; the game deletes their players, characters and isolated realm instances (the latter exist after 34; write the purge to handle them).

### Tests

Guest token claims; upgrade keeps the id and character; duplicate email on upgrade; purge removes only inactive guests on both sides; rate limit.

