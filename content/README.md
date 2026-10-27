# Placeholder content

These files are deliberately fake scaffolding for engine and integration tests.
They are not intended to establish names, balance, or final game content.

`xp_curve.json` contains 99 per-level costs for levels 1 to 100. Generate it
with `python scripts/gen_xp_curve.py` from the repository root. The generator
uses high-precision Decimal arithmetic and searches for an amplitude whose
floored costs sum to exactly 10,000,000 (design §5.1). The server validates and
sums this static table; it never regenerates the exponential curve.

`progression.json` owns skill tier thresholds and placeholder titles. Later
prompts extend this strict pack for proficiency, taper and rate settings.
