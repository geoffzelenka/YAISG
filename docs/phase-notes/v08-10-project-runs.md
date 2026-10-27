## Built

- Added `realm_project_runs`, immutable `realm_contributions` with nullable realm
  contributor identities, `characters.last_kickoff_at`, and the tag-to-run FK.
  Migration `v08_0005_projects` supports upgrade, downgrade and fresh rebuild;
  a partial unique index independently enforces one active attempt per realm.
- Added kickoff and contribution endpoints. Kickoff checks the specified gates
  in order, atomically plans all selector payments, consumes goods, and moves
  gold into the realm treasury. The rolling 24-hour limit is character-wide.
  Visitors can contribute; every accepted call consumes goods, records its
  actual payment and resets the idle timestamp. Fully funded attempts build.
- Added `resolve_realm` behind the existing sorted realm-lock adapters, including
  character resolution with or without an action. Due votes (stub), builds and
  transitions finalize in time order before ticks. Completed tags carry the
  exact build due time and run identity, even after a long absence. Equal-time
  events use vote, build, transition order. The event queue is recomputed after
  each event so a future vote hook can schedule an already-due transition.
- Added content-owned `economy.project` and `economy.tick` settings, integer
  milli-unit progress, pure cumulative-rounded erosion arithmetic, failure and
  cooldown. Tick catch-up preserves the unprocessed timestamp backlog. Named
  steps 0–10 follow §14.5; only step 5 erosion operates in this phase.
- Realm detail/list responses include the active attempt, cost-line snapshots,
  progress, status, idle flag and build timing. Tag detail returns the kickoff
  identity, total consumed goods per character, and the realm's own share.
  Treasury balances remain private. Client economy types and content fixtures
  include the added settings; project controls remain with Prompt 21.
- Untouched known non-isolated realm templates receive conflict-safe initialization
  under sorted locks. This supports projects after travel into a realm where
  nobody has created a character, before Prompt 13 introduces world seeding.
- Picked up 00/02/09 hand-offs: reused selector payment, retained lock order and
  caller transaction ownership, linked tag acquisition to project attempts,
  and restored run-scoped contribution logs and public credits.
- Tests added in `services/game/tests/test_projects.py`:
  `test_kickoff_codes_in_order` (nine gates), `test_project_offering_rules`
  (three independent reasons), `test_kickoff_selector_payment_and_gold_conservation`,
  `test_daily_kickoff_limit_across_realms`,
  `test_contribute_presence_clamping_and_credits`,
  `test_build_exact_due_time_before_ticks_and_transition`,
  `test_erosion_failure_cooldown_and_reset`,
  `test_resolve_realm_idempotence_and_bounded_catchup`,
  `test_erosion_rounding_conserves_daily_rate` (Hypothesis),
  `test_postgres_two_kickoffs_one_active_run`,
  `test_contribution_clamping_conserves_items` (Hypothesis),
  `test_build_completes_at_exact_boundary`,
  `test_character_resolution_finishes_build_and_realm_credits`,
  `test_realm_resolution_split_equals_single` (Hypothesis),
  `test_project_reads_and_contribution_errors`, and
  `test_fractional_remainder_consumes_one_whole_player_good`.
  Fixtures honor `TEST_DATABASE_URL`; the kickoff contention test skips on SQLite
  and uses PostgreSQL blocking detection with bounded waits.
- SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passes: auth 15, game 292 with
  six database-specific skips, client 41. Ruff, formatting, strict mypy,
  TypeScript, eslint, Vitest, production build, scripts and content lint pass.
  Fresh disposable SQLite `make db-reset`, subsequent `alembic upgrade head`
  and `alembic check` pass. No dependencies added.

- Round 1: removed the isolated-realm tick-loop bypass; projects now erode and
  fail in tutorial instances, while caravan/upkeep/decay exemptions live inside
  their own steps and market/tax work remains a scoped hook. Made kickoff-code
  cases cumulative, based `stalled` on the authored idle grace, added typed tag
  credits with `UNKNOWN_REALM` handling, promoted `get_character` / `as_utc`, and
  blocked first-touch creation from isolated templates. Added
  `test_isolated_project_erodes_and_fails`,
  `test_stalled_uses_content_grace_and_resets`,
  `test_tag_credits_realm_errors_and_typed_response`, and
  `test_first_touch_never_instantiates_isolated_template` (both template kinds).
  Strengthened `test_kickoff_codes_in_order` and updated the existing read test
  for grace-period behavior. All eight adjacent gate-order mutations are caught.
  Round 1 SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passes: auth 15, game 297
  with six database-specific skips, client 41; all format, lint, type and build
  checks pass. No dependencies added.

## Removed

None. No existing tests were removed or weakened.

## Design ambiguities resolved

- §12.3 / §14.1: snapshot cost lines in authored order and store contributed
  progress as integer milli-units. Erosion uses cumulative flooring, so rounding
  each hourly share cannot erase daily erosion. A contribution resets both
  grace and the rounding sequence. Kickoff initializes the idle timestamp.
- §12.3 / §14.1: inventory payments are whole goods. A fractional remaining
  requirement needs one final whole good; clamp the withdrawal to the ceiling
  of that remainder and cap credited progress at the exact requirement. The
  consumed whole amount is recorded in credits, including its final fractional
  excess. Realm payments can supply exact milli-units. This avoids introducing
  fractional player inventory or preventing players from finishing eroded lines.
- §12.3 / §14.2: overlapping selectors choose the most specific matching line
  (item, tiered class, class), then authored order. A funded matching line rejects
  further payments. No inventory or project progress changes on rejected calls.
- §12.3 (Round 1 ruling): `stalled` means a funding attempt whose idle time is
  strictly greater than `economy.project.idle_grace_days`, so erosion applies.
  It is false during grace, at the exact boundary, and during building. Any
  accepted payment restarts grace. This follows the orchestrator's clarification
  of the idle-erosion table's public-label wording.
- §12.4: credits report summed quantities of goods consumed over the attempt,
  including contributions subsequently eroded; they are not surviving progress.
  Character UUIDs identify contributors; null identity is the separate realm
  share. A tag without a project-run link has empty credits and null kickoff.
- §12.1 / §14.5 / §20 (Round 1 correction): isolated realms run every ordered
  tick step, including ordinary project erosion and failure. Only caravan,
  upkeep, decay, market and tax work is exempted within the owning steps;
  isolation does not bypass the tick framework or the ordinary project engine.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 13-stores-lines: use funding run snapshots for the project overlay. Replace or
  integrate first-touch zero-treasury realm initialization with world seed data;
  seed each world realm before its first public resolve. Preserve `_lock_realm`'s
  guard: first touch must never create shared state for an isolated template;
  isolated realms are per-player instances created by the tutorial lifecycle.
- 14-realm-tick: fill steps 1–4, 6–7 and 10 in `services/realm_ticks.py` and add
  the scheduled driver. Step 5 must withdraw from stores above reserve, call
  `services.projects.contribute` with null character and milli-unit payment,
  then apply idle erosion. The contribution helper returns the consumed amount;
  the caller must withdraw it from stores in the same transaction. Handle build
  events created during tick catch-up at their exact due times. Keep every step
  running for isolated realms, with upkeep exemptions only inside steps 2–4 and
  market/tax exemptions scoped within step 10. Project erosion/failure is never
  skipped for isolation. Keep step order.
- 15-decay: fill steps 8–9; exempt isolated realms from upkeep/decay gauge work
  within these steps, never by skipping the tick loop. Preserve D4 stamps and
  exact transition completion through the realm resolver.
- 19-votes: implement `has_open_vote`, `vote_close_event` and `close_due_vote`.
  Close using the supplied due time, update vote status, and start transitions
  from that exact time. The resolver rechecks newly scheduled events before ticks.
  Enforce D6's reciprocal active-project gate when calling a vote.
- 20-caravans: fill step 0 arrivals before estate production and upkeep;
  preserve its isolated-realm caravan exemption.
- 34-tutorial: create isolated realms explicitly as owned per-player instances.
  `_lock_realm` first touch must never auto-create a `realm_state` row from an
  isolated template. Preserve its guard when adding instance lookup/lifecycle;
  tutorial projects and tags use the ordinary resolver, including idle erosion.
- 21-client-realm-estate: kickoff and contribution return a `ProjectRunResponse`;
  realm detail adds nullable `active_run`. Required lines are `{selector, quantity}`
  in authored order, and `contributed` is the parallel array in good units.
  Display credits from `/realms/{id}/tags/{tag_id}` and discover project ids from
  the current node's content. Client controls are intentionally not implemented.

## New error codes

- Kickoff: `NOT_PRESENT`, `RESIDENTS_ONLY`, `PROJECT_NOT_OFFERED`, `PROJECT_ACTIVE`,
  `REALM_VOTING`, `REALM_TRANSITIONING`, `PROJECT_COOLDOWN`, `KICKOFF_LIMIT`.
  Existing `MISSING_INPUTS` and `UNKNOWN_REALM` are reused.
- `PROJECT_NOT_FUNDING`: no funding attempt accepts the contribution.
- `PROJECT_ITEM_NOT_NEEDED`: item does not match a needed line, or that line
  is already funded.
- `UNKNOWN_REALM_TAG`: the realm does not currently hold the requested stack tag.
