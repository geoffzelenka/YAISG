Prompt 4.2 — Estate endpoints: upgrades and transformation

Expose the estate over HTTP per §5.6 and §7.3. Structures from 4.1 are complete.

Requirements:

GET /estates/me — the character's home estate: id, form (id + resolved content summary), realm_id, level, status, upgrade_slots (resolved cap, §7.1), installed upgrades (slot_index, upgrade id, name, active|inert with the inert reason), and pending-relocation fields (always null until 4.3).
POST /estates/me/upgrades/{upgrade_id} — purchase per §5.6:
Resolve the character first (§4.2 rule: every mutating endpoint resolves).
Validate: upgrade exists (UNKNOWN_UPGRADE), a free slot exists under the resolved estate_upgrade_slots cap (NO_FREE_SLOT), not already installed (ALREADY_INSTALLED), inputs affordable (MISSING_INPUTS — reuse the engine's input-check semantics; costs are items and consumed from inventory).
Install into the lowest free slot_index; one transaction; concurrent double-purchase of the last slot must yield exactly one install (row-lock the estate; same dialect-guarded pattern as resolve_character).
Response: updated estate payload. If the upgrade grants cap bonuses or modifiers, subsequent resolves must reflect them (no caching bugs — effective values are computed per resolve, §4.2).
POST /estates/me/transform {form_id} — per §7.3:
Validate: a transformation edge exists from the current form to form_id (INVALID_TRANSFORMATION), costs affordable (MISSING_INPUTS), estate status is active (ESTATE_BUSY otherwise — future-proofing for relocation/decay states).
Charge cost, update form_id, re-evaluate installed upgrades' inert status against the new form/realm (per §7.3's note that inertness may consider form), one transaction.
Transformation does not change level, slots contents, or realm. If the new form's base caps shrink estate_upgrade_slots below the number of installed upgrades, reject with WOULD_ORPHAN_UPGRADES (v1 rule — simplest safe behavior; note for design ratification).
Both mutations append a structured audit line (existing JSON logging) with character id, estate id, and the change — cheap provenance until real audit needs arrive.

Tests (integration): estate payload shape and inert annotation; upgrade happy path including effective-value change visible in a subsequent action resolve; every error code; last-slot concurrency (two sessions); transform happy path camp→homestead including cost consumption; transform with shrinking slots rejected; ESTATE_BUSY (simulate by setting a non-active status directly).

Out of scope: relocation (4.3), any client work (4.4), transfer/escheat, second estates.
