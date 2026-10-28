## Built

- Added strict consumable content: exactly one of positive heal, a scoped timed
  buff with positive duration_ms, or utility_for (melee/ranged/magic). Buff skill
  references are checked at boot. Added minimal fake food, buff, ammunition and
  belt, plus authored progression.combat HP constants and regeneration settings.
- Added character_belt and character_buffs, characters.hp/hp_updated_at and
  migration v08_0014_consumables_hp. Existing migration/reset tests cover fresh
  creation, metadata parity, downgrade/rebuild and repeated two-service reset.
- Added authenticated PUT /equipment/utility and PUT /equipment/belt/{slot}.
  Transfers resolve prior work under character, sorted realms, estate locks,
  validate pure transfer plans, and persist inventory and holders atomically.
  Replacement returns the previous stack before assigning the requested total;
  repeating an assignment is idempotent. Combat rejects setup changes.
- Belt capacity adds equipped belt positions and the resolved belt_slots cap.
  Healing and buff triggers are validated against item purpose. Existing holders
  survive capacity loss and can be returned even from an unavailable position.
  Returns share the §7.5 distinct-stack rule and increased-stack quantity limits.
- Timed effects populate group C independently of permanent group G, preserving
  scope matching and the existing XP cap. Uniform resolution splits at expiry,
  carries partial cycle progress to the new speed, and removes expired modifiers
  from returned state. Journey steps use active buffs at their historical start;
  an already-paid step keeps its snapshot. Expired rows remain available for
  resolving elapsed work; reads do not delete their historical boundaries.
- Lazy HP regenerates through the shared character-resolution adapter, including
  idle reads. Profiles report hp, max_hp, hp_updated_at, equipment stack quantities
  and belt stacks/triggers. The maximum uses Vigor and authored armour HP.
  Equipment changes preserve damage and clamp HP when the maximum falls.
- Extended the content lint with simultaneous distinct buff subsets in group C
  and documented its conservative bound. Updated exact lint expectations to
  include the authored gathering buff, retaining all previous assertions.
- Picked up 03/04/24/26 hand-offs: populated C, kept utility out of permanent gear
  modifiers/caps, counted belt goods alongside equipment/utility, added utility
  and belt transfers to both OPERATIONS and the independent required set, and
  hoisted function-local imports in test_equipment.py. Permanent equipment
  responses now preserve untouched utility quantities.
- Added tests in test_consumables_hp.py:
  test_consumable_content_validation;
  test_trigger_validation;
  test_belt_capacity_from_belt_and_cap;
  test_stack_return_preserves_over_cap_rule_and_stack_limits;
  test_buff_group_c_expires_at_segment_boundary;
  test_hp_regeneration_math_and_max_clamp (Hypothesis);
  test_maximum_hp_uses_vigor_and_armour;
  test_consumable_lint_combines_simultaneous_buffs;
  test_setup_holders_capacity_triggers_and_conservation;
  test_profile_lazy_hp_and_buff_adapter;
  test_concurrent_belt_assignments_transfer_stack_once;
  test_armour_hp_formula_and_removal_clamp;
  test_multiple_buff_expiries_match_online_polling (Hypothesis).
  Database fixtures honor TEST_DATABASE_URL, including concurrent requests.
- Extended test_random_world_operations_conserve_goods_and_gold with real
  authenticated utility/belt assignment and return operations. Its database
  Hypothesis deadline remains disabled. Golden compatibility still checks all
  historical fields and now explicitly asserts the new timed_buffs field is empty.
- Validation: PATH=$PWD/.venv/bin:$PATH make ci passes on SQLite: auth 15,
  game 675 with 20 dialect-specific skips, client 90. Ruff formatting/lint,
  strict mypy, TypeScript, ESLint, Vitest, production build, scripts and content
  lint pass. Migration parity/downgrade and disposable database reset tests pass.
  git diff --check is clean.

## Removed

None. No existing tests or features removed.

## Design ambiguities resolved

- §9.3: positions are zero-based; hp_below_pct is a finite number in (0, 100],
  and buff_missing must be literal true. A threshold of zero can never trigger
  and is rejected. Heal uses the HP trigger and timed buffs use buff_missing;
  utility items use only the utility holder. Null item_id and quantity zero
  clear either holder; clearing is idempotent. Existing stacks beyond a reduced
  position cap remain recoverable rather than being destroyed or auto-returned.
- §9.3 / §7.1: one buff row per character and source item prevents duplicate
  stacking of the same buff. Expiry is exclusive: a cycle completing exactly
  at expires_at receives no expired XP/drop modifier. When speed expires within
  a cycle, preserve its completed fraction using the existing equipment-change
  interpretation; translated progress is represented to the nearest millisecond.
  This preserves online/offline equivalence across expiry boundaries.
- §9.3: no manual consumable-use endpoint is specified. This phase supplies
  setup, persistence and active-effect resolution; automatic activation and goods
  consumption belong to 29-combat-resolver and 31-keys. Utility has no effect
  outside its combat cycle and never contributes permanent group G bonuses.
- §9.4 / §10.3: HP is fractional, avoiding loss from frequent reads. The authored
  regen_per_min is the fraction of maximum regenerated per minute (0.01 means
  1%). base_hp=100 and hp_per_level=10 are synthetic placeholder content, not
  engine constants. New characters start at full health. A null stored timestamp
  denotes uninitialized disposable data and initializes full HP on first resolve.
  Backwards timestamps add no regeneration and do not move hp_updated_at back.
- §9.4: regeneration of elapsed time uses the pre-equipment-change maximum;
  the resulting maximum then clamps current HP without granting a free heal.
  min_engage_hp_pct is authored at the design default for the combat start gate.
- §7.3: lint relaxes buff acquisition, duration and belt occupancy to bound all
  simultaneous distinct buff subsets. This can overestimate but cannot conceal
  a reachable non-combat stack. Utility combat effects remain for combat lint.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 28-combat-model: reuse progression.combat HP constants and pure
  engine/health.py formulas; extend combat settings/modifier mechanics and enforce
  min_engage_hp_pct when combat starts. Utility purpose is an attack style.
- 29-combat-resolver: consume utility at cycle start and at most one triggered
  belt item per cycle, moving the goods into explicit consumption results.
  Apply healing and upsert timed buffs with the authored duration at activation.
  Integrate HP in combat state and regenerate per cycle; replace the adapter's
  outer passive regeneration for combat so it does not heal an entire offline
  interval before fighting or regenerate that interval twice. Keep inactive-time
  regeneration and timestamp clamping. Setup already rejects ongoing combat.
  Retain expired buff boundaries until elapsed work has been resolved.
- 30-client-equipment-combat: profile exposes hp/max_hp/hp_updated_at at the root,
  equipment as slot -> {item_id, quantity}, and belt as zero-based position ->
  {item_id, quantity, trigger}. Setup returns both equipment and belt. Extend
  client content types for consumable and progression.combat. Report capacity as
  the resolved belt_slots cap plus the equipped belt's equip.belt_slots.
- 31-keys: implement exploration buff activation and discovery shaping; retain
  uniform expiry segmentation. Extend inventory capacity accounting with held
  instances as already handed off by Prompt 26.
- 36-hardening: simultaneous buff subset enumeration is exponential, like the
  gear/estate bounds; preserve a conservative bound if optimizing. Buff rows are
  historical resolution inputs, not physical goods holders.

## New error codes

- INVALID_BELT_SLOT (409): negative or unavailable position for an assignment.
- INVALID_CONSUMABLE (409): incompatible item/holder/trigger or stack limit.
- Reused UNKNOWN_ITEM (404), MISSING_INPUTS, INVENTORY_FULL and
  EQUIPMENT_IN_COMBAT (409); malformed request shapes use INVALID_REQUEST (422).
- No dependencies added.
