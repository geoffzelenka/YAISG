## Prompt 11 — Map health, key-market scans, market retry

**ID:** `11-read-scale` · **Needs:** 10 · **Source:** F7 (v0.8 22 and 32 hand-offs) · **Design:** §15.5, §19.5, §22

### Build

1. **Map health.** A batched world-health read with a server-computed `below_reserve`, replacing client per-realm fan-out. Update the client.
2. **Key-market browse.** Define a scan cap and cursor policy for sparse filters, so one browse request is bounded however selective the filter. Return a cursor when the cap stops the scan before a page fills.
3. **Transition-due buy and `MARKET_RETRY`.** Specify and implement the transaction and idempotency rules: commit the due transition before returning the error, and make an automatic client retry safe (a buy repeats at most once, with the optional `price_gold` guard). Record the rules in the phase note.
4. Durable key-sale history stays out of scope (separate schema work).

### Tests

- The batched health response matches per-realm reads, and the query count is bounded and independent of realm count beyond one set-based query.
- A sparse key-market filter is bounded per request and pages to completion.
- `MARKET_RETRY`: the retry succeeds or fails cleanly without a double purchase. Concurrency on PostgreSQL.
- Client tests for the health view and the automatic retry.

### Out of scope

Key-sale history; treasury visibility (Q4: fields retained).

### Review focus

The treasury balance is never exposed (§15.5). Retry idempotency.
