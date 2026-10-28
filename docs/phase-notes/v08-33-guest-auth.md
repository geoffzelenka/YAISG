## Built

- Auth users support guest/full kind and nullable credentials. POST /auth/guest
  uses the existing per-IP credential limiter and normal access/refresh cookies.
  Bearer-authenticated POST /auth/upgrade validates the existing email/password
  rules and promotes the same user. Refresh always signs the current stored kind.
- Access tokens include kind and a signed session_exp upper bound matching the
  refresh session lifetime. Game rejects missing/invalid kind claims, records
  activity through the injected server clock, promotes existing players without
  replacing their characters, and retains the longest observed session expiry.
  Older guest tokens cannot demote full players or shorten session protection.
- Added strict, frozen, extra-forbidden private content/auth.json with
  guest_ttl_days = 14. Both services read the same pack independently; Compose
  mounts content read-only into auth as well as game. No database tables are
  shared. The game content loader validates and hashes the private auth pack.
- Added independent migrations 0003_guests and v08_0020_guests. Game project/vote
  initiators may be null after deletion, preserving shared runs and ballots.
- Daily purge drivers use PostgreSQL advisory locks and log/roll back failures.
  Auth protects unexpired, unrevoked refresh sessions. Game protects the longest
  verified signed session expiry and rechecks kind/activity under locks. All
  candidate character locks precede sorted realm, estate and order locks;
  SQLite obtains write intent before authoritative reads.
- Purge explicitly disposes inventory, equipment, belt/utility, wallet, order
  escrow/slots, held/listed keys, mobile estates/larders, buffs and action state.
  Shared fixed estates become realm-owned with their upgrades and larders intact.
  Sold keys remain with buyers; discoverer names survive identity removal.
  Shared project contributions and initiators are anonymized; isolated projects,
  votes, tags, lines, stores, estates, shipments and realm instances are removed.
  Foreign isolated references cause atomic failure even on SQLite without FK
  enforcement. Historical market executions and audit records survive deletion.
- Every physical goods sink has a negative milli-item GoodsLedger entry with
  holder identity, character and time. Every gold sink has a negative GoldLedger
  guest_purge entry. Audits and deletions share one transaction. Generated world
  operations include guest_purge in both coverage sets, compare independent
  expected goods losses with durable audit totals, and retain the gold oracle.
- Auth lifecycle fixtures now honor TEST_DATABASE_URL; PostgreSQL contention
  regressions use independent sessions, observed pg_blocking_pids waits and
  bounded timeouts, and skip SQLite. Auth migration smoke tests use their own
  temporary SQLite database. No dependencies added.
- Added auth tests: test_guest_claims_upgrade_identity_and_refresh;
  test_guest_upgrade_duplicate_email_and_validation;
  test_guest_creation_rate_limit; test_auth_purge_only_inactive_guests;
  test_postgres_auth_purge_rechecks_concurrent_activity;
  test_auth_purge_job_rolls_back_and_logs;
  test_auth_guest_migration_schema_and_downgrade;
  test_auth_lifespan_purges_and_stops_worker.
- Added game tests: test_guest_claim_upgrade_preserves_player_and_character;
  test_untrusted_guest_kind_is_rejected;
  test_guest_activity_does_not_shorten_live_session;
  test_game_purge_only_inactive_guests;
  test_guest_purge_audits_every_holder_and_isolated_realms;
  test_guest_purge_rollback_restores_holders_and_audits;
  test_postgres_purge_rechecks_concurrent_activity;
  test_guest_purge_job_rolls_back_and_logs;
  test_guest_purge_preserves_foreign_isolated_references.
  Extended scheduler cadence and generated world conservation tests.

- Final repository-virtualenv SQLite make ci passed: auth 22 with one
  dialect-specific skip; game 812 with 27 dialect-specific skips; client 100.
  Ruff, formatting, strict mypy, ESLint, Prettier, TypeScript, Vitest, build,
  script checks and warning-only content lint passed. Disposable SQLite
  make db-reset, both head upgrades and schema checks, and both ASGI lifespan
  health checks passed; auth guest creation and game content manifest returned
  201 and 200 respectively. git diff --check is clean.

## Removed

- No routes, features or tests removed. Existing test token issuers now include
  kind so missing-claim authentication can be rejected rather than defaulted.

## Design ambiguities resolved

- §20.1: upgrade authenticates the current guest with its verified bearer token,
  consults the locked database kind, and returns a fresh normal session. Existing
  refresh sessions also observe full kind on their next rotation.
- §20.1: activity exactly at the TTL boundary survives until the next daily pass;
  both services require activity strictly older than the shared cutoff. A live
  session prevents purge even when its last recorded activity is older. Game
  conservatively retains signed refresh-session protection through session_exp;
  it cannot observe auth logout/revocation through its independent database.
- §20.1 / §13: abandonment keeps shared fixed estates under realm ownership,
  with no surrender payout. Mobile and isolated estates disappear. All destroyed
  holdings are explicit signed sinks, never silent FK cascades. Shared project
  and ballot history remains with nullable initiators and contribution identities.
- §23.2 / §3: game reuses its existing APScheduler. Auth uses one standard-library
  thread lifespan driver at daily cadence, since APScheduler is a game-service
  dependency. Its transaction runner has the same advisory-lock, rollback and
  logging behavior without adding an auth dependency.

## Deviations

- §23.1: activity metadata commits at the existing player-provisioning dependency
  boundary before the gameplay transaction. This records activity for failed
  gameplay requests and releases the player lock before character locking.
  Character/realm/estate/order mutations retain their existing transaction;
  every purge and its signed audits are atomic in one transaction.

## Ratification needed

None introduced. Earlier combat and commodity self-matching questions remain
unchanged; this prompt adds no rules for either.

## Hand-offs

- 34-tutorial: create isolated realms with owner_character_id. Purge already
  handles isolated stores/treasuries, estates, projects, votes, shipments, keys
  and listing custody. Departure needs its own tutorial_destroy gold cause;
  guest_purge audits must remain durable after ephemeral holders are deleted.
  Enforce isolation so foreign characters or market holders cannot reference
  tutorial instances; purge deliberately rejects inconsistent foreign references.
- 35-client-keys-tutorial: use POST /auth/guest and bearer POST /auth/upgrade;
  both return the normal access token and refresh cookie. After upgrade, install
  the returned token and refresh /players/me so game observes full kind before
  departure. Subsequent /auth/refresh also carries full kind. Preserve the same
  player/character cache identities; /players/me now exposes stored kind.
- 36-hardening: retain both purge contention regressions, active-session guards,
  atomic sink auditing and generated guest_purge coverage. Purge currently locks
  all realms conservatively; narrow that set only with complete provenance and
  market/estate/isolation dependency coverage and the existing lock ordering.
  Ensure auth deployments mount the shared content pack and exercise auth
  TEST_DATABASE_URL fixtures alongside the game matrix.

## New error codes

- ACCOUNT_ALREADY_FULL (409): upgrade was requested for an account that already
  has credentials.
- UNAUTHORIZED (401) is now also used by auth upgrade for missing, invalid or
  inactive bearer identities. Reused EMAIL_TAKEN, INVALID_EMAIL, WEAK_PASSWORD,
  RATE_LIMITED and existing request-validation envelopes.
