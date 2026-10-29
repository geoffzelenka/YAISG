## Prompt 14 — Client completion and polish

**ID:** `14-client-polish` · **Needs:** 13 · **Source:** F5 (v0.8 30 and 35 hand-offs, plus 37 review) · **Design:** §24

### Build

Every remaining F5 item in `docs/v08/conformance.md`:

1. Fractional HP text (show whole numbers consistently).
2. Encounter initial combat filter and stable React keys.
3. Stance hook naming.
4. Tests that poll active meta, the idle profile and active inventory, written as mutation-catching tests.
5. Key panel:
   - errors shown next to the key or listing that caused them;
   - friendly lifecycle and realm labels from content;
   - tests for unbound keys, destroy (confirm then DELETE) and "fully paid at kickoff".
6. Split `guestSession(credentials?)` into `createGuest` and `upgradeAccount`.
7. An equipment test that pins the missing-skill default of level 1 (`EquipmentPanel.tsx`, v0.8 37 review).
8. Any client display left over from Prompts 01–06.

Preserve auth promotion ordering (upgrade, then `/players/me`) and the key combat locks.

### Tests

A vitest test for each item, each of which fails when its behaviour is broken.

### Out of scope

New features or visual redesign.

### Review focus

No regression in the guest upgrade flow; tests are mutation-catching.
