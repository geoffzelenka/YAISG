## Prompt 10 — Project runs and `resolve_realm`

**ID:** `10-project-runs` · **Workstream:** E · **Needs:** 09 · **Design:** §12.3, §12.4 (credits), §14.5 (skeleton), D6, D14 · **Vision:** V§7.7.1

### Goal

Implement the project lifecycle and introduce the lazy, idempotent realm resolver that every later realm feature plugs into.

### Build

1. **`realm_project_runs`** (§12.3); `realm_contributions` gains `run_id` and a nullable `character_id` (null = the realm). `characters.last_kickoff_at`.
2. **`POST /realms/{id}/projects/{project_id}/kickoff`** with every condition and code in the §12.3 table, in that order: `NOT_PRESENT`, `RESIDENTS_ONLY`, `PROJECT_NOT_OFFERED`, `PROJECT_ACTIVE`, `REALM_VOTING`, `REALM_TRANSITIONING`, `PROJECT_COOLDOWN`, `KICKOFF_LIMIT`, `MISSING_INPUTS`. `REALM_VOTING` checks a function that returns false until Prompt 19 wires it. Kickoff gold goes to the realm treasury; kickoff goods are consumed (D14).
3. **`POST /realms/{id}/project/contribute {item_id, quantity}`**: presence required, residence not; clamped to what the matching cost line still needs; goods consumed; a contribution row per call; resets the idle clock. When every line is met: `building`, `build_completes_at = now + build_seconds`.
4. **`resolve_realm(realm, now)`** under the realm's row lock: first finalise timed events at their exact due times in time order (vote close: stub for 19; build completion: push the tag and mark the run complete; transition completion: `finalize_realm`); then apply whole ticks since `last_tick_at` at `tick.per_day` (*default* 24), at most `tick.max_catchup` (*default* 72) per call. A tick is an ordered list of step functions numbered as in §14.5. In this prompt only project erosion is real; the other steps are named no-ops that Prompts 14–15 fill in. Every read or write of a realm's projects calls it first; `resolve_character` calls it for the current realm (character lock first).
5. **Idle erosion** (§12.3): after `idle_grace_days` (*default* 2) without a contribution (realm contributions count), each tick every line's contributed amount falls by `erosion_pct_per_day` (*default* 20) of its required amount, pro rata to the tick. All at zero: the run fails and the project enters `fail_cooldown_hours` (*default* 36). Settings in `economy.project`.
6. **Reads.** `GET /realms/{id}` adds the active run (required, contributed, status, `stalled`). `GET /realms/{id}/tags/{tag_id}` returns credits: who kicked off, total contributed per character, and the realm's own share.

### Tests

- Each kickoff code; the daily limit across two realms; presence for contribute; clamping and item conservation.
- A build completes at exactly `build_completes_at` even when the realm is first resolved days later, before any tick runs.
- Erosion arithmetic, failure, cooldown; any contribution resets the clock.
- `resolve_realm` twice equals once; catch-up beyond 72 ticks completes over successive calls; one active run per realm under a race (two kickoffs, PostgreSQL).

### Out of scope

Realm contribution from stores and the project overlay (13–14); votes (19).

### Review focus

The tick framework's step order and numbering must make Prompts 14–15 pure additions.

