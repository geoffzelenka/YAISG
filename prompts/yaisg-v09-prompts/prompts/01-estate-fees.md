## Prompt 01 — Estate gold fees leave the economy; no zero-valued forms

**ID:** `01-estate-fees` · **Needs:** 00 · **Source:** Q1, Q2 · **Design:** §13.2–13.4, §18, D14

### Rulings

- **Q1:** "Any gold fees for estate upgrades/transforms will be removed from the economy. The estates don't have a treasury."
- **Q2:** "Yes, Forbid zero-valued fixed-form estates."

### Goal

Gold paid to build, transform or upgrade an estate is destroyed and ledgered as a gold sink, instead of being credited to the realm's treasury. Fixed forms can no longer have zero value.

### Build

1. **Q1 reading (the orchestrator's):** "removed from the economy" means the gold is burned. The fee still exists and is still paid. Applies to the gold part of:
   - `POST /estates/build` (`build_cost`);
   - `POST /estates/me/transform` (the destination's `build_cost`);
   - `POST /estates/me/upgrades/{upgrade_id}` (the upgrade's cost).

   Goods paid on those paths are unchanged.
2. Each burn writes one `gold_ledger` row with a new destruction cause (e.g. `estate_fee_burn`), the character id and the estate's realm. Add it to the §18 destroyed paths in `GET /admin/economy` and to the world conservation accounting.
3. **Unchanged:**
   - buying a realm-owned estate (`POST /estates/{id}/buy`), which pays the sale price to the treasury;
   - surrender buy-backs;
   - estate **value**, which still counts gold at face value.

   Record under Design ambiguities that value still includes burned gold, so the surrender/buy loss rule holds.
4. **Q2:** the content loader rejects any fixed form (and any form reachable as a fixed estate) whose value, as §13.4 computes it, can be zero, and so whose sale or surrender price can be zero. Use a clear content validation error. Update placeholder content so every fixed form has a positive value.
5. Update the client so estate build, transform and upgrade screens no longer imply the realm receives the gold.

### Tests

- Build, transform and upgrade each destroy exactly the gold paid: wallet down, treasury unchanged, one ledger row with the new cause.
- The world conservation suite and `GET /admin/economy` still balance with the new sink in the generated operations.
- The loader rejects a zero-valued fixed form and accepts the shipped content.
- Buy and surrender still move gold between the player and the treasury, and buying then surrendering still always loses.
- Rewrite the v0.8 tests that pin treasury credit for these paths (list them under Removed).

### Out of scope

Changing fee sizes; any other gold path.

### Review focus

Every gold change has a named holder or a ledger row. No path still credits estate fees to a treasury. Q2 validation uses the same value computation as §13.4.
