## Prompt 02 — Goods, actions, selectors, categories, caps

**ID:** `02-content-model` · **Workstream:** A · **Needs:** 01 · **Design:** §4.2 (skills, items, caps), §4.3, §5.3 (validation), §6.1, §6.2 (shape) · **Vision:** V§4.2–4.3, V§5

### Goal

Reshape skills, actions and items to the v0.8 content model, introduce selectors with deterministic payment, and rename caps. Enforcement of `requires` comes in Prompt 05; this prompt establishes shapes and validation.

### Build

1. **Skills.** `category ∈ {gathering, refining, manufacturing, combat, exploration, travel}`. Rename `crafting` → `manufacturing` in content, code, API and client labels. Add the fixed skills of §6.1 to placeholder content (`melee`, `ranged`, `magic`, `accuracy`, `defense`, `vigor`, `travel`, `exploration`), with no actions yet. Remove the old placeholder combat skill. Character creation creates a row for every content skill.
2. **Items** gain `tier`, `classes: [str]`, `reference_price: int > 0`, `bullion: bool = false`, `spoilage_pct_per_day: number = 0`. (`equip` and `consumable` blocks arrive in Prompts 26–27; do not add them now.)
3. **Selectors** (§4.3): `{"item"}`, `{"class", "tier"}`, `{"class"}`. One Pydantic type used everywhere. Boot validation rejects a selector that matches no item.
4. **Deterministic payment.** A pure engine function `pay_selector(holding, selector, quantity)` returning withdrawals or a shortfall: cheapest by `reference_price` first, then lowest item id. Every later prompt that pays a selector uses it.
5. **Actions** become the §6.2 record: `tier`, `unlock_level` (renamed from the shipped field), `base_cycle_ms`, `inputs: [{selector, quantity}]`, `outputs: [{item_id, quantity_min, quantity_max, chance, off_tier?}]`, `xp`, `requires {facility, realm_tags, skill_levels, tool_class}` (all optional, validated for references now, enforced in 05), `resolver` (defaults from category), `off_curve`.
6. **Validation** (§5.3): an action's `tier` equals `tier_for_level(unlock_level)`; outputs are of the action's tier unless flagged `off_tier`; every item an input selector can match is of the action's tier or lower.
7. **Uniform resolver** consumes selector inputs through `pay_selector` each cycle; the start check reports `MISSING_INPUTS` through the same function.
8. **Caps pack**: `market_listings` → `order_slots`; add `key_listings` and `belt_slots` with placeholder bases.
9. **Placeholder content conversion**: tiers, one or two classes, reference prices on every item; at least one action whose input is a class selector matched by two items of different reference price.

### Tests

- Parametrised validator failures: tier ≠ tier of unlock level; output of another tier without `off_tier`; input selector matching a higher-tier item; selector matching nothing; unknown category.
- `pay_selector`: cheapest first, tie broken by id, spans several items, reports shortfall without partial withdrawal.
- Resolver with a class input consumes the cheaper item first across a batch, then the other; conservation property still holds.
- Character creation creates rows for all eight fixed skills.

### Remove

`crafting` naming everywhere; `market_listings`; old action field names; the old combat placeholder skill.

### Out of scope

Enforcing `requires` (05); the `economy` pack (first created when a prompt needs it); demand-line class rules (13).

### Review focus

Every later selector payment must be able to call `pay_selector`; check it is in the engine and pure. Renames are complete in the client too.

