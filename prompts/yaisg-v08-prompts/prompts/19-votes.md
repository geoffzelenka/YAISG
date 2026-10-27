## Prompt 19 — Realm upgrade votes and transitions

**ID:** `19-votes` · **Workstream:** K · **Needs:** 18 · **Design:** §12.5, §12.6, D5, D6 · **Vision:** V§7.7.2

### Goal

Let residents call and decide realm upgrades by a weighted, secret ballot.

### Build

1. **Tables** `realm_votes`, `realm_vote_eligibility` (§12.5).
2. **`POST /realms/{id}/upgrades/{upgrade_id}/call`**: caller is a resident (presence not required); realm holds every required tag; no active project run; no open vote; no pending transition; `vote_cooldown_until` passed. Caller pays `fee_gold` to the treasury at once, never refunded. Choose and record codes.
3. **Eligibility snapshot** at the call: every resident at that moment with Prompt 11's weight. Later arrivals cannot vote; leavers keep their vote.
4. **`POST /realms/{id}/vote {choice}`**: one vote per eligible character, no changes. Adds weight to `yes_weight` or `no_weight` and sets `voted_at`. The choice is stored nowhere against the character: not in a column, a log line, the reward feed or request logs.
5. **`GET /realms/{id}/vote`**: participation (who has voted) is public; totals only after close.
6. **Close** in `resolve_realm`'s timed-event pass at `closes_at` (`vote.duration_hours`, *default* 72) or as soon as every eligible character has voted. Pass iff `yes_weight > no_weight` (D5) → `start_transition(…, "upgrade")`. Fail → `vote_cooldown_until = now + vote.fail_cooldown_hours` (*default* 72).
7. **Wire D6 both ways**: Prompt 10's `REALM_VOTING` check is now real.

### Tests

- Tie fails; no votes fails; one "no" with everyone else abstaining fails; weights sum correctly.
- Snapshot excludes later arrivals and keeps leavers.
- Secrecy: inspect the schema and captured logs for any record linking a character to a choice.
- Early close; cooldown; fee kept on failure.
- No kickoff while a vote is open; no call while a run is active.
- A passed vote's transition raises reserves (from 13) and completes through `finalize_realm`.

### Out of scope

Key deprecation (31).

### Review focus

Secrecy is structural, not a filter on reads.

