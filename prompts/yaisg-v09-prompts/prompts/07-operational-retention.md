## Prompt 07 — Allowance pruning and metric compaction

**ID:** `07-operational-retention` · **Needs:** 06 · **Source:** F1, and the v0.8 37 review nits · **Design:** §23.1, §23.2, §23.6

### Goal

Bounded operational tables that can't interfere with gameplay.

### Build

1. **Allowance pruning.** A scheduled maintenance job deletes stale `mutation_windows` rows. It runs in bounded batches, each in its own transaction:
   - PostgreSQL uses `FOR UPDATE SKIP LOCKED`, and rechecks staleness under the lock.
   - A request path never deletes another account's row.
   - Add back the window index only if the job's query needs it.
2. **Metric compaction.**
   - Move `compact_deltas` out of the all-realm lifecycle transaction (`services/game/app/services/market_lifecycle.py:53`) into its own transaction after that commit.
   - Fix the `ORDER BY name, id LIMIT 1000` starvation (`services/game/app/services/metrics.py:63`), so that every counter makes progress each pass, e.g. a per-name budget or a round-robin cursor.
3. In `services/game/tests/test_conformance.py:754`, add `SET LOCAL lock_timeout` so a SKIP LOCKED regression fails instead of hanging. Do the same in every new PG locking test.
4. Document retention behaviour and tunables in the README's configuration table.

### Tests

- On PostgreSQL, the pruning job racing live mutations never deletes a row in use, never deadlocks, and keeps rate limits correct across the prune.
- Compaction preserves every counter's totals, every counter progresses under sustained load, and a compaction failure doesn't roll back order expiry or purge.
- Lock-timeout guards fail fast when SKIP LOCKED is removed (mutation check in review).

### Out of scope

Changing rate-limit semantics or counter definitions.

### Review focus

Lock order (§23.1); no request-path cross-account writes; bounded work per pass.
