## Prompt 00 — Ratification map and v0.9 progress

**ID:** `00-preflight` · **Needs:** — · **Source:** Q1–Q9, F1–F9 · **Changes behaviour:** no (one approved dependency fix)

### Goal

Give every later prompt and reviewer one map from each human ruling to the design text it supersedes, and to the code and tests that pin the old behaviour today.

### Build

1. Write `docs/v09/ratification-map.md`. For each of Q1–Q9 in `docs/v08/human_ratifications.md`:
   - the ruling, quoted exactly;
   - the design §§ and vision §§ it supersedes or refines, quoting the affected sentence;
   - the code sites that implement the old behaviour (`file:line`) and the tests that pin it (test names);
   - the v0.9 prompt that implements it (Q4 needs no code: record "Retain fields" as closing the question, with no prompt);
   - the reading the target prompt names, and any ambiguity you see in the ruling's wording.
2. Write the same map for F1–F9 from `docs/v08/conformance.md`: the row, the phase-note hand-offs it collects, and the v0.9 prompt that takes it.
3. Create `docs/v09/progress.md` with one row per prompt in the README §5 sequence (status `pending`).
4. **Approved dependency (human, 2026-10-28):** add `psycopg[binary]>=3.2,<4` to `services/auth/pyproject.toml`, the same driver and range the game service uses. The GitHub `auth (postgres)` job and the auth Docker image install only the auth service, so without it a `postgresql+psycopg://` URL can't import its driver (v0.8 38 review). Check by installing only `services/auth[dev]` into a fresh virtualenv and importing psycopg.
5. Audit that `main` is green on both databases and that `docs/v08/conformance.md` is current. Record any finding that would block a ruling prompt as `BLOCKER`.

### Tests

None new. `make ci` stays green, and the auth suite passes on PostgreSQL from an auth-only install.

### Out of scope

Any behaviour change.

### Review focus

Sample at least five `file:line` and test citations per ruling and open them. Check that every ruling's superseded § is really the text that conflicts with it.
