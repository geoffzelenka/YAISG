## Prompt 05 — Tags, action requirements, availability report

**ID:** `05-tags` · **Workstream:** C · **Needs:** 03 · **Design:** §6.2 (availability, `REQUIREMENT_LOST`), §7.4, §7.5, §12.2 (`inherent_tags`, `actions`), §14.6 (stage effects on tags), D11 · **Vision:** V§4.1, V§7.2

### Goal

Introduce tags as the unit of facility, bonus and access, emit them from nodes, forms and upgrades, and enforce where an action may run.

### Build

1. **`tags` pack** with the §7.4 schema (kind, modifiers, cap bonuses, upkeep, effects). Validate every effect field now; the effects are read by later prompts.
2. **Emission.** Nodes gain `inherent_tags` and `actions`. Forms and upgrades gain `tags`. Realm stack tags arrive in Prompt 09: the resolver takes them as an input, empty for now.
3. **Active tags with stage effects (D11).** Add `decay_stage` (default `fed`) to `realm_state` and `estates` now; Prompt 15 drives it. A pure `active_tags(holder, stage)` returns each tag with a factor: in Faltering or worse, `facility` tags are suspended and `bonus`/`malus` modifiers scaled by `decay.faltering_factor` (*default* 0.5). Create the `economy` pack now (served, strict), with a `decay` section; later prompts add sections to it; `access` tags are untouched. Tags from inert upgrades are inactive.
4. **Tags feed bonuses and caps**: realm tags into group R, estate tags into group E; cap bonuses into caps (§7.5).
5. **Availability (§6.2 rules 1–4).** Gathering, combat and exploration actions run only where listed in the current node's `actions`. Refining and manufacturing run where their `requires.facility` is an active tag of the current realm or of the character's own estate when that estate is in the current realm. Travel runs everywhere. `realm_tags` must all be active in the realm; `skill_levels` met; `tool_class` unmet whenever set (no equipment until 26).
6. **Inert rule** reads active tags: an upgrade or form with `requires_realm_tags` missing in the estate's realm is inert.
7. **`GET /actions/available`** returns every action of the character's skills with a list of unmet requirements: `INSUFFICIENT_LEVEL`, `NOT_OFFERED_HERE`, `MISSING_FACILITY`, `MISSING_REALM_TAG`, `MISSING_SKILL_LEVEL`, `MISSING_TOOL`, `MISSING_INPUTS`. `POST /actions/start` uses the same check.
8. **`REQUIREMENT_LOST`.** Each resolve re-checks the running action. If requirements no longer hold, cycles are granted up to the resolve at which the loss is detected and the action ends with `REQUIREMENT_LOST`. (Interpretation of "at that moment"; record it.)
9. Placeholder content: one facility tag on a node, one on an upgrade, one access tag, one bonus tag.

### Tests

- Node-listed gathering is offered and unlisted is not; a facility from the realm, from the owner's estate when present, and not when the estate is elsewhere (set the realm column directly).
- Faltering: facility suspended, bonus scaled 0.5, access unaffected; Fed and Strained identical.
- Inert upgrade's tags contribute nothing.
- Each requirement code appears exactly when its condition fails.
- `REQUIREMENT_LOST` when a required realm tag is removed between resolves.
- A tag's cap bonus raises the effective cap.

### Out of scope

Realm tag stack and projects (09–10); driving decay stages (15); equipment (26).

### Review focus

D11 exactly: access tags survive Faltering. Stage effects live in one pure function others reuse.

