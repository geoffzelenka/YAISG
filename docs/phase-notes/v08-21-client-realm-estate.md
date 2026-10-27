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
  either the current payout or zero-payout donation. Presence state and map
  travel links accompany estate/realm controls.
- Extended the private home-estate response with larder milli-unit holdings and
  a nullable current surrender payout. Prices/payouts are explicitly rechecked
  at execution. Existing mutations and lock order remain authoritative.
- Added typed development reads/mutations and invalidation of realm, estate,
  profile/inventory/action and map queries after successful changes. Countdown
  expiry refreshes realm state through the existing shared cosmetic clock.
- Added Vitest cases for kickoff unavailable reasons, stocked eligibility,
  open-vote secrecy/public participation, larder units and zero upkeep,
  build confirmation asset losses/cancellation, RESERVE_SHORT on both entry
  points, and the earlier Prompt 08 completed-edge arrival toast hand-off.
- Added test_kickoff_availability_reports_gates_without_payment and extended
  test_build_buy_surrender_and_larder to verify the private projection, capped
  payout and empty replacement larder. Database fixtures honor TEST_DATABASE_URL.
- Disposable SQLite db-reset and subsequent upgrade to head succeeded.
- SQLite PATH=$PWD/.venv/bin:$PATH make ci passes: auth 15, game 575
  with 18 database-specific skips, client 55. Formatting, lint, strict typing,
  production build, migration/reset tests, scripts and content lint pass.
  git diff --check is clean.

## Removed

None. No existing tests or gameplay features removed.

## Design ambiguities resolved

- §24 / §12.3: availability needs personal cooldown/payment state unavailable
  in the public realm projection. Added a private read that shares kickoff
  validation rather than guessing those reasons from public data.
- §24 / §13.6: larder cover is matching milli-units divided by 1,000 and daily
  upkeep, shown separately for each selector. The UI explains shared goods for
  overlapping selectors and that realm supplies/spoilage change actual cover.
  Zero daily upkeep displays “No upkeep”; this is not a simulated survival timer.
- §24 / §13.4–13.5: expose only the surrender payout, not the underlying
  valuation or treasury. Confirmation labels it a current snapshot because
  lazy resolution and competing activity can change the execution-time amount.

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
