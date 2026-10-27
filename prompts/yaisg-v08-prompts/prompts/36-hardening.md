## Prompt 36 — Rate limits, counters, load, seed-check in CI

**ID:** `36-hardening` · **Workstream:** R · **Needs:** 35 · **Design:** §23.2–23.6

### Build

1. Per-character rate limits on game mutation endpoints, with a stable `RATE_LIMITED` code and configurable limits.
2. Counters (§23.6): ticks run and duration, gold minted, gold by holder type, matches and tax, realm trades, caravan shipments and losses, tags shed, regressions, keys discovered. Exposed on an operator endpoint or a metrics endpoint.
3. `make seed-check` runs in CI and fails the build.
4. A k6 (or equivalent) load script for polling, realm reads and market inserts, with a documented baseline run.
5. Confirm the scheduled job's advisory lock under two processes.

### Tests

Rate-limit behaviour; counters increment on their events; seed-check in CI.

