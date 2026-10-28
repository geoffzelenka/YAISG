## Built

- Added `item_instances` and migration `v08_0016_keys`, with provenance,
  independent rolled payloads, finite uses, lifecycle state, binding timestamp,
  holder and realm references. Active actions have a nullable key-instance FK.
  Instances never enter the commodity item index. Each held instance, including
  invalid/depleted trophies, takes one inventory slot.
- Added the strict public `exploration` pack, hashing, cross-reference validation,
  typed client pack transport and minimal synthetic content. Exploration actions
  are indexed under the Exploration skill and offered by `node.actions`;
  `requires.skill_levels` uses the existing shared availability/start gates.
  Progression supplies one absolute Exploration benefit row per tier.
- Extended the uniform resolver with per-cycle XP, discovery probability,
  weighted template selection, independently rolled count/uses/output quantities,
  group P expedition speed, belt buff activation and discovery shaping. Overflow
  reports `keys_lost`, retains fitting instances and stops by the ordinary
  inventory-overflow rule. Details also report discoveries and keys_created.
  Timed bonuses retain uniform expiry segmentation.
- Added `POST /actions/start {key_id}`, `GET /keys/me`, and holder-only
  `DELETE /keys/{id}`. Starts validate ownership, state, remaining uses, realm,
  inline gathering level/tool or combat engagement HP. Binding occurs on first
  successful start. Private inline actions are persisted in server-authored
  metadata, never added to public realm offerings. Gather batches clip to uses;
  combat charges every spawn, including the initial encounter at start, and
  finishes its final paid encounter before KEY_DEPLETED. Trophies remain held
  until deletion. Equipment, consumable and estate action consumers understand
  private action definitions.
- Both session-backed transition finalization and preloaded tick catch-up
  deprecate/invalidate keys and end private actions with claim-once
  KEY_INVALIDATED feed entries. Discovery during a pending transition produces
  deprecated keys. Tick context preloads keys and actions once, performs no
  per-tick queries, and batches stop logs/deletions at persistence. Fixed query
  budgets increase by two preload SELECTs equally for short and full catch-up.
- Character mutations use prepare_sqlite_write, character serialization,
  sorted realm locks (including held-key realms), then estate locks. Realm
  invalidation never locks or changes character rows after realm locks. The
  character adapter reloads its active action after realm completion.
- Extracted the shared §7.5 inventory fit helper for equipment and consumables.
  Uniform drops, combat loot, realm purchases and order collection count held
  instances too. Extended the deadline-free world conservation property with
  exploration, key_use, key_delete and key_invalidate in both OPERATIONS and
  the independent required set. The oracle counts physical instances separately
  from commodities; discovery is their source and DELETE their physical sink.
  Invalidation destroys access while retaining the counted trophy.
- Added these tests in `services/game/tests/test_keys.py`:
  - test_keys_never_stack_and_all_gains_count_instance_slots
  - test_rolled_values_independent_across_keys_of_one_discovery
  - test_discovery_rate_seeded_long_run_within_tolerance
  - test_binding_uses_clip_batch_and_depletion
  - test_exploration_tier_speed_is_group_p_and_belt_shapes_discovery
  - test_equipment_and_consumable_returns_share_instance_capacity
  - test_combat_keys_charge_initial_and_each_spawn_and_finish_last_encounter
  - test_key_api_private_binding_depletion_disposal_and_commodity_rejection
  - test_transition_deprecation_and_invalidation_stops_running_key (both paths)
  - test_key_start_gates_and_discoverer_snapshot
  - test_other_character_cannot_see_use_or_delete_a_key
  - test_combat_key_start_charges_spawn_and_locks_equipment
  - test_rarity_weight_shifts_and_template_tag_filtering
  - test_postgres_key_polls_serialize_uses_and_rewards
  - test_exploration_pack_validation (nine invalid-content cases)
  - test_postgres_transition_completes_while_key_owner_waits_for_realm
  - test_discovery_during_pending_transition_is_deprecated
  - test_market_collection_and_realm_purchase_count_instance_slots
  - test_partial_exploration_does_not_activate_belt_or_create_reward_details
  - test_combat_loot_counts_instance_slots
- Updated the content-provider fetch fixtures for the added exploration pack,
  preserving all estate, inventory, skill and realm UI assertions.
- Disposable SQLite make db-reset rebuilt both services. Subsequent game head
  upgrade and Alembic schema check passed; a lifespan smoke test seeded the
  world, started/stopped the scheduler and served the manifest/exploration pack
  with HTTP 200.
- Both PostgreSQL regressions use independent sessions, bounded waits and actual
  pg_blocking_pids observations; SQLite skips them. Existing migration tests
  cover fresh upgrade, schema parity, downgrade/rebuild and disposable reset.

- Final repository-virtualenv SQLite `make ci` passes: auth 15; game 777 with
  24 dialect-specific skips; client 100. Ruff lint/format, strict mypy,
  TypeScript, ESLint, Prettier, Vitest, production build, script checks and
  warning-only content lint pass. `git diff --check` is clean.

## Removed

- Removed duplicate equipment/consumable fit arithmetic in favor of the shared
  helper. No gameplay features, tests or public routes removed.
- Updated the former empty-Exploration availability expectation to assert its
  authored expedition. The empty-skill lint test now explicitly constructs an
  empty Exploration skill. Golden comparisons retain every historical field
  and additionally assert that instances default to empty. Content mutation
  fixtures mark the new template's deliberately off-tier by-product explicitly.

## Design ambiguities resolved

- §19.2–19.3 / V§3.8: rarity is a positive ascending integer. Effective template
  weight is authored weight times `(1 + shift) ** (rarity - 1)`. Shift adds the
  Exploration tier's rarity_weight_shift, active consumable weight_shift and
  the same authored tier-row shifts for the expedition's cross-skill gates and
  the template's gathering skill, counted once each. This leaves common weights
  unchanged and increasingly favors rarer templates without a hardcoded balance
  coefficient. The design specifies direction but no weight-shifting formula.
- §19.2–19.3 / §9.3: chance_pct is a relative percentage increase to discovery
  chance; active effects multiply, then probability clamps at one. Missing buff
  triggers consume at most one item in belt position order at cycle completion,
  before that cycle's discovery roll. Generic buff speed/XP applies to following
  cycles, matching the established combat belt activation boundary. Already
  active buffs keep the uniform resolver's expiry behavior.
- §19.3: each key rolls each output's inclusive quantity range once and stores
  that fixed quantity in its inline action; ordinary per-cycle output chance
  still applies. Uses and quantities are rolled separately for every key.
  Identity randomness comes exclusively from the injected RNG.
- §19.4: a successful action start binds the key, including stopping before the
  first gathering cycle completes. A combat key becomes a depleted trophy when
  its last spawn is paid, but its running encounter remains legal until kill
  or another normal combat stop; no additional spawn is permitted.
- §19.6 / §12.6: completion invalidates all realm keys, including depleted
  trophies. Stop-only logs record the exact completion timestamp without
  resolving character work from a realm tick. Unresolved private progress is
  discarded at invalidation; no character simulation or reverse character lock
  is introduced into realm work. Invalid keys remain physical holders.
- §19.1 / §22: GET /keys/me returns `{keys: [...]}` with rolled payload,
  provenance and lifecycle fields; holder identity is implied by authentication.
  Bound/private action metadata is visible only through the holder's endpoints.

## Deviations

None.

## Ratification needed

No new questions. Prompt 29's zero-HP regeneration and combat XP multiplier/cap
questions remain unchanged. Keys use the existing combat resolver as required.

## Hand-offs

- 32-key-market: implement listing holders, transfer and tax using ItemInstance;
  nullable holder_character_id supports removing listed keys from inventory.
  Only active, unbound keys may be listed. Reuse the rolled payload and shared
  slot rule. Extend both session and preloaded tick invalidation paths with
  listing cancellation/return, preserving the character -> sorted realms ->
  estate -> order lock order and the no-query-per-tick contract. Extend world
  accounting and both generated-operation coverage sets with listing transfers.
- 33-guest-auth / 34-tutorial: explicitly dispose of held instances before
  deleting ephemeral characters/realms. Holder/realm FKs prevent silent loss;
  discovered_by_character_id uses SET NULL while the copied name survives.
- 35-client-keys-tutorial: render GET /keys/me, start with key_id, support DELETE,
  show bound/deprecated/invalid/depleted state and KEY_DEPLETED/KEY_INVALIDATED.
  Private actions have template ids rather than ordinary content action ids;
  use active.meta.key_action and key_id for identity and combat setup locking.
  Exploration definitions are served in content.exploration.actions; merge them
  into skill presentation. Discovery summaries expose keys_created/keys_lost.
- 36-hardening: preserve instance holders in the conservation oracle, both
  transition paths, PostgreSQL lock regressions and fixed catch-up SQL budgets.

## New error codes

- UNKNOWN_KEY (404): the instance is absent or not held by this character.
- KEY_WRONG_REALM (409): the holder is outside the key's realm.
- KEY_UNAVAILABLE (409): an unsupported lifecycle state cannot be used.
- KEY_DEPLETED and KEY_INVALIDATED (409 on start, or automatic stop reasons).
- Reused existing level/tool/HP, inventory and validation error envelopes.
- No dependencies added.
