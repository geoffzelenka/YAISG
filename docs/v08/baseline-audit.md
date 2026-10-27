# v0.8 baseline alignment audit

Audited 2026-10-26 on `v08/00-preflight`, baseline commit
`697dd2d6005ff7c616617c3d014e18760a87d7da` (v0.5 Phases 0–4).
Scope: every labeled SHIPPED/CHANGE/NEW section and pack in design v0.8,
including the mixed-mark sections, consolidated model/API (§21–22), and §27
carry-forward decisions. NEW/OK means **absent as expected**, not implemented.
Paths below are repository-relative; a symbol or test identifies the evidence.
Grouped rows cover related clauses with the same implementation and owner.
Absorbing prompt means scheduled work that must address the finding; it does
not mean that work has already been implemented or that its prompt text has
been amended. The only runtime change fixes shipped GET /realms lock ordering, with a
PostgreSQL regression test. No content or design documents changed.

Build item 2: the orchestrator recorded `make ci` green on SQLite at 697dd2d:
auth 15, game 99, client 22 tests, approximately 67 seconds total. Its PostgreSQL
16 `TEST_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_test
make game-ci` passed 99 tests in approximately 15 seconds. A stale
`services/game/.mypy_cache` initially caused an INTERNAL ERROR in zipimport.pyi;
deleting that cache restored green. This was cache/environment trouble, not a
source fix. Local SQLite `make ci` passed all checks: auth 15 tests in 3.25s, game 99
in 6.56s (three SQLite datetime-adapter deprecation warnings), client 22 in
7.60s; Vite build 4.83s. Total wall time was not instrumented for that run.
Local PostgreSQL `make ci` attempted the same URL: auth 15 passed in 5.89s,
game 74 passed and 25 fixture setup errors in 18.54s, command wall time 27.826s;
client was not reached. psycopg reported “connection is bad: no error details
available”. A direct socket probe to 127.0.0.1:5432 produced PermissionError,
errno 1, Operation not permitted, confirming the sandbox cannot connect.
PostgreSQL green therefore relies on the orchestrator's recorded 99-test run
above, not an independent green run here. No database or source failure is
inferred from the blocked connection. Logs were kept in temporary files
`/tmp/yaisg-sqlite.log` and `/tmp/yaisg-postgres.log` (not committed).

Review round 1 verification: SQLite `make game-ci` passed Ruff/format/strict
mypy and pytest (99 passed, 1 PostgreSQL-only test skipped, 6.73s). The new
`test_get_realms_locks_in_id_order` still needs orchestrator execution on
PostgreSQL 16; the earlier green baseline does not verify this fix.

Severity: INFO is expected baseline or drift absorbable by named work;
FIX-HERE requires a small shipped-behavior regression fix now; BLOCKER means
a later prompt cannot absorb its false starting point. One FIX-HERE finding
(GET /realms lock ordering) is fixed with a PostgreSQL regression test. There
are no BLOCKER findings. Other transaction ordering drift remains assigned to
07-travel and 12-estate-ownership, with character locking carried into 06.

| §ref | mark | status (OK / DRIFT / MISSING / PARTIAL) | evidence | absorbing prompt | severity (INFO / FIX-HERE / BLOCKER) |
|---|---|---|---|---|---|
| §0 | INPUT | OK | `design/design.md` header: Version 0.8; `design/the-vision.md` exists and was read. | — | INFO |
| §3 | SHIPPED | OK | `services/{auth,game}/app/main.py:app`; independent `app/db.py`, `alembic.ini`, `migrations/env.py`; auth heads 0002, game 0006. | — | INFO |
| §3 | SHIPPED | OK | `services/auth/app/security.py:hash_password, SigningKeys.issue_access_token`; Argon2 and RS256; `app/config.py:ACCESS_TOKEN_SECONDS` = 900; `app/api.py:jwks`; game `app/auth.py:verify_access_token`. | — | INFO |
| §3, §27 | SHIPPED | OK | `services/auth/app/security.py:new_refresh_token, hash_refresh_token`; `app/api.py:refresh`; `tests/test_auth.py:test_refresh_rotates_stored_token`, `test_refresh_reuse_revokes_all_user_tokens`, `test_concurrent_refresh_only_rotates_once`. | — | INFO |
| §3 | SHIPPED | OK | `services/{auth,game}/app/db.py` SQLAlchemy; `.github/workflows/ci.yml:python` matrix auth/sqlite, game/sqlite, game/postgres, image postgres:16. | — | INFO |
| §3 | SHIPPED | OK | `client/package.json` React 18, Vite, TypeScript, TanStack Query, Zustand, Tailwind; `client/src/api/http.ts` REST; no WebSocket implementation. | — | INFO |
| §3, §23.2 | SHIPPED / NEW | DRIFT | `services/game/app/main.py` has no scheduler lifecycle; `services/game/pyproject.toml` has no APScheduler dependency. §3 labels a future job shipped; §23.2 explicitly makes it new. | 14-realm-tick | INFO |
| §3 | SHIPPED | OK | `Makefile:ci, auth-ci, game-ci, client-ci`; `.github/workflows/ci.yml` invokes those same targets. | — | INFO |
| §3 | SHIPPED | OK | `services/game/app/engine/core.py:resolve` accepts state/content/now/rng; `engine/levels.py` pure math; DB, CSPRNG and clocks remain in adapters. | — | INFO |
| §3 | SHIPPED | OK | `services/{auth,game}/app/errors.py:api_error`; `main.py:http_exception_handler, validation_exception_handler`; `logging.py:log_request` envelopes unhandled exceptions. | — | INFO |
| §4.1 | SHIPPED | OK | `services/game/app/content/schemas.py:ContentModel` uses frozen=True and extra="forbid"; tuple records reject unknown fields. Frozen is shallow (nested dictionaries remain mutable). | — | INFO |
| §4.1 | SHIPPED | DRIFT | `services/game/app/content/schemas.py:ContentModel.model_config` does not set strict=True; Pydantic default coercion remains. If “strict” means no coercion, baseline does not meet it; pack-schema work must make the interpretation explicit. | 02-content-model | INFO |
| §4.1 | SHIPPED | OK | `services/game/app/content/loader.py:_validate, _unique, _require_items` validates cross-pack references; `tests/test_content.py` invalid-content cases. | — | INFO |
| §4.1 | SHIPPED | OK | `services/game/app/content/loader.py:_canonical_bytes, load_content` sorted compact JSON and SHA-256; overall version includes XP; `tests/test_content.py:test_manifest_version_changes_with_content`. | — | INFO |
| §4.1, §27 | SHIPPED | OK | `services/game/app/api/content.py:get_manifest, get_pack, PUBLIC_CONTENT_PATHS`; quoted strong ETags and 304; `main.py:require_authentication` exempts exact public paths; `tests/test_content.py:test_pack_etag_and_not_modified_response, test_only_known_content_routes_are_public`. | — | INFO |
| §6.4 | SHIPPED | OK | `services/game/app/engine/core.py:resolve`; `tests/test_engine.py:test_exact_and_partial_cycle_timestamp_math, test_repeated_resolve_equals_one_large_resolve`. Whole cycles only; last_resolved_at advances by consumed milliseconds. | — | INFO |
| §6.4, §27 | SHIPPED | OK | `services/game/app/engine/core.py:resolve` refreshes effective values when level changes; `tests/test_engine.py:test_level_up_changes_subsequent_cycle_resolution`. It loops per cycle; “closed-form batch” in §6.3 overstates the implementation, see separate row. | — | INFO |
| §6.3 | SHIPPED | DRIFT | `services/game/app/engine/core.py:resolve` has a per-cycle while loop rather than closed-form reward batching. Preserve semantics when introducing resolver dispatch; no performance rewrite here. | 06-resolver-presence | INFO |
| §6.4, §27 | SHIPPED | OK | `tests/test_engine.py:test_offline_cap_resolves_only_budgeted_cycles, test_exact_offline_budget_advances_by_resolved_cycles, test_offline_cap_does_not_end_action_when_no_cycle_fits`; `core.py:resolve`. | — | INFO |
| §6.4, §27 | SHIPPED | OK | `core.py:StopReason, resolve` in `services/game/app/engine/`; `tests/test_engine.py:test_overflow_precedes_input_exhaustion_in_same_cycle, test_action_ends_when_final_recipe_is_consumed`. | — | INFO |
| §6.4 | SHIPPED | MISSING | `services/game/app/engine/core.py:StopReason` has only inputs_exhausted, offline_cap, inventory_full; `resolve` never revalidates realm requirements. Requirements-lost stopping is future availability work. | 05-tags | INFO |
| §6.4 | SHIPPED | OK | `services/game/app/services/actions.py:resolve_character` constructs random.Random(secrets.randbits(256)) per productive resolve; RNG never seeded inside engine. | — | INFO |
| §6.4, §27 | SHIPPED | OK | `services/game/tests/test_engine.py:test_clock_regression_is_a_no_op`; `engine/core.py:resolve` returns untouched state/action on backwards time. | — | INFO |
| §6.4, §27 | SHIPPED | OK | `services/game/app/services/actions.py:claim_rewards` locks and stamps claimed_at; `api/actions.py` builds response before commit; `tests/test_actions.py:test_offline_cap_rewards_once_and_stops, test_profile_resolution_remains_in_reward_feed`. | — | INFO |
| §6.4 | SHIPPED | OK | `services/game/app/models/character.py:ActiveActionRecord` character primary key; `api/actions.py` start/stop; `tests/test_actions.py:test_switching_mid_cycle_resolves_old_action_without_rewards`. | — | INFO |
| §7.4 | SHIPPED | OK | `services/game/app/engine/core.py:_active_modifiers, resolve_caps` derives inertness from upgrade.realm_tags each call, no persisted inert flag; `api/estates.py:_upgrade_inert_reason`; `tests/test_engine.py:test_modifiers_stack_additively_and_inert_upgrade_is_excluded, test_caps_include_active_upgrades_and_ignore_inert_ones`. Field is realm_tags, not yet requires_realm_tags. | — | INFO |
| §9.1 | SHIPPED | OK | `services/game/app/models/character.py:Inventory` primary key (character_id,item_id), positive quantity; `engine/core.py:resolve` enforces distinct-item slots and stack limits, deletes empty stacks; `tests/test_engine.py:test_stack_limit_overflow_is_discarded, test_consuming_input_frees_a_slot_before_drops`. No bank/estate storage tables. | — | INFO |
| §13.1 | SHIPPED | OK | `services/game/app/models/character.py:Estate, EstateOwnershipHistory, Character` nullable owner_character_id, stable estate id, home_estate_id without unique owner constraint; migration `0006_realm_estate_v05.py`; history currently character_id/acquired_at/relinquished_at (not new from_at/to_at names). | — | INFO |
| §13.3 | SHIPPED | OK | `services/game/app/api/estates.py:purchase_upgrade` implements UNKNOWN_UPGRADE, NO_FREE_SLOT, ALREADY_INSTALLED, MISSING_INPUTS; `tests/test_estates.py:test_upgrade_errors`. | — | INFO |
| §13.3 | SHIPPED | OK | `services/game/app/api/estates.py:transform_estate` implements INVALID_TRANSFORMATION, MISSING_INPUTS, ESTATE_BUSY, WOULD_ORPHAN_UPGRADES, excluding installed bonuses for destination cap; `tests/test_estates.py:test_transform_errors_and_shrinking_slots, test_transform_rejects_busy_estate_before_charging`. Costs currently transformation-edge items (future build_cost belongs to 11). | — | INFO |
| §13.3 | SHIPPED | OK | `services/game/app/api/estates.py:_home_estate(lock=True), purchase_upgrade`; `tests/test_estates.py:test_last_slot_concurrency_installs_exactly_once` uses two sessions on PostgreSQL; SQLite branch checks final outcome, not real handler contention. | — | INFO |
| §21, §23.1 | SHIPPED | OK | `services/game/app/db.py:configure_sqlite_engine` emits BEGIN IMMEDIATE for sqlite_write_intent; `services/actions.py:_lock_active_action`, `services/realms.py:prepare_sqlite_write` acquire writer intent before loading; PostgreSQL uses with_for_update(). | — | INFO |
| §23.1 | SHIPPED | DRIFT | `services/game/app/services/actions.py:_lock_active_action` locks active action if present, character only when absent; `resolve_character` calls finalize_relocation (estate lock) before finalize_realms (realm locks). Target character→realm→estate ordering is not universal. 07 removes finalize_relocation; 12 Build 7 establishes character→realm→estate ordering. | 07-travel; 12-estate-ownership | INFO |
| §21, §23.1 | SHIPPED | DRIFT | FIXED: GET /realms previously locked in content order, opposite to sorted multi-realm mutations (reviewer reproduced a PostgreSQL AB-BA deadlock). `services/game/app/api/realms.py:get_realms` now calls `services/realms.py:finalize_realms` before building responses in content order; `services/game/tests/test_estates.py:test_get_realms_locks_in_id_order` proves the higher-id row remains available while the request waits on the lower-id row. PostgreSQL test execution pending orchestrator verification. | 00-preflight | FIX-HERE |
| §23.4 | SHIPPED | OK | `services/game/tests/test_engine.py:test_repeated_resolve_equals_one_large_resolve, test_recipe_input_conservation` use Hypothesis; `test_seeded_drop_frequency_is_close_to_declared_chance` uses seeded RNG. | — | INFO |
| §23.4 | SHIPPED | OK | `services/game/tests/test_actions.py:test_concurrent_resolves_contend_and_do_not_double_reward` thread events verify blocking and one reward; `test_estates.py:test_last_slot_concurrency_installs_exactly_once`; both fixtures honor TEST_DATABASE_URL. | — | INFO |
| §23.5 | SHIPPED | OK | `services/game/app/main.py:require_authentication`, `app/auth.py:verify_access_token`; auth `app/rate_limit.py:IpRateLimiter` and `tests/test_rate_limit.py`; boundary Pydantic schemas and route validation. Game mutation rate limits absent as intended until 36. | — | INFO |
| §23.6 | SHIPPED | OK | `services/{auth,game}/app/logging.py:log_request` JSON with request_id/method/path/status/duration, response X-Request-Id; `tests/test_health.py:test_exception_is_logged_with_request_id` in each service. | — | INFO |
| §24 | SHIPPED | OK | `client/src/App.tsx` sidebar and skills/profile/estate/realm/map routes; `features/actions/ActionExperience.tsx` global action strip, WelcomeBack, reward toasts; `features/profile/InventoryPanel.tsx` grid. | — | INFO |
| §24 | SHIPPED | OK | `client/src/features/actions/actionStore.ts` shared 250ms interval and nextPollDelay with ±10% jitter; `actionStore.test.ts` fake timers/boundary tests; `ActionExperience.test.tsx` welcome summary and reward display. | — | INFO |
| §4.2 | CHANGE | OK | `services/game/app/content/loader.py:PUBLIC_PACKS`: skills, items, realms, upgrades, caps, map, estate_forms, development, projects. xp_curve private and versioned. Exactly nine served packs. | — | INFO |
| §5.1, §2.1 R1 | CHANGE | OK | `content/generate_xp_curve.py:build_curve` sums floor(100*1.12**(level-2)) per step into cumulative thresholds; `content/xp_curve.json` levels 1–99; `engine/levels.py:level_for_xp`; XP SQL Integer, not BigInteger. | 01-foundation | INFO |
| §6.1 | CHANGE | OK | `content/skills.json` gathering/refining/crafting and empty combat-monsters; `schemas.py:Skill` has no category. Categories are not yet modeled. | 02-content-model | INFO |
| §6.2, §4.2 items | CHANGE | OK | `schemas.py:Action` level_required, cycle_ms, item-id inputs, xp, drops, realm_tags; `Item` id/name/stack_limit/tags only; no selectors, tiers or reference prices. | 02-content-model | INFO |
| §6.3 | CHANGE | OK | `services/game/app/engine/core.py:CycleRewardStrategy, StandardCycleRewards, resolve(reward_strategy=...)`; no resolver dispatch by category. | 06-resolver-presence | INFO |
| §7.1–7.2 | CHANGE | OK | `services/game/app/engine/core.py:_modifier_total, effective_cycle_time, effective_xp, effective_drops` additive across node/form/upgrades; cycle time base*(1+pct/100), minimum 1ms; ModifierType.CYCLE_TIME_PCT. | 03-bonus-model | INFO |
| §7, §27 | CHANGE | DRIFT | `services/game/app/content/schemas.py:ModifierType.MARKET_TAX_PCT`, `client/src/api/content.tsx:Modifier`, `client/src/App.tsx:describeModifier` retain retired market_tax_pct; no active engine tax behavior. | 03-bonus-model | INFO |
| §7.5 | CHANGE | OK | `schemas.py:CapsConfig, CapType`; `content/caps.json` market_listings; `engine/core.py:Caps, resolve_caps`; no order-slot model. | 02-content-model | INFO |
| §11.1 | CHANGE | OK | `schemas.py:MapEdge, MapCost` undirected pair plus gold/items/time_ms; `engine/core.py:path_cost` chooses gold then time; no terrain/supply/Travel gates. | 07-travel | INFO |
| §11.2 | CHANGE | OK | `services/game/app/models/character.py:Character.realm_id` residence cache synchronized from home estate; no current_realm_id or independent presence. | 06-resolver-presence | INFO |
| §12.1–12.2 | CHANGE | OK | `schemas.py:DevelopmentNode, DevelopmentEdge`; `models/character.py:RealmState, RealmEdgeProgress` table realm_edge_progress (not realm_edges); node archetype/tags/modifiers/caps; edges progress_target/kind/transition_ms. | 09-development-graph | INFO |
| §12.3 | CHANGE | OK | `models/character.py:RealmProject` realm_projects with totals/status; `schemas.py:Project` targets/edge awards; `api/realms.py:contribute` from anywhere, clamps contributions; no kickoff/build/erosion or project tiers in shipped schema. | 09-development-graph; 10-project-runs | INFO |
| §12.6 | CHANGE | OK | `services/game/app/services/realms.py:award_edge_progress, finalize_realm, finalize_realms` awards start transitions; finalization resets departed-node edges and closes unavailable projects; `tests/test_realms.py` exercises both. | 09-development-graph | INFO |
| §13.1–13.2 | CHANGE | OK | `models/character.py:Estate` has relocating_to_realm_id, relocation_completes_at, level, upgrade_slots; `schemas.py:EstateForm` relocation_class/base_caps and dormant upkeep_profile/production_profile; `EstateFormsPack` edge transformations. | 11-estate-forms | INFO |
| §4.2 realms, §15 | CHANGE | OK | `schemas.py:Realm.market_offers, MarketOffer` fixed buy/sell prices; `content/realms.json` offers only, no executing market routes. Remove field as templates are remodeled. | 09-development-graph | INFO |
| §18, §2.1 R12 | CHANGE | OK | `services/game/app/config.py:STARTING_GOLD` environment default 100; `api/characters.py:create_character` grants Currency gold; no mint. | 01-foundation | INFO |
| §20 | CHANGE | OK | `services/game/app/api/characters.py:CreateCharacterRequest, create_character` POST /characters accepts name and realm_id; `client/src/App.tsx:CharacterCreation` realm picker. Normal registered auth only. | 34-tutorial | INFO |
| §11, §27 | CHANGE | OK | `services/game/app/api/realms.py:relocate, preview_relocation` POST /characters/me/relocate and GET preview; `engine/core.py:path_cost, relocation_cost`; instant/delayed gold+item charge; `services/realms.py:finalize_relocation` arrival. | 07-travel | INFO |
| §4.3 | NEW | OK | Selectors and class payment absent as expected: `services/game/app/content/schemas.py:ItemQuantity only names item_id`. | 02-content-model | INFO |
| §5.2 | NEW | OK | Rate targets and content lint absent as expected: `Makefile has only ci/auth-ci/game-ci/client-ci`. | 04-content-lint | INFO |
| §5.3 | NEW | OK | Tiers and progression pack absent as expected: `services/game/app/content/schemas.py:Skill, Action, Item lack tier; loader.py:PUBLIC_PACKS lacks progression`. | 01-foundation | INFO |
| §7.3 | NEW | OK | Combined XP cap absent as expected: `services/game/app/engine/core.py:effective_xp uses uncapped additive percent`. | 03-bonus-model | INFO |
| §7.4 | NEW | OK | Tag definitions, emissions and availability report absent as expected: `services/game/app/schemas.py has string realm_tags only; no TagsPack; api/actions.py uses can_start`. | 05-tags | INFO |
| §8.1–8.3 | NEW | OK | Proficiency, XP taper and Travel/Exploration benefits absent as expected: `services/game/app/engine/core.py:effective_cycle_time, effective_xp have no tier tables; loader.py lacks progression`. | 03-bonus-model | INFO |
| §9.2 | NEW | OK | Equipment absent as expected: `services/game/app/models/character.py:Inventory only commodity rows; main.py has no equipment router`. | 26-equipment | INFO |
| §9.3–9.4 | NEW | OK | Consumables, belts, buffs and HP absent as expected: `services/game/app/models/character.py:Character has no HP or equipment; schemas.py:Item lacks consumable/equip`. | 27-consumables-hp | INFO |
| §11.3–11.4 | NEW | OK | Journeys and Travel resolver absent as expected: `services/game/app/models/character.py:ActiveActionRecord contains only action id/timestamps/meta; engine/core.py only uniform resolve and relocation_cost`. | 07-travel | INFO |
| §12.4 | NEW | OK | Tag stack and credits absent as expected: `services/game/app/models/character.py:RealmContribution records items, no acquired-tag stack model`. | 09-development-graph | INFO |
| §12.5 | NEW | OK | Realm votes absent as expected: `services/game/app/models/character.py:RealmState only pending transition; main.py has no vote router`. | 19-votes | INFO |
| §13.4 | NEW | OK | Estate build/buy/surrender and realm-owned estate flows absent as expected: `services/game/app/api/estates.py only GET me, upgrade, transform; nullable owner is shipped scaffolding, no realm ownership endpoints`. | 12-estate-ownership | INFO |
| §13.6 | NEW | OK | Active estate production, upkeep and larder absent as expected: `services/game/app/content/schemas.py:EstateForm dormant profiles; engine/core.py never reads them; models/character.py no larder`. | 14-realm-tick | INFO |
| §13.7 | NEW | OK | Estate gauge/decay absent as expected: `services/game/app/models/character.py:Estate lacks gauge/decay_stage/shed_progress`. | 15-decay | INFO |
| §14.1–14.4 | NEW | OK | Stores, demand lines and project overlay absent as expected: `services/game/app/models/character.py:RealmState has treasury/data only, no stores/demand-line models`. | 13-stores-lines | INFO |
| §14.5 | NEW | OK | Realm tick absent as expected: `services/realms.py has only development and relocation finalizers; main.py no job`. | 14-realm-tick | INFO |
| §14.6–14.7 | NEW | OK | Realm gauges, stages, shedding and regression absent as expected: `services/game/app/models/character.py:RealmState has no deficit/decay fields; services/realms.py no shed implementation`. | 15-decay | INFO |
| §14.8, §18 | NEW | OK | Mint, gold ledger and economy operator report absent as expected: `services/game/app/models/character.py:Currency and RealmState treasury only, no gold ledger; main.py no admin router`. | 18-mint-gold | INFO |
| §14.9 | NEW | OK | World seed absent as expected: `services/game/app/content/loader.py:load_content only nine public packs plus xp_curve; no world_seed schema/file`. | 13-stores-lines | INFO |
| §15.1–15.5 | NEW | OK | Realm market curve, budgets and health visibility absent as expected: `services/game/app/content/schemas.py:MarketOffer fixed prices; api/realms.py:RealmResponse has no quotes, stores or treasury bands`. | 16-realm-pricing | INFO |
| §15.6 | NEW | OK | Realm trades and treasury gifts absent as expected: `services/game/app/api/realms.py route decorators expose reads/contribute/relocate only`. | 17-realm-trade | INFO |
| §16 | NEW | OK | Caravans, remoteness, shipments absent as expected: `services/game/app/engine/core.py:path_cost computes relocation path only; models/character.py no shipment model`. | 20-caravans | INFO |
| §17 | NEW | OK | Global order book, slots, tax, expiry and purge absent as expected: `services/game/app/models/character.py has no market order/escrow model; main.py no market router; caps market_listings is unused capacity scaffolding`. | 23-global-market; 24-market-lifecycle | INFO |
| §19.1–19.4 | NEW | OK | Instanced keys, exploration and invalidation absent as expected: `services/game/app/content/schemas.py:Item stackable only; models/character.py no instances; loader.py no exploration pack`. | 31-keys | INFO |
| §19.5 | NEW | OK | Key market absent as expected: `services/game/app/main.py router registry has no keys or market; models/character.py no listings`. | 32-key-market | INFO |
| §20.1 | NEW | OK | Guest auth and purge absent as expected: `services/auth/app/models.py:User, RefreshToken normal accounts; app/api.py register/login/refresh/logout/JWKS only`. | 33-guest-auth | INFO |
| §20.2–20.3 | NEW | OK | Tutorial instances, hints and departure absent as expected: `services/game/app/models/character.py:RealmState uses content realm id; main.py no tutorial route; loader.py no tutorial pack`. | 34-tutorial | INFO |
| §23.2 | NEW | OK | Scheduled driver/advisory lock absent as expected: `services/game/app/main.py has no startup scheduler; pyproject.toml no scheduler dependency`. | 14-realm-tick | INFO |
| §23.6 extended | NEW | OK | Economy/game counters absent as expected: `services/game/app/logging.py:log_request only request timing/status, no metrics backend`. | 36-hardening | INFO |
| §24 extended | NEW | OK | New client panels absent as expected: `client/src/App.tsx route registry has shipped skills/profile/estate/realm/map only; no market/equipment/combat/keys/tutorial panels`. | 08-client-skills-travel; 21-client-realm-estate; 22-client-realm-market; 25-client-global-market; 30-client-equipment-combat; 35-client-keys-tutorial | INFO |
| §10, §6.3 combat | NEW | PARTIAL | `content/skills.json` empty combat-monsters skill; `services/game/tests/test_actions.py:test_available_actions_reflect_realm_level_and_combat_placeholder`; `engine/core.py:CycleRewardStrategy` future-combat seam. No combatants, stats, hit/stance logic, pools or combat resolver. 02 removes the placeholder skill; 06 removes CycleRewardStrategy; 28/29 build the combat model/resolver. | 02-content-model; 06-resolver-presence; 28-combat-model; 29-combat-resolver | INFO |
| §4.2 tags | NEW | OK | `services/game/app/content/loader.py:PUBLIC_PACKS, load_content` and `content/` contain no tags pack; owning prompt creates it (world_seed remains private). | 05-tags | INFO |
| §4.2 combatants | NEW | OK | `services/game/app/content/loader.py:PUBLIC_PACKS, load_content` and `content/` contain no combatants pack; owning prompt creates it (world_seed remains private). | 28-combat-model | INFO |
| §4.2 exploration | NEW | OK | `services/game/app/content/loader.py:PUBLIC_PACKS, load_content` and `content/` contain no exploration pack; owning prompt creates it (world_seed remains private). | 31-keys | INFO |
| §4.2 economy | NEW | OK | `services/game/app/content/loader.py:PUBLIC_PACKS, load_content` and `content/` contain no economy pack; owning prompt creates it (world_seed remains private). | 01-foundation | INFO |
| §4.2 progression | NEW | OK | `services/game/app/content/loader.py:PUBLIC_PACKS, load_content` and `content/` contain no progression pack; owning prompt creates it (world_seed remains private). | 01-foundation | INFO |
| §4.2 tutorial | NEW | OK | `services/game/app/content/loader.py:PUBLIC_PACKS, load_content` and `content/` contain no tutorial pack; owning prompt creates it (world_seed remains private). | 34-tutorial | INFO |
| §4.2 world_seed | NEW | OK | `services/game/app/content/loader.py:PUBLIC_PACKS, load_content` and `content/` contain no world_seed pack; owning prompt creates it (world_seed remains private). | 13-stores-lines | INFO |
| Build 2 | CHECK | OK | `Makefile:ci`; local SQLite exit 0 at baseline 697dd2d: 15 auth, 99 game, 22 client; Ruff/format/mypy/eslint/prettier/tsc/Vitest/build passed. Timings above. | 00-preflight | INFO |
| Build 2 | CHECK | OK | Local PostgreSQL make ci could not connect: 25 fixture setup errors; direct socket probe PermissionError errno 1. Orchestrator PostgreSQL 16 game-ci green: 99 tests, ~15s at 697dd2d. Environment limitation, not design drift or a code regression; recorded baseline evidence accepted under the task environment notes. | 00-preflight | INFO |
| §22 actions | CHANGE | OK | `services/game/app/api/actions.py` exposes GET /characters/me/actions/available, POST /characters/me/action, GET /characters/me/action, DELETE /characters/me/action; consolidated v0.8 /actions/start,poll,stop paths are future work. | 06-resolver-presence | INFO |
| §22 profile/map/realms | CHANGE | OK | `services/game/app/api/characters.py:ProfileResponse` old skills/estate/caps; `api/realms.py:get_map, RealmResponse` old topology and development progress, without v0.8 gauge, stores, active run or vote. | 08-client-skills-travel; 21-client-realm-estate; 22-client-realm-market | INFO |
| §22 realm detail additions | NEW | OK | `services/game/app/api/realms.py` has no /realms/{id}/estates or /realms/{id}/tags/{tag_id} routes; holdings/tag-detail APIs absent as expected. | 09-development-graph; 12-estate-ownership | INFO |
| §22 stance | NEW | OK | `services/game/app/api/characters.py` has no PUT /characters/me/stance; Character model no stance field, absent as expected. | 28-combat-model | INFO |
