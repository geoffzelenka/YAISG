## Prompt 01 — Schema reset, XP curve, levels to 100, tiers, zero gold

**ID:** `01-foundation` · **Workstream:** A · **Needs:** 00 · **Design:** §5.1, §5.3 (thresholds), §18, §21 · **Vision:** V§3.1–3.3

### Goal

Reset the game database baseline for destructive pre-release work, replace the XP curve with the vision's curve to level 100, introduce skill tiers, and remove starting gold.

### Build

1. **Migration baseline.** Collapse the game service's Alembic history into a single `v08_0000_baseline` that creates the current schema on both databases. Add `make db-reset` (game and auth) that drops the development databases and upgrades to head. Document the policy in `codebase-map.md`: later prompts add migrations freely and destructively.
2. **XP table.** Add `scripts/gen_xp_curve.py` that computes `xp(L) = floor(A · r^L)` for `L = 1…99`, `r = 2^(1/7)`, finding the `A` for which the floored values sum to exactly 10,000,000 using high-precision `decimal` arithmetic. Check the output in as `content/xp_curve.json` (99 integers). The server never recomputes it.
3. **Boot validation** of the table: 99 entries, strictly increasing, sum exactly 10,000,000. The table remains part of the content version hash and is not served as a pack.
4. **Levels 1–100.** `level_for_xp` reads the per-level table (cumulative sums). XP keeps accumulating past 10,000,000 with no further level. `character_skills.xp` becomes a 64-bit integer. The profile reports XP to next level, `null` at 100.
5. **`progression` pack** (new, served, strict schema that later prompts extend): `tier_thresholds = [1, 50, 75, 90, 95]` and tier titles (placeholder text). Pure `tier_for_level(level, thresholds)`. Boot validation: thresholds strictly increasing, first is 1, last ≤ 100. The profile reports tier and tier title per skill.
6. **Zero starting gold.** Remove the starting-gold grant and its constant. New characters have 0 gold.

### Tests

- The table matches design §5.1 exactly: steps 1→2 = 57, 50→51 = 7,365, 75→76 = 87,564, 90→91 = 386,714, 93→94 = 520,478, 95→96 = 634,470, 99→100 = 942,820, and cumulative values 70,189 / 840,648 / 3,714,612 / 4,999,703 / 6,094,836 / 9,057,180.
- Halfway: cumulative XP to reach 93 < 5,000,000 ≤ cumulative XP to reach 94.
- `level_for_xp` at every boundary ±1 for a sample of levels, at exactly 10,000,000 (level 100) and far beyond (still 100).
- `tier_for_level` at 1, 49, 50, 74, 75, 89, 90, 94, 95, 100.
- Boot rejects a table of 98 entries, a non-increasing table, and a table summing to 9,999,999 (parametrised fixtures).
- A new character has 0 gold.
- `make db-reset` followed by the full suite passes on both databases.

### Remove

The cumulative `1.12` curve, its generator and its tests; level cap 99; the starting-gold constant.

### Out of scope

Bonus changes; action and item tiers (Prompt 02).

### Review focus

The generator must find `A` by exact search, not by trusting the quoted `52.120034248…`. Rounding is `floor`. No curve math at boot.

