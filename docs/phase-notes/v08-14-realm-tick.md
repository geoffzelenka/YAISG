## Built

- Filled ordered steps 1–7 and 10: estate production into realm stores,
  larder-first upkeep, proportional estate sharing above reserve, realm upkeep
  below reserve, surplus project payments before erosion, spoilage, line and
  warehouse cap loss, and final derived demand lines. No gold moves.
- All estates with tick profiles participate regardless of ownership. Inert
  forms produce nothing. Forms with neither production nor upkeep are skipped.
  Stage scaling remains a 1.0 hook for Prompt 15. Existing isolation exemptions
  remain inside the relevant steps rather than bypassing the tick loop.
- Extended RealmTickContext with stores, estates, larders, active tags, derived
  lines, estate shortfalls and realm due/unmet amounts. Load once before
  catch-up; aggregate production and persist each holding once after catch-up.
  Line replacement runs once. No step queries or flushes inside the tick loop.
- Reused the run loaded by exact-event finalization. Zero-tick resolution skips
  context construction and the tick flush. Builds started during catch-up finish
  at their exact due timestamp, including between the final tick and now.
- Extracted apply_project_payment from the request contribution adapter so tick
  payments share progress, idle reset, immutable credits and build-start rules
  without issuing per-tick database calls. Required costs use run snapshots.
- Added an APScheduler lifespan driver at the content tick cadence, with
  coalescing, one executing job per process and clean shutdown. A session
  advisory lock excludes competing PostgreSQL drivers; SQLite uses its single
  process deployment and writer transaction. Jobs visit sorted, non-isolated
  realm ids; ordinary requests retain lazy resolution.
- Added dependency apscheduler>=3.10,<4, explicitly required by this prompt and
  design §23.2. The human approved it on 2026-10-27; APScheduler 3.11.3 is
  installed for Round 1 verification. The world-seeding lifespan test now
  exercises real scheduler startup and shutdown.
- Added test_golden_reserve_estates_first_then_realm,
  test_estates_share_shortfall_pro_rata,
  test_production_realm_owned_player_owned_and_inert,
  test_spoilage_stores_and_larders_and_most_plentiful_cap,
  test_pro_rata_conservation (deterministic Hypothesis),
  test_resolve_tick_split_idempotence,
  test_scheduler_no_players_and_repeat,
  test_postgres_two_scheduler_instances,
  test_scheduler_cadence_and_lifecycle, and
  test_realm_overlay_completes_without_player_contributions.
  The PostgreSQL contention test uses two independent scheduled driver calls,
  bounded thread synchronization, and asserts production is credited once.
- Tightened test_realm_catchup_statement_bound to exactly nine statements for
  both two ticks and max_catchup (eleven for paying realms), with a persistent
  node line to keep final write shapes comparable. Added explicit failed status and exact failed_at checks.

- Validation: full SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passes: auth 15,
  game 375 with 11 skips, client 41. Formatting, lint, strict typing, client
  build, scripts and content lint pass. Existing migration/reset tests rebuild
  both services, upgrade to head, check schema parity and exercise downgrade.
  `git diff --check` is clean.

- Round 1: added a resolver-driven multi-tick golden, hourly Hypothesis split /
  idempotence / per-step payment conservation with fractional daily rates,
  geometric overlay and reserve-boundary regressions, fractional spoilage,
  warehouse cap, isolated scheduler filtering, failed-realm continuation and
  final-now build completion tests. Both tag acquisition paths share the
  session-free duplicate-guarded builder. The scheduler holds a session advisory
  lock across the pass but commits each realm separately, logs the realm id on
  failure and continues. The golden kills all four reported tick-order swaps;
  the hourly property kills constant tick_index. Separate mutation checks kill
  spoilage ceiling, missing warehouse cap, missing isolation filter and missing
  overlay spreading. SQL-count coverage now includes paying realms;
  RealmContribution rows grow with ticks × paid items even though their inserts
  are batched. Dependency approval: human, 2026-10-27 (APScheduler 3.11.3).
  Round 1 full SQLite `make ci` passes: auth 15, game 387 with 10 skips,
  client 41; formatting, lint, typing, builds, scripts and content lint pass.

## Removed

- Replaced the production, upkeep, spoilage, caps and line-recomputation stubs.
  Removed the redundant active-run load and zero-tick flush. No tests deleted
  or weakened; no routes, schema columns or content fields removed.

## Design ambiguities resolved

- §14.1 / §14.5: use the absolute UTC tick index for cumulative daily-rate
  rounding, so split resolution has the same rounding phase as catch-up.
- §14.5 step 3: allocate scarce milli-units by largest remainder, breaking ties
  by the preloaded estate-id order. Larder payments reduce each estate's claim
  before sharing. Selector payments use reference-price then item-id order.
- §14.5 steps 6–7: floor spoilage losses in milli-units using exact fractions
  of authored percentages. Remove cap excess in descending initial quantity,
  breaking ties by item id; unmatched items use warehouse_cap.
- §3 / §14.5 and Prompt 10 hand-off: share apply_project_payment with contribute
  rather than calling the session-owning adapter in every tick. This preserves
  payment semantics while satisfying the binding 10a batching hand-off.

## Deviations

- Prompt 14 completion-time test: the no-player-help completion scenario uses
  one tick per day and a one-day overlay. The general hourly completion-time
  promise cannot follow from the specified remaining-cost formula; see below.

## Ratification needed

- §14.4 / V§9.4.6: should the overlay use a fixed amortization rate or retain
  remaining_requirement / realm_completion_days? The explicit formula was
  implemented. With T ticks/day and D completion days, remaining cost follows
  approximately R_next = R * (1 - 1/(T*D)); at D days about 37% remains, rather
  than zero. Integer rounding can also leave a small remainder receiving no
  payment until idle erosion resumes. General completion in about D days needs
  a different formula or a completion rule. No such rule was invented.
  For D > 1, int(remaining / D) reaches zero once remaining < D milli-units:
  realm payments stop, the idle clock stops resetting, and erosion resumes.
  On the overlay alone the project cycles and never completes. Round 1 pins
  the present geometric behavior at the default hourly cadence.

## Hand-offs

- 15-decay: consume context.realm_due, context.realm_unmet and context.owed
  during steps 8–9; shortfalls reset each tick. Supply production_factor stage
  scaling, update active tags and derived lines after decay, and preload any
  additional state outside the loop. Preserve no-query steps, exact build
  timestamps, D4 stamps, isolation exemptions and cosmetic Strained behavior.
- 16-realm-pricing: add budgets and treasury-band work to step 10. The current
  replacement intentionally retains zero budgets and never exposes treasury.
- 18-mint-gold: extend step 4 with mint demand/consumption/coinage and the gold
  ledger. Consumption helpers currently operate in ordinary item milli-units;
  add value-measured weighting for bullion and cap accounting with its demand.
- 20-caravans: fill step 0 using preloaded arrivals before production; keep
  isolated realms excluded and avoid queries inside catch-up.
- 36-hardening: extend the existing lifespan scheduler for other scheduled jobs;
  retain advisory exclusion and request-driven lazy resolution.

## New error codes

None.
