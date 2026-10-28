## Built

- Added strict item equip blocks, concrete equipment slots, either-side ring/arm
  definitions, skill gates, modifiers, additive caps and authored weapon/armour,
  tool and belt-capacity data. Boot validates equipment skill references and
  tool requirements against authored main-hand tools. Only capes may carry XP
  modifiers; two-handed items and tools require right_hand.
- Added CharacterEquipment and migration v08_0013_equipment. Concrete slots are
  unique per character; permanent quantities are one, with positive utility
  quantities reserved for Prompt 27. Fresh migration, parity and downgrade/reset
  coverage remains in the existing migration tests.
- Added authenticated POST /equipment/equip and /equipment/unequip. Both resolve
  elapsed work under the shared character, sorted realms, estate lock order,
  validate a pure transfer plan and commit all holders together. Replacement
  returns displaced items, two-handed equipment clears the left hand, and a
  blocked left hand or inadequate inventory space rejects the whole change.
  Combat actions reject equipment changes after resolution. Removing a required
  tool detects REQUIREMENT_LOST at the mutation timestamp, preserving its reward
  feed entry and preventing further tool-less work.
- Equipped modifiers populate group G; cap grants populate additive caps, and
  main-hand tool_class feeds the shared action requirement check. Profiles
  expose equipment as slot -> {item_id, quantity}. Action/profile state loaders
  use the request's content index. Review round 1 extends this to the previously
  missed travel and estate loaders. Equipped goods are neither consumed nor
  degraded.
- Added the requested fake pickaxe, XP cape and two-handed item. Content lint
  enumerates legal concrete gear layouts, including empty slots, either-side
  jewellery and two-handed exclusions. Gear estate-slot grants also participate
  in the conservative estate bound. Updated docs/v08/content-lint.md.
- Picked up 03/04/05 and 24 hand-offs: populated the gear adapter, enforced tools,
  extended the lint, counted equipment in world goods holders, and added equip
  and unequip to both OPERATIONS and the independent required-operation set.
  Generated transfers run through the real authenticated endpoints.
- Added tests in test_equipment.py: test_validator_rejects_xp_outside_cape,
  test_slots_two_handed_requirements_and_conservation,
  test_unequip_needs_capacity_and_stack_space,
  test_gear_lint_respects_hands_and_ring_sides,
  test_tool_group_g_and_mid_action_change,
  test_equipment_caps_xp_and_failed_changes_are_atomic,
  test_concurrent_equips_transfer_single_item_once,
  test_every_permanent_slot_round_trips (14 slots),
  test_two_handed_displacement_is_atomic_when_inventory_is_full,
  test_equipped_tool_unlocks_action_start,
  test_equipment_changes_rejected_during_combat, and
  test_gear_lint_includes_estate_slot_grants. Database fixtures honor
  TEST_DATABASE_URL; the concurrent request test runs on either database.

- Validation: repository-virtualenv make ci passes on SQLite: auth 15, game
  650 with 20 database-specific skips, client 90 (review round 1). Formatting, lint, strict
  typing, production build, scripts and content lint pass. Disposable SQLite
  make db-reset, subsequent upgrade to head, alembic check and application
  lifespan/content-manifest smoke check pass. git diff --check is clean.

- Review round 1: fixed B1's over-cap handling and limited stack-limit checks to
  increased quantities. Added test_over_cap_equip_without_displacement_is_allowed,
  test_over_cap_swap_is_allowed and test_unequip_capacity_gear_uses_resulting_cap.
  The first also retains an untouched stack already above its stack limit.
- Applied N1–N8: added test_validator_rejects_incompatible_equipment_fields
  (two-handed/tool right-hand restrictions and belt-only capacity),
  test_loader_rejects_unknown_equipment_skill (requires/modifier references),
  test_loader_requires_equipped_tool_class (goods class alone is insufficient),
  and test_custom_equipment_content_in_estate_and_travel (all six missed loader
  calls). Unknown equip item ids now return 404. Changed
  test_equipment_caps_xp_and_failed_changes_are_atomic to assert exact XP bonuses
  with and without the cape, 404 for unknown items and matching mutation/profile
  equipment shapes. Changed test_tool_group_g_and_mid_action_change and the cape
  test to narrow optional equip definitions with explicit assertions.
- Added services/equipment.py: inventory and equipment persistence updates only
  changed rows, preserving unrelated holdings and existing slot quantities.
  Equip/unequip responses reuse the profile's EquippedStack shape.

## Removed

- Replaced the unconditional missing-tool blocker with the equipped main-hand
  comparison. No tests or existing features removed. Existing exact lint
  expectations include the new gear factor. Golden compatibility checks retain
  every historical field and explicitly assert the new tool field is empty.

## Design ambiguities resolved

- §9.2 / §6.4: preserve the fraction of an unfinished uniform cycle when gear
  changes. Resolve completed cycles with the old gear first, then translate the
  remaining fraction to the new cycle duration. New speed does not retroactively
  accelerate time already spent. Completion rewards use the current gear.
  Journeys retain their already-paid edge snapshots, per Prompt 07.
- §9.2: requests name {item_id, slot} or {slot}; ring/arm items require an explicit
  concrete side. Replacing an occupied slot returns its old item atomically.
  Capacity is checked after removing the incoming item and adding all displaced
  items. A transfer above the resulting cap is rejected only when distinct-stack
  usage increases; existing over-cap usage may stay constant or shrink (§7.5).
  Stack limits gate only quantities increased by the transfer. Existing stacks
  can receive returned items without a new distinct-item slot.
- §7.3: lint independently maximizes the gear factor and gear estate-slot grant,
  as it already independently maximizes estate/realm sources. Requirements and
  acquisition history are relaxed, preserving an upper bound. Legal hand and
  jewellery occupancy is enforced within each gear layout.
- §9.2: modifier blocks reuse the established {type, value, skill_id/category}
  schema rather than introducing a second scope/pct representation.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 27-consumables-hp: implement utility/belt assignment and consumption. The
  utility slot and positive stack quantity are reserved in the equipment table;
  permanent equip/unequip rejects utility. When adding utility holders, exclude
  utility from permanent group G. The changed-row persistence preserves
  quantities on untouched slots. Read equip.belt_slots for the physical
  belt positions plus the resolved cap. Keep consumable modifiers in C rather
  than G, and extend holders and both generated-operation coverage sets again.
- 28-combat-model / 29-combat-resolver: consume authored weapon/armour blocks and
  extend modifier types for combat stats. The equipment change guard checks the
  active action's combat resolver after resolution; its test injects an ordinary
  resolver through the existing seam, without implementing combat mechanics.
- 30-client-equipment-combat: profile equipment is slot -> {item_id, quantity};
  mutations accept concrete slots and return
  {equipment: {slot: {item_id, quantity}}}, matching the profile.
  Refresh profile, inventory and action data after changes. Render gear/tool
  requirements from the public items pack and extend client content types with
  equip; no equipment client UI is built here.
- 31-keys: extend the transfer capacity check with held item-instance slots when
  those holders exist. Current inventory capacity counts distinct commodity ids.
- 36-hardening: gear lint enumeration is exponential in authored slot choices;
  preserve the conservative bound if replacing it for larger content packs.

## New error codes

- INVALID_EQUIPMENT_SLOT (409): item/slot mismatch or reserved utility setup.
- NOT_EQUIPPABLE (409): item has no equip block.
- EQUIPMENT_LEVEL_REQUIRED (409): authored equipment skill gates are unmet.
- TWO_HANDED_CONFLICT (409): a two-handed right-hand item blocks the left hand.
- EQUIPMENT_SLOT_EMPTY (409): no item is available to unequip.
- EQUIPMENT_IN_COMBAT (409): a combat action remains active after resolution.
- Reused UNKNOWN_ITEM (404), MISSING_INPUTS and INVENTORY_FULL (409); malformed
  request shapes retain INVALID_REQUEST. No dependencies added.
