## Built

- Reshaped realm state into world/template instances with isolation, ownership,
  node, treasury, JSON transition, tick timestamp, gauge/decay/shedding, vote
  cooldown and treasury band fields. World creation sets id = template_id and
  initializes last_tick_at from the injected clock. Added destructive migration
  v08_0004_graph, with downgrade restoring the prior disposable schema.
- Strict realms, development and projects packs now use §12 shapes: selector
  upkeep/costs, node-owned tier_up/morph upgrades, regression, carried tags,
  kickoff eligibility/payment, tag grants and nonrepeatability. Cross-validation
  checks project/tag/selector references, satisfiable upgrade required_tags,
  destinations, exactly one barren root and every regression path reaching it.
- Minimal placeholder graph retains the tested barren identity, two tier-one
  types and one tier-two node, with tier_up/morph edges and regression paths.
  economy.transition.duration_days is authored as 7.
- realm_tags records acquisition order, D4 node stamp, timestamp and the future
  project-run link. push_realm_tag requires the caller's realm lock and advances
  a persistent sequence counter; deleting tags never reuses their sequence.
- start_transition records target, cause and exact content-defined completion
  time. Lazy finalization filters by destination-offered project tags and carried
  tags; upgrades preserve surviving stamps, regressions restamp and reset decay
  state. Locks refresh persisted realm snapshots and are acquired in sorted order.
- GET /realms and detail expose node/type/tier, acquired tags with seq/node_id,
  active tags through Prompt 05's active_tags, gauge, decay stage and pending
  transition. Raw treasury is absent. Template- and instance-isolated realms and
  their map edges are excluded from realm lists and the map.
- Picked up 00/04/05/07 hand-offs: stacks feed character state, journey arrival
  snapshots, estate annotations while owners visit elsewhere and content lint.
  Character resolution includes the estate's home realm before estate locks,
  so its due transition is finalized even while its owner is absent. Lint checks
  subsets of offered/carried stacks, including partial stacks that avoid maluses.
- Updated client content/API types, realm/profile identity and transition target
  consumption; retained the transition countdown and map/journey presentation.
- Added tests: test_graph_rejects_invalid_paths_and_requirements (unsatisfiable
  tags, regression cycle, two roots),
  test_finalize_exact_boundary_idempotent_stamps_and_filters (both causes),
  test_tag_sequence_never_reused,
  test_postgres_concurrent_finalizers_wait_for_realm_lock,
  test_transition_uses_content_duration_and_rejects_replacement,
  test_transition_finalization_is_idempotent (Hypothesis),
  test_isolated_realms_absent_from_lists_and_map (template/instance),
  test_realm_tag_stack_public_and_action_state,
  test_absent_owner_estate_uses_stored_realm_stack (Fed, Faltering, due regression),
  test_stack_bound_includes_project_and_carried_tags, and
  test_arrival_uses_destination_project_stack. Database fixtures select
  TEST_DATABASE_URL; the PostgreSQL contention test skips on SQLite.
- Disposable SQLite make db-reset, subsequent upgrade to head and alembic check
  succeeded. Existing migration tests retain full downgrade/rebuild coverage.
- Full SQLite PATH=$PWD/.venv/bin:$PATH make ci passes: auth 15, game 266
  with five database-specific skips, client 41; formatting, lint, strict mypy,
  TypeScript, Vitest, build, scripts and warning-only content lint are green.
  git diff --check is clean. No dependencies added.

- Round 1: refreshed codebase-map realm routes, instance/tag models and explicit
  transition clock APIs; documented the realm_contributions removal deviation
  and Prompt 10's recreation with run ids; added tutorial isolation, decay
  fixture and shared-tag-helper hand-offs. Added
  test_upgrade_requirement_satisfied_only_by_carried_tag; an in-process mutation
  removing carried_tags from validation makes this test fail as required.
  Full SQLite make ci passes: auth 15, game 267 with five database-specific
  skips, client 41; formatting, lint, type checks and builds are green.

## Removed

- RealmEdgeProgress/realm_edge_progress, RealmProject/realm_projects and the old
  contribution model/table/endpoint, edge awards, award_edge_progress, flat
  development edges and progress payloads, old project targets/awards,
  market_offers/MarketOffer, and client contribution form/hook/progress displays.
  No project-tier field existed in the baseline; the new strict schema has none.
- Removed tests of explicitly retired behavior:
  test_award_starts_transition_and_rejects_more_awards,
  test_regression_and_non_outgoing_awards_are_rejected,
  test_finalize_transition_resets_siblings_and_closes_projects,
  test_contribution_clamps_consumes_and_completes_with_one_award,
  test_contribution_rejects_pending_transition_without_consuming,
  content rejection cases for regression edge awards/missing transition_ms,
  and Vitest “clamps a contribution to held quantity and remaining target”.
  New graph/transition tests replace the retired development assertions.
- Removed two unused placeholder nodes; kept all identities used by unrelated
  engine, tag and action tests. Unrelated tests retain their behavior assertions.

## Design ambiguities resolved

- §12.2: barren is represented at tier 0 with no upkeep; developed node tiers
  remain 1–5. Retained node name for existing presentation alongside realm_type.
- §12.4: increasing seq survives deletion, so realm_state.tag_seq persists the
  high-water mark; a unique realm/seq constraint rejects duplicate ordering.
- §12.4 / §12.6: destination “offered” means tags granted by its listed projects,
  not inherent tags. Inherent tags come from the new node independently of the
  acquired stack. Public node.tags holds inherent ids, tags holds stack metadata,
  and active_tags holds the combined stage-filtered ids.
- §12.6: regression's zero gauge is represented as Fed immediately, consistent
  with §14.6's definition. Upgrade/morph causes preserve gauge and shedding.
- §5.2 / §12.2: lint considers every subset of possible offered/carried tags;
  prerequisite/build history is conservatively relaxed, like its existing
  installation-history relaxation, to retain an upper bound.

## Deviations

- §12.3 / §14.7: dropped realm_contributions along with the retired contribution
  endpoint, although the design retains contribution logs and the prompt's
  Remove list does not include this table. The old schema ties contributions
  to project definitions rather than attempts; Prompt 10 recreates the table
  with a run id for the new project-run lifecycle. Development data is disposable.

## Ratification needed

None.

## Hand-offs

- 10-project-runs: implement kickoff/contribution/build runs using the new Project
  schema. Call push_realm_tag under the locked realm and pass project_run_id;
  add its FK when realm_project_runs exists (the column is nullable scaffolding
  here). Recreate contribution logs with run ids and tag credits/detail once
  kickoff and contributor identities exist. Old project totals/logs are removed.
- 10-project-runs: integrate finalize_realm into resolve_realm; retain sorted
  realm locks, exact completion boundary and caller transaction ownership.
- 13-stores-lines / 14-realm-tick / 15-decay: consume upkeep and overrides; tick
  timestamps/gauges/shed_progress are persisted scaffolding. Decay starts a
  regression transition; it must not restamp tags before finalization.
- 16-realm-pricing: populate treasury_band; it remains nullable scaffolding.
- 19-votes: call start_transition with cause upgrade after a successful vote;
  eligibility/payment and selecting an authored edge remain vote responsibilities.
- 21-client-realm-estate: build project-run controls against Prompt 10's API.
  Legacy contribution controls are removed; full realm/estate UI remains yours.
- 31-keys: deprecate keys when start_transition runs, invalidate at finalization,
  and stop key actions; no key system exists yet. Ordinary action loss continues
  through the shared requirement check on the next character resolve.
- 34-tutorial: create isolated owned instances from templates; list/map filtering
  is ready. Per-player instance lifecycle and tutorial-specific travel remain yours.

- 34-tutorial: isolated templates can still be chosen in character creation
  (api/characters.py) and as travel destinations (api/travel.py), and the client
  picker does not filter them. Reject or filter these choices when isolated
  instances exist.
- 15-decay: the barren root node.verdant_t0_stub has the project-granted tag
  bonus.fake as an inherent tag. Decay and regression tests should use an
  inherent tag that no project grants.
- 36-hardening: public active_tags in api/realms.py and the engine's
  realm_active_tags assemble tag lists separately. Consolidate them into one
  pure helper.

## New error codes

None. UNKNOWN_REALM is retained. Internal transition misuse/duplicate tag pushes
raise contextual ValueError; content failures continue using ContentError.
