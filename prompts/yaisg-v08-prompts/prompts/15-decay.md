## Prompt 15 — Gauges, stages, shedding, regression, seed-check

**ID:** `15-decay` · **Workstream:** G · **Needs:** 14 · **Design:** §13.7, §14.6, §14.7, §14.9 (seed-check), D4, D11 · **Vision:** V§7.5, V§7.7.3, V§8.8.3, V§8.8.5, V§9.4.11–9.4.12

### Goal

Make hunger visible and, if it persists, destructive in the slow, recoverable way the vision describes.

### Build

1. **Step 8** gauges (§14.6) for the realm (its own upkeep only) and each estate: `unmet_share` weighted by reference value, rising by `unmet_share / T`, recovering at `recovery_per_day / T`, capped at `gauge.max`. Defaults in `economy.gauge`.
2. **Stages** Fed / Strained / Faltering / Failing / Regressed from thresholds (*defaults* 0.5, 2, 4 days). Prompt 05's stage effects now take the live stage. Estate Faltering also scales estate bonuses and production by `faltering_factor` (Prompt 14's hook).
3. **Step 9 realm shedding** (§14.7, D4): while Failing and no transition pending, `shed_progress` grows by `(base + per_gauge_day × (gauge − threshold)) / T`; at ≥ 1 remove the highest-`seq` tag whose `node_id` is the current node (credits survive in runs and contributions). With no such tag, start a regression transition (Prompt 09). The barren root stays Failing. Below Failing, `shed_progress` drains at `shed.recovery_per_day`.
4. **Step 9 estate decay** (§13.7): Failing removes installed upgrades, most recently purchased first, at the shed rate; with none left, the form drops to `regresses_to` with the gauge reset; with no `regresses_to` the estate is destroyed. A destroyed player estate is replaced by a `basic_mobile_form` estate in the owner's current realm.
5. **Visibility.** Stage and gauge days on `/map`, `/realms/{id}`, and estate lists (Strained shown to the owner).
6. **`make seed-check`**: run the tick over the seeded, player-less world for 30 simulated days; report each realm's gauge, treasury and stores; fail if any realm reaches Faltering. (Prompt 16 adds the funded-bid clause.)

### Tests

- Strained has no mechanical effect: every engine output for a realm and its characters is identical at Fed and Strained.
- Gauge weighting (an expensive missing good counts more); recovery cancels hunger day for day.
- Shed order and rate; no shedding during a transition; recovery drains progress.
- D4 scenario: tags survive a tier-up; regression starts only when no tag of the current node remains; surviving tags are restamped.
- Estate chain: upgrades shed, form regresses, estate destroyed, player receives a basic mobile estate.
- `seed-check` passes on placeholder content and fails on a starving fixture.

### Out of scope

Market prices; votes.

### Review focus

The vision's "Strained must stay purely cosmetic" is a test, not a comment. Lost tags never return automatically.

