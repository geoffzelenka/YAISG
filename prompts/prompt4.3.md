Prompt 4.3 — Realm endpoints: projects, awards, transitions, relocation, map

Implement the development-graph gameplay per §7.2, §7.4, and relocation per §5.6. This is the prompt with the trickiest concurrency; budget review here the way Phase 3 budgeted it for the engine.

Requirements:

Award interface (service layer, §7.4): award_edge_progress(session, realm_id, edge_id, amount, source) — increments realm_edge_progress (upsert), and if progress reaches the edge's progress_target, initiates the transition: set realm_state.transition_to_node_id and transition_completes_at = now + transition_ms. Serializes on the realm_state row (same dialect-guarded lock pattern). Rejects awards to regression edges and to edges not outgoing from the realm's current node (INVALID_EDGE_AWARD — internal error, not user-facing). If a transition is already pending, further awards to any edge of the departing node are rejected the same way (the node is already leaving; progress there would be reset anyway — simplest consistent rule, note for ratification).
Lazy transition finalization (§7.4): a finalize_realm(session, realm_id, now) service function, called at the top of every endpoint that reads or mutates realm-scoped state (realm details, contribution, relocation, and character resolves via the realm-identity lookup): if transition_completes_at <= now, atomically — set node_id = transition_to_node_id, clear transition fields, delete all realm_edge_progress rows for edges outgoing from the departed node (log #15 reset), and mark realm_projects rows closed for projects not offered by the new node. Idempotent and concurrency-safe (two simultaneous finalizations → one effect). Characters' effective values pick up the new node automatically because resolution reads realm_state.node_id per resolve.
GET /realms and GET /realms/{id} (§5.6): current node identity (tags, modifiers, cap_bonuses), pending transition {to_node_id, completes_at} | null, active projects with per-target contribution progress, and outgoing development-edge progress {edge_id, progress, target}. Treasury is not exposed (nothing funds it yet; avoid teaching the client a zero).
GET /map (§5.6, §7.2): nodes (realm id, name, position) and edges (realm pair, cost bag) straight from content. Unauthenticated is acceptable (it is pure content — consistent with log #8's rationale); note the choice in phase notes.
POST /realms/{id}/projects/{project_id}/contribute {item_id, quantity}:
Resolve character; validate project is offered by the realm's current node and not closed/completed (UNKNOWN_PROJECT), item is among the project's targets (INVALID_CONTRIBUTION), quantity > 0 and available (MISSING_INPUTS).
Clamp to remaining target (contribute at most what's still needed; return the accepted quantity), consume items, record realm_contributions, update realm_projects.contribution_totals — all serialized on the realm_projects row.
On completion (all targets met): mark completed, call award_edge_progress for each award, all in the same transaction. Two racing final contributions must produce exactly one completion and one award.
POST /characters/me/relocate {realm_id} (§5.6, §7.2, §7.3):
Resolve character; stop the active action if any (resolve then clear, same as DELETE /action — relocating mid-chop abandons the tree; note in response).
Validate: destination exists and differs from current (UNKNOWN_REALM, ALREADY_THERE), a path exists (UNREACHABLE — content may later ship disconnected realms), estate status is active and no relocation pending (ESTATE_BUSY).
Compute cost via engine path_cost × relocation_cost (4.1); charge gold and items up front (MISSING_INPUTS/INSUFFICIENT_GOLD). If effective time_ms is 0, complete instantly. Otherwise set estates.relocating_to_realm_id + relocation_completes_at, and finalize lazily: any resolve/read touching the character or estate past the timestamp completes the move — update estates.realm_id, sync characters.realm_id (§7.5 cache), re-evaluate inert upgrades, clear the pending fields.
During a pending relocation, the character retains the origin realm's identity (tags, modifiers) until arrival — deliberately mirroring the realm transitory-phase pattern (§7.4). Starting actions is allowed under origin rules; a second relocation is not. Record this rule in phase notes for design ratification.
Wire finalize_realm and relocation finalization into resolve_character's state loading so ordinary skilling polls pick up completed transitions/moves without touching realm endpoints.

Tests (integration, fake clock throughout):

Contribution happy path with clamping; every error code; racing final contributions → one completion, one award (two-session test, meaningful on Postgres).
Award reaching target sets pending transition; awards during pending rejected; GET /realms/{id} shows the pending window.
Transition finalization: advance clock past completes_at, hit a skilling poll (not a realm endpoint) → next action resolve uses the new node's modifiers; sibling edge progress rows deleted; non-offered projects closed; double-finalization race yields one effect.
Relocation: instant (zero-time synthetic content) and delayed paths; cost math against hand-computed path × class values; origin identity holds mid-relocation (action availability check); arrival syncs realm cache, re-evaluates inert upgrades (construct an upgrade inert only in the destination); active action stopped and its final rewards returned; ESTATE_BUSY on double-relocate.
Property: contributions conserve items (consumed = recorded totals) across random sequences (hypothesis).

Out of scope: treasury writes, regression edges (nothing traverses or fills them), transition cancellation, client work.
