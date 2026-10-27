## Prompt 04 — XP-rate content lint

**ID:** `04-content-lint` · **Workstream:** B · **Needs:** 03 · **Design:** §5.2, §7.3 (stack lint) · **Vision:** V§3.3.2, V§3.5–3.6

### Goal

Give the content designer a report of every non-combat action against the time-budget anchors. Warning-only; never fails CI.

### Build

1. `make content-lint` (and a CI step that prints the report and exits 0). Output both human-readable text and JSON.
2. `target_xp_per_hour(U) = R1 · g^(U−1)`, `R1 = 10,000,000 / 2,880`, `g` in `progression.lint` (*default* 1.015969), tolerance (*default* ±15%).
3. For each non-combat skill: each action's XP/h from `xp` and `base_cycle_ms`; actions outside tolerance listed unless `off_curve` is set; simulated hours 1→100 using the best unlocked action at each level, unbonused, no input constraints, reported against 720; the level-1 action alone, reported against 2,880.
4. **Stack lint**: per skill, an upper bound of `xp_pct total × cycle_speed_pct total` obtainable from content outside proficiency (best combination per group from nodes and tags offered there, forms and upgrades within slots, and later gear and consumables). Warn above 1.45. Document how the bound is computed.
5. Combat is skipped here; Prompt 28 adds per-combatant checks.

### Tests

- Target values match the §5.2 table at 1, 50 and 95 within rounding.
- Synthetic content with a new on-curve action every level → ≈ 720 h; a ten-level ladder at `g = 1.015969` → ≈ 778 h; at `g = 1.016938` → ≈ 720 h; the level-1 action alone → 2,880 h.
- `off_curve` suppresses the warning; the stack warning fires for a crafted over-stacked skill.
- The CI step exits 0 even with warnings.

### Out of scope

Changing content to satisfy the lint.

### Review focus

The simulations are exact arithmetic over the XP table, not sampling.

