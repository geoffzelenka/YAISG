## Prompt 12 — Content and lint helpers

**ID:** `12-content-lint-projections` · **Needs:** 11 · **Source:** F6 (v0.8 09, 18, 26, 27 and 28 hand-offs) · **Design:** §4, §5.2, §7.3, §10.6

### Build

1. Consolidate the duplicated tag and mint helpers into one module each.
2. Add a public lint projection API: a typed function the CLI, tests and future tools call, instead of reaching into internals.
3. Standard gear per combat style (§10.6), replacing the single `standard_gear`.
4. Validate damage-type references in content.
5. The gear, selector and buff enumeration stays exponential unless a measured bottleneck exists. If you optimize it, keep the conservative upper bound, and prove equality with the old enumeration on the shipped content and in Hypothesis.
6. v0.8 consumables hand-offs that are still open: use `engine.health.maximum_hp` in `create_character`, and extract one shared §7.5 fit check.

### Tests

- Lint output is unchanged on shipped content, except for the per-style standard gear. Explain that difference in the phase note.
- An unknown damage type is rejected.
- Each style's standard gear is used by the combat lint.
- Any optimized enumeration equals the old one.

### Out of scope

New content beyond placeholders.

### Review focus

The lint stays a conservative upper bound.
