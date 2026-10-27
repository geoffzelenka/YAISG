## Built

- Five pure bonus groups G/E/R/C/P: percentages add within a group and factors
  multiply across groups. State supplies empty gear/consumable provider tuples;
  estate includes form and non-inert upgrades only when estate_realm_id equals
  realm_id. Database adapters supply both ids. Caps use the same presence gate.
- Skill/category/all scope; separate speed, XP and drop calculations. Speed
  divides base milliseconds and floors; drop probabilities clamp to [0, 1].
- Strict progression fields: min_factor 0.25, min_cycle_ms 1, XP cap 45%,
  proficiency and taper tables for all six categories, including combat offense.
- XP cap precedes taper and a single floor. Existing level segmentation also
  recomputes proficiency/taper at tier boundaries.
- Profile actions map and available-action records share cycle_ms, xp_per_cycle,
  xp_bonus_uncapped/capped (percentages), proficiency_pct and taper_factor.
- Tests added: test_every_bonus_table_cell (30 cases, both tables),
  test_vision_groups_cap_floor_and_scope, test_cycle_minimum_and_drop_clamp,
  test_tier_up_resegments_time_and_xp, test_scope_and_cap_before_taper,
  test_profile_and_available_report_same_effective_values,
  test_retired_modifier_types_are_rejected (2 cases). Existing associativity,
  inert-upgrade, offline-cap and API timing tests retained and updated for D2.
- Final PATH=$PWD/.venv/bin:$PATH make ci passed on SQLite: auth 15, game
  175 passed / one PostgreSQL-only skip, client 23. Ruff, formatting, strict
  mypy, eslint, prettier, tsc, Vitest, build and scripts checks passed.
  git diff --check is clean; retired names occur only in rejection tests and
  historical/design documentation, not runtime content or code.
- SQLite db-reset rebuilt disposable /tmp databases successfully. No migration
  was needed; all new settings/state are content or derived values.

- Round 1: profile active modifiers now use modifier_groups, including estate
  presence; Skill.category reuses SkillCategory; modifier validation rejects
  mixed scopes and unscoped drop bonuses. Added test_proficiency_never_changes_xp,
  test_visitor_profile_excludes_estate_modifiers and
  test_modifier_rejects_invalid_scope (two cases).
- Round 1 final SQLite make ci passed: auth 15, game 179 passed / one
  PostgreSQL-only skip, client 23; all lint, formatting, type, build and scripts
  checks green. git diff --check passed. Committed by the orchestrator (a2b06c2, 9ee388a).
- Round 1 mutation check: temporarily applied group P to XP as well as speed;
  test_proficiency_never_changes_xp failed (1.2 != 1). Restored the engine.
- Orchestrator verification on a2b06c2: PostgreSQL 16 game-ci 176 passed,
  PostgreSQL db-reset green, alembic check clean. Round 1 PostgreSQL
  verification remains with the orchestrator.

## Removed

- Additive cross-source stacking, retired cycle-time modifier enum/content/client
  label, and market-tax modifier enum/client label (00 hand-off).
- Replaced additive-stacking test with multiplicative/inertness assertions;
  no tests deleted. Negative old time modifiers become positive speed modifiers.

## Design ambiguities resolved

- §7.2: min_cycle_ms has no prescribed default; chose the minimal placeholder
  of 1 ms in progression, retaining the old absolute lower bound as data.
- §8.1–8.2: category-keyed tables use five-element tuples indexed by distance
  0–4. Distance zero proficiency and categories with no below-tier proficiency
  use zero. Combat taper is stored under combat for later offensive use only.
- §7.3: reported XP bonuses are percentages before taper, named
  xp_bonus_uncapped and xp_bonus_capped; effective XP is xp_per_cycle.
- §7.1: realm_id is the current character column until 06 renames it. Pure
  state defaults both realm ids to the same empty value for existing callers;
  production adapters always supply the actual ids.

## Deviations

- PostgreSQL is unreachable from this sandbox, as specified by the orchestrator;
  PostgreSQL CI/reset verification must be performed externally. No locks or
  database schema were changed and no new concurrency path was introduced.

## Ratification needed

None.

## Hand-offs

- 04-content-lint: progression settings and bonus_total expose the engine math;
  exclude proficiency when computing the best external XP × speed stack.
- 05-tags: extend modifier_groups with active realm/estate tags; preserve group
  boundaries and inert/presence exclusions. Suspended upgrades have no current
  state representation; add exclusion when implementing their lifecycle.
- 06-resolver-presence: rename CharacterState.realm_id/adapter source to the
  current-realm column. Preserve estate_realm_id equality and segmentation.
- 26-equipment / 27-consumables-hp: populate gear_modifiers and
  consumable_modifiers from equipped/active sources; currently empty in adapters.
- 29-combat-resolver: taper_factor's combat row is offensive only; do not apply
  it to defensive XP. Proficiency table grants no combat cycle speed.
- 08-client-skills-travel: server reports all effective action figures; add UI
  presentation as needed. Content types include the new progression settings.
  Bonus percentages are raw floats (e.g. 45.199999999999996); format them for
  display in the client.

## New error codes

None. Invalid content continues to raise ContentError at boot.
