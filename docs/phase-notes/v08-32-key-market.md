## Built

- Added `key_listings` and migrations `v08_0018_key_market` and
  `v08_0019_key_listing_indexes`: unique instance
  custody, seller, fixed whole-gold price, creation realm/time, status and sale
  recipient/time. Listed instances have a null inventory holder.
- Added authenticated POST /keys/market, POST /keys/market/{id}/buy,
  POST /keys/market/{id}/cancel and remotely readable GET /keys/market.
  Creation requires an unused, active, unbound key and resolved market access;
  open listings consume the resolved key_listings cap independently of orders.
  Purchases require access and a free slot; cancellation requires ownership and
  a free slot, without an access gate. Settlement credits wallets directly.
- Reused global-market access checks, preparation, rational seller tax and burn
  ledger. Tax goes to the seller's listing realm even after the seller moves.
  Missing prepared tax recipients return MARKET_RETRY. Buyers and sellers are
  locked in ascending UUID order (canonical string ordering), before sorted
  realm locks, estate resolution and the authoritative refreshed listing lock.
  The initial listing read is only an identity hint: changed seller identities
  cause MARKET_RETRY rather than acquiring a late character lock.
- Browsing filters discovery realm, goods class, exact output item and resource
  kind (gather/combat). Combat filtering reads the combatant drop table; gathering
  filtering reads the stored inline outputs. Responses include rolled payload,
  uses, name provenance, lifecycle and an explicit deprecated flag. The discovery
  realm filter executes in SQL; browse uses bounded SQL seek batches to fill
  content-filtered cursor pages. Kind is restricted to gather/combat. Gathering
  dict outputs are explicitly normalized to Drop records; listings referencing
  removed goods or combatants are skipped rather than failing the page.
- Both session and preloaded tick transition completion cancel listings and
  return invalid trophies. The existing realm-key SELECT eagerly joins its
  unique listing, preserving the no-query-per-tick contract. Realm work changes
  only instance custody and listing state, never other characters' action rows.
- Extended world accounting to assert exactly one custodian for every instance:
  inventory holder or open listing. Both generated-operation coverage sets now
  include key_trade, key_cancel and key_listing_invalidate, with intermediate
  custody checks and the existing gold-minus-ledger conservation oracle.
- Added tests in test_key_market.py:
  test_bound_or_deprecated_keys_cannot_be_listed;
  test_key_listing_cap_and_cancel_return;
  test_key_tax_and_listing_realm_conserve_gold;
  test_buyer_and_cancelling_seller_need_free_slot;
  test_invalidation_returns_listed_keys_even_when_full (both transition paths,
  also pins first-cutoff-wins across repeated transitions);
  test_postgres_concurrent_key_buys_transfer_once (independent sessions/threads,
  skips SQLite);
  test_key_market_api_browse_filters_deprecation_access_and_ownership;
  test_key_buy_access_funds_and_cancel_ownership;
  test_new_listing_invalidation_in_same_transaction;
  test_stale_sale_id_cannot_buy_a_relisted_key;
  test_self_purchase_costs_exactly_the_tax;
  test_tick_listing_invalidation_issues_no_selects (one/four listings, cold ORM
  relationships; removing the eager load fails both statement-count assertions);
  test_postgres_buy_waits_for_seller_wallet_mutation (actual pg_blocking_pids wait,
  realm NOWAIT probe and independent committed wallet mutation);
  test_browse_cursor_filters_and_removed_content (equal timestamps, sparse
  filters, SQL realm/limit assertions, removed item/combatant ids, invalid inputs);
  test_due_transition_cancel_commits_return;
  test_unavailable_settlement_has_neutral_error.
- Added seller/status and status indexes for capacity and open-listing queries.
  DELETE /keys/{id} explicitly removes the associated closed listing before the
  instance, preserving cleanup on SQLite even without foreign-key enforcement.
  The API regression asserts that no orphan listing remains.

- Repository-virtualenv SQLite make ci passes: auth 15, game 804 with 26
  database-specific skips, client 100. Ruff lint/format, strict mypy, ESLint,
  Prettier, TypeScript, Vitest, production build, scripts and content lint pass.
  git diff --check is clean.
- Disposable SQLite make db-reset, subsequent head upgrade, Alembic schema
  check and an application lifespan/manifest HTTP 200 smoke test pass.

## Removed

- Removed listing-identity reuse, public discoverer character UUIDs from listing
  responses and the seller-wallet-specific GOLD_CAP response. No tests deleted;
  the relisting test now requires stale-intent isolation instead of identity reuse.

## Design ambiguities resolved

- §19.6: automatic invalidation returns the trophy even when inventory is full.
  The design mandates return but provides no overflow rule for it. Temporarily
  exceeding capacity preserves the instance; ordinary subsequent acquisitions
  remain capacity-gated. Explicit cancellation still requires a free slot.
- §19.5: every listing has a fresh immutable identity. Relisting deletes the
  previous closed row and inserts a new UUID, retaining UNIQUE(instance_id).
  A stale buy URL therefore returns UNKNOWN_KEY_LISTING rather than purchasing
  a later sale at a different price. No durable key-sale history is specified.
  An optional buy body {price_gold} additionally pins the buyer's observed price;
  a mismatch returns KEY_PRICE_CHANGED without transferring gold or custody.
- §19.5: kind filters gather/combat resource templates; response key.kind remains
  the instance discriminator `key`. Deprecated open listings remain purchasable
  until completion, consistent with their continuing access and explicit flag.
- §19.5: self-purchases use the same access, capacity and tax rules; one wallet
  loses only the tax. No exception or extra restriction is specified.
- §19.5: realm_id filters the resource's discovery realm (ItemInstance.realm_id),
  not the realm where the seller placed the listing. The former determines where
  the key works and its transition risk; the latter remains the tax recipient.
- §19.5 / §19.1: public listing responses retain discovered_by_name for permanent
  provenance, but omit discovered_by_character_id. The holder's private key API
  retains the id; market browsing does not expose a discoverer's character UUID.
- §19.6: cancelling a listing whose due transition returns the invalid trophy
  succeeds, including with a full inventory. Preparation finalizes the transition
  before status validation; the successful response commits that return rather
  than rolling it back with KEY_LISTING_CLOSED. Repeated cancellation of that
  returned invalid trophy also succeeds while the seller still holds it.

## Deviations

None.

## Ratification needed

None introduced. Earlier combat and commodity self-matching questions are
unchanged; this prompt adds no combat or commodity-matching rules.

## Hand-offs

- 33-guest-auth / 34-tutorial: account for listing custody before deleting
  characters or realm instances; seller/buyer/realm foreign keys prevent silent
  removal of live custody. Delete or cancel associated listing rows explicitly.
- 35-client-keys-tutorial: consume the key market endpoints and server-returned
  rolled values, uses and deprecated flag. Creation body is instance_id and
  price_gold; buy accepts an optional {price_gold} expectation. Browse returns
  listings/next_cursor, with limit=1..200 (default 50) and opaque before cursors;
  descending creation timestamp then UUID determines page order. Filters persist
  on subsequent pages. Mutations return one listing. Public provenance includes
  the discoverer's name, without their character UUID.
  Display INVENTORY_FULL for cancellation/purchase and MARKET_RETRY as retryable.
  Commodity pickers remain unchanged and continue excluding instanced items.
- 36-hardening: retain sorted two-character locking, realm-before-listing
  serialization, no-query-per-tick loading and both generated coverage sets.
  Transition-history pruning still requires the safe watermark described in 31;
  this prompt preserves historical cutoffs rather than discarding old windows.

## New error codes

- NO_KEY_LISTING_SLOT (409): resolved open-listing cap is exhausted.
- UNKNOWN_KEY_LISTING (404): listing is absent or cancellation is not owned.
- KEY_LISTING_CLOSED (409): the listing is sold or cancelled.
- KEY_PRICE_CHANGED (409): the optional expected buy price differs from the listing.
- MARKET_UNAVAILABLE (409): settlement cannot complete; the response deliberately
  gives no information about the seller's wallet (replaces the new GOLD_CAP code).
- Reused KEY_UNAVAILABLE, UNKNOWN_KEY, INVENTORY_FULL, NO_MARKET_ACCESS,
  INSUFFICIENT_GOLD and MARKET_RETRY. No new dependencies.

## Orchestrator verification and review hand-offs

- Verified:
  - SQLite `make ci`: auth 15, game 804 passed / 26 skipped, client 100.
  - PostgreSQL: game 829 passed / 1 skipped.
  - Alembic check clean; boot 200.
- Round 1: CHANGES_REQUESTED.
  - B1: relisting reused the listing id, so a stale buy paid the new price.
  - Fixed in c94a44e, with N1–N10: fresh ids, an optional expected-price guard, paginated browse, the seller-lock PG test, and indexes.
- Round 2 (Sonnet): APPROVE. B1 and the N3 change were mutation-checked.
- Hand-offs for 35/36:
  - When a buy lands on a due transition it returns 409 and rolls back. The transition is committed by the next request that resolves the world. Optionally, commit before raising.
  - Repeating a cancel on a key that went invalid in inventory returns 200. That is harmless.
  - A browse with a sparse content filter can scan every open listing in limit+1 batches. Consider a scan cap that returns a mid-scan cursor.
  - Relisting deletes the closed row, so there is no durable key-sale history. A ledger would need a separate table.
