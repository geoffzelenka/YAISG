# Tech debt

Known, accepted shortcomings to revisit later. Each entry states the behavior,
why it is not a correctness bug, and the direction for a future fix. Add new
items at the top.

## Reward feed groups by poll, not by cycle (client, UI polish)

**Area:** `client/src/features/actions/` (reward toasts / feed), phase notes 3.3.

**Behavior:** Reward toasts and the feed report everything accrued *since the
last poll*, not one entry per cycle. The client poll schedule is jittered
(±10%, `actionStore.ts` `nextCycleDelay`), so a poll can land just before a
cycle boundary and resolve zero cycles; the following poll then resolves two and
surfaces as a single "double XP" toast (e.g. 110 instead of 55 gathering XP).

**Why it is not a bug:** This is display grouping only. Persisted XP and item
totals are correct and never double-counted — the engine advances
`last_resolved_at` by exactly the cycles consumed (`app/engine/core.py`) and the
feed is claimed at-most-once (`app/services/actions.py` `claim_rewards`), per
`design/design.md` v0.8 §6.4. The cosmetic progress clock does not award
rewards; polling consumes server results. `actionStore.test.ts` covers bounded
poll jitter and `ActionExperience.test.tsx` covers the displayed reward envelope.

**v0.8 status:** Still open. `ActionExperience.tsx` renders one `RewardSummary`
per reward envelope, and `summarize` totals its XP and items without a uniform
cycle-count label. Prompts 30 and 35 added combat and key/tutorial presentation;
`ResolverDetails.tsx` now supplies combat/travel details, and the welcome-back
dialog shows cycle totals, but ordinary uniform-action toasts remain grouped by
poll. See `ActionExperience.test.tsx` ("omits shared envelope fields from a
uniform-cycle toast"). The illustrative XP amounts above are not balance data.

**Direction:** On a UI polishing pass, normalize toasts to per-cycle
granularity or otherwise signal multi-cycle catch-up (e.g. "×2 cycles") so a
single toast is not misread as double reward for one cycle.
