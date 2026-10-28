# v0.8 final conformance audit

Audited on `v08/37-conformance`, against design v0.8 and phase notes 00–36,
including inserted 10a. Paths and line numbers below refer to this working tree.
Test names are pytest functions, including parameterized cases. “Implemented”
means evidence exists for the specified mechanic; it does not close the human
questions or the follow-ups below. This is not an unconditional claim of full
conformance: the geometric project overlay and combat rules await human rulings,
and uniform resolution still loops per cycle instead of being closed-form.

## Human rulings already given

These authoritative rulings are separate from outstanding ratification:

- 19, §12.3/§12.5: “A project requires any positive balance, but a vote requires
  a 3 day reserve. This also means that realms' goods cap must be at least
  3 days worth”. Implemented through RESERVE_SHORT and vote.min_stock_days;
  empty demand sets pass. See test_reserve_gate_before_development.
- 34, §20.2: “the kickoff requirements for raft building should cover the whole
  cost of the project and the length of that project should be short, like a
  few seconds (just enough for the player to feel like something is happening)”.
  The raft site pays everything at kickoff and builds in two seconds.
- 36, §23.6: load generation uses existing httpx + asyncio; metrics are plain
  JSON, without prometheus_client.
- APScheduler was approved as a dependency (phase 14 records 2026-10-27).
- Q3, 14 §14.4 / V§9.4.6 (ruled 2026-10-28): use a fixed amortization rate.
  At kickoff, each cost line's per-tick realm payment is fixed at the original
  requirement / (tick.per_day × realm_completion_days), capped at what the line
  still needs and still taken only from stock above the reserve. An unhelped
  project then completes in realm_completion_days. Player help makes it finish
  sooner but does not reduce the per-tick draw. Not yet implemented: the code
  still uses remaining / D, which decays geometrically. Follow-up F9.

## Vision traceability (§28)

All 28 rows are represented, in design order. Q identifiers refer to the human
list below. Placeholder content intentionally does not claim release balance.

| Vision and design | Implementing code | Behavioral tests |
|---|---|---|
| V§3.1–3.3 · §5.1–5.2, §7.3 | `services/game/app/engine/levels.py:8` (level_for_xp); `services/game/app/engine/core.py:407` (effective_xp) | `services/game/tests/test_levels.py:29` (test_design_curve_reference_points_and_halfway); `services/game/tests/test_content_lint.py:68` (test_level_one_alone_is_exactly_2880_hours); `services/game/tests/test_engine.py:608` (test_vision_groups_cap_floor_and_scope) |
| V§3.2, 3.4, 4.4 · §5.3, §8 | `services/game/app/engine/levels.py:28` (tier_for_level); `services/game/app/engine/core.py:295` (proficiency_pct); `services/game/app/engine/core.py:309` (taper_factor) | `services/game/tests/test_levels.py:58` (test_tier_boundaries); `services/game/tests/test_engine.py:586` (test_every_bonus_table_cell); `services/game/tests/test_engine.py:659` (test_tier_up_resegments_time_and_xp) |
| V§3.5–3.6 · §5.2, §6.2 | `services/game/app/engine/core.py:489` (unmet_requirements) | `services/game/tests/test_content_lint.py:61` (test_exact_training_ladders); `services/game/tests/test_tags.py:99` (test_each_requirement_code_and_shared_start) |
| V§3.7, 4.5 · §10.3–10.6 (questions Q8–Q9) | `services/game/app/engine/combat.py:54` (eff); `services/game/app/engine/combat_resolver.py:47` (CombatSimulation) | `services/game/tests/test_combat_model.py:43` (test_eff_per_tier_and_vigor); `services/game/tests/test_combat_resolver.py:717` (test_exact_offensive_stance_and_defensive_taken_mitigated_split); `services/game/tests/test_combat_model.py:247` (test_combat_lint_pool_splits_and_respawn) |
| V§3.8 · §8.3 | `services/game/app/engine/travel.py:116` (travel_total); `services/game/app/engine/core.py:773` (UniformResolver) | `services/game/tests/test_travel.py:207` (test_travel_tier_benefit_is_group_p); `services/game/tests/test_keys.py:187` (test_exploration_tier_speed_is_group_p_and_belt_shapes_discovery) |
| V§4.1–4.3 · §6 | `services/game/app/content/schemas.py:270` (Skill); `services/game/app/engine/core.py:489` (unmet_requirements) | `services/game/tests/test_content.py:405` (test_category_defaults_resolver); `services/game/tests/test_tags.py:68` (test_facility_realm_owner_and_elsewhere) |
| V§4.6 · §7.1–7.2 | `services/game/app/engine/core.py:322` (modifier_groups); `services/game/app/engine/core.py:368` (scoped_bonus_total) | `services/game/tests/test_engine.py:608` (test_vision_groups_cap_floor_and_scope); `services/game/tests/test_engine.py:680` (test_scope_and_cap_before_taper) |
| V§5 · §4.2–4.3, §5.3 | `services/game/app/content/schemas.py:437` (Item); `services/game/app/engine/selectors.py:17` (pay_selector) | `services/game/tests/test_content.py:320` (test_content_model_validation); `services/game/tests/test_engine.py:462` (test_pay_selector_atomic_cheapest_first) |
| V§6 · §9.4, §10 (Q8) | `services/game/app/engine/combat_resolver.py:487` (CombatResolver); `services/game/app/engine/health.py:10` (maximum_hp) | `services/game/tests/test_combat_resolver.py:200` (test_defeat_ends_action_and_simultaneous_kill_counts_first); `services/game/tests/test_combat_resolver.py:343` (test_regeneration_rescues_zero_hp_before_terminal_check); `services/game/tests/test_combat_resolver.py:263` (test_offline_equals_online_polling) |
| V§7.1–7.2 · §12.1–12.2 | `services/game/app/models/character.py:131` (RealmState); `services/game/app/content/schemas.py:626` (DevelopmentNode) | `services/game/tests/test_realms.py:54` (test_graph_rejects_invalid_paths_and_requirements); `services/game/tests/test_estates.py:737` (test_realm_tag_stack_public_and_action_state) |
| V§7.3, 7.6 · §14.2 | `services/game/app/engine/stores.py:103` (derive_lines); `services/game/app/engine/stores.py:26` (Demand) | `services/game/tests/test_stores.py:46` (test_line_grouping_specificity_and_value_units); `services/game/tests/test_stores.py:211` (test_funding_overlay_uses_run_snapshot_and_full_estate_upkeep) |
| V§7.4, 7.7.1 · §12.3–12.4, §14.4 (Q3) | `services/game/app/services/projects.py:170` (kickoff); `services/game/app/services/projects.py:199` (contribute); `services/game/app/services/realm_ticks.py:342` (step_5_projects) | `services/game/tests/test_projects.py:139` (test_kickoff_codes_in_order); `services/game/tests/test_projects.py:269` (test_contribute_presence_clamping_and_credits); `services/game/tests/test_realm_ticks.py:490` (test_hourly_geometric_overlay_and_spreading) |
| V§7.7.2 · §12.5–12.6 (Q5; ruled stock gates) | `services/game/app/services/votes.py:75` (call_vote); `services/game/app/services/votes.py:154` (cast_vote); `services/game/app/services/votes.py:126` (close_vote) | `services/game/tests/test_votes.py:203` (test_api_participation_secrecy_and_logs); `services/game/tests/test_votes.py:135` (test_early_close_transition_and_finalize); `services/game/tests/test_votes.py:521` (test_reserve_gate_before_development) |
| V§7.5, 7.7.3, 9.4.11–12 · §14.6–14.7 | `services/game/app/engine/decay.py:19` (advance_gauge); `services/game/app/services/realm_ticks.py:478` (decay_realm) | `services/game/tests/test_decay.py:48` (test_strained_has_no_engine_effect); `services/game/tests/test_decay.py:172` (test_shed_order_rate_transition_pause_and_recovery); `services/game/tests/test_decay.py:202` (test_d4_upgrade_survivors_regress_and_restamp) |
| V§8.1–8.5 · §13.1–13.3 | `services/game/app/content/schemas.py:576` (EstateForm); `services/game/app/api/estates.py:361` (transform_estate) | `services/game/tests/test_estate_forms.py:56` (test_estate_form_graph_validation); `services/game/tests/test_estates.py:866` (test_transform_mobility_guard); `services/game/tests/test_estates.py:462` (test_transform_errors_and_shrinking_slots) |
| V§8.6, 8.8 · §13.6–13.7, §14.5 | `services/game/app/services/realm_ticks.py:250` (step_1_production); `services/game/app/services/realm_ticks.py:268` (step_2_larder_upkeep); `services/game/app/services/realm_ticks.py:523` (decay_estate) | `services/game/tests/test_realm_ticks.py:82` (test_golden_reserve_estates_first_then_realm); `services/game/tests/test_decay.py:242` (test_estate_chain_and_replacement_retains_history) |
| V§8.7 · §13.4 (Q1–Q2) | `services/game/app/services/estates.py:12` (persisted_estate_value) | `services/game/tests/test_estates.py:1244` (test_build_buy_surrender_and_larder); `services/game/tests/test_estates.py:1498` (test_buy_surrender_always_loses_gold) |
| V§9.2 · §17 (Q7) | `services/game/app/models/market.py:20` (MarketOrder); `services/game/app/models/market.py:78` (MarketMatch) | `services/game/tests/test_order_book.py:74` (test_price_time_maker_price_refund_and_partial_fills); `services/game/tests/test_order_book.py:209` (test_two_takers_race_one_resting_order); `services/game/tests/test_world_conservation.py:142` (test_random_world_operations_conserve_goods_and_gold) |
| V§9.3, 9.4.8 · §15 (Q4, Q6) | `services/game/app/engine/market.py:91` (quote); `services/game/app/services/realm_ticks.py:642` (step_10_lines) | `services/game/tests/test_market.py:52` (test_margin_round_trip_and_unit_integral); `services/game/tests/test_market.py:112` (test_market_visibility_quotes_and_private_treasury) |
| V§9.3.3 · §14.9 | `services/game/app/services/world.py:17` (create_world); `services/game/app/services/seed_check.py:32` (check_seed) | `services/game/tests/test_stores.py:148` (test_world_creation_twice_creates_once); `services/game/tests/test_tutorial.py:496` (test_seed_check_validates_arrival_bids_at_every_tick) |
| V§9.4.1–9.4.7 · §14.1–14.4, §16 | `services/game/app/engine/stores.py:18` (due); `services/game/app/services/caravans.py:19` (run_caravan_pass) | `services/game/tests/test_stores.py:34` (test_due_sums_to_daily_rate); `services/game/tests/test_caravans.py:103` (test_nothing_bought_twice_in_transit_and_arrivals); `services/game/tests/test_caravans.py:257` (test_equal_ask_nearer_seller_wins) |
| V§9.4.9–9.4.10 · §14.5 | `services/game/app/services/realms.py:291` (resolve_realm); `services/game/app/services/realm_ticks.py:387` (step_6_spoilage) | `services/game/tests/test_realm_ticks.py:399` (test_golden_tick_pipeline_order); `services/game/tests/test_realm_ticks.py:617` (test_hourly_split_idempotence_and_payment_conservation); `services/game/tests/test_projects.py:417` (test_realm_catchup_statement_bound) |
| V§9.5 · §14.8, §18, §2.4 | `services/game/app/services/realm_ticks.py:306` (step_4_realm_upkeep); `services/game/app/models/gold.py:12` (GoldLedger) | `services/game/tests/test_gold.py:236` (test_random_gold_operations_match_ledger); `services/game/tests/test_gold.py:131` (test_scarce_bullion_drains_treasury_until_mint_stops); `services/game/tests/test_gold.py:540` (test_wallet_retains_64_bit_gold) |
| V§9.6 · §11, §15–§16 (content archetypes) | `services/game/app/engine/travel.py:216` (TravelResolver); `services/game/app/services/caravans.py:19` (run_caravan_pass) | `services/game/tests/test_trade.py:225` (test_trade_and_gift_routes); `services/game/tests/test_caravans.py:155` (test_nearer_seller_and_never_cheaper_than_ask) |
| V§10 · §19 | `services/game/app/models/instances.py:24` (ItemInstance); `services/game/app/services/keys.py:56` (invalidate_keys) | `services/game/tests/test_keys.py:96` (test_keys_never_stack_and_all_gains_count_instance_slots); `services/game/tests/test_keys.py:166` (test_binding_uses_clip_batch_and_depletion); `services/game/tests/test_keys.py:372` (test_transition_deprecation_and_invalidation_stops_running_key); `services/game/tests/test_key_market.py:125` (test_key_tax_and_listing_realm_conserve_gold) |
| V§11 · §11 | `services/game/app/engine/travel.py:35` (route); `services/game/app/engine/travel.py:216` (TravelResolver); `services/game/app/engine/core.py:216` (is_present) | `services/game/tests/test_travel.py:153` (test_random_stops_keep_exactly_last_completed_realm); `services/game/tests/test_travel.py:107` (test_routing_terrain_level_one_way_and_tie_breaks); `services/game/tests/test_resolvers.py:163` (test_visitor_loses_only_estate_sources) |
| V§12.1–12.2 · §20 | `services/game/app/services/tutorial.py:42` (create_island); `services/game/app/services/tutorial.py:170` (depart) | `services/game/tests/test_tutorial.py:85` (test_guest_completes_island_upgrades_and_departs_with_zero_gold_and_raft); `services/game/tests/test_tutorial.py:624` (test_raft_kickoff_pays_all_costs_and_completes_after_five_days_idle) |
| V§12.3 · §9.2–9.3 | `services/game/app/models/equipment.py:12` (CharacterEquipment); `services/game/app/models/equipment.py:36` (CharacterBelt) | `services/game/tests/test_equipment.py:364` (test_every_permanent_slot_round_trips); `services/game/tests/test_consumables_hp.py:235` (test_setup_holders_capacity_triggers_and_conservation) |

## Reconciliation (§2.1 R1–R17)

References select the preceding evidence rows without substituting a phase note
for implementing code or executable tests.

| Requirement | Implementing code | Behavioral tests |
|---|---|---|
| R1 XP curve | `services/game/app/engine/levels.py:8` (level_for_xp); `services/game/app/engine/core.py:407` (effective_xp) | `services/game/tests/test_levels.py:29` (test_design_curve_reference_points_and_halfway); `services/game/tests/test_content_lint.py:68` (test_level_one_alone_is_exactly_2880_hours); `services/game/tests/test_engine.py:608` (test_vision_groups_cap_floor_and_scope) |
| R2 Tiers | `services/game/app/engine/levels.py:28` (tier_for_level); `services/game/app/engine/core.py:295` (proficiency_pct); `services/game/app/engine/core.py:309` (taper_factor) | `services/game/tests/test_levels.py:58` (test_tier_boundaries); `services/game/tests/test_engine.py:586` (test_every_bonus_table_cell); `services/game/tests/test_engine.py:659` (test_tier_up_resegments_time_and_xp) |
| R3 Bonus stacking | `services/game/app/engine/core.py:322` (modifier_groups); `services/game/app/engine/core.py:368` (scoped_bonus_total) | `services/game/tests/test_engine.py:608` (test_vision_groups_cap_floor_and_scope); `services/game/tests/test_engine.py:680` (test_scope_and_cap_before_taper) |
| R4 Categories | `services/game/app/content/schemas.py:270` (Skill); `services/game/app/engine/core.py:489` (unmet_requirements) | `services/game/tests/test_content.py:405` (test_category_defaults_resolver); `services/game/tests/test_tags.py:68` (test_facility_realm_owner_and_elsewhere) |
| R5 Tag development and votes | `services/game/app/services/votes.py:75` (call_vote); `services/game/app/services/votes.py:154` (cast_vote); `services/game/app/services/votes.py:126` (close_vote) | `services/game/tests/test_votes.py:203` (test_api_participation_secrecy_and_logs); `services/game/tests/test_votes.py:135` (test_early_close_transition_and_finalize); `services/game/tests/test_votes.py:521` (test_reserve_gate_before_development) |
| R6 Project lifecycle | `services/game/app/services/projects.py:170` (kickoff); `services/game/app/services/projects.py:199` (contribute); `services/game/app/services/realm_ticks.py:342` (step_5_projects) | `services/game/tests/test_projects.py:139` (test_kickoff_codes_in_order); `services/game/tests/test_projects.py:269` (test_contribute_presence_clamping_and_credits); `services/game/tests/test_realm_ticks.py:490` (test_hourly_geometric_overlay_and_spreading) |
| R7 Decay unwinds stack | `services/game/app/engine/decay.py:19` (advance_gauge); `services/game/app/services/realm_ticks.py:478` (decay_realm) | `services/game/tests/test_decay.py:48` (test_strained_has_no_engine_effect); `services/game/tests/test_decay.py:172` (test_shed_order_rate_transition_pause_and_recovery); `services/game/tests/test_decay.py:202` (test_d4_upgrade_survivors_regress_and_restamp) |
| R8 Pairwise remoteness | `services/game/app/engine/stores.py:18` (due); `services/game/app/services/caravans.py:19` (run_caravan_pass) | `services/game/tests/test_stores.py:34` (test_due_sums_to_daily_rate); `services/game/tests/test_caravans.py:103` (test_nothing_bought_twice_in_transit_and_arrivals); `services/game/tests/test_caravans.py:257` (test_equal_ask_nearer_seller_wins) |
| R9 Estate ownership and production | `services/game/app/services/realm_ticks.py:250` (step_1_production); `services/game/app/services/realm_ticks.py:268` (step_2_larder_upkeep); `services/game/app/services/realm_ticks.py:523` (decay_estate) | `services/game/tests/test_realm_ticks.py:82` (test_golden_reserve_estates_first_then_realm); `services/game/tests/test_decay.py:242` (test_estate_chain_and_replacement_retains_history) |
| R10 Journeys replace relocation | `services/game/app/engine/travel.py:35` (route); `services/game/app/engine/travel.py:216` (TravelResolver); `services/game/app/engine/core.py:216` (is_present) | `services/game/tests/test_travel.py:153` (test_random_stops_keep_exactly_last_completed_realm); `services/game/tests/test_travel.py:107` (test_routing_terrain_level_one_way_and_tie_breaks); `services/game/tests/test_resolvers.py:163` (test_visitor_loses_only_estate_sources) |
| R11 Presence without visitor malus | `services/game/app/engine/travel.py:35` (route); `services/game/app/engine/travel.py:216` (TravelResolver); `services/game/app/engine/core.py:216` (is_present) | `services/game/tests/test_travel.py:153` (test_random_stops_keep_exactly_last_completed_realm); `services/game/tests/test_travel.py:107` (test_routing_terrain_level_one_way_and_tie_breaks); `services/game/tests/test_resolvers.py:163` (test_visitor_loses_only_estate_sources) |
| R12 Zero gold and mint | `services/game/app/services/realm_ticks.py:306` (step_4_realm_upkeep); `services/game/app/models/gold.py:12` (GoldLedger) | `services/game/tests/test_gold.py:236` (test_random_gold_operations_match_ledger); `services/game/tests/test_gold.py:131` (test_scarce_bullion_drains_treasury_until_mint_stops); `services/game/tests/test_gold.py:540` (test_wallet_retains_64_bit_gold) |
| R13 Combat | `services/game/app/engine/combat_resolver.py:487` (CombatResolver); `services/game/app/engine/health.py:10` (maximum_hp) | `services/game/tests/test_combat_resolver.py:200` (test_defeat_ends_action_and_simultaneous_kill_counts_first); `services/game/tests/test_combat_resolver.py:343` (test_regeneration_rescues_zero_hp_before_terminal_check); `services/game/tests/test_combat_resolver.py:263` (test_offline_equals_online_polling) |
| R14 Keys | `services/game/app/models/instances.py:24` (ItemInstance); `services/game/app/services/keys.py:56` (invalidate_keys) | `services/game/tests/test_keys.py:96` (test_keys_never_stack_and_all_gains_count_instance_slots); `services/game/tests/test_keys.py:166` (test_binding_uses_clip_batch_and_depletion); `services/game/tests/test_keys.py:372` (test_transition_deprecation_and_invalidation_stops_running_key); `services/game/tests/test_key_market.py:125` (test_key_tax_and_listing_realm_conserve_gold) |
| R15 Equipment | `services/game/app/models/equipment.py:12` (CharacterEquipment); `services/game/app/models/equipment.py:36` (CharacterBelt) | `services/game/tests/test_equipment.py:364` (test_every_permanent_slot_round_trips); `services/game/tests/test_consumables_hp.py:235` (test_setup_holders_capacity_triggers_and_conservation) |
| R16 Guests and tutorial | `services/game/app/services/tutorial.py:42` (create_island); `services/game/app/services/tutorial.py:170` (depart) | `services/game/tests/test_tutorial.py:85` (test_guest_completes_island_upgrades_and_departs_with_zero_gold_and_raft); `services/game/tests/test_tutorial.py:624` (test_raft_kickoff_pays_all_costs_and_completes_after_five_days_idle) |
| R17 Caravan procurement | `services/game/app/engine/stores.py:18` (due); `services/game/app/services/caravans.py:19` (run_caravan_pass) | `services/game/tests/test_stores.py:34` (test_due_sums_to_daily_rate); `services/game/tests/test_caravans.py:103` (test_nothing_bought_twice_in_transit_and_arrivals); `services/game/tests/test_caravans.py:257` (test_equal_ask_nearer_seller_wins) |

R8 uses `services/game/app/engine/caravans.py:19` (remoteness) for pairwise
route costs and additionally has no distance input in engine/market.py:quote; R9 ownership
is covered separately by the estate sales row. R17 largest-draw ordering is
pinned by test_largest_reference_draw_gets_single_capacity_allowance and buyer
priority by test_hungriest_buyer_gets_shared_seller_capacity (test_caravans.py).
R16 auth upgrade identity is pinned by auth test_guest_claims_upgrade_identity_and_refresh.

## Required testing inventory (§23.4)

Every named behavior has an existing executable test below. Defeat uses authored
zero regeneration; the separate revival regression deliberately pins Q8's
literal order. Database Hypothesis tests disable deadlines. PostgreSQL-specific
lock tests skip on SQLite; their presence does not claim local PG execution.

| Clause | Test evidence |
|---|---|
| Existing resolve associativity | `services/game/tests/test_engine.py:127` (test_repeated_resolve_equals_one_large_resolve) |
| Existing recipe conservation | `services/game/tests/test_engine.py:418` (test_recipe_input_conservation) |
| Seeded drops | `services/game/tests/test_engine.py:401` (test_seeded_drop_frequency_is_close_to_declared_chance) |
| Two-session reward contention | `services/game/tests/test_actions.py:356` (test_concurrent_resolves_contend_and_do_not_double_reward) |
| §5 Total and halfway level | `services/game/tests/test_levels.py:29` (test_design_curve_reference_points_and_halfway) |
| §5 Tier thresholds | `services/game/tests/test_levels.py:58` (test_tier_boundaries) |
| §7 1.452, multiplication, cap, negative groups | `services/game/tests/test_engine.py:608` (test_vision_groups_cap_floor_and_scope) |
| §8 Every table cell | `services/game/tests/test_engine.py:586` (test_every_bonus_table_cell) |
| §8 Tier-up within batch | `services/game/tests/test_engine.py:659` (test_tier_up_resegments_time_and_xp) |
| §10 Hit bounds | `services/game/tests/test_combat_model.py:49` (test_hit_bounds_rounding_and_miss_mitigation) |
| §10 Pools drain once, respawn refill, kill remainder | `services/game/tests/test_combat_resolver.py:88` (test_pools_drain_once_refill_only_on_respawn_and_remainder_lost) |
| §10 Ammunition exhaustion | `services/game/tests/test_combat_resolver.py:156` (test_ranged_requires_ammunition_melee_and_magic_continue) |
| §10 Defeat | `services/game/tests/test_combat_resolver.py:200` (test_defeat_ends_action_and_simultaneous_kill_counts_first) |
| §10 Seeded online/offline equivalence | `services/game/tests/test_combat_resolver.py:263` (test_offline_equals_online_polling) |
| §11 No limbo; stopping | `services/game/tests/test_travel.py:153` (test_random_stops_keep_exactly_last_completed_realm) |
| §11 Boat/terrain | `services/game/tests/test_travel.py:107` (test_routing_terrain_level_one_way_and_tie_breaks) |
| §12 One active run | `services/game/tests/test_projects.py:575` (test_postgres_two_kickoffs_one_active_run) |
| §12 Daily kickoff limit | `services/game/tests/test_projects.py:228` (test_daily_kickoff_limit_across_realms) |
| §12 Erosion/failure | `services/game/tests/test_projects.py:349` (test_erosion_failure_cooldown_and_reset) |
| §12 Ballot secrecy | `services/game/tests/test_votes.py:203` (test_api_participation_secrecy_and_logs) |
| §12 Weights | `services/game/tests/test_votes.py:108` (test_weights_snapshot_excludes_arrivals_keeps_leavers) |
| §12 Early close | `services/game/tests/test_votes.py:135` (test_early_close_transition_and_finalize) |
| §12 Tie/no-votes failure | `services/game/tests/test_votes.py:86` (test_tie_abstention_and_no_votes_fail) |
| §14 Idempotent and split catch-up | `services/game/tests/test_realm_ticks.py:617` (test_hourly_split_idempotence_and_payment_conservation) |
| §14 Tick order | `services/game/tests/test_realm_ticks.py:399` (test_golden_tick_pipeline_order) |
| §14 Strained cosmetic | `services/game/tests/test_decay.py:48` (test_strained_has_no_engine_effect) |
| §14 Strained tick equality | `services/game/tests/test_decay.py:675` (test_strained_has_no_realm_tick_effect) |
| §14 Shed order | `services/game/tests/test_decay.py:172` (test_shed_order_rate_transition_pause_and_recovery) |
| §14 Regression restamps | `services/game/tests/test_decay.py:202` (test_d4_upgrade_survivors_regress_and_restamp) |
| §14 Mint/authorized gold sources only | `services/game/tests/test_gold.py:236` (test_random_gold_operations_match_ledger) |
| §15 Ask margin, random round trip, summed unit integrals | `services/game/tests/test_market.py:52` (test_margin_round_trip_and_unit_integral) |
| §15 Budgets bounded by treasury | `services/game/tests/test_market.py:76` (test_budget_conservation_and_bisection) |
| §16 No duplicate transit purchases | `services/game/tests/test_caravans.py:103` (test_nothing_bought_twice_in_transit_and_arrivals) |
| §16 Equal ask prefers nearer | `services/game/tests/test_caravans.py:257` (test_equal_ask_nearer_seller_wins) |
| §16 Delivery never cheaper than ask | `services/game/tests/test_caravans.py:155` (test_nearer_seller_and_never_cheaper_than_ask) |
| §17 World conservation | `services/game/tests/test_world_conservation.py:142` (test_random_world_operations_conserve_goods_and_gold) |
| §17 Price-time and maker price | `services/game/tests/test_order_book.py:74` (test_price_time_maker_price_refund_and_partial_fills) |
| §17 Racing takers | `services/game/tests/test_order_book.py:209` (test_two_takers_race_one_resting_order) |
| §19 Never stack | `services/game/tests/test_keys.py:96` (test_keys_never_stack_and_all_gains_count_instance_slots) |
| §19 Binding | `services/game/tests/test_keys.py:166` (test_binding_uses_clip_batch_and_depletion) |
| §19 Invalidation stops actions | `services/game/tests/test_keys.py:372` (test_transition_deprecation_and_invalidation_stops_running_key) |
| §20 No island gold exported | `services/game/tests/test_tutorial.py:85` (test_guest_completes_island_upgrades_and_departs_with_zero_gold_and_raft) |

## Consolidated data model (§21)

Every retained/new table exists. Existing migration test
`services/game/tests/test_migrations.py:test_v08_baseline_upgrade_check_and_downgrade`
upgrades to head, compares actual tables/columns against metadata via Alembic,
downgrades and rebuilds. Auth has its independent guest migration test.

| Table | Design status | Model evidence |
|---|---|---|
| `characters` | CHANGE | `services/game/app/models/character.py:27` (Character) |
| `character_skills` | CHANGE | `services/game/app/models/character.py:56` (CharacterSkill) |
| `currency` | CHANGE | `services/game/app/models/character.py:73` (Currency) |
| `estates` | CHANGE | `services/game/app/models/character.py:89` (Estate) |
| `estate_ownership_history` | SHIPPED | `services/game/app/models/character.py:114` (EstateOwnershipHistory) |
| `realm_state` | CHANGE | `services/game/app/models/character.py:131` (RealmState) |
| `realm_tags` | NEW | `services/game/app/models/character.py:163` (RealmTag) |
| `estate_upgrades` | SHIPPED | `services/game/app/models/character.py:186` (EstateUpgrade) |
| `inventories` | SHIPPED | `services/game/app/models/character.py:201` (Inventory) |
| `active_actions` | CHANGE | `services/game/app/models/character.py:216` (ActiveActionRecord) |
| `reward_log` | SHIPPED | `services/game/app/models/character.py:237` (RewardLog) |
| `realm_project_runs` | NEW | `services/game/app/models/character.py:264` (RealmProjectRun) |
| `realm_contributions` | CHANGE | `services/game/app/models/character.py:295` (RealmContribution) |
| `estate_larder` | NEW | `services/game/app/models/character.py:313` (EstateLarder) |
| `character_equipment` | NEW | `services/game/app/models/equipment.py:12` (CharacterEquipment) |
| `character_belt` | NEW | `services/game/app/models/equipment.py:36` (CharacterBelt) |
| `character_buffs` | NEW | `services/game/app/models/equipment.py:53` (CharacterBuff) |
| `gold_ledger` | NEW | `services/game/app/models/gold.py:12` (GoldLedger) |
| `goods_ledger` | Extension (33/36) | `services/game/app/models/gold.py:37` (GoodsLedger) |
| `item_instances` | NEW | `services/game/app/models/instances.py:24` (ItemInstance) |
| `key_listings` | NEW | `services/game/app/models/key_market.py:20` (KeyListing) |
| `market_orders` | NEW | `services/game/app/models/market.py:20` (MarketOrder) |
| `market_matches` | NEW | `services/game/app/models/market.py:78` (MarketMatch) |
| `metric_deltas` | Extension (33/36) | `services/game/app/models/operations.py:11` (MetricDelta) |
| `mutation_windows` | Extension (33/36) | `services/game/app/models/operations.py:20` (MutationWindow) |
| `players` | SHIPPED | `services/game/app/models/player.py:12` (Player) |
| `realm_shipments` | NEW | `services/game/app/models/shipments.py:12` (RealmShipment) |
| `realm_stores` | NEW | `services/game/app/models/stores.py:20` (RealmStore) |
| `realm_lines` | NEW | `services/game/app/models/stores.py:34` (RealmLine) |
| `world_state` | NEW | `services/game/app/models/stores.py:52` (WorldState) |
| `realm_votes` | NEW | `services/game/app/models/votes.py:21` (RealmVote) |
| `realm_vote_eligibility` | NEW | `services/game/app/models/votes.py:55` (RealmVoteEligibility) |
| `realm_edges` / actual legacy `realm_edge_progress` | DROP: absent from current metadata | migration v08_0004_graph; test_v08_baseline_upgrade_check_and_downgrade |
| `realm_projects` | DROP: absent, replaced by runs | migration v08_0004_graph then v08_0005_projects; same migration test |
| Auth `users` | CHANGE: kind and nullable credentials | services/auth/app/models.py:User; test_auth_guest_migration_schema_and_downgrade |

Column spelling differences retained from shipped code: belt `slot` rather than
`slot_index`; ownership history `acquired_at`/`relinquished_at` rather than
`from_at`/`to_at`. Larder uses `quantity_milli` as §21 requires (the §13.1 sketch
says quantity). No unique-owner schema limit was introduced. History survives
estate destruction through unowned tombstones (phase 15 decision).

## Consolidated API (§22, including §17.3)

All specified operations are registered. The key market shares a handler whose
operation parameter is restricted to buy/cancel; the inventory regression checks
that enum as well as the concrete operation URLs. The inventory below lists actual route
spelling (parameter variable names do not change the URI contract). Status is
SHIPPED/CHANGE/NEW as in §22. Tests of business semantics are the tables above;
OpenAPI and authenticated 404 tests additionally pin action removals.
`test_design_tables_and_endpoints_exist_without_retired_schema` checks the
complete expected table/endpoint inventory. The realm summary now includes
open_vote, tested for secrecy on list/detail and null after closure.

| Method and endpoint | Design status | Handler evidence |
|---|---|---|
| `GET /actions/available` | CHANGE | `services/game/app/api/actions.py:176` (available_actions) |
| `POST /actions/start` | CHANGE | `services/game/app/api/actions.py:210` (start_action) |
| `GET /actions/poll` | CHANGE | `services/game/app/api/actions.py:291` (get_action) |
| `POST /actions/stop` | CHANGE | `services/game/app/api/actions.py:338` (stop_action) |
| `GET /admin/economy` | NEW | `services/game/app/api/admin.py:16` (economy) |
| `GET /admin/metrics` | NEW | `services/game/app/api/admin.py:52` (metrics) |
| `POST /characters` | CHANGE | `services/game/app/api/characters.py:168` (create_character) |
| `GET /characters/me` | CHANGE | `services/game/app/api/characters.py:385` (get_profile) |
| `GET /characters/me/inventory` | CHANGE | `services/game/app/api/characters.py:401` (get_inventory) |
| `PUT /characters/me/stance` | NEW | `services/game/app/api/characters.py:434` (change_stance) |
| `GET /content/manifest` | SHIPPED | `services/game/app/api/content.py:21` (get_manifest) |
| `GET /content/{pack}` | SHIPPED | `services/game/app/api/content.py:27` (get_pack) |
| `POST /equipment/equip` | NEW | `services/game/app/api/equipment.py:135` (equip) |
| `POST /equipment/unequip` | NEW | `services/game/app/api/equipment.py:147` (unequip) |
| `PUT /equipment/utility` | NEW | `services/game/app/api/equipment.py:273` (setup_utility) |
| `PUT /equipment/belt/{slot}` | NEW | `services/game/app/api/equipment.py:285` (setup_belt) |
| `GET /estates/me` | SHIPPED | `services/game/app/api/estates.py:292` (get_estate) |
| `POST /estates/me/upgrades/{upgrade_id}` | SHIPPED | `services/game/app/api/estates.py:309` (purchase_upgrade) |
| `POST /estates/me/transform` | SHIPPED | `services/game/app/api/estates.py:361` (transform_estate) |
| `POST /estates/build` | NEW | `services/game/app/api/estates.py:484` (build_estate) |
| `POST /estates/{estate_id}/buy` | NEW | `services/game/app/api/estates.py:539` (buy_estate) |
| `POST /estates/me/surrender` | NEW | `services/game/app/api/estates.py:585` (surrender_estate) |
| `POST /estates/me/larder` | NEW | `services/game/app/api/estates.py:631` (deposit_larder) |
| `POST /keys/market` | NEW | `services/game/app/api/key_market.py:55` (create) |
| `POST /keys/market/{identifier}/{operation}` | NEW | `services/game/app/api/key_market.py:80` (transfer) |
| `GET /keys/market` | NEW | `services/game/app/api/key_market.py:140` (browse) |
| `GET /keys/me` | NEW | `services/game/app/api/keys.py:52` (get_keys) |
| `DELETE /keys/{identifier}` | NEW | `services/game/app/api/keys.py:73` (delete_key) |
| `POST /market/orders` | NEW | `services/game/app/api/market.py:87` (place_order) |
| `GET /market/orders/me` | NEW | `services/game/app/api/market.py:118` (own_orders) |
| `GET /market/history/me` | NEW | `services/game/app/api/market.py:153` (own_history) |
| `GET /market/book/{item_id}` | NEW | `services/game/app/api/market.py:193` (book) |
| `POST /market/orders/{order_id}/cancel` | NEW | `services/game/app/api/market.py:225` (cancel) |
| `POST /market/orders/{order_id}/collect` | NEW | `services/game/app/api/market.py:243` (collect) |
| `GET /players/me` | SHIPPED (identity bootstrap) | `services/game/app/api/players.py:24` (get_me) |
| `GET /realms` | CHANGE | `services/game/app/api/realms.py:243` (get_realms) |
| `GET /realms/{realm_id}` | CHANGE | `services/game/app/api/realms.py:282` (get_realm) |
| `GET /map` | CHANGE | `services/game/app/api/realms.py:303` (get_map) |
| `GET /realms/{realm_id}/projects/availability` | Extension (21) | `services/game/app/api/realms.py:364` (project_availability) |
| `POST /realms/{realm_id}/projects/{project_id}/kickoff` | CHANGE | `services/game/app/api/realms.py:390` (kickoff_project) |
| `POST /realms/{realm_id}/project/contribute` | CHANGE | `services/game/app/api/realms.py:411` (contribute_project) |
| `GET /realms/{realm_id}/tags/{tag_id}` | NEW | `services/game/app/api/realms.py:450` (tag_credits) |
| `GET /realms/{realm_id}/estates` | NEW | `services/game/app/api/realms.py:504` (get_realm_estates) |
| `GET /realms/{realm_id}/market` | NEW | `services/game/app/api/realms.py:602` (get_market) |
| `GET /realms/{realm_id}/market/quote` | NEW | `services/game/app/api/realms.py:625` (get_market_quote) |
| `POST /realms/{realm_id}/market/trade` | NEW | `services/game/app/api/realms.py:674` (trade_market) |
| `POST /realms/{realm_id}/treasury/gift` | NEW | `services/game/app/api/realms.py:702` (gift_treasury) |
| `POST /realms/{realm_id}/upgrades/{upgrade_id}/call` | NEW | `services/game/app/api/realms.py:752` (call_upgrade_vote) |
| `POST /realms/{realm_id}/vote` | NEW | `services/game/app/api/realms.py:774` (submit_vote) |
| `GET /realms/{realm_id}/vote` | NEW | `services/game/app/api/realms.py:796` (get_vote) |
| `GET /travel/preview` | NEW | `services/game/app/api/travel.py:75` (preview) |
| `POST /travel/start` | NEW | `services/game/app/api/travel.py:127` (start) |
| `POST /tutorial/depart` | NEW | `services/game/app/api/tutorial.py:23` (departure) |
| `POST /auth/guest`, `POST /auth/upgrade` | NEW | services/auth/app/api.py:guest, upgrade; auth test_guest_claims_upgrade_identity_and_refresh |
| `GET /characters/me/relocate/preview`, `POST /characters/me/relocate` | REMOVE: absent | test_travel_preview_start_stop_and_removed_routes; test_consolidated_action_routes_replace_aliases |
| Legacy character-scoped action aliases | Removed here (06 hand-off) | test_removed_action_aliases_return_not_found |

Content and map remain public; auth guest is public and upgrade needs a bearer
identity. Character/equipment/combat fields are server projections. Realm reads
resolve before quotes; world/tick jobs are liveness drivers. Tutorial detail
reads are owner-only; world list/map hide isolated instances. No raw treasury is
returned by player projections; operator-only economy/metrics intentionally
report private holdings (§18/§23.6). Q4 concerns inference from required fields.

## Removal audit

Runtime source and authored content were searched, excluding migrations and
historical phase notes. Old names survive only as rejection/removal assertions,
golden historical snapshots or documentation where appropriate.

| Removed concept | Result and replacement | Regression evidence |
|---|---|---|
| Starting grant / STARTING_GOLD | Zero currency; explicit isolated seed ledger | tutorial end-to-end and gold conservation tests above |
| crafting category; market_listings cap | manufacturing; order_slots | test_content_model_validation; strict content boot |
| cycle_time_pct; market_tax_pct modifiers | cycle_speed_pct; flat seller tax | test_retired_modifier_types_are_rejected |
| CycleRewardStrategy seam | ActionResolver registry | test_registry_dispatch_and_clipped_budget; pre-refactor goldens |
| Relocation endpoints, cost helpers and estate columns | Travel steps and presence | test_travel_preview_start_stop_and_removed_routes; migrations parity |
| Character realm_id | current_realm_id | migration parity; travel persistence tests |
| Edge progress/awards, old projects and contribute route | tag stacks, project runs | graph/project tests above; metadata parity |
| market_offers | dynamic realm quote/integral | strict realm schema; market tests above |
| Estate level/upgrade_slots, transformation edges, dormant profiles | form tier, slots, transforms_to, production/upkeep | test_estate_form_graph_validation; migration parity |
| Legacy action URL aliases | consolidated /actions routes only | test_consolidated_action_routes_replace_aliases; authenticated 404 test |

## Cross-cutting and client evidence

- §3/§23.1: pure engine inputs; orchestration owns database/clock/RNG, character
  locks precede sorted realms, estates, swept orders. test_postgres_resolve_locks_character_with_or_without_action,
  test_postgres_travel_holds_character_realms_and_estate,
  test_postgres_two_buyers_one_estate, test_postgres_buy_waits_for_seller_wallet_mutation
  and test_scheduler_realm_lock_order_matches_python_sorting cover these seams.
- 10a batching: test_realm_catchup_statement_bound compares short/full catch-up
  including decay/mint/key cases, with telemetry's separate single insert batch.
  Generated world conservation keeps OPERATIONS and an independent required set;
  every example exercises transfers, losses, instances, gear, belt and tutorial.
- §23.2/§23.5/§23.6: test_postgres_scheduler_advisory_lock_two_processes,
  test_all_mutation_routes_include_limiter_and_reads_use_method_gate,
  test_postgres_stale_rate_windows_do_not_deadlock, and transactional metric
  regressions in test_hardening.py. New test_conformance.py pins bounded metric
  compaction, rollback, periodic invocation and PostgreSQL skip-locked overlap.
  The implementation is services/game/app/services/metrics.py:compact_deltas,
  called by services/game/app/services/market_lifecycle.py:run_market_lifecycle.
- §24: client/src/features/{skills,realm,estate,market,equipment,combat,keys,tutorial}
  contain the panels and co-located tests. Named examples: “previews server edge
  times and supplies then starts the selected journey” (TravelForm.test.tsx),
  “blocks guest departure, upgrades in place, confirms game promotion, then departs”
  (TutorialBanner.test.tsx), and “keeps unequip and assigned stack returns disabled
  during combat” (EquipmentPanel.test.tsx). Deferred presentation coverage is
  explicitly listed below; panel existence does not imply all polish is complete.

## Ratification needed (consolidated for a human)

All 38 earlier notes, including their orchestrator sections, were considered.
Repeated “unchanged” references in 24–36 are deduplicated. Resolved phase-19
stock gates and the phase-34 raft ruling are above, not outstanding questions.
No new gameplay decision is taken here.

| ID | Source / authority | Question and behavior implemented meanwhile |
|---|---|---|
| Q1 | 11 §13.3–13.4; 12 payment reading | Should build/transform gold go to the estate realm treasury? It currently does, following D14/conservation. |
| Q2 | 12 §13.4 | Forbid zero-valued fixed forms? Formula permits zero buy/surrender prices, so strict loss cannot hold at zero. Formula retained; positive values tested. |
| Q4 | 16 §15.5 / V§9.4.8 (orchestrator question) | Required funded_total and visible weights allow close treasury estimates. Retain fields or change privacy/visibility requirements? Raw balances remain hidden. |
| Q5 | 19 §12.5–12.6 / §14.7 | Ratify interim conflict precedence? A yes-majority with pending transition or vanished edge fails, fee retained, cooldown from exact close; existing transition preserved. |
| Q6 | 17/22 §15.3 / §22 | Align NO_DEMAND statuses? Quote returns 400, trade 409; client handles both by code. |
| Q7 | 23 §17.1 (repeated 24–36) | Prohibit self-matching? Allowed, with ordinary escrow/tax. It can inflate volume and steer tax; world conservation uses distinct owners. |
| Q8 | 29 §10.5 steps 6–8 / V§6.2.2 (repeated 30–36) | Zero-HP regeneration makes DEFEATED unreachable with default positive regeneration. Choose (a) latch defeat at step 3, (b) suppress regen at 0 but permit belt rescue, or (c) retain literal order and rebalance content. Literal order retained; carried attacks at 0 can still award defensive mitigation XP (dependent N3). |
| Q9 | 29 §7.2–7.3 / §10.5 / V§4.5 | Apply xp_pct and general XP cap to combat pools? Current pool formulas ignore both and retain per-encounter ceilings. Decide multiplier/drain/cap interaction. |

## Follow-up prompts and hand-off disposition

These are scoped work proposals, not silently implemented architecture changes.
None authorizes a new dependency. No §25 excluded feature was added.

| Follow-up | Origin | Scope / acceptance |
|---|---|---|
| F1 Operational retention | 36 → 37 | Metric roll-up fixed here: bounded locked batches replace raw deltas with equivalent summed deltas in one lifecycle transaction. Allowance pruning remains optional, separately scoped: bounded independent maintenance transaction, PostgreSQL SKIP LOCKED, recheck stale windows under lock, race against live attempts, preserve rate limits. Request paths never delete other accounts. Unused window index removed here; recreate with pruning when justified. Sustained ingestion above one compaction batch per lifecycle cadence needs capacity measurements/tuning. |
| F2 Lock/dependency protocol | 07/20/21/23/24/33 → 36 → 37 | Narrow global travel/map, market, availability, caravan, lifecycle and guest-purge locks only with complete provenance dependencies, empty-book serialization, deterministic ordering and actual PG races. Existing conservative locks remain correct. |
| F3 Resolver scaling | 00/06 §6.3 | Uniform still rolls each cycle; closed-form wording is not met. Preserve seeded reward order, overflow/input precedence, tier/buff boundaries and goldens if implementing safe batching. Combat retains its bounded stepped loop and normal-CI 12-hour test. |
| F4 Historical key retention | 31/32 → 36 | Establish safe action/discovery timestamp watermark before pruning transition_history; cache parsing only while retaining first-cutoff-wins and exact historical earnings. No unsafe truncation. |
| F5 Client completion/polish | 30/35 → 36 → 37 | Equipment met/unmet/current levels, missing-skill default, doll group, belt legends, and explicit unequip/return combat coverage fixed here. Remaining: fractional HP text, encounter initial combat filter/stable keys, stance hook naming, active meta and idle-profile/active-inventory poll mutation tests; scoped key/listing errors, friendly lifecycle/realm labels, unbound/destroy/fully-paid kickoff tests; split guestSession API. Preserve auth promotion ordering and key combat locks. |
| F6 Content/lint projections | 09/18/26/27/28 → 36 | Consolidate tag/mint helpers; public lint projection API; style-specific standard gear; damage-type reference validation. Optimize selectors/gear/buff enumeration only with bottleneck evidence and preserved conservative upper bounds. |
| F7 Read/API scale | 22/32 → 36 | Batched map health with server below_reserve; sparse key-market scan cursor/cap policy; transition-due buy commit-before-error and MARKET_RETRY automatic retry need explicit transaction/idempotency rules. Durable key-sale history is separate schema work, not a conformance requirement. |
| F8 Reset/migration isolation | 01/28 → 36 | Host alias/DNS identity policy for destructive reset guard; decouple old stance migration from evolving application content loader. Existing guard and migration tests retained. |
| F9 Project overlay amortization | 14 → Q3 ruling | Implement the Q3 ruling in tick step 5: fix each cost line's per-tick realm payment at kickoff (original requirement / (per_day × realm_completion_days), rounded up to whole milli-units), cap it at the remaining need and at stock above the reserve. Replace the pinned geometric test; make test_realm_overlay_completes_without_player_contributions cover the default hourly cadence and D > 1, and check that a fully funded line stops drawing. |

## Verification

Final SQLite make ci passes: auth 39 passed / 1 skipped, game 855 passed /
34 skipped, client 124 passed, including formatting, lint, strict typing,
production build, scripts, warning-only content lint and fatal seed-check.
The existing external sandbox asyncio wake-up shim was used, as in phase 36;
no shim ships. Disposable SQLite reset, head upgrade, schema comparison and
app lifespan/content-manifest smoke checks pass.
This sandbox cannot connect to PostgreSQL; the new PG-only compaction regression
uses the existing TEST_DATABASE_URL fixture and skips on SQLite. PG execution
belongs to the orchestrator. No existing tests were deleted or weakened; old
alias callers were migrated to consolidated endpoints with the same assertions.
No dependency added. Design and prompt files were left untouched.
