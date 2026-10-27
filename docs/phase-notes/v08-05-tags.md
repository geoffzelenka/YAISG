## Built

- Strict, served `tags` and `economy` packs, included in content hashing, public
  routes, client loading and cache fixtures. Tags validate kind, existing typed
  modifiers, additive cap bonuses, selector upkeep, and every future effect
  field (market/caravan access, mint value, edge loss reduction, reserve delta).
  Economy owns `decay.faltering_factor`, authored as 0.5.
- Nodes emit `inherent_tags` and list `actions`; forms and upgrades emit `tags`
  and declare all-of `requires_realm_tags`. Placeholder content includes node
  and upgrade facilities, an access effect, and a numeric bonus tag.
- Realm and estate `decay_stage` columns default to fed. Pure
  `engine/tags.py:active_tags(holder, stage)` suspends facilities and scales
  bonus/malus modifiers in Faltering, Failing and Regressed. Fed and Strained
  are identical; access remains active. The adapter loads both stages.
- Active tags feed R/E modifiers and additive caps. Estate sources require
  presence; inert forms/upgrades contribute neither legacy bonuses/caps nor
  emitted tags. Empty realm requirements are unrestricted. Content lint now
  uses the runtime group/cap rules, including emitted tag modifiers. It checks
  Fed and Faltering candidates because weakening a malus can increase a bound.
- Shared `unmet_requirements` reports all seven blockers in stable order;
  both availability and start use it. Availability returns every action.
  Added `/actions/available` and `/actions/start`, retaining the existing
  character-scoped endpoints for the current client.
- Each resolve checks running requirements and stops with `REQUIREMENT_LOST`.
  Zero-cycle loss records survive intervening reads and are claimed once;
  the migration permits nonnegative reward-log cycles for stop-only records.
- New tests in test_tags.py: test_node_listed_gathering_and_unlisted,
  test_stage_effects_preserve_access, test_facility_realm_owner_and_elsewhere,
  test_inert_upgrade_contributes_nothing,
  test_each_requirement_code_and_shared_start,
  test_requirement_lost_grants_cycles_through_detecting_resolve,
  test_zero_cycle_requirement_loss, test_tag_bonus_group_and_cap,
  test_tag_effect_fields_are_strict,
  test_form_tags_are_inert_scaled_and_presence_scoped,
  test_lint_includes_emitted_tag_modifiers,
  test_lint_accounts_for_weakened_malus.
- New API tests using the existing TEST_DATABASE_URL fixture:
  test_tag_availability_start_and_estate_presence (changes estate.realm_id
  directly), test_requirement_lost_after_realm_node_change,
  test_zero_cycle_requirement_loss_survives_availability_read.
  Existing availability, content, engine, estate and lint tests were updated
  for the replacement field names and complete requirements report.

- Review follow-up: profiles now use load_character_state, sharing persisted
  realm/estate stages, modifiers, caps and effective action values with resolve
  and availability. The engine and content lint share modifier_applies for
  skill/category scope checks. Estate upgrade annotations use realm_active_tags
  and tags_present with the estate realm loaded once outside the upgrade loop.
- Review regression tests: test_profile_and_available_share_decay_stage_state
  covers Fed/Faltering bonuses and suspended estate cap bonuses;
  test_upgrade_annotation_uses_estate_realm_active_tags covers Fed/Faltering
  facilities while the owner is visiting another realm.

## Removed

- Legacy upgrade `realm_tags` and any-of/wildcard inertness; replaced by
  `requires_realm_tags`. Legacy node `tags` is now `inherent_tags` (realm/profile
  response summaries still expose their existing `tags` presentation field).
- Action wildcard requirements in placeholder content; an empty list expresses
  no requirement. The obsolete WRONG_REALM start code and availability filtering
  are replaced by explicit blockers. No tests were deleted.

## Design ambiguities resolved

- §6.2: “at that moment” means the detecting resolve boundary. Full accrued
  cycles are granted through that boundary under the current snapshot and
  existing offline/input/inventory constraints, then the action stops. A lost
  non-input requirement takes precedence over another stop reason. Missing
  inputs retain ordinary INPUTS_EXHAUSTED semantics rather than becoming
  REQUIREMENT_LOST. A zero-cycle detection still stops and remains reportable.
- §7.4: tag modifiers use the existing strict `{type, value, skill_id/category}`
  modifier schema established in 03, interpreting the tag sketch's scope/pct
  notation consistently with every other modifier source.
- §7.4–7.5 / §14.6: the factor scales modifiers only, not additive cap amounts,
  upkeep or effects. Facility suspension removes the whole tag. Repeated
  emissions of the same tag on a holder activate once; distinct realm and
  estate holders contribute independently in their respective groups.
- §6.2 / §22: introduce the specified start/report URLs now as aliases; retain
  character-scoped poll/stop and client calls until the resolver/presence phase
  reconciles the remaining consolidated endpoints.

- §7.4 / §14.7 / D11: inherent node tags “cannot decay” means they are never
  shed. Faltering suspension and modifier halving still apply to inherent
  tags, through the same active_tags function as other emissions. 15-decay
  depends on this distinction when implementing shedding and recovery.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 06-resolver-presence: populate the current realm from current_realm_id;
  preserve estate presence, shared requirements, stage loading, and stop-only
  reward claims. Complete the consolidated poll/stop endpoint migration.
  Existing action/realm serialization remains for that phase to replace.
- 09-development-graph: supply `CharacterState.realm_stack_tags` (empty by
  default) from completed projects. Reuse active_tags rather than duplicating
  stage rules. Keep lint's possible stack candidates aligned with new projects.
  Populate the estate realm stack used by api/estates.py:_estate_response and
  _upgrade_inert_reason, including when the owner is visiting another realm.
- 11-estate-forms / 12-estate-ownership: retain form and upgrade all-of inertness,
  owner-only estate facilities and E-group presence when replacing estate forms,
  ownership and lifecycle. Suspended upgrades have no separate runtime lifecycle
  representation yet; exclude their emissions when that state is introduced.
- 14-realm-tick / 15-decay: extend the strict economy.decay schema and drive
  the existing decay_stage columns. Consume validated tag upkeep/effects and
  use the shared pure activation function. Access survives every weak stage.
- 16-realm-pricing / 18-mint-gold / 20-caravans / 23-global-market: consume the
  validated tag effects; no economy effect execution was added here.
- 26-equipment: replace unconditional MISSING_TOOL for set tool_class with
  equipped-tool validation in the shared requirement check.

## New error codes

- NOT_OFFERED_HERE, MISSING_FACILITY, MISSING_REALM_TAG,
  MISSING_SKILL_LEVEL, MISSING_TOOL. Existing INSUFFICIENT_LEVEL and
  MISSING_INPUTS remain. REQUIREMENT_LOST is the new automatic stop reason.
