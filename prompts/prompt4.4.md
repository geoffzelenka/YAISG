Prompt 4.4 — Client: Estate, Realm, Map, and caps display

Implement the Phase 4 client surface per §9. Server from 4.1–4.3 is complete.

Requirements:

Estate panel (sidebar section goes live): form name + specialty tags, level, upgrade slots as a filled/empty grid (installed upgrades show name + active/inert badge with reason tooltip), available upgrades from content with costs and affordability state, purchase flow with optimistic-safe invalidation (invalidate estate + profile + inventory on success). Transformation UI: available form edges with costs, confirm dialog stating what changes (slots/caps deltas) — wired to the transform endpoint and its error codes.
Profile realm view: current node name/archetype, tags, active modifiers; pending transition rendered as a prominent banner with target identity and a live countdown (from the single 4 Hz clock store — no new intervals); on countdown expiry, refetch realm + available-actions queries (the server finalizes lazily; the client just has to ask again).
Realm panel (GET /realms/{id} for the character's realm): projects with per-target progress bars and a contribute form (item picker limited to target items the player holds, quantity clamped client-side to min(held, remaining) — server clamp remains authoritative); development-edge progress displayed as the realm's "path forward."
Map view (new route under the Realm/Profile area): render the realm graph from GET /map positions as a simple SVG — nodes labeled, current realm highlighted, edges with cost summaries on hover. This is a diagram, not a game map; no pan/zoom needed for two realms.
Relocation flow: from the map or realm view, choose a destination → preview computed cost/duration (server-provided via a dry-run: add GET /characters/me/relocate/preview?realm_id= to the server in this prompt — thin wrapper over the cost function, no state change) → confirm → pending-relocation banner (destination + countdown, same clock store) shown in the global strip area; on expiry, refetch profile/estate/available-actions. Surface the stopped-action notice from the relocation response in the reward feed.
Resolved caps display (closes the §7.1 gap client-side): inventory grid header and market-relevant spots read caps.effective from the profile response; remove any use of content-pack base caps for display.
Content hook updates: useContent() serves the four new packs; localStorage cache keyed by the new manifest version invalidates cleanly for existing users.

Tests (vitest + testing-library): estate slot grid renders installed/inert/empty from fixtures; upgrade affordability gating; transition banner countdown math and expiry-triggered refetch (fake timers); contribution form clamping; relocation preview → confirm flow with mocked endpoints; caps display uses effective values.

Acceptance criteria (manual, in browser): create character → buy an estate upgrade and watch a skill's effective cycle time change → transform camp → homestead → contribute to the realm project until the edge fills → see the transition banner, wait out the 5-minute placeholder window, watch the realm's identity and available actions change → relocate to the other realm, wait out the travel time, confirm arrival re-evaluates an inert upgrade and the inventory header shows resolved caps throughout.
