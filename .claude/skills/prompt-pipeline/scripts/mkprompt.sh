#!/bin/bash
# usage: mkprompt.sh <prompt-id> [body.md]
# Writes $W/<id>/prompt.md: orchestrator environment notes, the pipeline README,
# then the prompt (prompts/yaisg-$V-prompts/prompts/<id>.md, or body.md for a
# prompt that lives outside prompts/). Append an "===== ORCHESTRATOR NOTES ====="
# section afterwards for prompt-specific hand-offs and human decisions.
source "$(dirname "$0")/common.sh"
set -e
ID=$1; BODY=${2:-$PROMPTS/prompts/$ID.md}
[ -f "$BODY" ] || { echo "no prompt at $BODY" >&2; exit 1; }
mkdir -p "$W/$ID"
BASE=$(git -C "$R" rev-parse --short HEAD)
{ cat <<HDR
You are the coding agent for prompt $ID of the YAISG $V pipeline.
Read AGENTS.md and CLAUDE.md first. The pipeline README (authority, conventions, definition of done, reviewer checklist) and the prompt follow below.
Before coding, read everything in the README's CONTEXT list, including every earlier phase note in docs/phase-notes/. Pick up every hand-off that names $ID.

ENVIRONMENT NOTES (from the orchestrator):
- You are on branch $V/$ID, created from main at $BASE.
- Use the repo virtualenv: prefix commands with \`PATH=\$PWD/.venv/bin:\$PATH\` (the shell's default python belongs to another project).
- Your sandbox cannot reach PostgreSQL and .git is read-only. Do not try to commit; leave all changes in the working tree. The orchestrator commits and runs the PostgreSQL 16 suites (\`TEST_DATABASE_URL=$PGB/yaisg_test\`). Write PG-only tests so they skip on SQLite, following the existing TEST_DATABASE_URL fixture pattern.
- Database-backed Hypothesis tests use deadline=None.
- Run \`PATH=\$PWD/.venv/bin:\$PATH make ci\` (SQLite) before finishing and make it green. If asyncio hangs in your sandbox, a temporary shim outside the repo is acceptable; nothing in the repo may depend on it.
- Do not edit design/design.md, design/the-vision.md, or anything under prompts/.
- Never touch, delete or commit design/.the-vision.md.swp (the human's editor swap file).
- No new dependencies unless the prompt names an approved one; if you add one, say so prominently in the final message (a human must approve it).
- Do not write commit status or "PostgreSQL pending" notes in the phase note; the orchestrator records verification. Write docs/phase-notes/$V-$ID.md with the exact README headings, and set the $ID row in docs/$V/progress.md to "ready for review".
- Final message: files changed, tests added (names), anything under Ratification needed, any new dependency, and anything you could not verify.

===== README =====
HDR
cat "$PROMPTS/README.md"; echo; echo "===== PROMPT ====="; cat "$BODY"; } > "$W/$ID/prompt.md"
echo "$W/$ID/prompt.md"
