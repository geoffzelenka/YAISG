## Prompt 09 — Closed-form uniform resolution

**ID:** `09-uniform-closed-form` · **Needs:** 08 · **Source:** F3 (v0.8 00 and 06 hand-offs) · **Design:** §6.3, §6.4

### Goal

§6.3 describes the uniform resolver as a closed-form batch segmented at level-ups. v0.8 still rolls each cycle. Make it closed-form without changing a single result.

### Build

1. Resolve whole cycles in batches between segment boundaries. Boundaries are:
   - level-ups and tier changes;
   - buff expiries (§9.3);
   - input exhaustion and inventory overflow (overflow takes precedence over inputs in the same cycle, §6.4);
   - key uses (§19.4);
   - requirement loss.
2. Preserve the seeded reward order: the RNG draw sequence for drops must produce the same items in the same order as the per-cycle loop for the same seed, or the change must be justified as statistically and observably identical. Record which you chose. If exact equality is impossible, ask for ratification rather than change results.
3. Keep the per-cycle loop available as a reference implementation in tests only.
4. The combat resolver keeps its bounded stepped loop, and the travel resolver is unchanged.

### Tests

- Hypothesis: for random content, state, budgets and seeds, the closed-form result equals the reference loop: XP, items, consumed inputs, stop reason, `last_resolved_at` and partial-cycle carry.
- All existing golden tests pass unchanged.
- A 12-hour offline resolve of a fast action runs in bounded time and uses no per-cycle iteration. Assert an operation count, not wall-clock time.

### Out of scope

Combat closed form (§10.5 says there is none).

### Review focus

Exact equivalence with the reference. Every §6.4 boundary is a segment boundary.
