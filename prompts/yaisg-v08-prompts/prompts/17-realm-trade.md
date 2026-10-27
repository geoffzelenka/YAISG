## Prompt 17 — Realm trade and treasury gift

**ID:** `17-realm-trade` · **Workstream:** H · **Needs:** 16 · **Design:** §15.3, §15.6, §23.1 · **Vision:** V§9.3.4, V§9.4.3–9.4.4

### Goal

Let players present in a realm buy from and sell to it.

### Build

1. **`POST /realms/{id}/market/trade {item_id, side, quantity, limit_gold}`**, presence required, all-or-nothing, under character then realm locks, after `resolve_realm`.
2. **Selling**: `NO_DEMAND` (no line with draw), `STORES_FULL` (would pass the cap), `UNFUNDED_DEMAND` (over the line's budget or the treasury; the error carries the largest fundable quantity). Treasury and the line's budget fall by the gold paid.
3. **Buying**: `NOT_FOR_SALE` (only stock above reserve, and only of that item), `INSUFFICIENT_GOLD`, `INVENTORY_FULL`.
4. **`PRICE_MOVED`** when the quote is worse than `limit_gold`; nothing changes.
5. **`POST /realms/{id}/treasury/gift {gold}`**, presence required.
6. `realm_lines` is adjusted on each trade so reads stay exact.

### Tests

- Every code; `PRICE_MOVED` leaves all state unchanged.
- Property: random sequences of trades and gifts conserve gold (wallets + treasuries) and goods (inventories + stores).
- Two sellers race to exhaust one line's budget on PostgreSQL: the total paid never exceeds the budget.

### Out of scope

Mint and ledger (18).

### Review focus

Whole units on the player side, milli-units in stores; no rounding gap leaks a unit.

