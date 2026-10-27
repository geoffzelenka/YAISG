## Prompt 34 — Tutorial Island

**ID:** `34-tutorial` · **Workstream:** P · **Needs:** 33 · **Design:** §12.1 (instances), §20.2, §20.3, D7 · **Vision:** V§9.5.4, V§12.2

### Goal

Each new player gets two private, isolated realms that teach the loop, then leaves for the world with a raft and no gold.

### Build

1. **`POST /characters {name}`** (no realm): one transaction creates the character (0 gold, first `tutorial_step`), two isolated realm instances owned by the character from `tutorial.realm_1` and `tutorial.realm_2`, and a `progression.tutorial_camp_form` estate. The character starts in realm 1.
2. **Isolated realms**: no upkeep, no decay, no market, no caravans, no tax; skipped by the scheduled job; never in lists or the map. Map edges between the two tutorial templates resolve to the character's own instances; no edge leads to the world.
3. **`tutorial` pack**: realm templates, arrival realms, the raft-site project, and `steps [{id, hint, done_when}]` with the §20.3 condition kinds. `tutorial_step` advances lazily on profile resolve.
4. **Seed gold**: on first arrival in realm 2, grant gold equal to the raft-site kickoff cost (ledger `tutorial_seed`). The raft is a transform of the camp into the raft form.
5. **`POST /tutorial/depart {destination_realm_id}`**: requires the raft form, a full account (`ACCOUNT_REQUIRED`), a destination in `tutorial.arrival_realms`. Sets gold to zero (ledger any non-zero amount as `tutorial_destroy`), moves character and estate, deletes both instances and their treasuries (ledger `tutorial_destroy`), clears `tutorial_step`.
6. **Placeholder content** that completes the §20.2 run in a few cycles per step: gather, make clothes and a club, fight, make food, travel, kick off and fund the raft site, build the raft, depart.
7. **seed-check**: the arrival-realm funded-bid clause from Prompt 16 is now active and must pass.

### Tests

- End-to-end: a guest completes the island, is refused departure, upgrades, departs, arrives with 0 gold and a raft.
- No gold leaves the island: world gold before and after departure is equal, and the ledger nets to zero for the island.
- Two players' islands are independent (concurrent kickoffs both succeed).
- Isolated realms never appear in `/realms`, `/map`, the scheduler or caravans.

### Review focus

Zeroing the wallet is a guard; the mechanism is that gold spent on the island dies with its treasury (§20.2).

