## Built

- Realm inspection supports selecting a world realm, node/type/tier, inherent
  and acquired tags with kickoff/contribution credits, decay stage, gauge days,
  below-reserve lines and arriving quantities. Map rows also display gauge
  days from the public snapshot. No raw treasury is displayed.
- Added project funding progress, stalled/build state, build countdown,
  selector-aware contribution controls and confirmed kickoff payments.
  Kickoff eligibility uses a new authenticated
  GET /realms/{id}/projects/availability read. It shares the existing mutation
  validation, including presence, residency, held tags, project/vote/transition
  exclusion, cooldowns, daily limit, RESERVE_SHORT and selector payment planning.
  Reads neither pay nor create attempts; ordinary lazy resolution still runs.
- Added authored upgrade requirements with held/missing tags, stock gates,
  confirmed fee payment, current/latest ballot, public participation and weights,
  confirmed immutable choices, vote countdown and closed totals. Open totals
  are hidden even if mistakenly populated in a client fixture. Server errors,
  including RESERVE_SHORT from vote calls and kickoff, remain visible.
- Estate panel adds mobility, stage/gauge, authored transform graph, larder
  holdings and per-line days of cover, confirmed irreversible deposits, build,
  buy, surrender and donation flows. Existing upgrade installation now confirms
  its consumed costs; transformation retains its confirmation.
- Build/buy confirmation names the mobile estate, larder and all installed
  upgrades lost under D8. Surrender names ownership/assets transferred and
  either the uncapped payout upper bound or zero-payout donation. Presence
  state and map travel links accompany estate/realm controls.
- Extended the private home-estate response with larder milli-unit holdings and
  a nullable uncapped surrender_value for fixed estates. Prices/payments are
  rechecked at execution. Existing mutations and lock order remain authoritative.
- Added typed development reads/mutations and invalidation of realm, estate,
  profile/inventory/action and map queries after successful changes. Countdown
  expiry refreshes realm state through the existing shared cosmetic clock.
- Added Vitest cases for kickoff unavailable reasons, stocked eligibility,
  open-vote secrecy/public participation, larder units and zero upkeep,
  build confirmation asset losses/cancellation, RESERVE_SHORT on both entry
  points, and the earlier Prompt 08 completed-edge arrival toast hand-off.
- Added test_kickoff_availability_reports_gates_without_payment and extended
  test_build_buy_surrender_and_larder to verify the private projection, uncapped
  value independent of treasury, actual capped payment and empty replacement
  larder. Database fixtures honor TEST_DATABASE_URL.
- Disposable SQLite db-reset and subsequent upgrade to head succeeded.
- SQLite PATH=$PWD/.venv/bin:$PATH make ci passes: auth 15, game 575
  with 18 database-specific skips, client 60. Formatting, lint, strict typing,
  production build, migration/reset tests, scripts and content lint pass.

- Review round 1: removed the treasury-derived surrender preview. Regression
  asserts the exposed value remains unchanged at treasury 3 while actual
  surrender conservation still holds. Audited the new response fields:
  larder comes from estate holdings, surrender_value from asset valuation,
  project availability from existing gates; none returns a treasury-derived
  amount. Existing treasury bands remain categorical health projections.
- Review round 1: replaced estate/realm navigation anchors with router Links.
  Estate travel passes its realm as a destination query parameter; MapPanel
  validates it against visible destinations through TravelForm before selecting.
  Purchases display form names, required response fields have no dead
  fallbacks, ProjectRun uses a top-level type import and Estate field order
  matches its response. Successful confirmed vote casts reset mutation state.
- Added estate-to-map preselection, invalid/current-destination rejection,
  upper-bound surrender/donation confirmation and successful vote reset client
  tests. Extended kickoff availability with a
  resolved empty-demand-line RESERVE_SHORT assertion and unchanged wallet,
  inventory and attempt count.

## Removed

- Removed the treasury-derived surrender_payout response field, replacing it
  with the uncapped surrender_value. Actual surrender payment is unchanged.
- No existing tests or gameplay features removed.

## Design ambiguities resolved

- §24 / §12.3: availability needs personal cooldown/payment state unavailable
  in the public realm projection. Added a private read that shares kickoff
  validation rather than guessing those reasons from public data.
- §24 / §13.6: larder cover is matching milli-units divided by 1,000 and daily
  upkeep, shown separately for each selector. The UI explains shared goods for
  overlapping selectors and that realm supplies/spoilage change actual cover.
  Zero daily upkeep displays “No upkeep”; this is not a simulated survival timer.
- §24 / §13.4–13.5 / §15.5: expose the uncapped estate surrender value,
  independent of treasury funding. Confirmation promises only “up to” that
  amount and explains that the realm pays less if its treasury cannot cover it,
  rechecked on surrender. A capped preview would disclose the raw treasury
  whenever funding falls below the estate value; it is not returned.
- §24 / §12.5: the realm projection does not expose vote_cooldown_until.
  The server remains authoritative for vote-call cooldowns; rejected calls
  display the existing VOTE_COOLDOWN message and code.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 22-client-realm-market: reuse typed demand-line selectors, milli-line-unit
  conventions, development mutation invalidation and presence presentation.
  Market trade, gifts, treasury bands and world-health UI remain yours.
- 36-hardening: the new personal kickoff availability read follows existing
  character → sorted realms → estate resolution locks. Include it when
  narrowing read-path locks or adding rate limits.

## New error codes

None. Existing server codes and messages are preserved. No dependencies added.
