# Tech debt

Known, accepted shortcomings to revisit later. Each entry states the behavior,
why it is not a correctness bug, and the direction for a future fix. Add new
items at the top.

## Reward feed groups by poll, not by cycle (client, UI polish)

**Area:** `client/src/features/actions/` (reward toasts / feed), phase notes 3.3.

**Behavior:** Reward toasts and the feed report everything accrued *since the
last poll*, not one entry per cycle. The poll timer is cosmetic and jittered
(±10%, `actionStore.ts` `nextCycleDelay`), so a poll can land just before a
cycle boundary and resolve zero cycles; the following poll then resolves two and
surfaces as a single "double XP" toast (e.g. 110 instead of 55 gathering XP).

**Why it is not a bug:** This is display grouping only. Persisted XP and item
totals are correct and never double-counted — the engine advances
`last_resolved_at` by exactly the cycles consumed (`app/engine/core.py`) and the
feed is claimed at-most-once (`app/services/actions.py` `claim_rewards`), per
`design/design.md` §9.2. Verified: across a jittered polling simulation every
feed entry's XP equalled `cycles × per-cycle XP`.

**Direction:** On a UI polishing pass, normalize toasts to per-cycle
granularity or otherwise signal multi-cycle catch-up (e.g. "×2 cycles") so a
single toast is not misread as double reward for one cycle.
