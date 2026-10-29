## Prompt 02 — Fixed-rate project overlay

**ID:** `02-project-overlay` · **Needs:** 01 · **Source:** Q3, F9 · **Design:** §14.4, §14.5 step 5, §12.3 · **Vision:** V§9.4.6

### Ruling

**Q3:** "Use a Fixed Rate draw on realm reserves for project contribution". The full rule is recorded in `docs/v08/conformance.md`, "Human rulings already given".

### Goal

With no player help, a funded project completes in `realm_completion_days`. The v0.8 overlay (`remaining / D`) decays geometrically and can stall on rounding, so an unhelped project never completes.

### Build

1. At kickoff, fix each cost line's per-tick realm payment:

   ```
   rate = ceil(original requirement / (tick.per_day × realm_completion_days))   # whole milli-units
   ```

   Store it on the run, or derive it deterministically from immutable run fields. It must not change as the remainder shrinks.
2. **Step 5** of the tick: each funding line takes `min(rate, remaining need, stock above the reserve)`. A fully funded line stops drawing. Player contributions shorten the run but don't change `rate`.
3. The extra draw the overlay adds to a line (§14.4, used by reserves and pricing) becomes `rate × tick.per_day` per day while the line still needs goods, and 0 once it is funded. Record this under Deviations as §14.4 superseded by Q3.
4. Idle erosion (§12.3) is unchanged. A realm payment still counts as a contribution for the idle clock.

### Tests

- At the default hourly cadence, with D = 1 and D > 1 and no players, a funded project completes within `realm_completion_days` (exactly, when stock allows). Extend `test_realm_overlay_completes_without_player_contributions`.
- Player contributions shorten completion and leave the per-tick realm payment unchanged until the remainder is below it.
- A line with no stock above the reserve pays nothing and doesn't stall others.
- Hypothesis: catch-up of n ticks equals n single ticks with the new rate.
- Rewrite the v0.8 geometric-overlay regression tests to pin the fixed rate (list them under Removed).

### Out of scope

Changing `realm_completion_days` content values.

### Review focus

Rounding is a ceiling and in milli-units. The rate is immutable for the run. Conservation of goods holds, and only stock above the reserve is used.
