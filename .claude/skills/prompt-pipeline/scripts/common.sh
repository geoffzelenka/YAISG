# Shared settings for the prompt-pipeline scripts. Source, don't run.
# Required: PIPELINE_VERSION (e.g. v09). Optional: PIPELINE_WORK (default
# /tmp/yaisg-pipeline-$PIPELINE_VERSION), COAUTHOR_TRAILER (full
# "Co-Authored-By: ..." line appended to commits this tooling makes).
set -u
: "${PIPELINE_VERSION:?set PIPELINE_VERSION, e.g. v09}"
V=$PIPELINE_VERSION
R=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
W=${PIPELINE_WORK:-/tmp/yaisg-pipeline-$V}
PROMPTS=$R/prompts/yaisg-$V-prompts
PROGRESS=$R/docs/$V/progress.md
PGB=postgresql+psycopg://yaisg:yaisg@localhost:5432
PG_CONTAINER=${PG_CONTAINER:-yaisg-pg16}
export PATH=$R/.venv/bin:$PATH
trailer() { [ -n "${COAUTHOR_TRAILER:-}" ] && printf '\n\n%s' "$COAUTHOR_TRAILER"; return 0; }
# Recreate a disposable PostgreSQL database; refuses anything off the allowlist.
pg_recreate() {
  case "$1" in yaisg_test|yaisg_review_test|yaisg_*_dev) ;; *) echo "refusing to reset $1" >&2; return 1;; esac
  docker exec "$PG_CONTAINER" psql -U yaisg -d postgres -qc "DROP DATABASE IF EXISTS $1" -c "CREATE DATABASE $1" >/dev/null
}
