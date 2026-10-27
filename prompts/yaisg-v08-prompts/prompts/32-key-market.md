## Prompt 32 — The key market

**ID:** `32-key-market` · **Workstream:** O · **Needs:** 31 · **Design:** §19.5, §19.6 (listings), D13 · **Vision:** V§10.5

### Build

1. **`key_listings`** (§19.5). `POST /keys/market` lists an unbound `active` key at a fixed price; requires market access; counts against `key_listings`; the key leaves the inventory.
2. **`POST /keys/market/{id}/buy`**: market access; buyer pays the price; seller receives it less the global seller tax, credited to the realm where the seller listed (burn share ledgered); key goes straight to the buyer, who needs a free slot.
3. **`POST /keys/market/{id}/cancel`** returns the key if the seller has a free slot.
4. **`GET /keys/market?realm_id=&class=&item_id=&kind=`**: browse by realm, goods class or exact good (matched against template outputs or the combatant's drop table), showing uses and rolled values; deprecated listings flagged.
5. Transition completion cancels open listings of invalidated keys and returns them.

### Tests

Bound or deprecated keys cannot be listed; cap enforcement; tax and realm; buyer slot required; invalidation returns listed keys; gold conservation with listings in the suite.

