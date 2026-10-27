## Prompt 22 — Client: realm market and world health

**ID:** `22-client-realm-market` · **Workstream:** Q · **Needs:** 21 · **Design:** §24 (Realm market, Map), §15.5

### Goal

Let haulers see where the world is hungry and trade there.

### Build

1. **Realm market panel**, viewable for any realm: lines with stock, reserve, cap and days of cover; bids with funded quantity; items for sale; shortfalls; band; presence state.
2. **Quote-then-confirm trade form** using `/quote`, sending `limit_gold`; handles `PRICE_MOVED` by re-quoting; treasury gift form.
3. **Map**: stage and band per realm, a "hungry realms" list sorted by gauge with their short lines.

### Tests (vitest)

- Quote flow and the `PRICE_MOVED` path; trade disabled when not present; shortfalls render without a buy button.

### Review focus

Read-anywhere, trade-in-person (V§9.3.5).

