## Prompt 03 — Source groups, multiplication, XP cap, proficiency, taper

**ID:** `03-bonus-model` · **Workstream:** B · **Needs:** 02 · **Design:** §7.1–7.3, §8.1–8.2, §6.4 (changes), D1, D2 · **Vision:** V§3.3.3, V§3.4, V§4.4, V§4.6

### Goal

Replace additive stacking with the five-source multiplicative model, the XP cap, and tier proficiency and taper.

### Build

1. **Source groups** G, E, R, C, P (§7.1). G and C are empty providers until Prompts 26–27. E is the estate form plus non-inert upgrades, contributing only when the estate's realm equals the character's realm (the predicate is written now; Prompt 06 renames the column). R is the current realm's node modifiers (tags join in Prompt 05). P is proficiency.
2. **Combining** (§7.2): `factor(group) = max(min_factor, 1 + Σpct/100)`; `total = ΠG,E,R,C,P`. `min_factor` (*default* 0.25) in `progression`. Modifier scope is a skill, a category, or all. Types never combine with each other.
3. **`cycle_speed_pct`** replaces `cycle_time_pct` (D2): `cycle_ms = max(min_cycle_ms, floor(base_cycle_ms / total))`. Add `min_cycle_ms` to `progression` (the design gives no default; choose a placeholder and record it). The validator rejects `cycle_time_pct`. Convert placeholder content.
4. **XP** (§7.3, D1): `xp = floor(base_xp × min(total, 1 + xp_bonus_cap_pct/100) × taper)`, `xp_bonus_cap_pct = 45` in `progression`. Cycle speed is not capped.
5. **Drop chance**: `clamp(base_chance × total, 0, 1)`.
6. **Proficiency and taper tables** (§8.1, §8.2) in `progression`, keyed by category and tier distance, including the combat offensive row of the taper table (used in 29). Tier distance = `max(0, character tier in the action's skill − action tier)`. Proficiency feeds only `cycle_speed_pct` as group P.
7. **Segmentation.** A tier change inside a batch is a segment boundary, like a level-up.
8. **Reporting.** The profile and `GET /actions/available` report, per action: effective cycle ms, XP per cycle, the XP bonus uncapped and capped, proficiency percentage and taper factor.

### Tests

- The vision's example: two gear +5%, estate +10%, realm +20% of one type → 1.452 (feed G through a test provider).
- One group of several sources adds; groups multiply; a group of maluses floors at 0.25.
- XP cap clamps at 1.45 and both figures are reported.
- Every cell of both tables, parametrised against literal expected values from the design (not read back from content).
- A tier-up inside a batch changes subsequent cycle time and XP (crafted content).
- Cycle time never below `min_cycle_ms`; drop chance clamps at 1.
- Existing resolve associativity property still passes.

### Remove

Additive cross-source stacking, `cycle_time_pct`, and their tests.

### Out of scope

Gear, consumables, tags as bonus sources (wired by 05, 26, 27); the lint (04).

### Review focus

Taper is applied after the cap. Proficiency never touches XP. Floors where the design says floor.

