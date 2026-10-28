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
Combat skills are omitted from this uniform-action report and receive the
separate encounter report described below.

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
eligibility when their rules change.


## Combat pools

Combat reports are included in both text and JSON output. For every combatant,
its referencing actions and every `progression.stances` entry, the report gives
time to kill, time including respawn, the four receiving skills' XP/hour,
target XP/hour at the action's unlock level, and the skills outside the authored
tolerance. An unreferenced combatant reports `NO_COMBAT_ACTION` because it has
no unlock level; an opponent the standard player cannot damage reports
`UNDEFEATABLE`, null durations and zero rates. Warnings retain exit status zero.

`progression.combat.standard_gear` maps concrete slots to item ids. It is a
content-owned baseline, independent of a live character's equipment. Boot
checks that this layout fits the slots, respects two-handed exclusions and is
usable at every combat action's unlock level. Empty slots use the unarmed
fallback. All six combat skills are set to the action's unlock level. Gear
modifiers and tier effectiveness participate; realm, estate and consumable
bonuses are excluded from this baseline.

The estimate enumerates every integer damage roll using the engine's weakness,
resistance and armour floors and the clamped hit chance. It divides combatant
HP by mean player damage and rounds up to whole player cycles, then adds
respawn time. Enemy attacks count whole enemy intervals during the estimated
fight. Their expected damage taken and mitigated determine the defensive split,
scaled proportionally when the defensive pool caps it. The offensive pool is
split by stance. Respawn time trains neither stream.

This is a deterministic sizing estimate, not an encounter simulation: it omits
survival, utility consumption, reactive items and timed buffs, and approximates
the expected number of attacks needed to kill by HP / mean damage. A pool that
is not exhausted before the estimated kill contributes only its expected draw.
Actual combat resolution belongs to Prompt 29.
