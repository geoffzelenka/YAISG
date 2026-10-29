# YAISG v0.9 Implementation Prompts

Companion to `design/design.md` **v0.8**, `design/the-vision.md`, the human rulings in `docs/v08/human_ratifications.md` and the v0.8 audit in `docs/v08/conformance.md`.

v0.8 shipped the full design with nine questions left for a human (Q1–Q9) and eight follow-ups (F1–F8, plus F9 for the Q3 ruling). v0.9 applies the rulings first, then works through the follow-ups, and ends with a fresh conformance audit.

There are 16 prompts in `prompts/yaisg-v09-prompts/prompts/`. Run them strictly in the order of §5. Each prompt is one feature-sized, self-contained, testable unit. It ends with `make ci` green on both databases and is merged to local `main` before the next one starts.

---

## 1. How the pipeline runs

```
for prompt in SEQUENCE:
    git switch main && git switch -c v09/<prompt-id>
    coder(prompt, CONTEXT)                       → commits on the branch + phase note
    loop (max 3 rounds):
        verdict = reviewer(prompt, CONTEXT, diff main...branch, phase note, CHECKLIST)
        APPROVE            → break
        CHANGES_REQUESTED  → coder(fix list) ; continue
        ESCALATE           → stop the pipeline, hand to a human
    if 3 rounds without APPROVE → ESCALATE
    git switch main && git merge --no-ff v09/<prompt-id>
    make ci            (on main, SQLite and PostgreSQL) → if red: ESCALATE
    update docs/v09/progress.md
```

**CONTEXT given to every coder and reviewer invocation**

1. This README (authority, conventions, definition of done, review checklist).
2. The single prompt being run.
3. `design/design.md` (v0.8) and `design/the-vision.md`.
4. `docs/v08/human_ratifications.md`, `docs/v08/conformance.md`, and `docs/v09/ratification-map.md` (written by Prompt 00).
5. `docs/v08/codebase-map.md`, every `docs/phase-notes/v08-*.md`, and every earlier `docs/phase-notes/v09-*.md`.
6. The current repository state on the branch.

**Stop conditions (orchestrator escalates to a human)**

- Prompt 00 records any finding marked `BLOCKER`.
- A reviewer returns `ESCALATE`.
- Three review rounds pass without `APPROVE`.
- `make ci` is red on `main` after a merge.
- A phase note lists an item under **Ratification needed** that the next prompt's Build list depends on.

---

## 2. Authority (read first)

The order of authority, highest first:

1. **Human rulings.** `docs/v08/human_ratifications.md` (Q1–Q9) and the "Human rulings already given" section of `docs/v08/conformance.md`. A ruling overrides any design text it contradicts.
2. **`design/design.md` v0.8.** It remains the specification everywhere a ruling does not reach.
3. **The vision.** `design/the-vision.md` decides readings where both of the above are silent.

Agents never edit `design/design.md`, `design/the-vision.md` or anything under `prompts/`. When a ruling supersedes design text, the phase note's **Deviations** section cites the design § and the ruling (e.g. "§13.3 superseded by Q1"); that is not a silent deviation. `docs/v09/ratification-map.md` lists every superseded section, so reviewers can check it.

Where a ruling is ambiguous, choose the reading closest to its words and the vision, implement it, and record it under **Design ambiguities resolved**. Each prompt names the reading the orchestrator expects. Where a ruling cannot be implemented without a further human decision, record it under **Ratification needed** and stop.

---

## 3. Conventions for every prompt

As in v0.8 (`prompts/yaisg-v08-prompts/README.md` §2), with these changes:

- **Branch** `v09/<prompt-id>`. **Phase note** `docs/phase-notes/v09-<prompt-id>.md`, with the same seven headings exactly:

  ```
  ## Built
  ## Removed
  ## Design ambiguities resolved   (each: §ref or Qn, the reading chosen, why)
  ## Deviations                    (each: §ref, what differs, why — cite the ruling when one supersedes it)
  ## Ratification needed           (each: §ref, question, what was implemented meanwhile)
  ## Hand-offs                     (stubs or hooks a named later prompt must fill)
  ## New error codes
  ```

- **Progress** is tracked in `docs/v09/progress.md` (created by Prompt 00). Update your prompt's row.
- **Pre-release.** Development data is still disposable. Migrations may be destructive, and `make db-reset` must rebuild a working database from nothing on SQLite and PostgreSQL.
- **Content is data, engine purity, lock order (§23.1), error shape, determinism and both-database testing** are unchanged from v0.8. Database-backed Hypothesis tests use `deadline=None`.
- **Dependencies.** A human must approve any new Python or npm dependency. The only one approved for this set is `psycopg[binary]` for the auth service (Prompt 00, approved 2026-10-28).
- **Changing pinned behaviour.** Several rulings change behaviour that a v0.8 test deliberately pins. Rewrite such a test to pin the ruled behaviour, and list it by name in the phase note under **Removed** with the ruling that changed it. Any other deleted or weakened test is a blocking finding.
- **Client.** A prompt that changes an API response or error a client feature uses also updates that client feature and its vitest tests in the same prompt.

---

## 4. Definition of done and reviewer checklist

As in v0.8 (`prompts/yaisg-v08-prompts/README.md` §3–§4), with two additions to the checklist:

**E. Rulings**
- [ ] Every ruling the prompt implements matches the words in `docs/v08/human_ratifications.md`. The reading recorded in the phase note is the one the prompt names, or a better-justified one.
- [ ] Every superseded design § is listed under **Deviations** with its ruling, and appears in `docs/v09/ratification-map.md`.
- [ ] Rewritten v0.8 tests are listed under **Removed** and now pin the ruled behaviour, and each would fail on the old behaviour.

**F. Follow-ups**
- [ ] For a follow-up prompt (F1–F8), every item in its `docs/v08/conformance.md` row is done, or listed under **Hand-offs** for `15-conformance` with a reason.

**Verdict format** (unchanged)

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

| # | ID | Title | Source | Needs |
|---|---|---|---|---|
| 00 | `00-preflight` | Ratification map and v0.9 progress | Q1–Q9, F1–F9 | — |
| 01 | `01-estate-fees` | Estate gold fees leave the economy; no zero-valued forms | Q1, Q2 | 00 |
| 02 | `02-project-overlay` | Fixed-rate project overlay | Q3, F9 | 01 |
| 03 | `03-regression-precedence` | Regression beats a passed upgrade | Q5 | 02 |
| 04 | `04-market-rulings` | NO_DEMAND status; no self-matching | Q6, Q7 | 03 |
| 05 | `05-hp-regen-interval` | Interval hit-point regeneration; reachable defeat | Q8 | 04 |
| 06 | `06-combat-xp-bonuses` | XP bonuses on combat pools | Q9 | 05 |
| 07 | `07-operational-retention` | Allowance pruning and metric compaction | F1 | 06 |
| 08 | `08-key-history-retention` | Safe transition-history retention | F4 | 07 |
| 09 | `09-uniform-closed-form` | Closed-form uniform resolution | F3 | 08 |
| 10 | `10-lock-narrowing` | Narrow global locks with proof | F2 | 09 |
| 11 | `11-read-scale` | Map health, key-market scans, market retry | F7 | 10 |
| 12 | `12-content-lint-projections` | Content and lint helpers | F6 | 11 |
| 13 | `13-reset-migration-isolation` | Reset guard and migration isolation | F8 | 12 |
| 14 | `14-client-polish` | Client completion and polish | F5 | 13 |
| 15 | `15-conformance` | v0.9 conformance audit | all | 14 |

Rulings come first because they change gameplay that later follow-ups (closed-form resolution, lock narrowing) must preserve. Q4 ("Retain fields") needs no code; Prompt 00 records it and Prompt 15 closes it.
