## Built

- Registered the pure CombatResolver through ActionResolver. Combat uses the
  existing player_stats, opponent_stats, attack and maximum_hp formulas, equipped
  weapon style, persisted stance and the combat taper row. No background loop,
  database access or wall-clock access was added to the engine.
- Added the engagement HP gate to the shared availability/start blocker path.
  The inclusive threshold uses the authored min_engage_hp_pct and current maximum
  HP. Start and poll report weapon-derived combat cycle time.
- Implemented the literal §10.5 ordering: matching utility consumption; clipped
  player attack; all carried opponent attacks, including retaliation after a
  killing blow; offensive pool drain/taper/stance split; defensive pool drain and
  Vigor/Defense split; regeneration; one triggered belt item in slot order; kill
  and loot, then defeat. Melee and magic continue without matching utility;
  ranged stops with OUT_OF_AMMO. Stance changes remain legal.
- Encounter metadata stores opponent HP, both pools, opponent attack carry,
  remaining respawn wait, exact HP and XP carries, buff expiries, deterministic
  random-stream state and running totals. Pool remainders are discarded on kill;
  new pools are created only when the respawn wait finishes. Waits consume budget
  without attacks and split at buff expiries for consistent regeneration.
- HP and XP calculations use integer numerators/denominators through standard
  library Fraction, including fractional authored settings. Whole XP is credited
  with explicit per-skill carries. Clipped fractional damage is carried in the
  integer damage summary too. Level changes affect following cycles.
- Replaced outer passive regeneration during combat with the simulated cycle and
  respawn healing. Persisted HP timestamps follow consumed simulation time;
  stopped characters regenerate for the remaining idle interval. Inventory,
  equipment utility quantities, belt quantities and activated buff expiries are
  persisted atomically under the existing character -> sorted realms -> estate
  locks. The state loader accepts explicit evaluation time rather than treating
  hp_updated_at as a clock; action, profile, equipment and travel callers pass it.
- Enforced the authored max_cycles_per_resolve and the shared offline-time
  budget, including a budget spent entirely waiting for respawn. Combat returns
  uppercase OFFLINE_CAP; existing non-combat stop codes are retained.
- Summary details expose kills, defeats, damage_dealt, damage_taken, xp_by_skill,
  consumables_used, loot and stop_reason. Running totals stay in meta; reward-log
  claims preserve at-most-once reporting. Private random-stream state is omitted
  from public action metadata.
- Picked up the 03/06/07/26/27/28 combat hand-offs, including real Fed/Strained
  reward equivalence and utility/belt EQUIPMENT_IN_COMBAT endpoint coverage.
  The 10a preloaded realm tick/transaction boundary is unchanged.
- Added these tests in test_combat_resolver.py (the defeat test has two cases):
  - test_pools_drain_once_refill_only_on_respawn_and_remainder_lost
  - test_ranged_requires_ammunition_melee_and_magic_continue
  - test_defeat_ends_action_and_simultaneous_kill_counts_first
  - test_offensive_taper_drains_pool_defense_and_drops_unchanged
  - test_offline_equals_online_polling (Hypothesis, JSON round trips)
  - test_regeneration_then_one_belt_item_in_slot_order
  - test_cycle_ceiling_stops_with_uppercase_offline_cap
  - test_twelve_hours_two_second_cycles_time_bound
  - test_engagement_gate_and_consumable_setup_combat_guards
  - test_combat_persists_hp_consumption_buffs_and_claims_once
  - test_postgres_combat_poll_waits_and_never_double_rewards
  - test_combat_regeneration_is_not_applied_before_fighting_or_twice
  - test_loot_overflow_discards_excess_and_stops
  - test_respawn_wait_buff_expiry_and_regeneration_match_polling
  - test_offline_budget_clips_respawn_wait
- The database fixtures honor TEST_DATABASE_URL. The PostgreSQL-only regression
  observes a real backend blocking relationship before releasing the first
  combat transaction, then verifies one cycle, one HP deduction and one claim.
  Pure polling equivalence injects seeded randomness and clock values.
- Normal CI runs the twelve-hour performance regression against the pure core:
  21,600 two-second cycles, including opponent attacks and regeneration, under a
  generous 30-second bound. Measured targeted runtime: 4.93 seconds.
- SQLite make ci passes: auth 15, game 740 with 22 dialect-specific skips,
  client 90; Ruff, strict mypy, TypeScript, ESLint, Vitest, production build,
  scripts and content lint pass. Existing migration/reset tests verify fresh
  schema creation and rebuild. No schema migration or content change is needed.

## Removed

- Replaced test_combat_actions_wait_for_registered_resolver with
  test_combat_actions_use_registered_resolver: the authored combat action is now
  startable. Retained the generic unknown-resolver gate.
- Replaced the combat-only early skip in test_strained_has_no_engine_effect with
  the real seeded resolver comparison, retaining its combat-stat assertions.
- Golden uniform compatibility still compares every historical field and now
  explicitly asserts all six newly added combat-state fields have empty defaults.
  No production feature or historical behavior test was removed.

## Design ambiguities resolved

- §10.5 / §9.4: HP may have a fractional remainder, as established by 27.
  Combat keeps it as an exact rational and projects it to the existing persisted
  HP column. XP is awarded in whole units with explicit fractional carry, rather
  than losing XP on each small hit or poll. Already-earned XP fractions survive
  respawn; unspent pool fractions do not.
- §10.5: when the defensive pool clips a cycle, its taken/mitigated components
  are reduced proportionally before applying taken_to_defense_pct. This prevents
  either receiving skill from exceeding the amount drained.
- §10.5 steps 6–8: regeneration and belt healing can rescue zero HP before the
  terminal check. No earlier defeat latch is introduced. With no rescue, a
  simultaneous kill and defeat awards the drop before ending the action.
- §10.5 / §9.3: buffs and weapon speed are evaluated at historical cycle starts;
  belt buffs activate at cycle completion for subsequent cycles. Expired buff
  records remain available as historical inputs. Respawn healing is segmented at
  expiry, so splitting a wait across polls cannot alter its result.
- §9.3: utility content currently defines its attack-style purpose without a
  stat-effect payload. The resolver consumes the matching stack and enforces the
  ammunition gate; no unauthored numeric utility bonus is invented.
- §10.5: details contain per-resolution deltas, and meta.totals contains
  cumulative action totals. Integer damage summaries carry fractional clipped
  damage between resolves, just as integer XP does. The existing reward feed
  wraps individual details in its resolutions list.

## Deviations

- §6.4 / §10.5: combat retains its seeded random sequence in action metadata
  across resolves, rather than discarding the sequence and reseeding every poll.
  It initializes exclusively from the injected RNG (CSPRNG-seeded by the adapter),
  preserving the prompt's required seeded online/offline equivalence. Uniform
  and travel sampling are unchanged. Random state is private to persistence and
  filtered from the public action response.

## Ratification needed

- §10.5 steps 6–8 / V§6.2.2: should passive regeneration revive zero HP before
  the terminal check? The literal ordering does so, meaning positive regeneration
  prevents defeat even when opponent attacks exhaust HP every cycle. Implemented
  the required ordering without a defeat latch; the regeneration/belt-order test
  explicitly verifies this behavior. Defeat and simultaneous kill/defeat tests
  use authored zero regeneration. A different zero-HP regeneration rule needs a
  design ruling; no such rule was invented here.

## Hand-offs

- 30-client-equipment-combat: display uppercase OUT_OF_AMMO, DEFEATED and
  OFFLINE_CAP, combat summary fields and the encounter metadata. The poll reward
  details retain the existing resolutions wrapper. Use server cycle_ms, HP and
  persisted stance; utility and belt setup still reject ongoing combat.
- 31-keys: use the registered combat resolver; charge combat-key uses when a
  new encounter begins (CombatSimulation.spawn), including the initial encounter.
  Key exhaustion must prevent a further spawn rather than interrupt a current
  encounter. Combat-key ownership, invalidation and use accounting are not built
  here.
- 36-hardening: retain the normal-CI twelve-hour pure-core bound, deterministic
  polling property, explicit Fraction carries, private RNG state and PostgreSQL
  serialization regression when optimizing combat. The inherited 28 hand-offs
  about combat lint standard loadouts/content projections remain applicable.

## New error codes

- INSUFFICIENT_HP (409): current HP is below min_engage_hp_pct of maximum HP.
  Availability reports the same blocker.
- OUT_OF_AMMO and DEFEATED are combat stop reasons, not HTTP error responses.
- OFFLINE_CAP is the combat-specific uppercase stop reason for either the
  authored cycle ceiling or the shared offline-time ceiling. Existing lowercase
  non-combat stop reasons remain compatible.
- Reused EQUIPMENT_IN_COMBAT (409) for permanent equipment, utility and belt.
- No dependencies added.
