## Built

- `make content-lint`, included in local CI and game GitHub CI jobs, emits text
  and JSON. CLI supports separate formats and alternate content directories.
  Warnings return success; malformed content retains normal loader failures.
- Strict progression.lint settings: g 1.015969 and tolerance_pct 15, authored in
  the progression pack; public client content type and fixtures updated.
- Rational target comparisons and exact integration over the 99 XP costs with
  the best unlocked base rate. Reports optimal / 720 and level-one / 2880 hours;
  empty skills report null hours. Combat is skipped. off_curve suppresses only
  the action-rate warning.
- External stack bound maximizes joint XP × speed within realm and estate
  groups, including scoped modifiers, inertness and distinct upgrades within
  slots. Excludes proficiency and runtime XP clamping. Warns above 1.45.
- Added designer documentation in docs/v08/content-lint.md explaining command
  formats, assumptions, arithmetic and conservative bound computation.
- Tests added: test_target_matches_design_table,
  test_exact_training_ladders, test_level_one_alone_is_exactly_2880_hours,
  test_training_uses_best_unlocked_rate_and_exact_costs,
  test_off_curve_suppresses_only_action_warning,
  test_stack_warning_excludes_proficiency_and_xp_cap,
  test_stack_respects_slots_scope_and_inert_upgrades,
  test_empty_skills_report_blocked_and_combat_is_skipped,
  test_content_lint_command_exits_zero_with_warnings,
  test_lint_settings_reject_invalid_values, test_rate_tolerance_is_inclusive,
  test_stack_maximizes_joint_factors_and_keeps_groups_separate.
- Final SQLite make ci passed: auth 15; game 200 plus one skip; client 23.
  Formatting, lint, strict typing, client build and scripts checks pass.
  SQLite db-reset rebuilt both services in disposable /tmp databases; head
  upgrade and alembic check passed with no schema drift.

## Removed

None.

## Design ambiguities resolved

- §5.2: simulations use continuous base rates, ignoring taper and whole-cycle
  overshoot as well as bonuses. This reproduces the specified analytical time
  anchors and permits exact XP-table integration. Multiple level-1 actions use
  the fastest; missing ones report null rather than a non-JSON infinity.
- §7.3: use uncapped external XP factors for authoring warnings; clamping first
  would conceal over-stacked content. Maximize XP × speed jointly per group.
  Separate realm/estate maxima and final-slot feasibility conservatively allow
  combinations whose joint node or installation history may be unreachable.
  These relaxations can produce extra warnings but preserve an upper bound.
- §5.2: lint fields are g and tolerance_pct; defaults live in the content pack,
  not duplicated in code. Invalid content remains an error; warnings do not.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 05-tags: reconcile the engine treating empty upgrade realm_tags as inert
  with §7.4 and the lint treating them as unrestricted. Keep scope matching in
  lint.py `_group_bound` aligned with engine `bonus_total` (or share a helper)
  when changing tag or scope matching.

- 05-tags / 09-development-graph: extend stack candidates with tag modifiers
  offered on each node, respecting tag stacking/eligibility in the same group.
  There is currently no tags pack; node tag strings only govern inert upgrades.
- 11-estate-forms / 12-estate-ownership: adapt estate bound to new form and
  upgrade slot/eligibility rules. Current exhaustive subset search fits the
  small placeholder pack; preserve an upper bound if replacing it for scale.
- 26-equipment / 27-consumables-hp: add group G equipment slot combinations
  and group C simultaneous buffs/utility candidates. Their current factors
  are identities because their content schemas do not exist yet.
- 28-combat-model: combat remains skipped; add per-combatant lint separately.

## New error codes

None. No API changes; content validation continues to use ContentError.
