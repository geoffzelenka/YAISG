## Prompt 14 — The realm tick and the scheduled job

**ID:** `14-realm-tick` · **Workstream:** G · **Needs:** 13 · **Design:** §13.6, §14.4, §14.5, §23.2 · **Vision:** V§8.6, V§8.8.1–8.8.2, V§9.4.9–9.4.10

### Goal

Make realms and their estates eat, produce and spoil, and guarantee realms advance even when nobody looks.

### Build

Fill the tick steps of Prompt 10's framework in §14.5 order:

1. **Step 0**: caravan arrivals (no-op hook for 20).
2. **Step 1**: each estate's production into the realm's stores, scaled by a stage factor hook (1.0 until 15); inert forms produce nothing; realm-owned estates produce too.
3. **Step 2**: estates take upkeep from their larder.
4. **Step 3**: estates still short take from stores above each line's reserve, shared pro rata to what each is owed when short.
5. **Step 4**: the realm takes its own upkeep (node, tags; mint hook for 18), allowed below reserve. Record unmet line units per tick for Prompt 15's gauge.
6. **Step 5**: the realm contributes to its funding project from stock above reserve, up to the tick's share of the overlay; then erosion (from 10).
7. **Step 6**: spoilage pro rata to the tick from stores and larders.
8. **Step 7**: anything above a cap is lost; for a line, from its most plentiful item first.
9. **Step 10**: recompute `realm_lines` (budgets and band arrive in 16).

Estates with no upkeep and no production are skipped. Steps 1–3 are set-based (one upsert per item; estates loaded in one query per realm). Integer arithmetic only, no randomness.

**Scheduled job** (§23.2): one APScheduler in the game service runs `resolve_realm` for every non-isolated realm each tick, under a PostgreSQL advisory lock so only one process fires (single-process on SQLite). Requests still resolve realms themselves; the job is a liveness driver.

### Tests

- A golden multi-tick scenario that exercises "above the reserve, estates eat first; below it, the realm eats first".
- `resolve_realm` twice equals once; catch-up of *n* ticks equals *n* single ticks.
- Pro rata sharing between estates; spoilage; cap loss from the most plentiful item.
- With no players, a funded project completes in about `realm_completion_days` from the overlay alone.
- Production is credited to the realm's stores and never to the owner.
- Two scheduler instances on PostgreSQL run each tick once.

### Out of scope

Gauges, stages and decay (15); prices and budgets (16).

### Review focus

Tick order is literally §14.5. No gold moves in the tick in this prompt.

