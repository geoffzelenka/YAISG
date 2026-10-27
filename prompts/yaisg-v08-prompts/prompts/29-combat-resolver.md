## Prompt 29 — The combat resolver

**ID:** `29-combat-resolver` · **Workstream:** N · **Needs:** 28 · **Design:** §8.2 (combat row), §9.2 (lock), §9.4, §10.4, §10.5 · **Vision:** V§4.5, V§6.2

### Goal

Fight cycle by cycle, online and offline, with two XP streams from two per-encounter pools.

### Build

1. **Start**: requires at least `min_engage_hp_pct` (*default* 25%) of max HP; choose and record a code. Equipment changes are rejected while a combat action runs.
2. **Cycle** in exactly the order of §10.5, steps 1–8: utility (ranged without ammunition → `OUT_OF_AMMO`); player attack clipped to the combatant's HP; combatant attacks from the carry; offensive XP `dealt × pool_offense / max_hp`, clipped, tapered by the combat taper row, split by stance (tapered-away XP still drains the pool); defensive XP to Vigor and Defense with `taken_to_defense_pct`; regeneration; at most one belt item by slot order; terminal checks (kill first, then defeat).
3. **Encounter state** in `meta`: combatant HP, both pools, carry, respawn remaining, buffs with expiry, running totals. Kill: roll drops into inventory under the overflow rule, discard pool remainders, wait `respawn_ms` (consumes budget without cycles), then a full new encounter. Defeat: `DEFEATED`, character idle and regenerating.
4. **Offline**: simulate within the offline budget; `combat.max_cycles_per_resolve` (*default* 50,000) ends with `OFFLINE_CAP`. HP persisted at the end.
5. **Summary `details`**: kills, defeats, damage dealt and taken, XP by skill, consumables used, loot, stop reason.

### Tests

- Pools drain once and refill only on respawn; remainder lost on kill.
- Ranged stops without ammunition; melee continues without its utility.
- Defeat ends the action; both at zero counts the kill then the defeat.
- Offline equals online polling for the same seed and timeline.
- Tapered offensive XP still drains the pool; the defensive stream is never tapered; drops never reduced.
- Twelve hours of two-second cycles resolve within a time bound in CI.

### Out of scope

Combat keys (31).

### Review focus

Step order literally §10.5; integer arithmetic; no per-character background loop.

