## Prompt 05 — Interval hit-point regeneration; reachable defeat

**ID:** `05-hp-regen-interval` · **Needs:** 04 · **Source:** Q8 · **Design:** §9.4, §10.5 steps 3, 6 and 8 · **Vision:** V§6.2.2

### Ruling

**Q8:** "Player HP regeneration interval should occur at long enough interval that the player can reach a 0hp state."

### Goal

In v0.8, regeneration runs every cycle before the terminal check, so with the default content `DEFEATED` can never happen. Make regeneration discrete, on an authored interval, so a player can reach 0 HP and be defeated.

### Build

1. Add `progression.combat.regen_interval_ms` to the strict schema, with a placeholder default long enough that the default combatant can defeat a player at its unlock level.
   - Regeneration is applied in whole intervals: each completed interval since the anchor heals `regen_per_min × interval minutes × max_hp`, capped at `max_hp`.
   - Partial intervals carry over. They aren't lost and aren't granted early.
2. **One rule for idle and combat**, so offline equals online:
   - The lazy idle formula of §9.4 uses whole intervals since `hp_updated_at` and keeps the remainder.
   - The combat resolver's step 6 applies regeneration only on the cycles that complete an interval, carrying the rest in `active_actions.meta`.
   - Record under Deviations that §9.4's continuous formula is superseded by Q8.
3. Content validation, plus the lint where it fits: `regen_interval_ms` must be positive, and the lint warns when, for some authored combatant, a standard-gear player at the unlock level can't reach 0 HP because the interval heals more than the combatant deals per interval.
4. **Review nit N3 from v0.8 phase 29:** once the player is at 0 HP in step 3, the combatant's remaining carried attacks that cycle don't resolve and pay no defensive XP.
5. Remove `test_regeneration_rescues_zero_hp_before_terminal_check`'s revival rule (list it under Removed) and replace it with the interval behaviour.
6. The client shows HP regenerating in steps and, if useful, the time to the next regeneration.

### Tests

- With the shipped default content, a player who keeps fighting a combatant it can't beat reaches `DEFEATED`. Run it deterministically with a seeded RNG.
- Idle regeneration over arbitrary gaps equals the sum of whole intervals, with the remainder carried. Hypothesis: splitting a gap at any point gives the same HP and anchor.
- Combat offline equals combat polled online across interval boundaries.
- A belt heal can still rescue a player before step 8. Defeat is not a latch, Q8 does not remove belt rescue.
- No defensive XP is paid after 0 HP within a cycle (N3).

### Out of scope

Changing `regen_per_min`, `min_engage_hp_pct` or combat formulas other than step 6.

### Review focus

The interval anchor and its carry are exact integers in milliseconds. Online equals offline. Defeat is reachable with the default content and not only with authored zero regeneration.
