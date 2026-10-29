## Prompt 03 — Regression beats a passed upgrade

**ID:** `03-regression-precedence` · **Needs:** 02 · **Source:** Q5 · **Design:** §12.5, §12.6, §14.7, §19.6

### Ruling

**Q5:** "If a realm upgrade vote passes, yet the realm regresses somehow before the realm upgrade would occur, then the realm regression would take precedence causing the realm upgrade to fail."

### Goal

A passed upgrade whose transition is still pending fails if the realm meets the regression condition before it completes. The regression transition takes its place.

### Build

1. Find every way a realm can meet the regression condition (§14.7) while an upgrade transition is pending. §12.6 suspends shedding during a transition, so under v0.8 rules regression may be unreachable then.
   - **Orchestrator's reading:** while an upgrade transition is pending, the regression check in §14.7 still runs every tick. Treat a realm that is Failing and holds no tag of its current node as regressed, exactly as if no transition were pending.
   - Shedding stays suspended (§12.6). If you find that this reading makes the ruling unreachable, record that under **Ratification needed** and stop.
2. When regression wins:
   - the pending upgrade is cancelled and the vote is recorded as failed;
   - the fee is kept (§12.5);
   - `vote_cooldown_until` is set from the moment of cancellation;
   - a regression transition starts at that instant with its normal §12.6 effects.

   Keys already deprecated stay deprecated.
3. Keep the v0.8 interim rule for the case of a vote that closes with a yes-majority while a transition is already pending or the edge has vanished. Q5 confirms its direction. Remove its "interim" labelling.
4. Show the failed upgrade with its reason (e.g. `REGRESSED`) in the realm and vote responses and the client.

### Tests

- A realm with a pending upgrade transition that reaches the regression condition gets a regression transition. The upgrade never completes, and the vote is failed with the fee kept and the cooldown set.
- Lazy catch-up across the regression instant gives the same result as resolving tick by tick.
- An upgrade with no regression still completes as before.
- The keys of the realm follow §19.6 for the regression transition.

### Out of scope

Changing shedding or decay rates.

### Review focus

Exact timestamps (the cancellation and regression start), idempotence of `finalize_realm`, and no double transition.
