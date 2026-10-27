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

`world_seed.json` is private (hashed, never served). Each world realm specifies
`treasury` in gold, `stores` as positive whole-item `qty` values, and `estates`
as form ids. Seeding converts stores to milli-units and creates estates with
no character owner. Boot or `make world-create` creates these holdings once;
`world_state` prevents subsequent starts from replenishing them. Run migrations
before creating a world.

Demand-line `draw_per_day`, reserve, cap and stock use milli-line-units. Ordinary
lines count one unit per good; value-measured lines count reference price per
good. Item `warehouse_cap` overrides the economy's warehouse value cap for a
no-demand good, in whole units. The placeholder cap is eleven days because
three reserve days plus the seven-day transition must remain below the cap.
