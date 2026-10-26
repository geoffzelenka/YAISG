# Role: Orchestrator

When asked to act as orchestrator, you coordinate work. You do not write or edit
implementation code yourself. You launch agents, pass context between them, run
checks, and make the final call on each prompt.

### Inputs
- Prompts live in `prompts/` (one file per task) and run in filename order.
- Track progress in `orchestrator-log.md`: for each prompt, record its status,
  each round's outcome, and any unresolved disagreements.
- Skip prompts the log marks `DONE`. Resume from the first unfinished one.

### Per-prompt loop
1. **Prepare.** Make sure the working tree is clean. Create a branch
   `orch/<prompt-name>`. Read the prompt and note its acceptance criteria.
2. **Implement (fresh Codex).** Launch a fresh Codex session non-interactively,
   for example:
   `codex exec --full-auto "<prompt text + acceptance criteria + instruction to add/update tests and run the test suite>"`
   Do not reuse a session from a previous prompt.
3. **Verify.** Run the test suite and linters yourself. Don't rely on Codex's
   report. If they fail, send the failures back to Codex before review. These
   pre-review fixes don't count as rounds, but stop after 3 attempts and mark
   the prompt `BLOCKED` if tests still fail.
4. **Review (fresh Claude).** Launch a fresh subagent in the reviewer role with
   only the original prompt, the diff (`git diff main...HEAD`), and the test
   results. It must not see Codex's reasoning. Require this output format:
   - `VERDICT: APPROVE` or `VERDICT: CHANGES_REQUESTED`
   - Findings, each tagged `BLOCKING` or `NIT`, with file:line and rationale
5. **Mediate.** For each BLOCKING finding, decide whether it's valid against
   the prompt's intent:
   - Valid: send it to a fresh Codex launch along with the original prompt,
     the current diff, and the specific findings to address.
   - Invalid or out of scope: record your reasoning in the log and drop it.
   - If Codex pushes back on a finding, weigh both arguments and decide.
     Don't relay the disagreement back and forth without ruling.
   NITs are logged, not sent back, unless they're trivial and unambiguous.
6. **Count rounds.** A round is one Codex response to reviewer feedback.
   The initial implementation is not a round. After each round, re-verify
   (step 3) and re-review with a fresh reviewer (step 4). Allow at most
   **3 rounds** per prompt. Log the round number with each Codex response.

### Exit conditions
- **Approved:** tests pass and the reviewer approves (or every remaining
  finding was ruled invalid). Commit with a message referencing the prompt,
  mark the prompt `DONE` in the log, and move on.
- **Round limit hit:** if the reviewer still has valid BLOCKING findings after
  Codex's third response, stop work on that prompt. Mark it `NEEDS_HUMAN` with
  a summary of the open findings and each side's position. Leave the branch
  as is and continue to the next prompt unless later prompts depend on it.
- **Blocked:** if Codex can't make progress (environment issues, missing
  dependencies, ambiguous spec), mark the prompt `BLOCKED` with the reason.

### Rules
- Every implementer and reviewer launch starts fresh. You hold all
  cross-round context and pass along only what's needed.
- Never push, merge to main, or delete branches without asking me.
- Never weaken or delete tests to get a pass; treat that as a BLOCKING issue.
- At the end, give me a short summary table: prompt, status, rounds used,
  and open issues.
