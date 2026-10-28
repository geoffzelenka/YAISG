# XP-rate content lint

Run `make content-lint` from the repository root. It prints a human-readable
report followed by JSON. For a machine-readable stream alone, run
`cd services/game && python -m app.content.lint --format json`.
`--format text` and `--content-dir PATH` are also supported. Local `make ci`
and the game jobs in GitHub CI print the report. Warnings return exit status 0;
invalid content still fails validation, as it does at game boot.

`progression.lint.g` defaults in the authored pack to 1.015969, and
`progression.lint.tolerance_pct` to 15. Targets use the exact fraction
10,000,000 / 2,880 multiplied by g raised to unlock level minus one. Comparisons
use rational arithmetic, interpreting g's decimal representation exactly.
Output rounds only for display. An `off_curve` reason suppresses that action's
rate warning; it does not remove the action from training or hide its rate.

Training sums each of the 99 checked-in XP costs divided by the highest base
XP/hour available at that level. It assumes continuous training at that rate,
without rounding up to whole cycles or sampling, and excludes inputs, access,
bonuses, proficiency and taper. This deliberately measures the base-rate anchors,
rather than reproducing a live resolver. The baseline uses the fastest action
unlocked at level 1 for the whole XP table. Missing level-1 actions yield JSON
null hours (text explains that training is blocked), including empty skills.
Combat skills are omitted entirely.

The external stack report is an **uncapped upper bound** on XP factor times
cycle-speed factor. Each group adds matching skill/category/all modifiers and
uses the engine's `max(min_factor, 1 + sum / 100)` separately for XP and speed.
Their product is maximized jointly over each group's alternatives:

- Realm: each development node's modifiers and active inherent tags, plus every
  subset of its carried tags and tags granted by offered projects. Partial stacks
  matter because a completed project can add a malus. Prerequisite/build history
  is conservatively relaxed, preserving the upper bound.
- Estate: each form with every subset of distinct, non-inert upgrades that fits
  effective slot cap, including tag cap bonuses. Form and upgrade emissions
  and direct modifiers use the runtime all-of requires_realm_tags checks; an
  empty requirement is unrestricted. Candidates cover both distinct stage
  behaviors (Fed and Faltering), since weakening a malus can raise a bound.
  Estate emissions stay in E while realm emissions stay in R.
- Gear: every concrete slot can be empty or hold an authored item. Generic ring
  and arm definitions can fill either or both sides. Two-handed right-hand items
  exclude left-hand equipment. Skill requirements and acquisition history are
  conservatively relaxed. Permanent item modifiers add within G.
- Consumables: every subset of simultaneous distinct timed buffs, adding within C.
  Acquisition and duration restrictions are relaxed, preserving an upper bound;
  expired maluses can be omitted. Utility has no non-combat modifier block.
- Proficiency: excluded, as required by §7.3.

The realm and estate maxima are multiplied, even when they need different
nodes. Final slot feasibility includes slot grants from selected upgrades;
it does not prove that an installation sequence exists. Both relaxations can
overestimate but cannot hide a reachable stack. Estate absence contributes an
identity alternative. The XP cap, taper and millisecond cycle rounding are not
applied: this reports the authored external factors themselves. Above 1.45 it
warns even if the runtime XP cap would absorb some of the excess.

Subset enumeration is exponential in the number of eligible upgrades; current
placeholder packs are small. Larger packs may require a bounded optimization
that preserves the conservative guarantee. Prompts 11/12 must adapt form/slot
eligibility when their rules change. Prompt 28 owns combat checks.
