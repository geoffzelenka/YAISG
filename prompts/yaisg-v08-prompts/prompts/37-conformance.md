## Prompt 37 — Final design conformance audit

**ID:** `37-conformance` · **Needs:** 36 · **Design:** all; §23.4, §28 · **Changes behaviour:** only to fix gaps

### Goal

Prove that the design is fully implemented, and fix what is not.

### Build

1. Walk the §28 traceability table and §2.1 R1–R17: for each row, cite the implementing code and the tests. Walk §23.4's list: every named test exists.
2. Walk §21 and §22: every table and endpoint exists with the stated status; every **REMOVE** is gone.
3. Collect every **Ratification needed** item from all v0.8 phase notes into one list for a human.
4. Write `docs/v08/conformance.md`. Fix small gaps with tests in this prompt; list larger ones as follow-up prompts.

### Review focus

The reviewer samples at least fifteen rows and opens the cited code and tests.
