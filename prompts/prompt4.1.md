Prompt 4.1 — v0.5 migrations, content packs, and modifier/cap source resolution

Implement the structural layer of the v0.5 realm/estate model: schema, content, and engine source resolution. No new gameplay endpoints in this prompt — existing endpoints keep working on the new structures, and the one API change is caps exposure.

Content requirements (§6.3):

New Pydantic content schemas + loader integration for four packs:
map — undirected edges {realms: [id, id], cost: {gold: int, items: [{item_id, qty}], time_ms: int}}, plus positions (presentation-only, optional per realm). Referential integrity: edge realm ids must exist; no self-edges; no duplicate edges (unordered pair).
estate_forms — forms per §7.3 (id, name, specialty_tags, relocation_class, base_caps, modifiers, upkeep_profile, production_profile), transformations (from, to, cost), and relocation_classes ({cost_multiplier, time_multiplier} per class). Integrity: transformation endpoints and relocation classes must resolve; upkeep_profile/production_profile items must resolve but are otherwise validated-and-ignored in this phase.
development — nodes per §7.4 (id, archetype, name, tags, modifiers, cap_bonuses, upkeep_profile, projects) and edges (id, from, to, progress_target > 0, kind: "development"|"regression", transition_ms — required for development edges, forbidden or ignored for regression edges). Integrity: node/edge/project references resolve; every realm's starting node (see below) exists; the development-edge graph contains no self-loops.
projects — per §7.4 (id, name, targets: [{item_id, qty}], awards: [{edge_id, progress > 0}]). Integrity: items and edges resolve; a project may only award kind: "development" edges (regression edges fill exclusively from upkeep, §7.4 — enforce at load time).
Realm pack reshape: realms no longer carry tags, modifiers, or an inline project — identity lives on development nodes. A realm is now {id, name, starting_node_id, market_offers}. Update the realms schema accordingly and cross-check starting_node_id against the development pack.
Placeholder pack updates (scaffolding, obviously fake, minimal):
map.json: one edge between the two realms with small nonzero costs (e.g., 25 gold, no items, time_ms = 60000) so path math is exercised.
estate_forms.json: exactly the camp → homestead → orchard chain from §6.3, with the orchard's production_profile pointing at an existing placeholder tier-1 item; costs drawn from existing placeholder items.
development.json: per realm, a _t1 node (carrying that realm's previous tags/modifiers so action availability and effective rates are unchanged after migration) and a _t2 node with a small modifier delta; one development edge _t1 → _t2 (progress_target: 100, transition_ms: 5 minutes — short, for manual testing); one regression edge _t1 → _t0_stub node per realm (a bare node; never reachable in this phase).
projects.json: each realm's previous placeholder project, restructured to award its realm's development edge (100 progress on completion).
Served packs (§5.1): extend the content endpoints to serve map, estate_forms, development, and projects alongside the original five. This supersedes log #8's five-pack list — record in phase notes as a design-doc amendment. ETag/manifest machinery applies unchanged; manifest version must change with the new packs.

Migration requirements (§6.2) — one Alembic revision (or a small ordered set), with data backfill:

estates: rename character_id → owner_character_id (nullable), add form_id (backfill: form.homestead), status (default active), and relocation-pending columns relocating_to_realm_id NULL, relocation_completes_at NULL (used by 4.3; mirrors the realm-transition pattern — note in phase notes that these two columns extend the §6.2 schema and need a design-doc ratification entry). Replace the old one-estate uniqueness with a partial unique index on owner_character_id WHERE status = 'active' (SQLite and Postgres both support partial indexes; no dialect-specific SQL outside what Alembic/SQLAlchemy provide).
characters: add home_estate_id (backfill from each character's existing estate; enforce NOT NULL after backfill). realm_id remains, documented in the model as a cache (§7.5).
New tables: estate_ownership_history (backfill one row per existing estate: current owner, acquired_at = estate's original creation time if available, else migration time), realm_edge_progress, realm_projects.
realm_state: drop project_id, contribution_totals, tier; add node_id (backfill: the realm's starting_node_id), transition_to_node_id NULL, transition_completes_at NULL, treasury (integer, default 0, written by nothing in this phase), data JSON. realm_contributions: add project_id (backfill from the realm's previous single project id).
Character creation (POST /characters) updated: new characters get an estate with form_id = 'form.camp', an ownership-history row, and home_estate_id set — all in the creation transaction.

Engine requirements (§7, purity rules unchanged — no SQLAlchemy/FastAPI imports):

Extend CharacterState with estate_form_id and realm_node_id (replacing any realm-id-based modifier lookup). effective_cycle_time/effective_xp/effective_drops and resolve_caps now draw modifier/cap sources from: the realm's current development node (tags/modifiers/cap_bonuses), the estate form (modifiers/base_caps), and installed non-inert estate upgrades — additive within type per §7 (log #10 arithmetic unchanged). Action availability checks tags against the node's tags.
New pure helpers: path_cost(realm_a, realm_b, content) -> {gold, items, time_ms} (cheapest path over the map graph, summing each cost component along the path; document and test the tie-break: lowest gold, then lowest time) and relocation_cost(path_cost, form, content) applying the form's relocation-class multipliers (cost_multiplier scales gold and item quantities, time_multiplier scales time_ms; integer truncation).
resolve_caps incorporates estate-form base_caps and development-node cap_bonuses.

API requirement:

Resolved caps exposed (§7.1 gap): GET /characters/me gains a caps object — every cap type with {base, effective}. Client wiring lands in 4.4; this prompt only ships and tests the server field.

Tests:

Content: each new pack accepted; parameterized broken fixtures rejected (unknown realm in edge, duplicate unordered edge, project awarding a regression edge, missing transition_ms on a development edge, transformation to unknown form, realm with unknown starting_node_id); manifest changes when any new pack changes.
Migration: upgrade from the Phase-3 head against a fixture DB containing a player/character/estate/realm rows → all backfills correct (form, home_estate_id, ownership history, node_id, contributions' project_id); downgrade at least drops cleanly.
Engine: modifier resolution from node + form + upgrades matches hand-computed values, including inert-upgrade exclusion; a character in _t1 gets identical effective values to the pre-migration realm content (the "unchanged rates" guarantee in requirement 3); path_cost on the placeholder graph and on a synthetic 4-node graph with a cheaper indirect path; relocation_cost multiplier/truncation math; caps including form base caps and node bonuses.
API: profile response contains caps with correct effective values for a character with an upgrade granting a cap bonus.

Out of scope: any endpoint from §5.6, transitions, awards, relocation execution, treasury writes, anything reading upkeep_profile/production_profile.
