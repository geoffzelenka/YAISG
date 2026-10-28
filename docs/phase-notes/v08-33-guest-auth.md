## Built

- Auth users support guest/full kind and nullable credentials. POST /auth/guest
  uses the existing per-IP credential limiter and normal access/refresh cookies.
  Bearer-authenticated POST /auth/upgrade validates the existing email/password
  rules and promotes the same user. Refresh always signs the current stored kind.
- Access tokens include kind. Game rejects missing/invalid kind claims, records
  coarse activity through the injected server clock, and promotes existing players
  without replacing characters. Older guest tokens cannot demote full players.
- Strict, frozen, extra-forbidden private content/auth.json owns guest_ttl_days
  (14) and activity_write_interval_minutes (60). The latter must be positive and
  at most 1/24 of the TTL. Both services validate the same independently loaded
  pack; Compose mounts it read-only into both APIs. Game hashes the private pack.
  Auth guest refresh lifetimes and cookie Max-Age are capped at the TTL; rotation
  records activity. Purge eligibility in both services depends on inactivity alone.
- Game identity lookup begins with a plain read. Only provisioning, guest-to-full
  promotion, or a coarse activity interval elapsed acquires SQLite write intent
  and a player row lock, reloads, writes and commits. Recent GETs do not write.
- Added independent migrations 0003_guests and v08_0020_guests. Game project/vote
  initiators may be null after deletion, preserving shared runs and ballots.
- Daily purge drivers use PostgreSQL advisory locks and log failures. Each guest
  is deleted inside its own savepoint: failure rolls back that guest's holders
  and audits, logs its identity and continues with later guests. All candidate
  character locks still precede sorted realm, estate and order locks. Kind and
  inactivity are rechecked under lock; SQLite acquires write intent for the job.
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
  test_game_purge_only_inactive_guests;
  test_guest_purge_audits_every_holder_and_isolated_realms;
  test_guest_purge_rollback_restores_holders_and_audits;
  test_postgres_purge_rechecks_concurrent_activity;
  test_guest_purge_job_rolls_back_and_logs;
  test_guest_purge_preserves_foreign_isolated_references.
  Extended scheduler cadence and generated world conservation tests.

- Review round 1 adds auth tests: test_real_guest_purge_uses_inactivity_ttl;
  test_guest_refresh_rotation_counts_as_activity_and_caps_expiry;
  test_full_account_upgrade_cannot_replace_credentials;
  test_upgrade_rejects_invalid_bearer (missing, non-Bearer, expired, tampered);
  test_upgrade_rate_limit; test_auth_content_directory_error_is_clear;
  test_bad_auth_guest_does_not_block_another_purge;
  test_auth_activity_interval_must_be_well_under_ttl.
- Review round 1 adds game tests: test_real_guest_game_purge_uses_inactivity_ttl;
  test_game_activity_writes_only_after_content_interval;
  test_full_token_promotion_prevents_guest_purge;
  test_bad_guest_does_not_block_another_purge;
  test_game_activity_interval_must_be_well_under_ttl. The every-holder regression
  includes an isolated key with neither holder nor listing, explicitly checking
  its removal and signed sink. Existing holder and gold conservation assertions
  remain intact and account for that additional physical instance.

- Review round 1 repository-virtualenv SQLite make ci passed: auth 35 with one
  dialect-specific skip; game 818 with 27 dialect-specific skips; client 100.
  Ruff, format, strict mypy, ESLint, Prettier, TypeScript, Vitest, production
  build, script checks and warning-only content lint passed. Migration regressions
  cover both independent chains, fresh upgrades, schema parity and resets.
  A separate disposable SQLite make db-reset, both head upgrades and both
  Alembic schema checks also passed. git diff --check is clean.

## Removed

- Review round 1 removes the live-session purge exemption, its JWT claim and
  player column (including migration parts), and the obsolete
  test_guest_activity_does_not_shorten_live_session regression as explicitly
  directed by the upheld review ruling. No routes removed. Existing token test
  issuers include kind so missing-claim authentication can be rejected.

## Design ambiguities resolved

- §20.1: upgrade authenticates the current guest with its verified bearer token,
  consults the locked database kind, and returns a fresh normal session. Existing
  refresh sessions also observe full kind on their next rotation.
- §20.1 / §13: abandonment keeps shared fixed estates under realm ownership,
  with no surrender payout. Mobile and isolated estates disappear. All destroyed
  holdings are explicit signed sinks, never silent FK cascades. Shared project
  and ballot history remains with nullable initiators and contribution identities.
- §23.2 / §3: game reuses its existing APScheduler. Auth uses one standard-library
  thread lifespan driver at daily cadence, since APScheduler is a game-service
  dependency. Its transaction runner has the same advisory-lock, rollback and
  logging behavior without adding an auth dependency.

## Deviations

- §23.1: provisioning, promotion and coarse activity updates commit at the
  existing player-provisioning dependency boundary before gameplay, releasing
  the player lock before
  character locking. Recent identity reads do not acquire write intent or commit.
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
  both return the normal access token and refresh cookie. Immediately after a
  successful upgrade, the client must call /players/me with the returned/refreshed
  token so game observes full kind before departure. Subsequent /auth/refresh
  also carries full kind. Preserve the same player/character cache identities;
  /players/me exposes the stored kind.
- 36-hardening: retain both purge contention regressions, per-guest savepoints,
  atomic sink auditing, coarse activity-write checks and generated guest_purge
  coverage. Purge currently locks all realms conservatively (N7); narrowing that
  set is explicitly deferred until complete provenance and market/estate/isolation
  dependency coverage can preserve lock ordering. Audit the existing trusted-proxy
  X-Forwarded-For leftmost-hop selection (N5); this limiter change is also explicitly
  deferred. Ensure auth deployments mount the shared content pack and exercise
  auth TEST_DATABASE_URL fixtures alongside the game matrix.

## New error codes

- ACCOUNT_ALREADY_FULL (409): upgrade was requested for an account that already
  has credentials.
- UNAUTHORIZED (401) is now also used by auth upgrade for missing, invalid or
  inactive bearer identities. Reused EMAIL_TAKEN, INVALID_EMAIL, WEAK_PASSWORD,
  RATE_LIMITED and existing request-validation envelopes.

## Orchestrator verification and review hand-offs

- Verified:
  - SQLite `make ci`: auth 35, game 818 passed / 27 skipped, client 100.
  - PostgreSQL: game 844 passed / 1 skipped; auth 36 passed.
  - Fresh PostgreSQL upgrade and `alembic check` are clean for both services. Boot 200.
- Round 1: CHANGES_REQUESTED, three blocking findings, all fixed in 18cc6df together with N1–N4:
  - B1: a 30-day session guard made the TTL inert.
  - B2: every GET took write intent.
  - B3: the upgrade guards were untested.
- Round 2 (Sonnet): APPROVE. B2 and B3 were mutation-checked.
- Hand-offs:
  - 36: rightmost-untrusted XFF hop; the purge's all-realm lock.
  - 35: call /players/me right after an upgrade. Without that call, an upgraded player can still be purged as a guest.
