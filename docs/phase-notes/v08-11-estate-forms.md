## Built

- Added migration `v08_0006_estates`: estate gauge and shed_progress default to
  zero; existing nullable ownership, decay_stage, data and ownership history
  remain. No uniqueness constraint limits a character's estate ownership.
- Forms now own tier, build_cost (gold and selector goods), upgrade_slots,
  cap_bonuses, upkeep, production, transforms_to and regresses_to. Preserved
  mobile/profile validation, all-of requirements, owner-only facilities and
  presence-scoped E bonuses. Boot rejects mobility-changing edges, invalid
  regression tiers/references, empty selectors and an unsafe basic_mobile_form.
- Character creation uses progression.basic_mobile_form instead of a form id
  embedded in code. Form slots replace the former global-plus-form slot base;
  existing effective placeholder capacities remain 4, 6 and 7. Content lint
  continues using resolve_caps and exhaustive eligible-upgrade subsets.
- Transforms follow source.transforms_to and pay the destination's build_cost
  through pay_selector, in authored order against a shared remainder. All goods
  and gold are checked before withdrawals; gold credits the locked estate realm.
  Mobility, presence, journey-busy and orphan-upgrade guards retain stable codes.
  Orphan checking uses destination.upgrade_slots alone, without upgrade bonuses.
  Upgrade installation also checks ownership and presence. Character, sorted
  realms, estate lock order and the enclosing transaction are preserved.
- GET /estates/me exposes form, mobility, tier, slots, installed upgrades, tags
  and decay_stage. Profile estate level becomes tier with resolved slots.
  GET /realms/{id}/estates includes character UUID ownership or "realm-owned",
  form id and decay_stage, without treasury. Added pure engine.vote_weight,
  accepting the resolved EstateForm: mobile 1; fixed 9 + tier.
- Updated client content/API types and existing estate controls for the new
  fields and destination selector/gold costs. Extended the estate-panel test
  for tier, form-owned edges, slot change and destination build-cost display.
  Server validation remains authoritative for transform affordability.
- Added assert_world_estate_invariant test helper: every non-isolated character
  owns exactly one estate and its home pointer names that estate.
- New tests: test_estate_vote_weights, test_estate_form_graph_validation,
  test_fixed_form_graph_loads, test_estate_mutations_require_owner_presence,
  test_transform_mobility_guard,
  test_transform_selector_payment_and_treasury_conservation,
  test_transform_requires_destination_realm_tags,
  test_transform_overlapping_selectors_are_atomic,
  test_realm_owned_estates_listed, test_postgres_concurrent_transforms_pay_once.
  Estate API fixtures honor TEST_DATABASE_URL; the new PostgreSQL concurrency
  test skips on SQLite. Retained relocate ESTATE_BUSY and last-slot contention
  tests. Existing migration tests exercise reset, schema parity and downgrade.

- Validation: `PATH=$PWD/.venv/bin:$PATH make ci` passes on SQLite: auth 15,
  game 323 with seven database-specific skips, client 41. Formatting, lint,
  strict mypy, TypeScript, build, scripts and warning-only content lint pass.
  Disposable SQLite `make db-reset`, subsequent `alembic upgrade head` and
  `alembic check` pass. `git diff --check` is clean. No dependencies added.

- Round 1: removed the unused global estate slot base from content schema,
  caps.json, client Caps and fixtures; profiles now report the form's slots as
  base, so base plus applicable bonuses equals effective. Added
  test_profile_estate_slots_use_form_base_plus_bonuses and
  test_estate_mutations_reject_unowned_home_pointer (both mutations), asserting
  NOT_ESTATE_OWNER without spending goods or gold. Documented selector scope,
  vote_weight's EstateForm signature and the client transform limitations.
  Round 1 SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passes: auth 15, game 327
  with seven database-specific skips, client 41; all checks pass.

## Removed

- §7.5 / §13.2: removed estate_upgrade_slots from the global CapsConfig,
  caps.json, client content Caps type, fixtures and lint overrides. The runtime
  estate_upgrade_slots cap and bonus kind remain; its base is form.upgrade_slots.
- Estate level and persisted upgrade_slots columns and their API/client fields.
  Replaced the obsolete level-preservation assertion with gauge preservation
  and destination-tier assertions in the existing transform test.
- Separate transformation-edge records/costs, base_caps, specialty_tags,
  upkeep_profile and production_profile, replaced end to end by the form schema.
  Updated shrinking-slot and lint tests to express equivalent form-owned rules.
  No tests deleted.

## Design ambiguities resolved

- §13.2 / §7.5: upgrade_slots is the form's physical base, replacing the old
  global-plus-form base; cap_bonuses use the same typed records as upgrades and
  nodes. Inertness and presence still gate bonus sources, not physical slots.
- §13.3 "costs may use selectors": selectors apply to transforms only.
  Upgrade installs retain exact ItemQuantity costs, per the orchestrator ruling.
- §12.5 / §13.2: vote_weight takes the resolved EstateForm, not an estate
  record. Prompt 19 must resolve the form before calling this pure helper.
- §13.3: missing destination requirements return MISSING_REALM_TAGS; absence
  returns existing NOT_PRESENT, and a home pointer without ownership returns
  NOT_ESTATE_OWNER. Check relocate ESTATE_BUSY before other transform gates.
- §13.1 / §22: realm estate ownership is a character UUID or "realm-owned";
  form is its content id. The owner read retains installed-upgrade annotations
  and reports raw form tags separately from realm requirements.

## Deviations

None.

## Ratification needed

- §13.3–13.4: where should estate build/transform gold go? As directed by this
  prompt, transform gold credits the estate realm's treasury, consistent with
  D14 and conservation. Prompt 12 should use the same destination for builds.

## Hand-offs

- 12-estate-ownership: implement build, buy, surrender, valuation and larder;
  reuse destination build_cost, progression.basic_mobile_form and selector
  payment. Preserve ownership history, endpoint-only ownership limits and the
  world-character estate invariant; extend its helper across lifecycle tests.
- 13-stores-lines: seed realm-owned estates with null owner_character_id and
  content form ids. Realm estate reads already include them.
- 14-realm-tick: consume form production/upkeep for all estates, including
  realm-owned estates; no execution is implemented here. Preserve 10a's batched
  RealmTickContext and bounded-query hand-off when loading estate state.
- 15-decay: drive gauge, decay_stage and shed_progress; use regresses_to and
  basic_mobile_form for replacement. Preserve all-of inertness and E presence.
- 19-votes: snapshot engine.vote_weight(content.estate_form(estate.form_id))
  when creating eligibility; ownership/residency selection remains yours.
- 21-client-realm-estate: build the full ownership/larder/realm-estate UI;
  consume tier and decay_stage and the new public estate list. Current controls
  only received compatibility changes; transform affordability is server-side.
  Transform buttons are not disabled when their cost is unaffordable, and the
  cost line shows raw selector and item ids. Add affordability gating and
  readable cost labels in Prompt 21.

## New error codes

- MISSING_REALM_TAGS: the destination form's all-of realm requirements are absent.
- NOT_ESTATE_OWNER: the caller's home pointer does not name an estate they own.
- Reused NOT_PRESENT and every shipped upgrade/transform error code.
