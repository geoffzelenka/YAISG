## Prompt 06 — Resolver seam, `current_realm_id`, presence

**ID:** `06-resolver-presence` · **Workstream:** D · **Needs:** 05 · **Design:** §6.3, §7.1 (E applies when), §7.5 (caps below usage), §11.2 · **Vision:** V§11.5

### Goal

Widen the engine seam from a reward strategy to a resolver so stepped actions can exist, and make presence real.

### Build

1. **`ActionResolver` protocol** (§6.3) and a registry keyed by `action.resolver`. `ResolveResult` carries new action state, XP by skill, items gained and lost, elapsed time consumed, stop reason, and `details`. Port the uniform resolver with no behavioural change. Stepped resolvers keep state in `active_actions.meta`.
2. **`reward_log.details`** stores the resolver's details object.
3. **Rename `characters.realm_id` → `current_realm_id`** in schema, engine, services, API fields and client. Helpers: `home_realm(character)` (the estate's realm), `is_resident(character, realm)`, `is_present(character, realm)`.
4. **Presence.** Group E and estate cap bonuses apply only when the estate's realm equals `current_realm_id`. A visitor has no other malus. If a cap falls below usage, nothing is removed; gains beyond the cap follow the existing overflow rule.
5. The shipped relocation endpoints keep working against the renamed column until Prompt 07 removes them.

### Tests

- Before refactoring, record golden resolve results for a set of seeded scenarios; after, the uniform resolver reproduces them exactly.
- Registry dispatch by `resolver`.
- A visitor (current realm ≠ estate realm) gets no E bonus, no estate facility, no estate cap bonus, and nothing else changes.
- Inventory cap reduced below usage keeps items and discards further gains with the overflow record.

### Remove

`CycleRewardStrategy`; `characters.realm_id`.

### Out of scope

The travel resolver (07); the combat resolver (29).

### Review focus

Pure refactor plus rename: diffs to engine behaviour other than presence are blocking.

