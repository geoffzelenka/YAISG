## Prompt 31 — Instanced items, exploration, key actions

**ID:** `31-keys` · **Workstream:** O · **Needs:** 30 · **Design:** §8.3 (Exploration), §9.1 (instances), §12.6 (step 5), §19.1–19.4, §19.6 · **Vision:** V§3.8, V§10.1–10.4

### Goal

Exploration that discovers keys: one-of-a-kind items that grant private, finite access to a resource.

### Build

1. **`item_instances`** (§19.1); each instance takes one inventory slot; slot usage = distinct stackables + instances.
2. **`exploration` pack** (§19.2): discovery templates and exploration actions with `discovery_chance`, a weighted table and consumable effects; actions listed in `node.actions` with cross-skill gates in `requires.skill_levels`.
3. **Discovery** on the uniform resolver (§19.3): XP each cycle; with probability `discovery_chance` (after consumables) pick a template with weights shifted by the Exploration tier benefit and the character's tiers in the gating skills; roll key count plus the tier benefit's bonus; roll each key's uses and ranged values independently; create instances held by the explorer with `realm_id` = current realm and `discovered_by_name` copied. Overflow loses the key and the summary says so. Exploration tier benefits for cycle speed as group P.
4. **Using a key** (§19.4): `POST /actions/start {key_id}`; holder, state `active` or `deprecated`, uses left, in the key's realm, meets the inline action's level and tool or the combat engagement rule. First use sets `bound_at`. Gather keys run uniform with cycles clipped to `uses_remaining`; combat keys run the combat resolver and use one per spawn when the encounter begins. At zero: `depleted`, `KEY_DEPLETED`. `GET /keys/me`; `DELETE /keys/{id}` for any held key.
5. **Transitions** (§19.6): a starting transition marks the realm's active keys `deprecated`; completion marks them `invalid`, ends actions on them with `KEY_INVALIDATED`.

### Tests

- Keys never stack; slot accounting.
- Rolled values independent across keys of one discovery.
- Binding on first use; uses clip the batch; depletion.
- Deprecation at transition start; invalidation stops a running key action.
- Discovery rate over a seeded long run within tolerance.

### Out of scope

The key market (32).

