## Prompt 13 — Stores, demand lines, world seed

**ID:** `13-stores-lines` · **Workstream:** G · **Needs:** 12 · **Design:** §14.1–14.4, §14.9 (seed), §21 (`world_state`), D9 · **Vision:** V§9.3.3, V§9.4.2–9.4.6

### Goal

Give realms stores and an appetite, and create a world from a seed.

### Build

1. **`realm_stores (realm_id, item_id, quantity_milli)`** and the pure `due(d, n, T)` of §14.1.
2. **Demand lines** (D9), a pure derivation each tick from: node upkeep, active tag upkeep, estates in the realm (full upkeep, larder or not), and the funding project's overlay (`remaining / realm_completion_days` per cost line). A hook for the mint line, empty until Prompt 18. Grouped by selector; each item belongs to its most specific matching line (item, then class with tier, then class); line units `w = 1` for ordinary lines and `reference_price` for value-measured lines.
3. **Validation and lint.** Boot rejects an ordinary class selector used as upkeep whose members differ in reference price. `content-lint` warns when two upkeep selectors overlap.
4. **Draw, reserve, cap** (§14.3) with tag `reserve_days_delta`, transition days while a transition is pending, and node overrides; defaults in `economy`. Goods with no line: reserve 0, hard cap `warehouse_value_cap / reference_price` (item override allowed).
5. **`realm_lines`**, a derived table with a single recompute function (`in_transit` 0 until 20; `budget_gold` 0 until 16).
6. **`world_seed` pack** (not served): per realm a starting treasury, starting stores and realm-owned estates. `world_state` single row (`seeded_at`, `last_caravan_pass`, content version). World creation runs once when `world_state` is empty (boot and `make world-create`), idempotently. Seed gold is recorded in the ledger by Prompt 18.
7. **`GET /realms/{id}`** adds lines and which are below reserve.

### Tests

- Property: `due` sums to exactly `d` over any day for random `d` and `T`.
- Line grouping and most-specific membership; value-measured units.
- Reserve with a tag delta and with a pending transition; hard cap for no-line goods.
- Validator rejects a mixed-price class line.
- World creation twice creates once.

### Out of scope

The tick's steps (14); budgets (16).

### Review focus

Derivation is pure and reproducible; stores are milli-units, trades whole units.

