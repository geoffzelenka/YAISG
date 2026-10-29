#!/bin/bash
# usage: merge.sh <prompt-id> "<title>" "<one-line progress summary>"
# Merges $V/<id> into main with --no-ff, runs CI on main (SQLite, PG game, PG
# auth), and only if all are green updates the <id> row of docs/$V/progress.md
# and commits it. Exits 1 with "CI RED ON MAIN" otherwise (a stop condition).
source "$(dirname "$0")/common.sh"
set -e
ID=$1; TITLE=$2; SUM=$3; mkdir -p "$W/$ID"; cd "$R"
git switch -q main
git merge -q --no-ff "$V/$ID" -m "Merge $V/$ID: $TITLE$(trailer)"
M=$(git rev-parse --short HEAD); echo merged=$M
set +e
make ci > "$W/$ID/m-sqlite.log" 2>&1; RS=$?; echo sqlite=$RS
pg_recreate yaisg_test
TEST_DATABASE_URL=$PGB/yaisg_test make game-ci > "$W/$ID/m-pg.log" 2>&1; RP=$?; echo pg=$RP
pg_recreate yaisg_test
(cd services/auth && TEST_DATABASE_URL=$PGB/yaisg_test python -m pytest -q > "$W/$ID/m-pgauth.log" 2>&1); RA=$?; echo pg_auth=$RA
grep -hE "^=+ .*(passed|failed)|Tests +[0-9]" "$W/$ID/m-sqlite.log" "$W/$ID/m-pg.log" "$W/$ID/m-pgauth.log"
[ $RS -eq 0 ] && [ $RP -eq 0 ] && [ $RA -eq 0 ] || { echo "CI RED ON MAIN"; exit 1; }
set -e
python3 - "$PROGRESS" "$ID" "$V/$ID" "$M" "$SUM" <<'PY'
import sys
path, pid, branch, merge, summary = sys.argv[1:]
lines = open(path).read().split("\n")
for i, line in enumerate(lines):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) >= 7 and cells[1].strip("`") == pid:
        cells[3:7] = ["done", branch, merge, summary]
        lines[i] = "| " + " | ".join(cells) + " |"
        break
else:
    sys.exit(f"no row for {pid} in {path}")
open(path, "w").write("\n".join(lines))
PY
git commit -q -am "Mark $ID done in $V progress$(trailer)"
echo progress=$(git rev-parse --short HEAD)
