Prompt 3.1 — Engine core: lazy resolution loop (test-first)

Implement the pure engine at the heart of the game, per §4 and §7. No API endpoints, no SQLAlchemy imports in engine/ — pure functions + dataclasses only. Write tests before implementation where practical; this prompt is judged primarily on its test suite.

Engine API to implement (in services/game/app/engine/):

Value types: CharacterState (skills xp/levels, inventory as dict, gold, realm id, installed upgrades, caps), ActiveAction (action id, started_at, last_resolved_at), ResolveResult (cycles completed, xp gained per skill, items consumed, items gained, level-ups, stop_reason: None | 'inputs_exhausted' | 'offline_cap' | 'inventory_full').
effective_cycle_time(action, state, content) -> int and effective_xp(...), effective_drops(...): apply modifier stacking per §7 — sum all cycle_time_pct/xp_pct/extra_drop_chance_pct from realm + realm tier + installed (non-inert) estate upgrades, additive within type, applied once. Inert upgrade rule per §7 (realm_tags mismatch → contributes nothing).
resolve(state, active, content, now, rng) -> (state', active', ResolveResult) implementing §4.2 exactly:
Full cycles only; preserve partial-cycle remainder in last_resolved_at.
Cap cycles by: remaining offline budget (from offline_hours cap, measured against elapsed since last_resolved_at), input availability, and inventory capacity (inventory_slots cap counts distinct stacks; overflow rule per §7.1 v1: drops beyond capacity are discarded and recorded in the result as overflowed_items — consuming inputs may free slots, account for ordering per cycle).
Consume inputs and roll drops per cycle via the injected rng (interface: rng.random() -> float, rng.randint(a,b)); grant xp; recompute levels; if a level-up occurs, recompute effective values from the next cycle onward (segmented resolution per §4.2's note — implement the segmented version, not the snapshot simplification, since we're doing it test-first anyway).
A stop_reason other than None means the action ends; active' is None.
can_start(action_id, state, content) -> Ok | ErrorCode checking level, realm tags, and inputs for at least one cycle (INSUFFICIENT_LEVEL, WRONG_REALM, MISSING_INPUTS).
resolve_caps(state, content) -> Caps — base caps + cap_bonuses from installed upgrades and realm tier (§7.1).

Required tests (pytest + hypothesis):

Exact-cycle and partial-cycle timestamp math (property: repeated resolve with increasing now is equivalent to one big resolve — idempotence/associativity from §8.4).
Offline cap: 13h elapsed with 12h cap → exactly 12h of cycles, correct stop_reason, and last_resolved_at advanced only by resolved cycles.
Input exhaustion mid-batch; inventory overflow with the discard rule; interaction of the two.
Level-up mid-batch changes subsequent cycle output (construct content where level affects an effective value via a level-gated modifier or verify xp accrual boundary behavior — at minimum, verify segmentation produces different results than naive whole-batch math in a crafted case).
Modifier stacking: additive within type, multiple sources, inert-upgrade exclusion.
Drop statistics: with a seeded RNG over 10k cycles, observed drop frequency within tolerance of chance.
Conservation property: for input-consuming actions, consumed inputs per recipe × cycles exact.

Out of scope: persistence, HTTP, combat cycle logic (framework must not preclude it — the per-cycle reward step should be a strategy function so Phase 6 can swap in a combat resolver).

