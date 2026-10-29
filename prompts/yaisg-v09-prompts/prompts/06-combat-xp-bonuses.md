## Prompt 06 — XP bonuses on combat pools

**ID:** `06-combat-xp-bonuses` · **Needs:** 05 · **Source:** Q9 · **Design:** §7.2, §7.3, §8.2, §10.5 steps 4–5, §10.6 · **Vision:** V§4.5

### Ruling

**Q9:** "Bonus XP gain modifiers should also apply to combat skills gains, the bonuses apply AFTER base xp is removed from the pool."

### Goal

Combat XP gets the same `xp_pct` bonuses as any other action. The pool limits only the base amount, so bonuses never drain the pool faster.

### Build

1. In §10.5 steps 4 and 5, compute the base XP exactly as v0.8 does: offensive XP is clipped to the remaining pool and times the taper; defensive XP is clipped to the remaining pool. Subtract that base from the pool.
2. Then multiply each skill's gain by the action's combined `xp_pct` total, with the §7.3 cap (1.45) applied as for every action. The bonus part is extra and doesn't come from the pool.
   - **Orchestrator's reading:** the cap is the general `xp_bonus_cap_pct`. Bonuses come from the same source groups as non-combat actions (§7.1–7.2), scoped to each receiving skill: style, Accuracy, Vigor or Defense.
3. Report uncapped and capped bonus figures for combat in the action and profile responses, as §7.3 requires for other actions.
4. Update the combat lint (§10.6) so its per-hour estimate includes the bonus bound. Keep the conservative bound of §7.3.
5. Update the resolver `details` and the client summary to show base and bonus XP.

### Tests

- With a 20% scoped XP bonus, the pool drains by the base only and each skill gains base × 1.2, for both offensive and defensive streams.
- The cap applies: bonuses summing above 45% give 1.45×.
- A bonus scoped to one combat skill doesn't affect the other skills in the split.
- Offline equals online, and a drained pool yields no bonus.
- The lint reflects the bonus bound.
- Rewrite the v0.8 test that pins combat ignoring `xp_pct` (list it under Removed).

### Out of scope

Changing pool sizes or the stance split.

### Review focus

The bonus is applied after the pool subtraction, not before. Rounding follows the existing XP rounding rules. No double application of the taper.
