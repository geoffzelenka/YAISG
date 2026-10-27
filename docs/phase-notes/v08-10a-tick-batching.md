## Built

- Added RealmTickContext as the shared preloaded state for ordered tick steps.
  The resolver loads the active project run after exact timed-event finalization,
  updates it in memory across catch-up, and flushes once after the tick loop.
  The caller still owns the transaction and realm lock; lock order is unchanged.
- Kept per-tick pure erode_project arithmetic, including cumulative rounding,
  grace boundaries, failure tick and failed_at. Timed events retain their
  existing exact-due-time processing and flushes outside the tick loop.
- Added test_realm_catchup_statement_bound for two ticks and full max_catchup,
  with an engine before_cursor_execute listener and a fixed ten-statement bound.
  Both cases exercise erosion and verify persisted progress and tick timestamps;
  the full catch-up also exercises failure. The fixture honors TEST_DATABASE_URL.
- Disabled Hypothesis deadlines for all three database-backed game properties:
  contribution conservation, split resolution and transition idempotence.
  Pure engine properties retain their existing settings. Existing assertions
  are unchanged; the timed-event test callback now accepts the shared context.

- Validation: full SQLite `PATH=$PWD/.venv/bin:$PATH make ci` passes
  (auth 15, game 299 with six database-specific skips, client 41), including
  formatting, lint, strict typing, build and migration/reset tests. Restoring
  the original resolver and steps makes the full-catch-up regression fail:
  205 SQL statements exceed the ten-statement bound. No assertions weakened.

## Removed

- Per-tick active_run query and per-tick resolver flush. Tick steps no longer
  receive a Session. No tests, APIs, schema fields or migrations removed.

## Design ambiguities resolved

- §3 / §14.5: the service context holds the loaded ORM run, whose tracked
  assignments are persisted in the final flush. Keeping the per-tick arithmetic
  avoids changing cumulative rounding; no closed-form optimization is needed.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 14-realm-tick: tick steps receive preloaded state through RealmTickContext
  and must not query per tick. Load new stores, estates and demand-line state
  once before the loop and write once after it. Extend
  test_realm_catchup_statement_bound when adding steps. Preserve exact build
  events created during catch-up and the existing isolated-realm exemptions.
- 15-decay: tick steps receive preloaded state through RealmTickContext and
  must not query per tick. Load new gauge, estate and tag state once before
  the loop and write once after it. Extend test_realm_catchup_statement_bound
  when adding steps; preserve D4 stamps and exact transition completion.

## New error codes

None. No dependencies added.
