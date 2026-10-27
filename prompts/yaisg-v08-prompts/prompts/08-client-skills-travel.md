## Prompt 08 — Client: skills, tiers, travel

**ID:** `08-client-skills-travel` · **Workstream:** Q · **Needs:** 07 · **Design:** §24 (Skills, Map), §6.2 (locked reasons)

### Goal

Bring the client up to Prompts 01–07.

### Build

1. Skill panels for Gathering, Refining, Manufacturing (renamed), with a Travel entry. Tier badge and title per skill; levels to 100; XP to next.
2. Per action: effective cycle time, XP per cycle, proficiency percentage, taper factor, and a visible marker when the XP bonus exceeds the cap (capped vs uncapped).
3. Locked actions show human-readable reasons from the requirement codes.
4. Map: choose a destination, mode (relocate enabled only with a mobile estate present), preview time and supplies per edge, start. Journey progress (step *n* of *m*, current edge) in the global action strip using the existing 4 Hz clock.
5. Welcome-back modal and reward feed render resolver `details` generically, with a travel-specific summary.
6. Remove relocation UI remnants.

### Tests (vitest + testing-library)

- Locked-reason rendering from fixture codes; tier badge at thresholds; travel preview form; journey progress from `meta`; welcome-back travel summary; capped XP marker.

### Out of scope

Realm, estate and market panels.

### Review focus

No client-computed values presented as authoritative; progress is cosmetic and snaps to server truth.

