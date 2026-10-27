## Built

- Pure `ActionResolver` protocol and immutable `ACTION_RESOLVERS` registry,
  keyed by `action.resolver`; callers can inject an alternate registry.
  `ResolveContext` supplies content, initial modifier groups, caps and active
  action state. The shared wrapper clips the elapsed budget, handles clock
  regressions and applies the existing offline/requirement stop precedence.
- `UniformResolver` ports the shipped algorithm unchanged: whole-cycle rewards,
  seeded drop order, level-boundary recomputation, selector payments, partial
  remainder and overflow/input stop precedence. `ResolveResult` additionally
  carries character state, active action state, elapsed milliseconds consumed
  and details. Reward-feed-only results leave the state fields empty.
- Active action metadata is loaded and persisted together with its action id
  and timestamps. Resolver details are stored directly in `reward_log.details`;
  stop-only requirement-loss claims remain supported. Poll summaries include
  details from every claimed resolution in order, without dropping nested data.
- Migration `v08_0002_presence` renames the character column to
  `current_realm_id`. Engine state, adapters, profile response, relocation
  finalization, client types and current-realm displays use the renamed field.
  Estate and realm records retain their own `realm_id`; character creation and
  relocation retain their existing `realm_id` destination request fields.
- Pure `home_realm`, `is_resident` and `is_present` helpers distinguish estate
  residence from current presence. E-group modifiers, estate facilities and
  estate cap bonuses share the existing presence gate. Visitors retain other
  sources and normal reward rules; a capacity reduction leaves existing items
  intact and applies the existing overflow rule to further gains.
- Picked up 00/02/03/05 hand-offs: replaced action-row locking with a character
  row lock for both idle and active characters, refreshing the pre-lock ORM
  snapshot; added `/actions/poll` and `/actions/stop`; switched the client to
  all four consolidated action routes. Existing character-scoped aliases and
  shipped relocation endpoints continue to work.
- Golden fixture `tests/resolve_goldens.json` records the original engine from
  baseline `2956a0c`, before the port: seeded gathering, level changes, partial
  cycles, offline cap, recipe exhaustion and backwards clock results. Tests
  compare every pre-existing state, active-action and reward field exactly,
  allowing only the specified location-field rename and additional seam fields.
- Added tests: `test_uniform_matches_pre_refactor_goldens`,
  `test_registry_dispatch_and_clipped_budget`, `test_presence_helpers`,
  `test_cap_below_usage_keeps_items_and_records_overflow`,
  `test_visitor_loses_only_estate_sources`,
  `test_resolver_meta_and_details_round_trip`, and
  `test_postgres_resolve_locks_character_with_or_without_action` (idle/active
  cases, SQLite skips). Existing concurrent reward resolution, presence,
  migration/reset and relocation tests are retained.
- SQLite `make ci` passed: auth 15, game 235 with three PostgreSQL-only
  skips, client 23; formatting, lint, strict typing, TypeScript and production
  build checks are green. Explicit `make db-reset` rebuilt disposable SQLite
  game/auth databases and a subsequent game `alembic upgrade head` succeeded.
  Migration tests cover
  fresh upgrade, schema parity, downgrade/rebuild and repeated two-service
  database reset followed by head upgrade.

## Removed

- `CycleRewardStrategy`, its injection argument and the unused per-cycle
  strategy method. The level-recomputation test now varies effective XP at the
  uniform calculation boundary, preserving the same 57/20/20 XP assertion.
- `characters.realm_id` and `CharacterState.realm_id`. Historical baseline
  audit/phase notes and the pre-refactor golden snapshot retain their old names
  as evidence. No tests were deleted or weakened.

## Design ambiguities resolved

- §6.3–6.4: the actual shipped implementation loops through drops per cycle
  and caches effective values until a level changes, despite the design calling
  it closed-form. Preserve that implementation and RNG consumption exactly;
  algorithmic optimization would exceed this prompt's pure-refactor scope.
- §6.3: preserve the existing outer `resolve` tuple API for callers, while the
  resolver protocol itself returns the richer `ResolveResult`. This keeps
  reward-feed aggregation separate from mutable simulation state without
  introducing a second reward-summary type.
- §6.3 / §22: `details` reserves the existing `level_ups` and `stop_reason`
  summary keys, with all other keys owned by the resolver. Aggregated API
  details use `{resolutions: [...]}` in reward-log order; merging arbitrary
  resolver-specific dictionaries would overwrite earlier summaries.
- §11.2 / §22: rename the character's location in profile responses; keep
  `realm_id` on estate/map/realm payloads and existing destination request
  fields because these describe different entities or client intent.

## Deviations

- The inherited relocation finalizer still locks its estate before realm
  finalization. The preflight hand-off explicitly assigns its removal to
  07-travel and the broader estate lifecycle lock work to 12-estate-ownership.
  This phase establishes the common character lock for action operations and
  preserves shipped relocation behavior until that replacement.

## Ratification needed

None.

## Hand-offs

- 07-travel: add the travel resolver to the registry. Store step progress in
  `ActiveAction.meta`; return updated state, active state and actual consumed
  time. Extend persistence for travel's current-realm/estate changes (the
  current uniform adapter still writes only skills and inventory). Remove
  legacy relocation routes/fields/finalization and its estate-before-realm
  locking as assigned by preflight. Use the character lock before realm locks
  in sorted id order, then estate locks.
- 08-client-skills-travel / 30-client-equipment-combat: consume ordered
  `since_last.details.resolutions` for stepped welcome-back summaries. Current
  client types accept details; existing uniform reward presentation is intact.
- 12-estate-ownership: complete estate lifecycle lock ordering as assigned by
  preflight; retain the shared character lock and presence-scoped E sources.
- 29-combat-resolver: register combat through `ActionResolver`; use action meta
  for progress, XP-by-skill and item deltas for rewards, and details for the
  summary. Uniform rolling is no longer a strategy injection seam.

- 37-conformance (orchestrator, from review): the pre-§22 aliases
  `/characters/me/actions/available` and GET/POST/DELETE `/characters/me/action`
  are still registered beside the consolidated routes; the client no longer
  calls them. Remove them unless a design section still lists them.
- 07-travel / 29-combat-resolver: `ResolveContext.modifier_groups` is computed
  per resolve but `UniformResolver` does not read it; it exists for later
  resolvers. Drop or use it there.
- Any prompt that touches stop reasons: `resolve_goldens.json` has no
  INVENTORY_FULL or REQUIREMENT_LOST row; add rows when regenerating.

## New error codes

None. Missing resolver implementations or invalid resolver state are internal
engine configuration errors, not new client error contracts.
