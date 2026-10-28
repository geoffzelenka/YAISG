## Built

- Added the public strict `combatants` pack, immutable indexed lookups, manifest
  hashing and public client pack loading. Combatants carry the §10.2 stats,
  timers, weaknesses/resistances, two XP pools and goods-only drops. Boot rejects
  unknown drop items, duplicate opponents, broken encounter references and tier
  mismatches. Bullion goods are valid drops; currency fields are forbidden.
- Combat actions carry `combatant_id` and `location`, inherit the combat resolver
  from their skill category and are offered through `node.actions`. Added one
  deliberately fake target/location plus a fake sword and armour. Availability
  and start share RESOLVER_UNAVAILABLE until the named resolver is registered.
- Added pure engine/combat.py: effective skill levels, equipped weapon style and
  unarmed fallback, attack/defense ratings, integer max hit, summed armour, shared
  maximum HP and weapon cycle time. All combat constants and standard lint gear
  are authored in progression.combat. Combat modifiers use the existing G/E/R/C
  multiplication; combat_effectiveness supplies P for accuracy, power and defense
  only. Armour, HP and cycle time receive no effectiveness bonus.
- Added pure attack and damage_on_hit: clamped hit probabilities, damage rolls
  on both hits and misses, weakness/resistance floors and armour block. Results
  partition rolled damage into dealt and mitigated, including full mitigation
  on a miss. Expected-rate lint reuses the same damage arithmetic.
- Added characters.stance and migration v08_0015_stance, validated authored
  stances/splits and a content-defined initial stance. Authenticated
  PUT /characters/me/stance serializes on the existing character lock and returns
  the persisted setting. Profiles expose character.stance. A change leaves
  elapsed work for the next resolution, as specified.
- Extended the shared maximum_hp helper with combat_hp_pct, used it through the
  existing adapter for new-character initialization, and retained max-HP clamping
  even when a read's clock precedes hp_updated_at. No HP formula is duplicated
  by the combat model.
- Added deterministic combat lint to make content-lint: standard gear at unlock
  level, mean dealt/mitigated damage, whole-cycle kill estimate plus respawn,
  capped defensive split and offensive stance shares for each receiving skill.
  Reports flag rates outside the existing tolerance, unreferenced combatants and
  undefeatable opponents. Updated docs/v08/content-lint.md.
- Added tests in test_combat_model.py:
  test_eff_per_tier_and_vigor;
  test_hit_bounds_rounding_and_miss_mitigation;
  test_attack_damage_partition (Hypothesis);
  test_effectiveness_three_stats_only;
  test_player_stats_weapon_armour_hp_and_speed;
  test_combat_lint_flags_oversized_pool;
  test_combat_pack_validation;
  test_stance_change_persists;
  test_equipped_style_drives_tier_distance_and_armour_totals;
  test_combat_lint_pool_splits_and_respawn;
  test_standard_gear_validation;
  test_combat_actions_wait_for_registered_resolver;
  test_stance_change_leaves_elapsed_work_for_next_resolve;
  test_postgres_stance_waits_for_character_lock;
  test_combat_actions_use_category_default_and_allow_bullion;
  test_hp_bonus_profile_and_backwards_clock_clamp.
  Database tests use the existing TEST_DATABASE_URL fixture. The PostgreSQL-only
  lock test confirms an actual blocking relationship and skips on SQLite.
- Extended the client modifier label map for all five combat stat types and
  retained the existing maximum-level profile test with a combat-label assertion.
  Public pack-cache tests now assert the fetched combatants payload.
- Updated public pack/cache fixtures and kept the existing availability and
  Strained assertions: Melee now has its authored action, and combat stats are
  compared for Fed/Strained while existing resolvers retain reward comparisons.
  The equipment combat-guard test still injects its fake resolver through the
  resolver seam and now declares it available to the endpoint as well.

- Validation: PATH=$PWD/.venv/bin:$PATH make ci passes on SQLite: auth 15,
  game 724 passed / 21 dialect-specific skips, client 90. Ruff formatting/lint,
  strict mypy, TypeScript, ESLint, Vitest, production build, scripts and content
  lint pass. Existing migration tests verify fresh creation, schema parity,
  downgrade/rebuild and repeated disposable database reset. git diff --check
  is clean.

## Removed

None. No existing tests or features deleted.

## Design ambiguities resolved

- §10.3 / D12: max hit is floored once after bonuses and clamped to at least one
  so the inclusive integer roll remains defined under large maluses. Accuracy,
  defense, armour and HP retain fractional values. A zero/zero accuracy contest
  uses an even chance before the authored probability clamp.
- §10.2–10.3: combatants have a style but no weapon or separate damage_type in
  the specified schema. The opponent adapter uses style as its damage type;
  player damage type comes from its authored weapon. Both directions use the
  same hit arithmetic. If a damage type appears in both weakness and resistance,
  multiply both factors and floor once before blocking.
- §7.2 / §10.3–10.4: combat stat scopes use the equipped attack style, with HP
  scoped to Vigor/combat so idle profiles and encounter stats use the same HP
  bonuses. Tier distance always comes from the attack style's skill tier,
  independent of the Accuracy/Defense skills' own effective levels.
- §10.5: progression.default_stance chooses the initial standing setting; the
  fake pack chooses balanced. Stance shares are fractions summing to one. No
  stance id is hardcoded into application logic or a persistence default.
- §10.6: standard gear is an explicit concrete-slot map in progression.combat.
  The baseline uses unlock level for all six skills and excludes estate, realm
  and consumable bonuses. Expected kill time is ceil(HP / mean dealt) player
  cycles; enemy attacks use whole intervals during that fight. Defensive pool
  exhaustion scales the expected taken/mitigated shares proportionally. This is
  a sizing estimate and does not attempt the resolver's survival/consumable loop.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 29-combat-resolver: register combat with ActionResolver; the availability/start
  blocker automatically disappears when ACTION_RESOLVERS contains combat.
  Load the character's persisted stance at resolve time and use its authored
  split. Reuse player_stats, opponent_stats, attack and maximum_hp; player_stats
  accepts concrete slot -> item id and a CharacterState containing the adapters'
  existing G/E/R/C modifiers. Utility is excluded from permanent stat equipment.
- 29-combat-resolver: implement encounter state, pools, offensive taper, rewards,
  respawn, defeat and the authored cycle ceiling. Consume style-matching utility
  and triggered belt items, activate buffs, regenerate per cycle and enforce
  min_engage_hp_pct at combat start. Replace the outer passive regen during
  combat as handed off by 27; these behaviors remain outside this model prompt.
- 29-combat-resolver: extend the existing Fed/Strained reward-equivalence test to
  run real combat once the resolver exists. Add the utility/belt in-combat setup
  rejection tests handed off by 27. Keep stance changes legal during combat.
- 30-client-equipment-combat: combatants and combat modifiers are in the public
  client content cache; actions expose encounter metadata in their pack.
  Profile character.stance and PUT /characters/me/stance are ready for controls.
  Equipment/HP/belt and progression.combat/stances UI typing and presentation
  remain yours, alongside 26/27's existing client hand-offs.

## New error codes

- INVALID_STANCE (422): the requested id is not in progression.stances.
- RESOLVER_UNAVAILABLE (409): an authored action's resolver is not registered;
  returned consistently by availability and start. Combat registration belongs
  to Prompt 29. Malformed requests retain INVALID_REQUEST.
- No dependencies added.
