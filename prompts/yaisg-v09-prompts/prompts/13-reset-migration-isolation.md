## Prompt 13 — Reset guard and migration isolation

**ID:** `13-reset-migration-isolation` · **Needs:** 12 · **Source:** F8 (v0.8 01 and 28 hand-offs) · **Design:** §3, §23.4

### Build

1. **Destructive reset guard.** Decide host identity by a clear policy for aliases and DNS names, not raw string matching, so `make db-reset` refuses any non-local host however it is spelled. Keep the database-name allowlist.
2. **Migration isolation.** The v0.8 stance migration imports the evolving application content loader. Make migrations self-contained: inline any constants they need, so future content changes can't break an old migration.
3. Audit every migration for imports from `app.`, except models needed for typing, and remove them.

### Tests

- The reset guard refuses non-local hosts in their alias forms and accepts the local ones.
- Every migration upgrades and downgrades from a fresh database with the content pack replaced by a minimal stub, proving migrations no longer depend on the content loader.
- Migration parity on both databases.

### Out of scope

Squashing migrations.

### Review focus

The guard fails closed.
