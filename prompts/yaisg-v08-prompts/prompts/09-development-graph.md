## Prompt 09 — Development graph, tag stack, transitions

**ID:** `09-development-graph` · **Workstream:** E · **Needs:** 07 · **Design:** §4.2 (realms, development, projects), §12.1, §12.2, §12.4, §12.6 · **Vision:** V§7.1–7.4, V§7.7

### Goal

Replace edge-progress development with nodes, a tag stack and transitions.

### Build

1. **`realm_state`** reshaped to §12.1 (`template_id`, `isolated`, `owner_character_id`, `current_node_id`, `treasury`, `pending_transition`, `last_tick_at`, `gauge`, `decay_stage`, `shed_progress`, `vote_cooldown_until`, `treasury_band`). For world realms `id = template_id`. Isolated realms are excluded from every list and the map.
2. **`realms` pack**: `{id, name, starting_node_id, isolated}`. Remove `market_offers` everywhere.
3. **`development` pack** node shape (§12.2) with `upgrades` (`tier_up` | `morph`, `required_tags`, `fee_gold`), `regression`, `carried_tags`, `upkeep` (selectors), `projects`, and optional `reserve_days`, `cap_days`, `margin_pct`. Validator: every `required_tags` entry is granted by a project offered at that node or is in `carried_tags`; regression edges reach the single barren root (the only node with `regression: null`) from every node.
4. **`projects` pack** reshaped to §12.3 (`grants_tag`, `kickoff {gold, goods, who}`, `cost`, `build_seconds`, `realm_completion_days`, `requires_tags`, `repeatable: false`). Remove project tiers.
5. **`realm_tags`** table (§12.4) with per-realm increasing `seq` and `node_id`. A realm's active tags are its node's inherent tags plus its stack, through Prompt 05's `active_tags`.
6. **Transitions.** `start_transition(realm, to_node, cause, now)` sets `pending_transition` with `completes_at = now + transition.duration_days` (*default* 7, in `economy.transition`). `finalize_realm`, lazy and idempotent at exactly `completes_at` (§12.6): swap node; drop tags neither offered nor carried by the new node; on upgrade keep `node_id`, on regression restamp to the new node, reset gauge and clear `shed_progress`. (Key invalidation is added in Prompt 31; action ending falls out of Prompt 05.)
7. **`GET /realms`, `GET /realms/{id}`**: node, type, tier, tags (with `seq` and `node_id`), decay stage, gauge, pending transition. Treasury never returned.
8. Placeholder content: a barren root; two tier-1 nodes of different types with projects; one `tier_up` and one `morph` edge; regression edges.

### Tests

- Validator rejects an unsatisfiable `required_tags`, a node that cannot regress to the root, two roots.
- `finalize_realm` twice equals once; upgrade keeps `node_id`; regression restamps and resets the gauge; tags not offered or carried are dropped.
- Isolated realms absent from `/realms` and `/map`.

### Remove

`realm_edges`, `realm_projects`, `award_edge_progress`, edge-progress endpoints and client code, project tiers, `market_offers`, and the old contribute endpoint (Prompt 10 adds the new one).

### Out of scope

Project runs (10); votes (19); decay driving regression (15).

### Review focus

D4's `node_id` semantics are encoded in data now; check the restamp rule.

