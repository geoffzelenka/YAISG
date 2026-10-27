## Prompt 12 — Build, buy, surrender, valuation, larder

**ID:** `12-estate-ownership` · **Workstream:** F · **Needs:** 11 · **Design:** §13.4, §13.6 (larder deposit), §23.1, D8 · **Vision:** V§8.4, V§8.7, V§8.8.4

### Goal

Let players move between mobile and fixed estates and prepay upkeep.

### Build

1. **Valuation** (§13.4), pure: the `build_cost` of every form on the path from tier 1 to the current form, plus each installed upgrade's cost. Gold at face value; each good at `min(reference_price, realm unit ask)` through a price-provider interface that returns "not selling" until Prompt 16 wires it (so `reference_price` is used). For a selector, the cheapest matching item. If several tier-1 paths exist, use the cheapest and record it.
2. **Sale price** `ceil(value × (1 + estate.sale_markup_pct/100))`, *default* 15, in `economy.estate`. Shown in `GET /realms/{id}/estates` for realm-owned estates.
3. **`POST /estates/build {form_id}`**: a tier-1 fixed form whose `requires_realm_tags` are active; the character is present with their mobile estate present; pays `build_cost` (gold per Prompt 11's rule); creates the fixed estate; destroys the mobile estate and its upgrades (D8); writes ownership history.
4. **`POST /estates/{id}/buy`**: realm-owned estate in the current realm; buyer present with their mobile estate present; pays the sale price to the treasury; ownership transfers; the mobile estate is destroyed.
5. **`POST /estates/me/surrender {donate}`**: fixed estates only; owner present; the realm pays `min(value, treasury)`, or nothing if `donate`; ownership passes to the realm; the character receives a new `basic_mobile_form` estate in the current realm.
6. **Larder**: `estate_larder (estate_id, item_id, quantity_milli)`; `POST /estates/me/larder {item_id, quantity}`, owner present, item must match one of the estate's upkeep selectors. Deposit only.
7. Lock order character → realm → estate. Choose and record codes (for example `NOT_FOR_SALE`, `CANNOT_SURRENDER_MOBILE`, `NOT_UPKEEP_ITEM`).

### Tests

- Valuation example with gold, goods and a selector; provider override changes the price used.
- Property: buy then surrender always loses gold, for random values and treasuries.
- Surrender into a poor treasury pays the treasury balance; donate pays nothing.
- Build destroys the mobile estate and its upgrades; the one-estate invariant holds after every flow.
- Two buyers race for one estate on PostgreSQL: exactly one succeeds.
- Larder rejects non-upkeep items and has no withdrawal path.

### Out of scope

Larder consumption and spoilage (14); estate decay (15).

### Review focus

Gold conservation in every flow; the confirmation step is a client concern (Prompt 21).

