# YAISG v0.8 Implementation Prompts

Companion to `design/design.md` **v0.8** and `design/the-vision.md`. These prompts take the code from the shipped v0.5 baseline (Phases 0–4) to the full v0.8 design, workstreams A–R of design §26.

There are 38 prompts located in `prompts/yaisg-v08-prompts/prompts/`. Run them strictly in the order of the table below. Each prompt is one feature-sized, self-contained, testable unit that ends with `make ci` green on both databases and is merged to local `main` before the next one starts.

---

## 1. How the pipeline runs

```
for prompt in SEQUENCE:
    git switch main && git switch -c v08/<prompt-id>
    coder(prompt, CONTEXT)                       → commits on the branch + phase note
    loop (max 3 rounds):
        verdict = reviewer(prompt, CONTEXT, diff main...branch, phase note, CHECKLIST)
        APPROVE            → break
        CHANGES_REQUESTED  → coder(fix list) ; continue
        ESCALATE           → stop the pipeline, hand to a human
    if 3 rounds without APPROVE → ESCALATE
    git switch main && git merge --no-ff v08/<prompt-id>
    make ci            (on main, SQLite and PostgreSQL) → if red: ESCALATE
    update docs/v08/progress.md
```

**CONTEXT given to every coder and reviewer invocation**

1. This README (conventions, definition of done, review checklist).
2. The single prompt being run.
3. `design/design.md` (v0.8) and `design/the-vision.md`.
4. `docs/v08/codebase-map.md` and `docs/v08/baseline-audit.md` (written by Prompt 00).
5. Every earlier `docs/phase-notes/v08-*.md` (they carry deviations and hand-offs forward).
6. The current repository state on the branch.

**Stop conditions (orchestrator escalates to a human)**

- Prompt 00 records any finding marked `BLOCKER`.
- A reviewer returns `ESCALATE`.
- Three review rounds pass without `APPROVE`.
- `make ci` is red on `main` after a merge.
- A phase note lists an item under **Ratification needed** that the next prompt's Build list depends on.

---

## 2. Conventions for every prompt

**Authority.** `design.md` v0.8 is the specification. Section references (§n) point into it; **V§n** points into the vision. Decisions D1–D15 (design §2.3) are settled. Where design is silent or ambiguous, choose the reading most consistent with the vision, implement it, and record it in the phase note. Where design appears to contradict the vision or itself, implement design as written unless that is impossible, and record it under **Ratification needed**. Agents never edit `design/design.md` or `design/the-vision.md`.

**Pre-release.** Development data is disposable. Migrations may be destructive: drop, rename and recreate freely, with no backfill and no data preservation. From Prompt 01 onward (which adds the target), `make db-reset` must always rebuild a working database from nothing on both SQLite and PostgreSQL.

**Content is data (pillar 2).** Every number the design marks *default* or *illustrative* lives in a content pack, never in code. When a prompt needs a setting, it adds that field to the owning pack's strict schema (`extra="forbid"`) with the design's default. A pack is created by the first prompt that needs it. Placeholder content is extended only as far as the prompt's tests need, stays obviously fake, and is never real game design (§25). The only content ids code may name are the fixed ones in §6.1: `melee`, `ranged`, `magic`, `accuracy`, `defense`, `vigor`, `travel`, `exploration`.

**Engine purity (§3).** Everything in `services/game/app/engine/` is a pure function of `(state, content, now, rng)`. No database, clock or global access there. The HTTP layer locks, loads, calls the engine and writes in one transaction. Lock order follows §23.1: character, then realm(s) in id order, then estate; swept orders in price-time order.

**Errors.** Every error uses `{error: {code, message}}`. Use the exact codes the design names. Where the design names none, choose a SCREAMING_SNAKE code, keep it stable, and list it in the phase note.

**Both databases.** `make ci` runs against SQLite by default. To run it against PostgreSQL 16, set `TEST_DATABASE_URL` as the CI matrix does (`.github/workflows/ci.yml`), e.g. `TEST_DATABASE_URL=postgresql+psycopg://yaisg:yaisg@localhost:5432/yaisg_test make ci`. "Green on both databases" means both runs pass. `docs/v08/codebase-map.md` (written by Prompt 00) records the exact local setup.

**Determinism.** Tests inject the clock and a seeded RNG. Property tests use Hypothesis. Anything touching locks or concurrency is tested on both SQLite and PostgreSQL 16 (the CI matrix already runs both).

**Branch, commits, notes.** Branch `v08/<prompt-id>`. Small coherent commits. Write `docs/phase-notes/v08-<prompt-id>.md` with these headings exactly:

```
## Built
## Removed
## Design ambiguities resolved   (each: §ref, the reading chosen, why)
## Deviations                    (each: §ref, what differs, why)
## Ratification needed           (each: §ref, question, what was implemented meanwhile)
## Hand-offs                     (stubs or hooks a named later prompt must fill)
## New error codes
```

Update the prompt's row in `docs/v08/progress.md` (status, branch, merge commit, one-line summary).

---

## 3. Definition of done (every prompt)

1. `make ci` passes on SQLite and PostgreSQL 16: ruff, mypy strict, pytest, tsc, eslint, vitest.
2. Every test named in the prompt's **Tests** section exists, is deterministic, and would fail if the behaviour it names broke.
3. No existing test is deleted or weakened, except tests of behaviour the prompt's **Remove** section removes; those are listed in the phase note.
4. Everything in **Remove** is gone end to end: routes, columns, content fields, engine functions, client calls and their tests. `grep` for the old names finds nothing outside migrations and phase notes.
5. From Prompt 01 onward, `make db-reset` then `alembic upgrade head` works on both databases; the app boots and loads content.
6. Nothing in the prompt's **Out of scope** or design §25 is built.
7. The phase note is complete and honest, and `progress.md` is updated.

---

## 4. Reviewer checklist

The reviewer reads the prompt, the diff `main...v08/<prompt-id>`, the phase note, and the design sections the prompt cites. It runs `make ci` itself. It then returns exactly one verdict.

**A. Specification**
- [ ] Every numbered Build item is implemented as the cited design section says. Check formulas, rounding direction (floor or ceil as written), ordering rules and tie-breaks literally.
- [ ] Error codes match the design's names exactly.
- [ ] Every D1–D15 decision the change touches is respected.
- [ ] Everything in Remove is fully removed (Definition of done item 4).
- [ ] Hand-offs from earlier phase notes that name this prompt are picked up.

**B. Pillars and vision (design §1, the vision)**
- [ ] Server-authoritative: no client-computed value is treated as truth.
- [ ] Content is data: no hardcoded content ids or tunable numbers in code.
- [ ] Lazy by timestamps: no new per-character background loops; realm work is lazy and idempotent from `last_tick_at`.
- [ ] Conservation: every good and every unit of gold moves between two named holders; nothing appears or vanishes except through the paths in §18 and the loss rules in §14 and §16.
- [ ] Engine purity and lock order (§3, §23.1).
- [ ] Nothing makes Strained mechanically different from Fed; no visitor malus; treasury balance never exposed. (These are the vision's explicit "musts".)

**C. Tests**
- [ ] Required tests exist and assert behaviour, not implementation details.
- [ ] Property tests cover the conservation or idempotence claims the prompt names.
- [ ] Concurrency tests run on PostgreSQL, not only SQLite.

**D. Hygiene**
- [ ] Out-of-scope work is absent; placeholder content stays minimal and fake.
- [ ] The phase note's ambiguity and deviation entries are real and correctly classified. A silent deviation is a blocking finding.

**Verdict format**

```
VERDICT: APPROVE | CHANGES_REQUESTED | ESCALATE
BLOCKING:
  - <file:line> — <rule or §ref broken> — <what to change>
NON-BLOCKING:
  - ...
ESCALATION REASON: (only for ESCALATE: a design contradiction, a BLOCKER, or a decision that belongs to a human)
```

Approve when nothing is blocking. Do not request changes for style preferences that the linters accept. Escalate rather than invent design.

---

## 5. Sequence

| # | ID | Title | Workstream | Needs |
|---|---|---|---|---|
| 00 | `00-preflight` | Baseline alignment audit | — | — |
| 01 | `01-foundation` | Schema reset, XP curve, levels to 100, tiers, zero gold | A | 00 |
| 02 | `02-content-model` | Goods, actions, selectors, categories, caps | A | 01 |
| 03 | `03-bonus-model` | Source groups, multiplication, XP cap, proficiency, taper | B | 02 |
| 04 | `04-content-lint` | XP-rate content lint | B | 03 |
| 05 | `05-tags` | Tags, action requirements, availability report | C | 03 |
| 06 | `06-resolver-presence` | Resolver seam, `current_realm_id`, presence | D | 05 |
| 07 | `07-travel` | Map edges, journeys, the Travel skill | D | 06 |
| 08 | `08-client-skills-travel` | Client: skills, tiers, travel | Q | 07 |
| 09 | `09-development-graph` | Nodes, tag stack, transitions | E | 07 |
| 10 | `10-project-runs` | Project runs and `resolve_realm` | E | 09 |
| 11 | `11-estate-forms` | Estate forms, transforms, realm-owned estates | F | 10 |
| 12 | `12-estate-ownership` | Build, buy, surrender, valuation, larder | F | 11 |
| 13 | `13-stores-lines` | Stores, demand lines, world seed | G | 12 |
| 14 | `14-realm-tick` | The realm tick and the scheduled job | G | 13 |
| 15 | `15-decay` | Gauges, stages, shedding, regression, seed-check | G | 14 |
| 16 | `16-realm-pricing` | Realm market pricing and visibility | H | 15 |
| 17 | `17-realm-trade` | Realm trade and treasury gift | H | 16 |
| 18 | `18-mint-gold` | Mint and the gold ledger | J | 17 |
| 19 | `19-votes` | Realm upgrade votes and transitions | K | 18 |
| 20 | `20-caravans` | Trade between realms | L | 19 |
| 21 | `21-client-realm-estate` | Client: realm, projects, votes, estate | Q | 20 |
| 22 | `22-client-realm-market` | Client: realm market and world health | Q | 21 |
| 23 | `23-global-market` | Global order book, slots, tax, access | I | 22 |
| 24 | `24-market-lifecycle` | Order expiry, purge, world conservation suite | I | 23 |
| 25 | `25-client-global-market` | Client: global market | Q | 24 |
| 26 | `26-equipment` | Equipment slots and gear bonuses | M | 25 |
| 27 | `27-consumables-hp` | Belt, utility, buffs, hit points | M | 26 |
| 28 | `28-combat-model` | Combatants, stats, the hit, stance, combat lint | N | 27 |
| 29 | `29-combat-resolver` | The combat resolver | N | 28 |
| 30 | `30-client-equipment-combat` | Client: equipment and combat | Q | 29 |
| 31 | `31-keys` | Instanced items, exploration, key actions | O | 30 |
| 32 | `32-key-market` | The key market | O | 31 |
| 33 | `33-guest-auth` | Guest accounts | P | 32 |
| 34 | `34-tutorial` | Tutorial Island | P | 33 |
| 35 | `35-client-keys-tutorial` | Client: keys, tutorial, guest upgrade | Q | 34 |
| 36 | `36-hardening` | Rate limits, counters, load, seed-check in CI | R | 35 |
| 37 | `37-conformance` | Final design conformance audit | — | 36 |

The order follows §26's dependency table, linearised. Client prompts follow the server work they display rather than being folded into each server prompt, so that every server prompt is reviewable on its own API and tests.

---
