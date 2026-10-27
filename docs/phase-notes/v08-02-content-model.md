## Built

- Converted skills/actions/items to the v0.8 shapes: six categories, eight fixed
  empty skills, tiers, selector inputs, output ranges, requirements, category
  resolver defaults, off-curve reasons, classes and reference prices. Character
  creation continues to derive every skill row from content (now eleven rows).
- Added pure engine `pay_selector` and `Shortfall`, exported from `app.engine`.
  Payments sort by reference price then id, return an atomic withdrawal plan,
  and never mutate the holding. Action input planning pays selectors in content
  order against a temporary remainder, preventing overlapping double payments.
  Start, availability and each resolution cycle use the same planner.
- Added boot checks for tier/unlock correspondence, output tiers (with explicit
  off-tier exceptions), every possible input match, empty selectors, facility
  and realm tag references, skill references/levels and tool classes.
- Added order_slots, key_listings and belt_slots throughout caps resolution,
  profile responses and client types. Converted client routes/labels to
  Manufacturing and recipes to selector inputs/output ranges.
- Placeholder class fake_plant accepts fake sprigs and worthless buttons at
  different reference prices. All placeholder goods remain tier one.
- Added tests: test_content_model_validation (nine cases),
  test_off_tier_output_and_resolver_defaults,
  test_selector_rejects_invalid_shapes (three cases),
  test_category_defaults_resolver (three cases),
  test_pay_selector_atomic_cheapest_first (three cases),
  test_pay_selector_tie_and_item_selector,
  test_class_recipe_batch_conservation (Hypothesis),
  test_overlapping_inputs_cannot_double_spend,
  test_omitted_requirements_do_not_block_start. Updated
  test_creation_builds_complete_profile to assert all eight fixed ids and all
  eleven database rows; updated API/client fixtures and existing rename tests.
- SQLite make db-reset rebuilt both services using disposable /tmp databases;
  subsequent game alembic upgrade head passed. No database schema change needed.
- Final PATH=$PWD/.venv/bin:$PATH make ci passed: auth 15; game 138 passed,
  one PostgreSQL-only skip; client 23. Ruff, format, strict mypy, eslint,
  prettier, TypeScript, Vitest, production build and scripts checks all green.
  git diff --check passed; retired names have no matches in runtime code,
  content or tests. Changes remain uncommitted as instructed.

## Removed

- Retired skill/category naming, old listing cap name, flat action requirements,
  item-id action inputs and old action output/level/base-time fields.
- Removed the empty combat-monsters skill; replaced its availability assertion
  with assertions for all eight fixed empty skills. No tests deleted.
- Historical baseline audit/design text remains a historical record; old names
  there were deliberately not rewritten. Effective API cycle_ms and internal
  reward drops still describe computed timings/rewards, not retired content fields.

## Design ambiguities resolved

- §4.1: strict means no scalar coercion. ContentModel now sets strict=True;
  loader validates JSON directly with strict=True, allowing JSON arrays to
  become tuples and enum strings to become enums. Records and sequences are
  frozen; existing map dictionaries and the new skill_levels mapping retain
  Pydantic's shallow freeze semantics. Consumers must not mutate these mappings.
- §4.3: payment needs item metadata to match classes and compare prices. The
  public signature is pay_selector(holding, selector, quantity, content), with
  an explicit ContentIndex instead of global content access. Shortfall.quantity
  is the unmet amount; a failed payment contains no partial withdrawals.
- §4.3/§6.2: multiple selectors are planned in declared input order, each against
  remaining goods. This follows the cheapest-first rule without inventing a
  global recipe optimization rule.
- §6.2: retained action name for existing presentation. The optional requirements
  block defaults empty; null/omitted resolver defaults from the owning category.
  Existing realm availability is preserved using requires.realm_tags until 05;
  no facility, tool or cross-skill requirement enforcement added here.
- §4.2/§5.3: item tier and action tier are constrained to the five design tiers;
  spoilage is a daily percentage in [0,100]. No economy pack needed.

## Deviations

- PostgreSQL checks cannot run in this sandbox, per orchestrator environment
  instructions. Orchestrator must run PostgreSQL 16 CI/reset verification.

## Ratification needed

None.

## Hand-offs

- 03-bonus-model: category, tier, unlock_level, base_cycle_ms and outputs are now
  available for proficiency/taper and bonus changes; progression unchanged.
- 05-tags: replace interim realm-tag availability with node action offerings and
  full requires enforcement/revalidation. Requirement references currently use
  development-node tags; extend that registry when introducing the tags pack.
  Requirement mappings are treated as read-only, like existing content maps.
- 06-resolver-presence: actions publish a concrete resolver; dispatch remains
  yours. Existing uniform implementation and CycleRewardStrategy seam preserved.
- 07-travel, 10-project-runs, 12-estate-ownership, 14-realm-tick, 18-mint-gold,
  20-caravans and other selector consumers: reuse Selector and pay_selector from
  engine/selectors.py. Pass explicit content; apply returned withdrawals only
  after the complete enclosing payment succeeds.
- 26-equipment/27-consumables-hp: item equip/consumable blocks are absent as
  requested; belt_slots already resolves through all existing cap sources.

## New error codes

None. MISSING_INPUTS remains shared by action start/availability. Invalid content
raises ContentError; invalid pure payment quantities raise ValueError.
