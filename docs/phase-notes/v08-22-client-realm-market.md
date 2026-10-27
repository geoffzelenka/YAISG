## Built

- Added the Realm Market sidebar route and realm picker. Any visible world
  realm can be inspected remotely, with line stock/reserve/cap in line units,
  server days of cover, decimal spot bids, alternative member funded quantities
  and totals, surplus sale quantities/asks, unfunded shortfalls, stage, gauge
  days, treasury band and current presence. No treasury balance is displayed.
- Added exact quote-then-confirm purchases and sales. Confirmation sends the
  quoted integrated gold as limit_gold. Editing intent discards the quote;
  requests are serialized while quoting/executing. PRICE_MOVED fetches a new
  quote and requires another explicit confirmation. Oversized quotes cannot
  confirm. Server affordability, capacity and presence checks remain authoritative.
- Added confirmed treasury gifts with 204 success handling. Trade confirmation
  and gifts are disabled while absent; visitors and residents use identical
  controls. Remote quote reads remain available, with travel links.
- Added typed market queries and transfer hooks, shared query invalidation
  after success, and periodic market/map refresh. Map hungry realms sort by
  descending gauge then realm id, showing below-reserve lines and links to
  inspect each market. Loading/read failures are explicit. Fixed the missing
  space before the middot in the existing map stage/gauge display.
- Picked up 15/16/17/20/21 hand-offs: live health fields, milli-line-unit versus
  whole-item quantities, shared-budget member alternatives, decimal spot bids,
  204 gifts, both HTTP statuses for NO_DEMAND, UNFUNDED_DEMAND maximum, and
  mutation invalidation. No in-transit quantity is treated as current stock.
- Added Vitest coverage in RealmMarketPanel.test.tsx for exact sale limits,
  PRICE_MOVED re-quote/reconfirmation, remote presence gating, nontradeable
  shortfalls and units, confirmed gifts, hungry-realm order/short lines and
  stage/band presentation, intent edits/buy limits, both NO_DEMAND statuses,
  and UNFUNDED_DEMAND fundable quantities.

- Updated existing positionless-map and estate-to-map fixtures for the new
  market reads, preserving their assertions and scoping SVG assertions to the graph.
- Disposable SQLite db-reset, subsequent upgrade to head and world creation
  succeeded.

- Final SQLite PATH=$PWD/.venv/bin:$PATH make ci passes: auth 15, game
  575 with 18 database-specific skips, client 70. Formatting, lint, strict
  typing, production build, scripts and content lint pass; git diff --check is clean.

## Removed

None. No tests or existing features removed.

## Design ambiguities resolved

- §24 / §15.5: hungry means a realm has at least one line below reserve,
  including funded shortages; unfunded shortfalls remain a separate market
  display. Sort highest gauge first, consistent with §16.3's hungry-first
  ordering; realm id breaks ties deterministically.
- §24 / §15.5: use parallel cached market reads for short-line information
  absent from GET /map rather than introduce another server projection. Each
  query retains explicit loading/error state and refreshes with the map.
- §15.5: display stored categorical bands 0–4 (poorest to richest), without
  inferring treasury balances or presenting hysteresis bands as exact cover.
- §15.3: preserve the existing NO_DEMAND status difference (quote 400,
  trade 409). Client error handling is code-based and handles both statuses.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 23-global-market / 25-client-global-market: Realm Market is a separate route;
  Player Market remains the existing placeholder. Successful economy mutations
  should continue invalidating character, realm, estate and map queries.
- 36-hardening: the map currently uses one cached market read per visible realm
  to obtain short lines. Consider a batched public health projection if world
  size makes this costly; preserve remote visibility and balance privacy.

## New error codes

None. Existing server errors are preserved. No dependencies added.
