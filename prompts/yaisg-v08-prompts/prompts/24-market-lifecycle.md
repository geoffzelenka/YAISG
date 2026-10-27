## Prompt 24 — Order expiry, purge, world conservation suite

**ID:** `24-market-lifecycle` · **Workstream:** I · **Needs:** 23 · **Design:** §17.2 (expiry, retention), §17.3 (history), §17.6, §23.2

### Goal

Finish the order lifecycle and prove the whole world's conservation invariant.

### Build

1. Scheduled job (every few minutes): open orders past `expires_at` (`market.order_days`, *default* 14) become collectable; closed orders past a retention window are purged. `market_matches` is the durable history.
2. **`GET /market/history/me`** from matches.
3. **World conservation suite** (§17.6): property tests over random interleavings of every operation built so far (realm trades, gifts, projects, larder deposits, estate build/buy/surrender, caravans, orders, collects, cancels, ticks). Gold is always in exactly one of: wallet, buy escrow, slot proceeds, treasury, and changes only by the ledger. Goods are always in exactly one of: inventory, sell escrow, slot fills, stores, larder, caravan, and change only by production, actions, upkeep, spoilage, cap loss and road loss, each counted. (Equipment and belt holders join in 26–27.)

### Tests

- Expiry moves to collectable without touching escrow; purge removes only closed orders past retention.
- The conservation suite itself, running on both databases in CI.

### Review focus

The suite must fail if any path leaks; the reviewer should inject a deliberate leak locally to confirm.

