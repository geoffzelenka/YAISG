---
name: prompt-pipeline
description: Run a YAISG versioned implementation pipeline (prompts/yaisg-vNN-prompts/) as Orchestrator — Codex implements each prompt, the orchestrator verifies on SQLite and PostgreSQL, a Claude reviewer approves, then merge and progress. Use when asked to run, resume or continue the v0.9 (or later) prompts.
---

# Prompt pipeline (Orchestrator)

This skill runs one prompt after another from `prompts/yaisg-<V>-prompts/`, following that set's README. The README defines the sequence, the CONTEXT list, the stop conditions, the definition of done and the reviewer checklist. Read it first; it overrides anything here that conflicts. CLAUDE.md's Orchestrator role and the user's memory rules also apply. The memory rules cover Codex sessions, review models by round, and pipeline practices.

## Setup (once per session)

```bash
export PIPELINE_VERSION=v09                          # the prompt set to run
export PIPELINE_WORK=<your scratchpad>/pipeline      # logs, prompts and Codex transcripts
export COAUTHOR_TRAILER="Co-Authored-By: ..."        # the attribution line from your system instructions
SK=.claude/skills/prompt-pipeline/scripts
```

Check that PostgreSQL is up: `docker ps | grep yaisg-pg16`. It is reachable at `postgresql+psycopg://yaisg:yaisg@localhost:5432`. The scripts only ever recreate `yaisg_test`, `yaisg_review_test` or `yaisg_*_dev`.

## Per prompt

1. **Branch:** `git switch main && git switch -c $PIPELINE_VERSION/<id>`.
2. **Build the Codex prompt:** run `$SK/mkprompt.sh <id>`, which prints the path to `prompt.md`. For a prompt that isn't under `prompts/`, use `$SK/mkprompt.sh <id> body.md`.
   - Then append an `===== ORCHESTRATOR NOTES =====` section to `prompt.md`. It carries human decisions for this prompt, which hand-offs are must-do versus optional, and anything the prompt needs that's only recorded in phase notes.
3. **Run Codex in a fresh session,** in the background:
   ```bash
   codex exec --sandbox workspace-write --json < $PIPELINE_WORK/<id>/prompt.md > $PIPELINE_WORK/<id>/codex-1.jsonl 2>&1
   ```
   - The thread id is on the first `thread.started` line. Keep it for review fixes.
   - On a usage-limit or capacity error, wait for the reset time it gives, then resume the same thread.
4. **Commit Codex's work.** Codex's `.git` is read-only, so the orchestrator commits:
   ```bash
   git add -A -- . ':!design/.the-vision.md.swp'
   ```
   The message says it was written by the Codex coding agent and committed by the orchestrator, and ends with the trailer. Never commit the swap file, and never commit untracked human work.
5. **Verify:** `$SK/verify.sh <id> v1`. Expect `sqlite=0 pg=0 pg_auth=0 reset_pg=0`, "No new upgrade operations detected." twice, and `boot=200`. Logs are in `$PIPELINE_WORK/<id>/`.
   - If something fails, send the failures back to Codex on the same thread before review. These pre-review fixes have their own counter and don't use review rounds.
6. **Review,** at most 3 rounds. For each round, copy `templates/review-brief.md` and fill it in. Use the `code-reviewer` agent; round 1 uses the default model, rounds 2–3 a fresh Sonnet reviewer. Give it:
   - the prompt and README paths;
   - the diff range;
   - the orchestrator's verification numbers;
   - human decisions and hand-offs it should check;
   - PostgreSQL `yaisg_review_test` and a scratch directory for mutation checks;
   - the instruction never to edit the repo.

   Rounds 2–3 also get the previous findings and rulings, and the fix commit's range. Rule on each finding. Copy `templates/fix-brief.md` to `$PIPELINE_WORK/<id>/fix-<N>.md`, fill in the valid findings, and send it with `codex exec resume <thread> --json "$(cat $PIPELINE_WORK/<id>/fix-<N>.md)"`, then commit and re-verify.
7. **Stop** on any condition in the README: ESCALATE, 3 rounds without APPROVE, red CI on main, a BLOCKER in preflight, or a "Ratification needed" item the next prompt depends on. Report it as `⚠️ NEEDS_HUMAN` and leave the branch as it is.
8. **Before merging,** append `## Orchestrator verification and review hand-offs` to `docs/phase-notes/<V>-<id>.md`. Record the verification numbers, each review round's verdict and the non-blocking hand-offs. Commit it.
9. **Merge:** `$SK/merge.sh <id> "<title>" "<one-line summary>"`. It merges with `--no-ff` and runs CI on main (SQLite, PG game, PG auth). Only if all are green does it update and commit the progress row. If it prints `CI RED ON MAIN`, stop.
10. Go on to the next prompt without asking. Finish with the summary table and the open questions for the human.

## Notes

- `docs/<V>/progress.md` rows must have the shape `| # | \`<id>\` | Title | Status | Branch | Merge | Summary |`, because `merge.sh` matches on the id column. The preflight prompt creates this file. Put the shape in its orchestrator notes.
- Codex can't reach PostgreSQL. Concurrency and locking tests it writes run only when you verify. Read the PG log, not just the exit code, when PG tests are new.
- Codex may need a temporary asyncio shim inside its sandbox. Your runs must not use one, and the repo must not depend on one.
- A reviewer that stops with background work still running may hold PostgreSQL locks. Stop it with TaskStop after its report arrives.
