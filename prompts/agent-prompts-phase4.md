# Coding Agent Prompts — Phase 4

Companion to `design.md` (**v0.5** — do not run these against v0.4 or earlier; the realm/estate model changed). Run prompts **in order**; each assumes all previous prompts (including Phases 0–3) are complete and their acceptance criteria pass. Every prompt should be given to the agent along with the full v0.5 design doc as attached context.

**Conventions (unchanged from the Phase 0–3 prompt file):**
- "Design doc" = `design.md` v0.5. Section references (§) point into it.
- Definition of done for *every* prompt: code compiles/lints clean (ruff + mypy for Python, tsc + eslint for TS), all new and existing tests pass **on both CI database engines**, `docker-compose up` yields a working stack, and a short `docs/phase-notes/<prompt-id>.md` summarizes what was built and any deviations.
- The agent must not build anything listed in §10 (non-goals). In Phase 4 this especially means: **no upkeep, decay, solvency, production, regression traversal, transfer/escheat, or inter-realm balancing mechanics** — several schemas and content fields for these exist and must be created, but nothing reads them except validation.
- The agent must not invent game content beyond the placeholder pack changes each prompt specifies.

**Phase-4-wide notes:**
- The flat-tier realm model from earlier phases is **superseded** (§7.4, log #15). Migrate, don't parallel-build: the old `realm_state.tier`/`project_id`/`contribution_totals` columns and any tier-based content go away in 4.1.
- Prompt 3.1's "engine is frozen" rule is relaxed for this phase in one specific way: the engine's *modifier/cap source resolution* is extended per §7 (development node + estate form as sources). Resolution math, the resolve loop, and all existing engine tests must not change behavior; every engine edit must keep the existing suite green untouched (except where a test hardcodes the old source model — those may be updated, listed in phase notes).

---

## Prompt 4.1 — v0.5 migrations, content packs, and modifier/cap source resolution

Implement the structural layer of the v0.5 realm/estate model: schema, content, and engine source resolution. **No new gameplay endpoints in this prompt** — existing endpoints keep working on the new structures, and the one API change is caps exposure.

**Content requirements (§6.3):**

1. New Pydantic content schemas + loader integration for four packs:
   - `map` — undirected edges `{realms: [id, id], cost: {gold: int, items: [{item_id, qty}], time_ms: int}}`, plus `positions` (presentation-only, optional per realm). Referential integrity: edge realm ids must exist; no self-edges; no duplicate edges (unordered pair).
   - `estate_forms` — forms per §7.3 (`id, name, specialty_tags, relocation_class, base_caps, modifiers, upkeep_profile, production_profile`), `transformations` (`from, to, cost`), and `relocation_classes` (`{cost_multiplier, time_multiplier}` per class). Integrity: transformation endpoints and relocation classes must resolve; `upkeep_profile`/`production_profile` items must resolve but are otherwise **validated-and-ignored** in this phase.
   - `development` — nodes per §7.4 (`id, archetype, name, tags, modifiers, cap_bonuses, upkeep_profile, projects`) and edges (`id, from, to, progress_target > 0, kind: "development"|"regression", transition_ms` — required for development edges, forbidden or ignored for regression edges). Integrity: node/edge/project references resolve; every realm's starting node (see below) exists; the development-edge graph contains no self-loops.
   - `projects` — per §7.4 (`id, name, targets: [{item_id, qty}], awards: [{edge_id, progress > 0}]`). Integrity: items and edges resolve; a project may only award `kind: "development"` edges (regression edges fill exclusively from upkeep, §7.4 — enforce at load time).
2. **Realm pack reshape:** realms no longer carry `tags`, `modifiers`, or an inline `project` — identity lives on development nodes. A realm is now `{id, name, starting_node_id, market_offers}`. Update the realms schema accordingly and cross-check `starting_node_id` against the development pack.
3. **Placeholder pack updates** (scaffolding, obviously fake, minimal):
   - `map.json`: one edge between the two realms with small nonzero costs (e.g., 25 gold, no items, `time_ms` = 60000) so path math is exercised.
   - `estate_forms.json`: exactly the camp → homestead → orchard chain from §6.3, with the orchard's `production_profile` pointing at an existing placeholder tier-1 item; costs drawn from existing placeholder items.
   - `development.json`: per realm, a `_t1` node (carrying that realm's previous tags/modifiers so **action availability and effective rates are unchanged** after migration) and a `_t2` node with a small modifier delta; one development edge `_t1 → _t2` (`progress_target: 100`, `transition_ms`: 5 minutes — short, for manual testing); one regression edge `_t1 → _t0_stub` node per realm (a bare node; never reachable in this phase).
   - `projects.json`: each realm's previous placeholder project, restructured to award its realm's development edge (100 progress on completion).
4. **Served packs** (§5.1): extend the content endpoints to serve `map`, `estate_forms`, `development`, and `projects` alongside the original five. This supersedes log #8's five-pack list — record in phase notes as a design-doc amendment. ETag/manifest machinery applies unchanged; manifest version must change with the new packs.

**Migration requirements (§6.2) — one Alembic revision (or a small ordered set), with data backfill:**

5. `estates`: rename `character_id` → `owner_character_id` (nullable), add `form_id` (backfill: `form.homestead`), `status` (default `active`), and relocation-pending columns `relocating_to_realm_id NULL`, `relocation_completes_at NULL` (used by 4.3; mirrors the realm-transition pattern — **note in phase notes that these two columns extend the §6.2 schema and need a design-doc ratification entry**). Replace the old one-estate uniqueness with a partial unique index on `owner_character_id WHERE status = 'active'` (SQLite and Postgres both support partial indexes; no dialect-specific SQL outside what Alembic/SQLAlchemy provide).
6. `characters`: add `home_estate_id` (backfill from each character's existing estate; enforce NOT NULL after backfill). `realm_id` remains, documented in the model as a cache (§7.5).
7. New tables: `estate_ownership_history` (backfill one row per existing estate: current owner, `acquired_at` = estate's original creation time if available, else migration time), `realm_edge_progress`, `realm_projects`.
8. `realm_state`: drop `project_id`, `contribution_totals`, `tier`; add `node_id` (backfill: the realm's `starting_node_id`), `transition_to_node_id NULL`, `transition_completes_at NULL`, `treasury` (integer, default 0, **written by nothing in this phase**), `data JSON`. `realm_contributions`: add `project_id` (backfill from the realm's previous single project id).
9. Character creation (`POST /characters`) updated: new characters get an estate with `form_id = 'form.camp'`, an ownership-history row, and `home_estate_id` set — all in the creation transaction.

**Engine requirements (§7, purity rules unchanged — no SQLAlchemy/FastAPI imports):**

10. Extend `CharacterState` with `estate_form_id` and `realm_node_id` (replacing any realm-id-based modifier lookup). `effective_cycle_time`/`effective_xp`/`effective_drops` and `resolve_caps` now draw modifier/cap sources from: the realm's **current development node** (tags/modifiers/cap_bonuses), the **estate form** (modifiers/base_caps), and installed non-inert **estate upgrades** — additive within type per §7 (log #10 arithmetic unchanged). Action availability checks tags against the node's tags.
11. New pure helpers: `path_cost(realm_a, realm_b, content) -> {gold, items, time_ms}` (cheapest path over the map graph, summing each cost component along the path; document and test the tie-break: lowest gold, then lowest time) and `relocation_cost(path_cost, form, content)` applying the form's relocation-class multipliers (`cost_multiplier` scales gold and item quantities, `time_multiplier` scales `time_ms`; integer truncation).
12. `resolve_caps` incorporates estate-form `base_caps` and development-node `cap_bonuses`.

**API requirement:**

13. **Resolved caps exposed** (§7.1 gap): `GET /characters/me` gains a `caps` object — every cap type with `{base, effective}`. Client wiring lands in 4.4; this prompt only ships and tests the server field.

**Tests:**
- Content: each new pack accepted; parameterized broken fixtures rejected (unknown realm in edge, duplicate unordered edge, project awarding a regression edge, missing `transition_ms` on a development edge, transformation to unknown form, realm with unknown `starting_node_id`); manifest changes when any new pack changes.
- Migration: upgrade from the Phase-3 head against a fixture DB containing a player/character/estate/realm rows → all backfills correct (form, home_estate_id, ownership history, node_id, contributions' project_id); downgrade at least drops cleanly.
- Engine: modifier resolution from node + form + upgrades matches hand-computed values, including inert-upgrade exclusion; a character in `_t1` gets identical effective values to the pre-migration realm content (the "unchanged rates" guarantee in requirement 3); `path_cost` on the placeholder graph and on a synthetic 4-node graph with a cheaper indirect path; `relocation_cost` multiplier/truncation math; caps including form base caps and node bonuses.
- API: profile response contains `caps` with correct effective values for a character with an upgrade granting a cap bonus.

**Out of scope:** any endpoint from §5.6, transitions, awards, relocation execution, treasury writes, anything reading `upkeep_profile`/`production_profile`.

---

## Prompt 4.2 — Estate endpoints: upgrades and transformation

Expose the estate over HTTP per §5.6 and §7.3. Structures from 4.1 are complete.

**Requirements:**

1. `GET /estates/me` — the character's home estate: id, form (id + resolved content summary), realm_id, level, status, `upgrade_slots` (resolved cap, §7.1), installed upgrades (slot_index, upgrade id, name, active|inert with the inert reason), and pending-relocation fields (always null until 4.3).
2. `POST /estates/me/upgrades/{upgrade_id}` — purchase per §5.6:
   - Resolve the character first (§4.2 rule: every mutating endpoint resolves).
   - Validate: upgrade exists (`UNKNOWN_UPGRADE`), a free slot exists under the resolved `estate_upgrade_slots` cap (`NO_FREE_SLOT`), not already installed (`ALREADY_INSTALLED`), inputs affordable (`MISSING_INPUTS` — reuse the engine's input-check semantics; costs are items and consumed from inventory).
   - Install into the lowest free `slot_index`; one transaction; concurrent double-purchase of the last slot must yield exactly one install (row-lock the estate; same dialect-guarded pattern as `resolve_character`).
   - Response: updated estate payload. If the upgrade grants cap bonuses or modifiers, subsequent resolves must reflect them (no caching bugs — effective values are computed per resolve, §4.2).
3. `POST /estates/me/transform` `{form_id}` — per §7.3:
   - Validate: a transformation edge exists from the current form to `form_id` (`INVALID_TRANSFORMATION`), costs affordable (`MISSING_INPUTS`), estate `status` is `active` (`ESTATE_BUSY` otherwise — future-proofing for relocation/decay states).
   - Charge cost, update `form_id`, re-evaluate installed upgrades' inert status against the new form/realm (per §7.3's note that inertness may consider form), one transaction.
   - Transformation does **not** change level, slots contents, or realm. If the new form's base caps shrink `estate_upgrade_slots` below the number of installed upgrades, reject with `WOULD_ORPHAN_UPGRADES` (v1 rule — simplest safe behavior; note for design ratification).
4. Both mutations append a structured audit line (existing JSON logging) with character id, estate id, and the change — cheap provenance until real audit needs arrive.

**Tests (integration):** estate payload shape and inert annotation; upgrade happy path including effective-value change visible in a subsequent action resolve; every error code; last-slot concurrency (two sessions); transform happy path camp→homestead including cost consumption; transform with shrinking slots rejected; `ESTATE_BUSY` (simulate by setting a non-active status directly).

**Out of scope:** relocation (4.3), any client work (4.4), transfer/escheat, second estates.

---

## Prompt 4.3 — Realm endpoints: projects, awards, transitions, relocation, map

Implement the development-graph gameplay per §7.2, §7.4, and relocation per §5.6. This is the prompt with the trickiest concurrency; budget review here the way Phase 3 budgeted it for the engine.

**Requirements:**

1. **Award interface** (service layer, §7.4): `award_edge_progress(session, realm_id, edge_id, amount, source)` — increments `realm_edge_progress` (upsert), and if progress reaches the edge's `progress_target`, initiates the transition: set `realm_state.transition_to_node_id` and `transition_completes_at = now + transition_ms`. Serializes on the `realm_state` row (same dialect-guarded lock pattern). Rejects awards to regression edges and to edges not outgoing from the realm's **current** node (`INVALID_EDGE_AWARD` — internal error, not user-facing). If a transition is already pending, further awards to *any* edge of the departing node are rejected the same way (the node is already leaving; progress there would be reset anyway — simplest consistent rule, note for ratification).
2. **Lazy transition finalization** (§7.4): a `finalize_realm(session, realm_id, now)` service function, called at the top of **every** endpoint that reads or mutates realm-scoped state (realm details, contribution, relocation, and character resolves via the realm-identity lookup): if `transition_completes_at <= now`, atomically — set `node_id = transition_to_node_id`, clear transition fields, **delete all `realm_edge_progress` rows for edges outgoing from the departed node** (log #15 reset), and mark `realm_projects` rows `closed` for projects not offered by the new node. Idempotent and concurrency-safe (two simultaneous finalizations → one effect). Characters' effective values pick up the new node automatically because resolution reads `realm_state.node_id` per resolve.
3. `GET /realms` and `GET /realms/{id}` (§5.6): current node identity (tags, modifiers, cap_bonuses), pending transition `{to_node_id, completes_at} | null`, active projects with per-target contribution progress, and outgoing development-edge progress `{edge_id, progress, target}`. Treasury is **not** exposed (nothing funds it yet; avoid teaching the client a zero).
4. `GET /map` (§5.6, §7.2): nodes (realm id, name, position) and edges (realm pair, cost bag) straight from content. Unauthenticated is acceptable (it is pure content — consistent with log #8's rationale); note the choice in phase notes.
5. `POST /realms/{id}/projects/{project_id}/contribute` `{item_id, quantity}`:
   - Resolve character; validate project is offered by the realm's current node and not `closed`/completed (`UNKNOWN_PROJECT`), item is among the project's targets (`INVALID_CONTRIBUTION`), quantity > 0 and available (`MISSING_INPUTS`).
   - Clamp to remaining target (contribute at most what's still needed; return the accepted quantity), consume items, record `realm_contributions`, update `realm_projects.contribution_totals` — all serialized on the `realm_projects` row.
   - On completion (all targets met): mark completed, call `award_edge_progress` for each award, all in the same transaction. Two racing final contributions must produce exactly one completion and one award.
6. `POST /characters/me/relocate` `{realm_id}` (§5.6, §7.2, §7.3):
   - Resolve character; **stop the active action if any** (resolve then clear, same as `DELETE /action` — relocating mid-chop abandons the tree; note in response).
   - Validate: destination exists and differs from current (`UNKNOWN_REALM`, `ALREADY_THERE`), a path exists (`UNREACHABLE` — content may later ship disconnected realms), estate `status` is `active` and no relocation pending (`ESTATE_BUSY`).
   - Compute cost via engine `path_cost` × `relocation_cost` (4.1); charge gold and items up front (`MISSING_INPUTS`/`INSUFFICIENT_GOLD`). If effective `time_ms` is 0, complete instantly. Otherwise set `estates.relocating_to_realm_id` + `relocation_completes_at`, and finalize lazily: any resolve/read touching the character or estate past the timestamp completes the move — update `estates.realm_id`, sync `characters.realm_id` (§7.5 cache), re-evaluate inert upgrades, clear the pending fields.
   - **During a pending relocation, the character retains the origin realm's identity** (tags, modifiers) until arrival — deliberately mirroring the realm transitory-phase pattern (§7.4). Starting actions is allowed under origin rules; a second relocation is not. Record this rule in phase notes for design ratification.
7. Wire `finalize_realm` and relocation finalization into `resolve_character`'s state loading so ordinary skilling polls pick up completed transitions/moves without touching realm endpoints.

**Tests (integration, fake clock throughout):**
- Contribution happy path with clamping; every error code; racing final contributions → one completion, one award (two-session test, meaningful on Postgres).
- Award reaching target sets pending transition; awards during pending rejected; `GET /realms/{id}` shows the pending window.
- Transition finalization: advance clock past `completes_at`, hit **a skilling poll** (not a realm endpoint) → next action resolve uses the new node's modifiers; sibling edge progress rows deleted; non-offered projects closed; double-finalization race yields one effect.
- Relocation: instant (zero-time synthetic content) and delayed paths; cost math against hand-computed path × class values; origin identity holds mid-relocation (action availability check); arrival syncs realm cache, re-evaluates inert upgrades (construct an upgrade inert only in the destination); active action stopped and its final rewards returned; `ESTATE_BUSY` on double-relocate.
- Property: contributions conserve items (consumed = recorded totals) across random sequences (hypothesis).

**Out of scope:** treasury writes, regression edges (nothing traverses or fills them), transition cancellation, client work.

---

## Prompt 4.4 — Client: Estate, Realm, Map, and caps display

Implement the Phase 4 client surface per §9. Server from 4.1–4.3 is complete.

**Requirements:**

1. **Estate panel** (sidebar section goes live): form name + specialty tags, level, upgrade slots as a filled/empty grid (installed upgrades show name + active/inert badge with reason tooltip), available upgrades from content with costs and affordability state, purchase flow with optimistic-safe invalidation (invalidate estate + profile + inventory on success). Transformation UI: available form edges with costs, confirm dialog stating what changes (slots/caps deltas) — wired to the transform endpoint and its error codes.
2. **Profile realm view**: current node name/archetype, tags, active modifiers; pending transition rendered as a prominent banner with target identity and a live countdown (from the single 4 Hz clock store — no new intervals); on countdown expiry, refetch realm + available-actions queries (the server finalizes lazily; the client just has to ask again).
3. **Realm panel** (`GET /realms/{id}` for the character's realm): projects with per-target progress bars and a contribute form (item picker limited to target items the player holds, quantity clamped client-side to min(held, remaining) — server clamp remains authoritative); development-edge progress displayed as the realm's "path forward."
4. **Map view** (new route under the Realm/Profile area): render the realm graph from `GET /map` positions as a simple SVG — nodes labeled, current realm highlighted, edges with cost summaries on hover. This is a diagram, not a game map; no pan/zoom needed for two realms.
5. **Relocation flow**: from the map or realm view, choose a destination → preview computed cost/duration (server-provided via a dry-run: add `GET /characters/me/relocate/preview?realm_id=` to the server in this prompt — thin wrapper over the cost function, no state change) → confirm → pending-relocation banner (destination + countdown, same clock store) shown in the global strip area; on expiry, refetch profile/estate/available-actions. Surface the stopped-action notice from the relocation response in the reward feed.
6. **Resolved caps display** (closes the §7.1 gap client-side): inventory grid header and market-relevant spots read `caps.effective` from the profile response; remove any use of content-pack base caps for display.
7. Content hook updates: `useContent()` serves the four new packs; localStorage cache keyed by the new manifest version invalidates cleanly for existing users.

**Tests (vitest + testing-library):** estate slot grid renders installed/inert/empty from fixtures; upgrade affordability gating; transition banner countdown math and expiry-triggered refetch (fake timers); contribution form clamping; relocation preview → confirm flow with mocked endpoints; caps display uses effective values.

**Acceptance criteria (manual, in browser):** create character → buy an estate upgrade and watch a skill's effective cycle time change → transform camp → homestead → contribute to the realm project until the edge fills → see the transition banner, wait out the 5-minute placeholder window, watch the realm's identity and available actions change → relocate to the other realm, wait out the travel time, confirm arrival re-evaluates an inert upgrade and the inventory header shows resolved caps throughout.

---

## Suggested prompt-to-agent packaging

For each run, provide: (1) design.md **v0.5**, (2) the single relevant prompt, (3) the current repo state. After each prompt, review the phase notes and diff before proceeding. Prompts 4.1 (migration + backfill correctness) and 4.3 (transition/relocation concurrency) deserve the closest human review. Three rules from this file's prompts need explicit design-doc ratification afterward: the served-packs extension (4.1), `WOULD_ORPHAN_UPGRADES` and the relocation-pending estate columns (4.1/4.2), and origin-identity-during-relocation plus no-awards-during-pending-transition (4.3) — collect them in the phase notes for the next design bump.
