## Prompt 10 — Narrow global locks with proof

**ID:** `10-lock-narrowing` · **Needs:** 09 · **Source:** F2 (v0.8 07, 20, 21, 23, 24 and 33 hand-offs) · **Design:** §23.1, §23.3

### Goal

Several v0.8 paths take all-realm or global locks conservatively: travel/map, market, availability, caravan, lifecycle and guest purge. Narrow each only where it can be proven safe, and keep the conservative lock elsewhere.

### Build

1. For each conservative lock, write down in the phase note:
   - which rows it actually reads and writes;
   - the full provenance of every value it depends on;
   - the narrower lock set that would be sufficient.
2. Narrow only those locks for which you can show complete dependencies, deterministic ordering consistent with §23.1, and empty-book serialization where the market needs it. Leave the rest as they are and say why.
3. Every narrowed path gets a PostgreSQL race test that fails under the old bug class (lost update, double spend or stale read) if the narrowed lock is removed.

### Tests

- One PostgreSQL concurrency test per narrowed path, with lock timeouts so a regression fails rather than hangs.
- The world conservation suite still passes with concurrent generated operations.

### Out of scope

Changing gameplay rules; narrowing a lock without a race test.

### Review focus

Narrowing a lock is a correctness change. Every narrowing needs proof and a test, and any doubt means keep the lock.
