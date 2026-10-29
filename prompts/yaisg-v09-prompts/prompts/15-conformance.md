## Prompt 15 — v0.9 conformance audit

**ID:** `15-conformance` · **Needs:** 14 · **Design:** all; §23.4, §28 · **Changes behaviour:** only to fix gaps

### Goal

Prove that design v0.8 plus the human rulings is fully implemented, and fix what is not.

### Build

1. Write `docs/v09/conformance.md`, starting from `docs/v08/conformance.md`:
   - Re-walk §28, §2.1 R1–R17, §21, §22 and §23.4, with current code and test citations.
   - Mark each row that a ruling changed with its Qn.
2. Add a **Rulings** section: for each of Q1–Q9, the implementing prompt, code and tests, or for Q4 "retained, no change".
3. Add a **Follow-ups** section: for each of F1–F9, done (with evidence) or still open (with a scoped next prompt).
4. Fix the v0.8 37 review documentation nits in the new report:
   - label `GET /admin/metrics` as "Extension (§23.6)";
   - `/players/me` is not a §22 endpoint;
   - give R8, R17, R10 and R11 distinct evidence, e.g. `test_remoteness_level_gates_direction_and_cheapest_path`, `test_remoteness_prefers_cheaper_two_hop_path` and `test_visitor_profile_excludes_estate_modifiers`.
5. Collect every **Ratification needed** item from all v0.9 phase notes into one list for a human.
6. Fix small gaps with tests in this prompt, and list larger ones as follow-up prompts.

### Review focus

The reviewer samples at least fifteen rows, including every ruling row, and opens the cited code and tests.
