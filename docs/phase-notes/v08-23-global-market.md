## Built

- Added market_orders slots and market_matches durable history, migration
  v08_0012_market, holding/status constraints, book and owner indexes. Match
  identifiers deliberately have no order foreign keys so retention can remove
  closed orders without losing executions or participant identities.
- Added POST /market/orders with strict whole-unit intent validation, resolved
  current-realm access, transactional non-closed slot counting and full wallet
  or inventory escrow. Crossing makers are swept best price, oldest timestamp,
  then id; each swept maker is locked in that order. Executions use maker prices,
  accumulate fills and buyer price improvements in slots, and leave remainders
  resting. Responses report actual immediate executions.
- Added access-gated collection with stack and distinct-item caps, early
  collection from open orders, partial collection, closed timestamps and slot
  reuse. Cancellation needs no access and moves remaining escrow into the slot.
  Neither execution nor cancellation credits an inventory or wallet.
- Added remotely readable aggregated GET /market/book/{item_id}?depth= and
  private GET /market/orders/me, including retained closed orders. All mutations
  use character serialization, sorted realm locks, estate resolution and then
  order locks. SQLite acquires writer intent before loading authoritative state.
- Extended the strict economy.market content schema and placeholder pack with
  tax_pct, tax_burn_pct and order_days. Pure rational arithmetic ceils seller tax
  and floors its burn share. The sell order's creation realm receives the rest;
  negative tax_burn ledger entries are written in the execution transaction.
- Picked up Prompt 05 access-tag activation and Prompt 18 accounting hand-offs:
  /admin/economy includes order_escrow and order_slots in its existing single SQL
  snapshot. Extended test_random_gold_operations_match_ledger with actual order
  creation, matching, cancellation, collection and nonzero burns. It now asserts
  endpoint sum(holders) minus sum(ledger) at baseline after mint ticks and every
  market transfer, including occupied escrow and uncollected slots.
- Added test_price_time_maker_price_refund_and_partial_fills,
  test_sell_taker_sweeps_highest_bids_at_maker_price,
  test_cancel_remainder_slots_and_capped_collection,
  test_tax_uses_sell_creation_realm_and_ledgers_burn,
  test_two_takers_race_one_resting_order,
  test_api_access_cancel_visibility_validation_and_ownership,
  test_inventory_slot_cap_never_blocks_a_fill,
  test_market_access_survives_weak_stages_until_shed and test_tax_rounding.
  The actual two-thread/two-session taker race and all integration fixtures honor
  TEST_DATABASE_URL, exercising the same behavior on both database dialects.

- Pre-review fix 1: normalize book price/quantity values with int(), matching
  /admin/economy, because PostgreSQL SUM(bigint) returns Decimal. Extended
  test_api_access_cancel_visibility_validation_and_ownership to assert actual
  JSON integer types on both buy and sell levels. Audited all new aggregates:
  economy sums already normalize with int(); order slot COUNT returns an integer.
- SQLite PATH=$PWD/.venv/bin:$PATH make ci rerun after pre-review fix 1 passes:
  auth 15, game 591
  with 18 database-specific skips, client 76. Ruff formatting/lint, strict mypy,
  TypeScript, ESLint, Vitest, production build, scripts and content lint pass.
  Migration schema parity, downgrade/rebuild and disposable database reset tests
  pass; git diff --check is clean.

## Removed

None. No existing tests or features removed.

## Design ambiguities resolved

- §17.1: equal maker timestamps use UUID id as the final deterministic tie-break.
  Self-matches are allowed because no exclusion is specified; escrow and tax
  accounting are identical for all matches.
- §17.2: cancelled sell remainders move to fill_items; cancelled buy escrow moves
  to fill_gold. quantity_remaining and escrow_gold_remaining then become zero.
  This represents every collectable holding with the specified columns and keeps
  cancellation and later expiry able to share one operation.
- §17.4: floor the burned share of the already-ceiled tax and credit the entire
  remaining tax to the treasury, conserving whole gold. The unspecified tax rate
  is a synthetic 5% in content; burn ships at zero and duration defaults to 14 days.
- §17.1: added an Item.instanced content marker, false for existing commodities,
  to reject instanced templates at this boundary before the instance model lands.
  Unknown instance identifiers are also rejected by the commodity lookup.
- §23.1: use sorted existing realm locks as coarse global book serialization.
  They cover tax recipients before estate/order locks and prevent phantom crossing
  inserts into an empty book. This favors simple correctness over throughput,
  consistent with the current coarse caravan transaction strategy.
- §17.2: collection also respects the wallet's signed 64-bit storage boundary,
  retaining excess gold in the slot rather than overflowing the wallet.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 24-market-lifecycle: implement scheduled expiry with cancel_order's escrow-to-
  slot behavior, retention of closed orders, and GET /market/history/me using
  durable match identities. expires_at already uses authored market.order_days.
  Extend the endpoint-based gold property into the full world goods/gold suite;
  sell escrow is quantity_remaining on open sell orders, slot goods are
  fill_items, buy escrow is escrow_gold_remaining and slot gold is fill_gold.
  Use the same realm serialization before order locks for expiry/purge.
- 25-client-global-market: Player Market remains the placeholder route. Consume
  server fill prices and slot balances; fills never mean inventory/wallet credit.
  Creation returns 201, collection reports actual moved items/gold, cancellation
  retains holdings, and successful mutations should invalidate economy/profile,
  realm, estate and map queries as handed off by Prompt 22. Extend the client
  content types for market tax/duration settings and the instanced marker.
- 31-keys / 32-key-market: keep instance ids outside the commodity lookup and
  preserve the instanced-item rejection when the concrete instance model lands.
- 34-tutorial: account for market slots before deleting characters/realm instances;
  order foreign keys intentionally prevent silent destruction of holdings.
- 36-hardening: narrow coarse world realm serialization only with a replacement
  per-good serialization scheme that handles empty books, tax recipient locks,
  new isolated realms and the established character/realm/estate/order lock order.

## New error codes

- NO_MARKET_ACCESS (409): current realm lacks active market access (specified).
- NO_ORDER_SLOT (409): all non-closed slots count against the resolved cap.
- INSTANCED_ITEM (409): instanced templates cannot use the commodity book.
- INVALID_ORDER (422): nonpositive intent or price times quantity exceeding
  signed 64-bit gold. HTTP field validation also rejects booleans/fractions.
- UNKNOWN_ORDER (404): missing order or a slot owned by another character.
- Reused UNKNOWN_ITEM, MISSING_INPUTS and INSUFFICIENT_GOLD. No dependencies added.
