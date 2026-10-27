## Prompt 20 — Trade between realms

**ID:** `20-caravans` · **Workstream:** L · **Needs:** 19 · **Design:** §16, D10 · **Vision:** V§9.4.1, V§9.4.7

### Goal

Let hungry realms buy from realms with excess through caravans that are always worse than a player hauler.

### Build

1. **Remoteness** (§16.2): all-pairs cheapest total `base_time_s` in hours over edges with `min_travel_level = 1`, computed once at boot from content.
2. **Access**: a realm takes part only while it holds an active tag with `effects.caravan_access`. Isolated realms never.
3. **The pass** every `caravan.pass_every_ticks` (*default* 6), run by the scheduled job and recorded in `world_state.last_caravan_pass`; never twice; missed passes are not replayed.
4. **Order and selection** exactly as §16.3: buyers by highest gauge then id; lines below reserve by largest draw by reference value; `need = reserve − stock − in_transit`; for each eligible seller the largest `q` satisfying every constraint (need, seller excess above its reserve, buyer treasury, the buyer's own bid integral for the delivered quantity, both realms' remaining `capacity_value_per_pass`); lowest delivered unit cost wins, ties to smaller remoteness.
5. **Costs**: goods cost from the seller's ask integral; fee `ceil(ref value of q × fee_pct_per_hour × remoteness / 100)` to the seller's treasury, less `fee_burn_pct` (ships 0; burns go to the ledger); loss `1 − Π(1 − edge loss)` with each edge's loss reduced by the summed `edge_loss_reduction_pct` of both adjoining realms' active tags, capped at 100%; delivered `floor(q × (1 − loss))`. Expected-value loss, no dice.
6. **Dispatch** in one transaction with both realms locked in id order; `realm_shipments`; `arrives_at = dispatched_at + remoteness × caravan.time_mult`; `in_transit` counted on the buyer's line; arrival credited at step 0 of the first tick at or after `arrives_at`.

### Tests

- Nothing is bought twice while in transit.
- At equal ask, the nearer seller wins; a caravan is never cheaper per delivered unit than the seller's ask.
- Loss with and without road tags; capacity limits respected.
- Missed passes not replayed; a pass is idempotent under two schedulers on PostgreSQL.
- Gold and goods conserved (goods lost on the road are the only goods leaving, and they are counted).

### Out of scope

Player cargo risk; mutable map state (§25).

### Review focus

Selection order is the vision's (largest draw, cheapest delivered, nearer), not v0.7's deficit weighting.

