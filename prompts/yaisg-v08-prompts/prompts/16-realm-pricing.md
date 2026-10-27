## Prompt 16 — Realm market pricing and visibility

**ID:** `16-realm-pricing` · **Workstream:** H · **Needs:** 15 · **Design:** §15.1, §15.2, §15.4, §15.5, §13.4 (price provider), §11.1 (band on map) · **Vision:** V§9.3, V§9.4.8

### Goal

Publish what every realm will pay and charge, priced by integrating a scarcity curve and limited by its treasury.

### Build

1. **Curve settings** `f, c, k, m` in `economy.market` (*illustrative* 0.33, 2.1, 3, 25%); node `margin_pct` override.
2. **`quote(ctx, item, side, quantity)`**, pure, with fixed-precision decimal arithmetic: `F(a, b)` as in §15.2; sell `floor((ref / w) × F(s, s + q·w))`; buy `ceil((1 + m) × (ref / w) × F(s − q·w, s))`. Returns the gold and the largest currently tradable quantity.
3. **Budgets** at step 10 (§15.4): `weight = (cap − stock) × unit reference value × (2 if below reserve)`; `budget = floor(treasury × weight / Σ weights)`. Funded quantity per line by bisection on the integral within budget and cap.
4. **Treasury band** at step 10: five buckets by days of the realm's upkeep the treasury could buy at reference prices (*defaults* <1, 1–3, 3–7, 7–14, >14) with 10% hysteresis. Stored in `realm_state.treasury_band`.
5. **`GET /realms/{id}/market`** (any logged-in player, any location): per line selector, members, stock, reserve, cap, draw, days of cover, spot bid, funded quantity and its total; per item for sale, quantity above reserve and spot ask; shortfalls (lines below reserve the realm cannot fund, with the missing amount); stage, gauge days, band. **`GET /realms/{id}/market/quote`**.
6. **Wire the estate valuation provider** (Prompt 12) to the realm's spot unit ask.
7. **`/map`** shows the band.
8. **`seed-check`** gains: every realm in `tutorial.arrival_realms` publishes funded bids for tier-1 goods throughout. Until the tutorial pack exists (Prompt 34), skip the clause and say so in the report.

### Tests

- Curve values ≈ 2.10, 1.08, 0.55, 0.33 at 0, ¼, ½ and full.
- §15.2's example: reference 10, cap 1,000, stock 100, selling 500 pays exactly 4,439.
- Property: `ask = bid × (1 + m)` over the same stretch for every quantity; buying then selling straight back never profits; the integral equals the sum of per-unit prices within rounding.
- Σ budgets ≤ treasury; an empty treasury publishes no bids.
- Band hysteresis does not flicker at a boundary.
- No realm or map response contains the raw treasury (assert across every endpoint's schema).

### Out of scope

Trading (17).

### Review focus

Decimal precision identical on both databases; rounding always favours the realm.

