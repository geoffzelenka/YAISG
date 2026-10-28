## Built

- Replaced the Player Market placeholder with /market and sidebar navigation.
  Added a commodity selector excluding instanced templates, aggregate bid/ask
  tables and selectable book depth, plus side/quantity/unit-price order entry.
- Creation and collection are disabled with a reason when the current realm's
  active tags do not grant market access, or access cannot be verified.
  Books, owned slots, cancellation and history remain available remotely.
- Slots display open, collectable and closed states, occupied count/resolved
  cap, remaining quantity, escrow gold, uncollected items/gold and expiry.
  Open fills may be collected; partial collection reports actual transfers
  and explains that remaining holdings stay in the slot until capacity permits.
- Immediate fills show the returned caller side, executed quantity, maker price
  and seller tax. Placement explicitly leaves holdings in slots until collection.
  History consumes matches/next_cursor and sends the opaque before cursor with
  limit=50. Durable history does not depend on retained slot rows.
- Mutations share a synchronous in-flight guard and invalidate global market,
  character, realm, estate and map queries after success. Existing server error
  messages/codes remain visible; MARKET_RETRY is surfaced with a retry instruction
  after rollback, without automatically resubmitting other failures.
- Extended client content types for instanced templates and market tax, duration,
  retention and lifecycle cadence. Cleared the previous realm-market success
  message when requesting another quote, as handed off by Prompt 22 review.
- Added GlobalMarketPanel.test.tsx cases:
  `access-gated controls leave books, history and cancellation available`;
  `slot state rendering and partial collection report actual transfers and invalidate holders`;
  `immediate-fill report uses server execution and leaves proceeds in slots`;
  `history passes the opaque cursor and book depth to the server`;
  `double submission sends one request and MARKET_RETRY is surfaced without resubmission`.
  `sell intent and a resting order do not imply an immediate fill`.
  RealmMarketPanel.test.tsx adds
  `requesting a quote clears the previous success line`.

- SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passes: auth 15, game 615
  with 20 database-specific skips, client 83. Formatting, lint, strict typing,
  production build, scripts and content lint pass; `git diff --check` is clean.
- Disposable SQLite `make db-reset` and subsequent game/auth Alembic upgrades
  to head succeeded. No schema or server behavior changed.

- Review round 1: strengthened the access test to choose a good before checking
  disabled creation, assert Side/Quantity/Unit price are disabled, submit the
  form directly, and assert no creation POST. A scratch mutation removing only
  the fieldset access gate fails at the disabled Place order assertion; the gate
  was restored. No scratch mutation remains.
- Review round 1: partial collection reports actual transferred and remaining
  item/gold amounts with singular/plural item labels. An open order with all
  current fills collected says “Nothing is waiting right now.” Slot tests now
  assert open status, waiting balances, enabled cancellation, collectable status
  and disabled cancellation, plus the partial remainder.
- Review round 1: every global-market mutation failure invalidates the current
  realm query so stale access is refreshed, including NO_MARKET_ACCESS. Global
  and realm market callers now use shared ApiError from api/http.ts, preserving
  error codes. Tax/expiry copy renders only when both content values exist.
  Fills, durable history and slot headings show authored item names.
- Review round 1 tests added in GlobalMarketPanel.test.tsx:
  `%s refreshes current realm access after mutation failure`
  (NO_MARKET_ACCESS, MARKET_RETRY, INSUFFICIENT_GOLD);
  `collecting all waiting holdings from an open order reports nothing waiting right now`;
  `omits incomplete tax and expiry settings %j` (three incomplete settings).
  Changed `access-gated controls leave books, history and cancellation available`,
  `slot state rendering and partial collection report actual transfers and invalidate holders`,
  and `immediate-fill report uses server execution and leaves proceeds in slots`.

- Review round 1 validation: SQLite
  `PATH=$PWD/.venv/bin:$PATH make ci` passes: auth 15, game 615 with 20
  database-specific skips, client 90. Formatting, lint, strict typing,
  production build, scripts and content lint pass.

## Removed

- Removed the Player Market placeholder. No tests removed or weakened.

## Design ambiguities resolved

- §24 / §17.3: depth uses a selector of 10/20/50/100 price levels per side,
  within the server's supported range. History uses its default page size 50
  and an explicit load-older action, preserving the server cursor unchanged.
- §24 / §17.5: fail closed for order creation/collection while realm access
  loads or fails, explaining the state. Read and cancellation controls remain
  usable. The server rechecks access and every transfer at execution.
- Prompt 23 hand-off: choose the explicitly permitted surfaced MARKET_RETRY
  response rather than automatic resubmission; the user can retry the intent.

## Deviations

None.

## Ratification needed

No new questions. Prompt 23's self-matching question remains unchanged; this
client displays the caller-side projections supplied by the server.

## Hand-offs

- 32-key-market: instanced templates remain excluded from this commodity picker;
  use the separate key market UI and API when implemented.
- 36-hardening: preserve access failure explanations, synchronous mutation guards,
  cursor pagination and holder-query invalidation if market reads are optimized.

## New error codes

None. Existing server codes are displayed. No dependencies added.

## Orchestrator verification and review hand-offs

- Orchestrator on 634856e: SQLite make ci green (auth 15, game 615 / 20
  skipped, client 90); PostgreSQL 16 game-ci 634 / 1 skipped; PG db-reset,
  alembic check and boot green. Review: round 1 CHANGES_REQUESTED (access-gate
  test could not fail), round 2 APPROVE.
- 36-hardening: RealmApiError (client/src/api/realms.ts:60) duplicates the new
  shared ApiError; alias or extend it.
