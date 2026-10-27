## Built

- Strict map edges with ids, endpoints, terrain, positive base seconds, selector
  supplies, Travel level gates, bounded loss percentages and one-way traversal.
  Mobile forms require a travel profile; fixed forms forbid one. Progression
  owns the visit profile, base-time XP rate and one Travel benefit row per tier.
- Pure time-based routing orders by total base time, edge count, then the full
  edge-id sequence, filtering terrain and level before searching. Routing and
  step arithmetic use exact fractions of authored decimal values, avoiding
  false ties, extra ceil charges and lost floor XP from binary float artifacts.
- Authenticated GET /travel/preview and POST /travel/start. Preview resolves
  prior work but starts no journey and charges no new supplies. It estimates
  each step using current realm snapshots and predicted Travel tier changes.
  Start fixes the route in action metadata and immediately pays the first step.
- TravelResolver registered alongside UniformResolver. Each paid step retains
  its duration and remaining milliseconds in metadata. Arrival changes presence,
  moves the estate only in relocate mode, grants floor(base seconds × XP rate),
  switches realm sources and prices the next step. Selector payments are atomic
  across overlapping supply lines. Shortfall stops in the step's starting realm.
- Partial progress persists across polls. Stop or another action discards the
  partial step and its paid supplies. The offline cap also stops a partial travel
  step when no full edge fits. Completed journeys end naturally. Details report
  edge ids completed, actual supplies used, XP and current realm; reward logs
  retain the existing transactional claim-once feed.
- Adapter writes presence and estate location with skills/inventory. It locks
  the character, sorted route realms, then estate. Start/preview conservatively
  lock all realm candidates before the estate so replacing an active journey
  does not acquire new realm locks out of order. A locked resolve entry point
  allows the immediate first payment without releasing SQLite's writer lock.
- Transform returns ESTATE_BUSY while a relocate journey remains active.
  Estate reads now resolve journeys before serializing residence. Poll timing
  reports the current travel step's stored effective duration.
- Public GET /map includes current node, authored node tier, decay stage,
  null treasury_band and transition_pending; it lazily finalizes transitions.
  Added node tier now because this response needs it before the fuller node
  reshape in 09-development-graph. No raw treasury value is exposed.
- Added tests in test_travel.py:
  test_routing_terrain_level_one_way_and_tie_breaks,
  test_supplies_paid_at_step_start_and_shortfall_stays_at_start,
  test_random_stops_keep_exactly_last_completed_realm (Hypothesis),
  test_estate_moves_only_when_relocating,
  test_base_time_xp_ceil_supplies_and_multiplicative_groups,
  test_travel_tier_benefit_is_group_p,
  test_offline_equals_online_polling (Hypothesis),
  test_offline_cap_discards_partial_step,
  test_travel_preview_start_stop_and_removed_routes,
  test_travel_arrival_persists_and_rewards_claim_once,
  test_starting_another_action_ends_journey,
  test_travel_validation_codes,
  test_postgres_travel_holds_character_realms_and_estate (SQLite skips),
  test_travel_edge_ranges_are_strict,
  test_form_profile_matches_mobility,
  test_overlapping_travel_supplies_are_atomic,
  test_profiles_multiply_time_and_supply_cost,
  test_next_step_uses_arrival_realm_bonus,
  test_decimal_ties_and_rounding_are_exact.
  API fixtures follow TEST_DATABASE_URL; engine properties use seeded RNGs and
  explicit timestamps. Existing map, content, availability and golden tests are
  updated for the new shapes, retaining their behavioral assertions.
- Full SQLite PATH=$PWD/.venv/bin:$PATH make ci passed: auth 15; game
  256 with four PostgreSQL-only skips; client 21. Ruff, format checks, strict
  mypy, eslint, prettier, TypeScript, Vitest, production build, script checks
  and warning-only content lint all passed. git diff --check is clean.
- SQLite reset of both services, subsequent game upgrade to head and Alembic
  schema check succeeded with no drift. No dependencies added.

## Removed

- GET/POST /characters/me/relocate and GET /characters/me/relocate/preview;
  gold path_cost, relocation_cost, MapCost, relocation classes, delayed
  relocation finalization, and the estate destination/completion columns.
  Migration v08_0003_travel drops the columns and supports downgrade/rebuild.
- Client relocation hooks, preview/confirm flow, pending banner, special reward
  event and their controls on realm/map pages. The map still renders graph edges
  using terrain/base time. Client content/estate/map types reflect the new data.
- Tests of explicitly removed behavior:
  test_placeholder_path_and_relocation_cost,
  test_path_cost_prefers_cheaper_indirect_route_then_lower_time,
  test_finalize_relocation_syncs_character_realm,
  test_relocation_preview_returns_terms_without_changing_state,
  test_relocation_preview_finalizes_due_arrival_before_pricing,
  test_delayed_relocation_charges_and_arrives_lazily,
  test_instant_relocation_and_unreachable_rollback;
  Vitest “shows pending relocation and retries profile invalidation after expiry”
  and “previews then confirms relocation through the mocked endpoints”.
  Journey tests replace these behaviors; unrelated tests remain intact.
- ResolveContext.modifier_groups: neither resolver consumed this initial-only
  snapshot (06 hand-off). Travel recomputes sources at each new step, including
  after arrival; uniform retains its existing level-boundary calculations.

## Design ambiguities resolved

- §11.4: effective time is rounded upward to whole milliseconds, with one
  millisecond as the representation's smallest unit. This never completes an
  edge before its effective duration. Supply quantities use ceil; XP uses floor.
- §11.3–11.4: snapshot a step's time and payment when it starts. Polls cannot
  reprice a partially completed step. Recompute the next step using arrival
  realm sources and the newly earned Travel tier. Route selection remains fixed.
- §11.3 / §22: start returns the existing action-feed shape, including immediate
  supply use and prior unclaimed rewards. Preview returns a route of edge ids,
  destination realm ids, time_ms and selector supplies. A journey action cannot
  be started through the generic action endpoint without its destination.
- §13.2: retain the existing placeholder transformation chain with all its forms
  mobile, supplying land profiles; fixed/water profiles are exercised through
  test content. This avoids authoring a new estate graph before Prompt 11.
- §11.1: use route as the replacement helper name, following this prompt's
  explicit removal of the gold path_cost API. Parallel edges have distinct ids;
  reverse traversal is permitted only when one_way is false.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 08-client-skills-travel: build journey controls against GET /travel/preview
  (destination_realm_id and mode query parameters) and POST /travel/start
  (the same fields in JSON). Start returns ActionFeedResponse. Current step
  timing comes from /actions/poll; summaries are ordered
  since_last.details.resolutions. Travel content action ids are discovered from
  the travel skill, never hardcoded. Its uniform action fields are placeholders;
  route preview supplies the meaningful per-edge time/supply values. The old
  controls have been removed, so no travel controls currently appear.
- 09-development-graph: preserve the authored DevelopmentNode.tier now consumed
  by GET /map. Extend the travel realm snapshot alongside realm_stack_tags when
  persisting project tag stacks, so later steps use their destination's tags.
- 11-estate-forms / 12-estate-ownership: retain mobility/profile validation,
  ESTATE_BUSY during relocate journeys, presence-based bonuses and the new
  character → sorted realms → estate lock order while reshaping lifecycle.
- 16-realm-pricing: fill treasury_band through the health-band calculation;
  the map currently returns null and never exposes raw treasury.
- 20-caravans: reuse map terrain, base_time_s, supplies, min_travel_level,
  base_loss_pct and one_way. Remoteness and caravan loss are not implemented.
- 29-combat-resolver: ResolveContext now carries content, active action and caps;
  use modifier_groups(state, content) at appropriate simulation boundaries.
- 34-tutorial: apply tutorial map exclusion when tutorial realms are introduced;
  this phase contains only the ordinary world graph.

## New error codes

- NO_ROUTE: no path matches terrain and Travel level.
- ALREADY_THERE: destination equals current character realm (retained name).
- ESTATE_FIXED: a fixed estate cannot relocate.
- ESTATE_NOT_HERE: relocation requires the estate in the current realm.
- TRAVEL_DESTINATION_REQUIRED: generic action start cannot start a journey.
- OUT_OF_SUPPLIES: journey stop reason; no partial payment and no movement.
  UNKNOWN_REALM and ESTATE_BUSY retain their existing names.
