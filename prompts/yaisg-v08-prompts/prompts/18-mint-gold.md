## Prompt 18 — Mint and the gold ledger

**ID:** `18-mint-gold` · **Workstream:** J · **Needs:** 17 · **Design:** §2.4, §14.8, §18 · **Vision:** V§9.5

### Goal

Add the only runtime source of gold and make every creation and destruction auditable.

### Build

1. **Bullion.** Validator: an item with `bullion: true` carries the `bullion` class, and only those do.
2. **Mint line.** An active tag with `effects.mint` adds one value-measured line on `{class: bullion}` with draw `value_per_day` (the largest if several). It has reserve, cap, bids and counts toward the gauge like any line.
3. **Coinage at step 4**: the mint consumes up to the tick's share of `value_per_day` in bullion from stores, and `treasury += floor(reference value consumed × economy.coinage_multiple)` (*illustrative* 1.2).
4. **`gold_ledger`** (§21) with causes `world_seed`, `mint`, `tutorial_seed`, `tutorial_destroy`, `tax_burn`, `caravan_fee_burn`. Record world-seed treasuries at creation (Prompt 13). Later prompts write their own causes.
5. **`GET /admin/economy`**, operator-only (an allowlist of auth user ids from configuration): world gold by holder type (wallets, treasuries, and later escrow and slots), and ledger totals by cause.
6. Placeholder content: a mint project, a bullion item, a node offering both.

### Tests

- Coinage arithmetic per tick and over a day.
- Throttle: with scarce bullion and high bids, the realm's treasury falls until it can no longer buy, and minting stops (§2.4: a brake, not a sink).
- Property: across random sequences of every gold operation implemented so far, world gold changes only by the ledger's net.
- `GET /admin/economy` rejects non-operators.

### Out of scope

Tax and fee burns (their prompts write those causes).

### Review focus

There is exactly one code path that increases world gold at runtime.

