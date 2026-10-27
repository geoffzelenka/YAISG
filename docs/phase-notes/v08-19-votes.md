## Built

- Added realm_votes aggregate ballots and realm_vote_eligibility snapshots, with
  migration v08_0010_votes, positive weight checks, bounded aggregate totals,
  valid statuses, and a partial unique index allowing one open vote per realm.
  No column records an individual choice.
- Added resident-only upgrade calls against the current node's authored edges.
  Required held tags, project/vote/transition exclusion, cooldown and fee are
  checked before payment. Fees transfer from the caller to the realm treasury
  immediately and remain there for either outcome. Presence is not required.
- Snapshots use active estate ownership and the existing pure vote_weight helper.
  Realm-owned and destroyed estates are excluded. Later arrivals are excluded;
  departing residents retain their original eligibility and weight. Active
  replacement estates participate even before lazy home-pointer repair.
- Added cast and read endpoints. Choices affect aggregate weights only;
  eligibility stores only weight and voted_at. Repeated casts fail. Public
  participation includes character id, weight and voted_at; aggregate totals
  are null while open and visible after close. No choice enters request logs,
  audit logs or reward feeds. The caller receives no automatic vote.
- Added strict economy.vote settings and public client content types/fixture:
  duration_hours and fail_cooldown_hours both default to and are authored as 72.
- Replaced all three Prompt 10 hooks: has_open_vote, vote_close_event and
  close_due_vote. Timed close uses the exact deadline before ticks; the final
  eligible cast closes immediately. Strictly greater yes weight passes; all
  other outcomes fail. Failure cooldown starts at the close timestamp. Passed
  ballots use start_transition with cause upgrade; existing reserve derivation
  and finalize_realm complete the lifecycle.
- Routes reuse character resolution and character → sorted realm → estate locks.
  PostgreSQL contention tests cover competing callers, repeat casts and distinct
  voters, using independent sessions, detected blocking and bounded waits.
- Extended fixed catch-up statement budgets by one open-vote lookup per realm
  resolution, independent of tick count; no per-tick database work was added.
- Added test_tie_abstention_and_no_votes_fail,
  test_weights_snapshot_excludes_arrivals_keeps_leavers,
  test_early_close_transition_and_finalize,
  test_fee_kept_cooldown_and_exact_deadline,
  test_vote_project_exclusion_both_ways,
  test_api_participation_secrecy_and_logs,
  test_postgres_concurrent_ballot_mutations,
  test_passed_vote_raises_reserves,
  test_snapshot_includes_unresolved_decay_replacement,
  test_call_gates_leave_wallet_untouched,
  test_late_resolution_closes_and_finalizes_at_due_times, and
  test_vote_cannot_replace_pending_decay_transition.
- Verification fix 1: resident test fixtures now use 20-character UUID hex
  prefixes for name and name_normalized, respecting PostgreSQL VARCHAR(20)
  without changing the schema.
- Re-ran SQLite PATH=$PWD/.venv/bin:$PATH make ci after the fixture fix: auth 15,
  game 487 with 17 database-specific skips, client 41. Lint, formatting, strict
  typing, migration/reset/schema checks, client build and content lint pass.

## Removed

- Replaced the open-vote and timed-close stubs. No routes, columns, content
  fields or existing tests removed.

## Design ambiguities resolved

- §12.5 / §22: GET vote returns the open or most recently called ballot, or null
  when none exists. This makes closed totals accessible without adding history
  endpoints. Status values are open, passed and failed; choice is yes or no.
- §12.5 / §14.5: an overdue vote fails at its closes_at timestamp, so cooldown
  starts there, following Prompt 10's binding exact-time hand-off. Early close
  starts cooldown or transition at the last cast's supplied server timestamp.
- §12.5 / §13.7: snapshot active owned estates rather than relying on every
  resident's home pointer already being repaired after decay. This includes
  all current residents while excluding destroyed estate tombstones.
- §12.5: required tags are held inherent/stack tags, regardless of temporary
  facility suspension, consistent with the explicit held-tag requirement.

## Deviations

None.

## Ratification needed

- §12.5 / §12.6 / §14.7: what happens when decay starts a regression while a
  ballot is open and that ballot later passes? Calls are allowed at any decay
  stage, and only pending transitions pause shedding; an open vote does not.
  The vote mandates an upgrade transition, but a regression transition may
  already be pending, or its completion may remove the original authored edge.
  Meanwhile the existing transition guard is preserved: the conflicting close
  raises and the transaction rolls back, without overwriting the regression or
  recording the final cast. A due conflicting ballot can therefore block realm
  resolution. The regression test confirms that rollback and guard. A human must
  choose cancellation, precedence or another rule; no such rule was invented.

## Hand-offs

- 21-client-realm-estate: consume the three vote endpoints. Discover upgrade
  ids from current-node development content. Open totals are null; participation
  remains public. A final cast may return a closed ballot. GET returns the latest
  closed ballot until another is called. No voting UI was added here.
- 31-keys: extend the existing transition start/finalization seams for key
  deprecation and invalidation; no key behavior belongs to this phase.
- 36-hardening: preserve body-free request logs for ballots and avoid recording
  choices in telemetry, request tracing, audit logs or reward feeds.

## New error codes

- UPGRADE_NOT_OFFERED: upgrade is absent from the current node.
- UPGRADE_TAGS_REQUIRED: realm lacks one or more required held tags.
- VOTE_COOLDOWN: failed-vote cooldown has not elapsed.
- NO_OPEN_VOTE: no currently open ballot accepts a cast.
- VOTE_INELIGIBLE: character is absent from the eligibility snapshot.
- ALREADY_VOTED: participation is already recorded; choices cannot be changed.
- All above use HTTP 409. Reused RESIDENTS_ONLY, PROJECT_ACTIVE, REALM_VOTING,
  REALM_TRANSITIONING, MISSING_INPUTS and UNKNOWN_REALM; malformed requests use
  the existing INVALID_REQUEST envelope. No dependencies added.
