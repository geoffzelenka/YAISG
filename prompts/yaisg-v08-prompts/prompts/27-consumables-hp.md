## Prompt 27 — Belt, utility, buffs, hit points

**ID:** `27-consumables-hp` · **Workstream:** M · **Needs:** 26 · **Design:** §7.1 (C), §9.3, §9.4 · **Vision:** V§6.3, V§12.3.3

### Goal

Set-up for consumables, timed buffs as bonus group C, and lazily regenerating hit points.

### Build

1. **Item `consumable` block**: `heal`, or `buff {modifiers, duration_ms}`, or `utility_for` (an attack style).
2. **`PUT /equipment/utility`** (one stack in the `utility` slot) and **`PUT /equipment/belt/{slot}`** with `{item_id, quantity, trigger}` (`hp_below_pct` or `buff_missing`). Belt positions = the belt's `belt_slots` plus the `belt_slots` cap. `character_belt` table.
3. **Buffs outside combat**: `character_buffs (character_id, item_id, expires_at)`; active buffs feed group C for the actions they scope. Exploration's use of buffs is Prompt 31.
4. **Hit points** (§9.4): `characters.hp`, `hp_updated_at`; `max_hp` from Vigor level and armour (formula constants in `progression.combat`); lazy regeneration at `regen_per_min` (*default* 1% of max per minute). Reported on the profile.
5. Goods held in utility and belt are a conservation holder.

### Tests

- Belt capacity from belt plus cap; trigger validation.
- A buff's modifier applies in group C until `expires_at` and not after (segment boundary at expiry).
- HP regeneration math and the max clamp.
- Conservation suite extended to utility and belt.

### Out of scope

Consumption during combat (29).

