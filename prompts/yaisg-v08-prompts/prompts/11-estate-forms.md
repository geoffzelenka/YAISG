## Prompt 11 — Estate forms, transforms, realm-owned estates

**ID:** `11-estate-forms` · **Workstream:** F · **Needs:** 10 · **Design:** §12.5 (weights), §13.1–13.3, §13.5 · **Vision:** V§8.1–8.5

### Goal

Reshape estates to mobile or fixed forms with an upgrade graph, and support estates owned by a realm.

### Build

1. **`estates`**: drop `level` and `upgrade_slots` (forms determine them); add `gauge`, `shed_progress`, `data` (`decay_stage` exists from 05). `owner_character_id IS NULL` means realm-owned.
2. **Form schema** (§13.2): `tier`, `build_cost {gold, goods}`, `requires_realm_tags`, `modifiers`, `cap_bonuses`, `tags`, `upgrade_slots`, `upkeep`, `production`, `transforms_to`, `regresses_to` (plus `mobility` and `travel_profile` from 07). Validator: a transform never changes mobility; `regresses_to` has the same mobility and a lower tier; `progression.basic_mobile_form` exists, is mobile, and has no upkeep or production.
3. **Transform** (§13.3) requires the owner to be in the estate's realm, pays the destination's `build_cost` via `pay_selector`, keeps all shipped codes. Upgrade install also requires presence.
4. **Build-cost gold destination.** The design does not say where estate build and transform gold goes. Credit the treasury of the estate's realm (consistent with D14 and the conservation pillar) and record it under **Ratification needed**.
5. **`vote_weight(estate)`** pure function: mobile 1; fixed tier *t* → 9 + *t*.
6. **Reads.** `GET /estates/me` reshaped (form, mobility, tier, slots, upgrades, tags, stage). `GET /realms/{id}/estates`: owner or "realm-owned", form, decay stage.
7. An invariant helper used in tests: every world character owns exactly one estate.

### Tests

- Transform: mobility guard; presence; `ESTATE_BUSY` during a relocate journey; `WOULD_ORPHAN_UPGRADES` unchanged.
- Weights for mobile and fixed tiers 1–3.
- Realm-owned estates listed; gold from a transform lands in the treasury.

### Out of scope

Build, buy, surrender, larder (12); production and upkeep (14).

### Review focus

No code assumes one estate per character beyond the endpoints (§13.1).

