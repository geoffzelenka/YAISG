## Prompt 23 — Global order book, slots, tax, access

**ID:** `23-global-market` · **Workstream:** I · **Needs:** 22 · **Design:** §17.1–17.5, D15, §23.1 · **Vision:** V§9.2

### Goal

One world-wide order book per good with escrow in slots, a flat seller tax to the seller's realm, and market-access gating.

### Build

1. **Tables** `market_orders`, `market_matches` (§17.2).
2. **`POST /market/orders {side, item_id, quantity, unit_price}`**: requires market access in the current realm (`NO_MARKET_ACCESS`); counts non-closed orders against `order_slots` inside the insert transaction; escrows gold (buy) or goods (sell); sweeps crossing resting orders best price first, oldest first, at the resting price, locking swept orders in price-time order; a buyer crossing at a better price gets the difference into its slot; any remainder rests. Reports immediate fills. Instanced items are rejected.
3. **Slots** walk `open → collectable → closed`. Fills accumulate in the slot. **`POST /market/orders/{id}/collect`** requires market access (D15); moves what fits within inventory caps and leaves the rest. **`POST /market/orders/{id}/cancel`** needs no access; the remainder waits in the slot.
4. **Tax** (§17.4): `market.tax_pct` from the seller's proceeds, rounded up, credited to the treasury of the sell order's `realm_id`; `tax_burn_pct` (ships 0) destroyed and ledgered.
5. **`GET /market/book/{item_id}?depth=`** (anywhere), **`GET /market/orders/me`**.

### Tests

- Price-time priority; maker price; price improvement refunded into the buyer's slot; partial fills.
- Cancel keeps the remainder in the slot; collect needs access, cancel does not.
- Slot counting; an inventory-capped collect leaves the rest.
- Tax credited to the realm where the sell order was created, not where the buyer is.
- Two takers race for one resting order on SQLite and PostgreSQL.

### Out of scope

Expiry and purge (24).

### Review focus

Fills never enter inventory or wallet except through collection.

