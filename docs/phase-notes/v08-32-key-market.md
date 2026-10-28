## Built

- Added `key_listings` and migration `v08_0018_key_market`: unique instance
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
  uses, provenance, lifecycle and an explicit deprecated flag.
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
  test_new_listing_invalidation_in_same_transaction.

- Repository-virtualenv SQLite make ci passes: auth 15, game 797 with 25
  database-specific skips, client 100. Ruff lint/format, strict mypy, ESLint,
  Prettier, TypeScript, Vitest, production build, scripts and content lint pass.
  git diff --check is clean.
- Disposable SQLite make db-reset, subsequent head upgrade, Alembic schema
  check and an application lifespan/manifest HTTP 200 smoke test pass.

## Removed

None. No existing tests removed or weakened.

## Design ambiguities resolved

- §19.6: automatic invalidation returns the trophy even when inventory is full.
  The design mandates return but provides no overflow rule for it. Temporarily
  exceeding capacity preserves the instance; ordinary subsequent acquisitions
  remain capacity-gated. Explicit cancellation still requires a free slot.
- §19.5: the unique instance listing row is reused on relisting, replacing its
  prior sale/cancellation metadata. The specified UNIQUE instance_id permits
  only one row, and keys remain transferable until binding. No durable key sale
  history is specified.
- §19.5: kind filters gather/combat resource templates; response key.kind remains
  the instance discriminator `key`. Deprecated open listings remain purchasable
  until completion, consistent with their continuing access and explicit flag.
- §19.5: self-purchases use the same access, capacity and tax rules; one wallet
  loses only the tax. No exception or extra restriction is specified.

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
  price_gold; browse envelope is listings, mutations return one listing.
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
- GOLD_CAP (409): the seller wallet cannot hold the proceeds.
- Reused KEY_UNAVAILABLE, UNKNOWN_KEY, INVENTORY_FULL, NO_MARKET_ACCESS,
  INSUFFICIENT_GOLD and MARKET_RETRY. No new dependencies.
