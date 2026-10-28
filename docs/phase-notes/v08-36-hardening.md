## Built

- Database-shared mutation allowances on all game mutation routers, including
  creation, both action aliases, equipment, projects, votes and tutorial departure.
  GAME_MUTATION_LIMIT (120) and GAME_MUTATION_WINDOW_SECONDS (60) are positive
  operational environment settings. Authenticated attempts count across routes
  and worker processes, including failed validation/business intents. Reads do
  not count. Atomic dialect upserts and a separate committed allowance prevent
  racing requests or game rollbacks from refunding attempts. Stale account rows
  reset in place; requests never prune other accounts. Refusals include Retry-After.
- Added migration v08_0022_operations and transactional metric_deltas. Operator
  GET /admin/metrics returns JSON counters for ticks, cumulative tick duration
  in nanoseconds, matches, seller tax, realm trades, caravan dispatches and whole
  goods lost on the road, realm tags shed, regression starts and persisted key
  discoveries. Minted gold comes from mint ledger deltas; holder gauges include
  wallets, treasuries, order escrow and gold in slots. Counters survive holder
  and history deletion and roll back with failed transactions. Ordinary reads
  never expose balances. Operator allowlist UUIDs are parsed at boot. Pending
  metric rows are cached in session.info with constant-time per-counter lookup;
  flushed or rolled-back rows are replaced rather than reused.
- FastAPI game handlers and synchronous player provisioning/database dependencies
  now run in the worker pool, preserving async JWT/JWKS handling. Direct-handler
  contention tests call their new synchronous interface without changing their
  locks or assertions. Added a test that observes resolution off the asyncio
  thread. Retained pure combat bounds, deterministic RNG and all conservation,
  SQL batching, private-instance and custody checks.
- Trusted proxy traversal now selects the rightmost untrusted forwarded hop,
  walking past allowlisted proxies; an arbitrary client prefix cannot rotate
  the auth limiter key. Trusted entries, peers and forwarded IP literals use
  ipaddress normalization so equivalent IPv6 spellings share trust and buckets.
  Malformed hops stop traversal as untrusted; malformed trusted entries fail
  configuration validation. Guest purge retains its all-realm lock for the correctness
  reasons below. SQL realm-lock ordering uses C collation on PostgreSQL/BINARY
  on SQLite to agree with Python sorting independently of deployment locale.
- A failing session advisory unlock invalidates the pooled connection and logs
  the cleanup error without masking an existing job failure. Added independent
  spawned-process scheduler overlap/exclusion/release testing and SQLite
  cross-process replay coverage. Existing expiry/purge transaction locks remain.
- make ci and the game workflow matrix now run fatal make seed-check; workflows
  also run scripts-ci. Added the auth/PostgreSQL matrix entry and matching auth
  migration verification, preserving the shared content mount already in Compose.
- Added scripts/load_pipeline.py using existing httpx and asyncio. It reports
  status totals, failures, throughput and p50/p95 latency; nonzero failures cause
  a nonzero exit. Each worker polls, reads a realm, inserts a sell order, cancels
  and collects it. Tokens come from YAISG_LOAD_TOKENS and are never printed.
  README documents disposable data, configuration, operator metrics and usage.
- Baseline command from the repository root:
  `PATH=$PWD/.venv/bin:$PATH bash -c 'cd services/game && python -m pytest -s -q tests/test_load_baseline.py'`.
  The baseline invokes the same load function against
  real ASGI routes with temporary SQLite/WAL, real verified JWTs, an empty book,
  synthetic market access and 100 stocked goods. Four workers share one character;
  five rounds each perform 100 HTTP requests. Measured result: 2.881 seconds,
  34.71 requests/s, p50 76.79 ms, p95 180.16 ms, 80 HTTP 200 and 20 HTTP 201,
  zero failures. Environment: Linux sandbox, Python 3.13.5 repository virtualenv,
  httpx ASGI transport, no TCP server or lifespan scheduler. This is a local
  contention baseline, not production capacity. In this sandbox asyncio's
  cross-thread completion did not wake its loop; local checks used an external
  /tmp sitecustomize timer
  shim via PYTHONPATH=/tmp/yaisg-asyncio-wakeup. No shim ships in the repository.
- Low-risk hand-offs completed: guest upgrade refreshes an expired access token
  once before retrying and still confirms /players/me after promotion; realm
  errors reuse shared ApiError; listing cancellation says owner-only; belt
  healing thresholds validate finite 0 < value <= 100 on submission (including
  tiny positive fractions), show an inline alert/aria-invalid when rejected, and
  clear that error after correction. Corrected the tutorial concurrency docstring and
  wrapped the earlier tutorial note. Existing upgrade retry/query refresh and
  key-combat identity behavior remain covered.
- Added named tests in test_hardening.py:
  test_rate_limit_shared_across_mutations_reads_free_and_window_resets;
  test_metrics_operator_only_and_tick_counters;
  test_tick_and_trade_metrics_idempotent_and_rollback;
  test_postgres_scheduler_advisory_lock_two_processes;
  test_rate_limit_concurrent_sessions_and_character_isolation;
  test_market_matches_and_tax_counters;
  test_caravan_shipment_and_loss_counters;
  test_decay_shed_and_regression_counters;
  test_discovery_counter_survives_key_destruction;
  test_key_invalidation_first_cutoff_wins;
  test_character_resolution_runs_off_event_loop;
  test_seed_check_is_a_fatal_ci_step;
  test_sqlite_scheduler_two_process_replay;
  test_scheduler_failed_unlock_invalidates_connection_and_preserves_error;
  test_operator_configuration_parses_uuid_and_rejects_invalid_ids;
  test_scheduler_realm_lock_order_matches_python_sorting.
  Added test_mixed_load_baseline and auth
  test_forwarded_chain_uses_rightmost_untrusted_hop. Client additions:
  "refreshes an expired guest token once before upgrading and confirming game
  promotion" and "validates healing trigger %s at submit even without native
  form validation" (seven boundaries). Catch-up tests retain their original
  gameplay query budgets and independently require one telemetry INSERT batch.


- Validation after review round 1: repository-virtualenv make ci passes on
  SQLite with the external sandbox wake-up shim described above: auth 39 passed /
  1 skipped, game 850 passed / 33 skipped, client 122 passed. Ruff formatting/lint,
  strict types, script checks, client build, fatal thirty-day seed-check and
  git diff --check pass. Focused hardening tests pass (17 passed / 3 skipped);
  auth limiter cases pass (6 cases), and equipment UI cases pass (15 cases).
  The market dependency mutation check fails as intended. Original disposable
  SQLite reset/migration/schema comparison and boot smoke checks remain valid;
  this review introduces no migration changes. Generated conservation retains
  both operation coverage sets.


- Review round 1 fixes: removed the request-path cross-account DELETE that
  deadlocked on PostgreSQL when stale accounts held their own upsert locks.
  No pruning job is introduced: one allowance row per seen account is retained
  and reset on its next mutation. Added
  test_postgres_stale_rate_windows_do_not_deadlock (2 and 4 accounts), with a
  post-upsert barrier that holds all own-row locks before requests proceed, so
  restoring the DELETE recreates the lock cycle deterministically.
- Added test_all_mutation_routes_include_limiter_and_reads_use_method_gate. It
  walks app.routes (effective contexts on lazy-router FastAPI versions), checks
  every mutation alias's dependency tree and verifies that limited GETs return
  before touching the database. An in-memory mutation removing the market order
  route's limiter is rejected with "Mutation route lacks limiter: /market/orders".
- Added test_metric_cache_preserves_flush_and_rollback_boundaries, including a
  nested savepoint rollback; auth
  test_ipv6_proxy_and_client_spellings_share_allowance (two trusted spellings)
  and test_malformed_forwarded_hop_stops_trusted_proxy_traversal; client
  "clears the inline threshold error when a healing trigger is corrected".
  The existing seven threshold boundaries now assert inline validation too.
  Load script help and README explain the 3 mutations per worker round, default
  120 attempts per account per minute, and shared-token budgeting.

## Removed

- No routes, gameplay, dependencies or tests removed. Removed synchronous game
  work from the event loop and raw-string operator identity comparison.

## Design ambiguities resolved

- §23.5: limits are operational environment configuration, rather than gameplay
  content. A fixed UTC window is shared across all mutation routes. Its key is
  the verified auth UUID because one account owns at most one character, and it
  also protects creation. Window boundaries permit adjacent-window bursts.
- §23.6: counters are durable transaction deltas, rather than per-worker memory.
  Matches/tax include commodity fills and key sales; losses are dispatch road
  loss, excluding later spoilage/cap loss; discoveries count persisted keys;
  regressions count starts. Duration measures completed realm catch-up batches,
  including loading/persistence, and is cumulative rather than a histogram.
- §23.1 / §23.3, Prompt 33 hand-off: retain guest purge's all-realm serialization.
  Cleanup follows references through orders, sold/listed keys, discoverer
  provenance, estates/history/replacements and isolated realms/shipments. A
  location-only lock set would omit those dependencies and could invert lock
  ordering against trading or transitions. There is no complete dependency-lock
  protocol to replace it safely in this prompt. Character-first ordering,
  per-guest savepoints and existing purge contention tests remain authoritative.
- §23.6 / §12.5: no ballot choices are counted or logged. README explicitly
  requires production SQL statement/parameter logging to stay disabled;
  application engine echo is already disabled. No ballot model change is needed.

## Deviations

- §23.1: operational rate bookkeeping commits in a short transaction before
  gameplay, rather than rolling back with a rejected intent. Otherwise invalid
  requests could evade the limit by refunding their own attempts. Gameplay
  state and its lock ordering remain atomic in the existing transaction, as
  before; identity provisioning already has an independent commit boundary.
- Python/httpx load generation and plain JSON metrics follow the explicit human
  rulings. Conservative gear/buff lint bounds are unchanged.

## Ratification needed

- None introduced. Earlier combat regeneration and commodity self-matching
  questions remain unchanged; no hardening behavior depends on a new ruling.

## Hand-offs

- 37-conformance: verify preserved holder conservation, generated-operation
  coverage, tutorial ownership/once-only grants, market lock contention and
  request-driven lazy advancement. No history watermark or pruning was added.
- Deferred 01 hostname-alias db-reset guard: resolving arbitrary PostgreSQL host
  aliases requires deployment/DNS policy; existing destructive target guard is
  unchanged. This does not affect rate limits, metrics or the scheduler.
- Deferred 02 selector indexing: current synthetic packs do not establish a
  bottleneck. Preserve (reference_price, id) ordering if indexing larger packs.
- Deferred 07/20/21/23/24/33 lock narrowing, including travel/map, market reads,
  personal kickoff availability, caravans, lifecycle and purge: retain global
  correctness until a complete replacement lock/dependency protocol exists.
  Locale-independent ordering is fixed here. Evaluate lifecycle/history indexes
  only with representative volumes; current no-query-per-tick bounds remain.
- Deferred 09 active-tag helper consolidation and 18 shared mint-value helper /
  remaining local-import hoisting: independent refactors of tested projections,
  outside operational behavior. UUID normalization is completed here.
- Deferred 22 batched map health projection and server below_reserve flag: needs
  an API/client projection change and scale evidence; remote visibility and
  balance privacy remain unchanged.
- Deferred 23 bounded MARKET_RETRY resubmission: automatic retries need an
  idempotency policy. Explicit fresh client requests remain the existing contract.
- 26/27 exponential gear/buff enumeration retains the conservative bound as
  instructed. Deferred 28 style-specific combat lint loadouts and public content
  projection interface: these require coordinated schema/content/lint changes
  and are separate from runtime hardening.
- Deferred 30 client polish: explicit unequip/return-in-combat and idle/active
  poll mutation tests need expanded UI mocks; fractional HP label formatting,
  met/unmet requirements with current levels, doll role/group, belt legends and
  encounter-log initial filtering/stable keys are independent presentation
  work. The submit guard and seven HP threshold boundary tests are completed.
- Deferred 31/32 transition-history pruning/reparse optimization: needs a safe
  timestamp watermark for historical action/discovery windows. Added the missing
  first-cutoff-wins test; historical cutoffs remain intact.
- Deferred 32 transition-due purchase commit-before-error: changes rollback/error
  semantics; retain explicit refresh then retry. Invalid-inventory cancellation's
  harmless success remains. Sparse-filter scan caps need a cursor/API rule to
  avoid losing matches. A complete durable sale ledger is separate schema work;
  new operational match/tax deltas already survive relisting and deletion.
- Deferred 35 per-key/per-listing error placement: needs independently scoped
  mutation state and UI fixtures. Friendly lifecycle labels and content realm
  names are presentation changes; unbound-key, confirmed destruction and fully
  paid kickoff UI tests need expanded panel fixtures. guestSession API splitting
  is a separate call-site refactor; expired-token refresh is fixed without
  changing the existing session/confirmation contract. Cancellation now
  explicitly labels the owner restriction without exposing seller identity.
- 37-conformance: metric_deltas roll-up remains required operational follow-up.
  Deltas are append-only; roll-up/compaction must atomically preserve durable
  totals and transaction semantics. Never prune raw deltas without rolling them
  into durable totals.
- 37-conformance: if abandoned account allowance rows need retention pruning,
  use an independent maintenance transaction and a bounded FOR UPDATE SKIP LOCKED
  selection on PostgreSQL before deletion, with concurrency tests against live
  mutations. Never restore cross-account cleanup to the mutation request path.
  There is no new pruning job in this phase.

## New error codes

- RATE_LIMITED (429), reused for game mutation exhaustion; Retry-After gives the
  remaining fixed-window seconds. OPERATOR_REQUIRED remains the operator gate.
- No new dependencies.
