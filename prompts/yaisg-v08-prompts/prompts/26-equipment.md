## Prompt 26 — Equipment slots and gear bonuses

**ID:** `26-equipment` · **Workstream:** M · **Needs:** 25 · **Design:** §7.1 (G), §9.2 · **Vision:** V§12.3

### Goal

Permanent gear in slots, feeding bonus group G and satisfying tool requirements.

### Build

1. **Item `equip` block** (§9.2): slot (or `ring`/`arm` for either side), `two_handed`, `requires {skill: level}`, `modifiers`, `cap_bonuses`, `weapon`, `armour`, `tool_class`, `belt_slots`. Validator: `xp_pct` on gear only in the `cape` slot.
2. **`character_equipment (character_id, slot, item_id, quantity)`** with the §9.2 slots.
3. **`POST /equipment/equip`, `POST /equipment/unequip`**: equipping moves the item from inventory to the slot; unequipping needs a free inventory slot; a two-handed item in `right_hand` unequips `left_hand`; a left-hand item while two-handed is held is rejected; requirement levels checked. The current action is resolved first, then the change applied. Choose and record codes.
4. **Group G** reads every equipped item's modifiers and cap bonuses. `requires.tool_class` is met by a `right_hand` item of that class. No durability anywhere.
5. Placeholder content: a pickaxe tool with a cycle-speed bonus, a cape with an XP bonus, a two-handed item.

### Tests

- Slot rules and two-handed interactions; requirement levels.
- The tool satisfies `MISSING_TOOL`; its speed bonus enters group G; an equip mid-action applies from that moment.
- Validator rejects `xp_pct` outside the cape.
- Goods conservation suite extended to equipment slots.

### Out of scope

Belt, utility, combat stats (27–29).

### Review focus

Gear is never consumed or degraded.

