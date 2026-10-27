## Prompt 07 — Map edges, journeys, the Travel skill

**ID:** `07-travel` · **Workstream:** D · **Needs:** 06 · **Design:** §8.3 (Travel), §11.1, §11.3, §11.4, §13.2 (`mobility`, `travel_profile`), §13.3 (`ESTATE_BUSY`), §22 · **Vision:** V§3.8, V§11

### Goal

Replace gold-priced relocation with journeys: a Travel skill action, one cycle per edge, paid in time and supplies.

### Build

1. **Edge shape** (§11.1): `terrain`, `base_time_s`, `supplies` (selectors), `min_travel_level`, `base_loss_pct`, `one_way`. Validate ranges.
2. **Forms** gain `mobility` and `travel_profile {time_mult, supply_mult, terrains}` (mobile only). The rest of the form reshape is Prompt 11. `progression` gains `visit_profile`, `travel_xp_per_second`, and Travel `tier_benefits` (`journey_speed_pct`, `supply_reduction_pct` per tier).
3. **Routing.** Cheapest path by total base time over edges whose terrain is in the traveller's profile and whose `min_travel_level` ≤ Travel level; ties by fewest edges, then edge ids. `NO_ROUTE` otherwise. Replaces `path_cost`.
4. **`POST /travel/start {destination_realm_id, mode}`** and **`GET /travel/preview`** (route, time and supplies per edge). `relocate` needs a mobile estate in the current realm; `visit` leaves the estate. Choose and record codes for "already there", "fixed estate cannot relocate" and "estate not here".
5. **Travel resolver** (§11.3): route fixed in `meta`; each step takes supplies at step start via `pay_selector` (`OUT_OF_SUPPLIES` ends the journey in the current realm), lasts the effective time, and at step end moves `current_realm_id` (and the estate when relocating) and grants `floor(base_time_s × travel_xp_per_second)` XP.
6. **Step cost** (§11.4): `time = base × time_mult / total(journey_speed_pct)`, `supplies = ceil(q × supply_mult / total(supply_reduction_pct))`, totals combined by §7.2 with the Travel tier benefit as group P.
7. **Stop and offline.** Stopping keeps the last completed realm; the partial step and its supplies are lost. Journeys run offline within the offline cap. Details: edges completed, supplies used, XP, current realm. Starting another action ends the journey.
8. **`ESTATE_BUSY`** on transform while a relocate journey runs.
9. **`GET /map`** reshaped: edges with the new fields; per realm node, tier, `decay_stage`, `treasury_band` (null until 16), `transition_pending`.

### Tests

- A water-only profile cannot relocate over land (`NO_ROUTE`); a Travel-level gate opens a shortcut; tie-breaks.
- Supplies taken per step; `OUT_OF_SUPPLIES` leaves the character in the step's start realm.
- Property: for random stop times along a route, the character is always in exactly one realm, and it is the realm of the last completed step.
- Relocate moves the estate step by step; visit does not.
- XP per edge depends on base time only (unchanged by a speed bonus); supply reduction uses `ceil`.
- Offline resolution equals step-by-step online polling for the same timeline.
- Removed endpoints return 404.

### Remove

`GET/POST /characters/me/relocate*`, `relocation_cost`, gold `path_cost`, `estates.relocating_to_realm_id`, `estates.relocation_completes_at`, and the client's relocate controls (Prompt 08 rebuilds travel UI).

### Out of scope

Caravans (20); remoteness (20); tutorial edges (34).

### Review focus

No between-realms state anywhere (V§11.3.1). XP from base time.

