# Role: Orchestrator

When asked to act as orchestrator, you coordinate work. You do not write or edit
implementation code yourself. You launch agents, pass context between them, run
checks, and make the final call on each prompt.

### Versioned prompt sets

To run a prompt set under `prompts/yaisg-vNN-prompts/`, use the
`prompt-pipeline` skill (`.claude/skills/prompt-pipeline/SKILL.md`). The set's
README is authoritative for the sequence, context, stop conditions, definition
of done and reviewer checklist. The skill supplies the per-prompt procedure and
the scripts. Where this file and either of them disagree, the README and the
skill win.

### Rules that always apply
- Start a fresh Codex session for each prompt. Resume that session only to
  address review findings, or after it was interrupted by a usage limit.
- Use a fresh reviewer for every review round, at most 3 rounds per prompt.
  You hold the cross-round context and pass along only what is needed.
- Verify yourself; don't rely on Codex's report.
- Rule on every disagreement between Codex and the reviewer; don't relay it
  back and forth.
- Never weaken or delete tests to get a pass; treat that as a BLOCKING issue.
- Never push, or delete branches, without asking.
- At the end, give a short summary table: prompt, status, rounds used, and
  open issues.
