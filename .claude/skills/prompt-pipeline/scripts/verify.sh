#!/bin/bash
# usage: verify.sh <prompt-id> [tag]
# Run on the prompt branch after committing Codex's work. Logs go to $W/<id>/<tag>-*.log.
# SQLite make ci; PostgreSQL game and auth suites on a fresh yaisg_test; PG
# db-reset of the dev databases; alembic check for both services; boot check.
source "$(dirname "$0")/common.sh"
ID=$1; T=${2:-v1}; L=$W/$ID/$T; mkdir -p "$W/$ID"; cd "$R"
rm -rf scripts/__pycache__
make ci > "$L-sqlite.log" 2>&1; echo sqlite=$?
pg_recreate yaisg_test
TEST_DATABASE_URL=$PGB/yaisg_test make game-ci > "$L-pg.log" 2>&1; echo pg=$?
pg_recreate yaisg_test
(cd services/auth && TEST_DATABASE_URL=$PGB/yaisg_test python -m pytest -q > "$L-pgauth.log" 2>&1; echo pg_auth=$?; tail -1 "$L-pgauth.log")
GAME_DATABASE_URL=$PGB/yaisg_game_dev AUTH_DATABASE_URL=$PGB/yaisg_auth_dev make db-reset > "$L-reset.log" 2>&1; echo reset_pg=$?
(cd services/game && GAME_DATABASE_URL=$PGB/yaisg_game_dev alembic check 2>&1 | tail -1)
(cd services/auth && AUTH_DATABASE_URL=$PGB/yaisg_auth_dev alembic check 2>&1 | tail -1)
grep -hE "^=+ .*(passed|failed|error)|Tests +[0-9]|FAILED" "$L-sqlite.log" "$L-pg.log" | head -12
(cd services/game && GAME_DATABASE_URL=$PGB/yaisg_game_dev timeout 8 uvicorn app.main:app --port 8767 > "$L-boot.log" 2>&1 &)
sleep 5
curl -s -o /dev/null -w "boot=%{http_code}\n" localhost:8767/content/manifest
rm -rf scripts/__pycache__
