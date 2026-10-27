## Prompt 28 — Combatants, stats, the hit, stance, combat lint

**ID:** `28-combat-model` · **Workstream:** N · **Needs:** 27 · **Design:** §10.1–10.4, §10.6, D12 · **Vision:** V§3.7, V§4.5, V§6.1

### Goal

The combat data model and the pure arithmetic the resolver will use.

### Build

1. **`combatants` pack** (§10.2). Drop tables may hold bullion; there is no gold field.
2. **Combat actions**: listed in `node.actions`, each naming a combatant and a location label; resolver `combat`.
3. **Pure stat functions** (§10.3): `eff(skill) = level × (1 + 0.05 × (tier − 1))` for the five non-Vigor skills; attack rating, max hit, defense rating, armour, max HP and cycle time with their bonus types; content-defined unarmed weapon; style from the equipped weapon.
4. **Pure `attack(attacker, defender, rng)`** (§10.3): `p_hit` clamped to [0.05, 0.95]; damage rolled whether or not it lands; weakness ×1.25, resistance ×0.75 (floor); armour block on a hit; returns dealt and mitigated. Constants in `progression.combat`.
5. **Tier effectiveness** (§10.4): `progression.combat_effectiveness[distance]` as group P for accuracy, power and defense (not HP, not cycle time).
6. **Stance**: `characters.stance`, `PUT /characters/me/stance`, stances and splits in `progression.stances`.
7. **Combat lint** (§10.6) added to `make content-lint`: per combatant, expected time to kill plus respawn for a standard-geared player at unlock level, and whether each pool share gives about `target_xp_per_hour` for the receiving skill.

### Tests

- `eff` per tier; Vigor has no multiplier.
- `p_hit` bounds; weakness and resistance rounding; a miss still yields mitigated damage.
- Effectiveness applies to the three stats only.
- Stance change persists; lint flags an oversized pool.

### Out of scope

The resolver (29).

