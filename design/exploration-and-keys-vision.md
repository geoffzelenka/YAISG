# Yet Another Idle Skilling Game — Exploration and Keys Vision Document

**Version:** 0.1 (first structured draft; refined from the rough draft through design-chat review)
**Scope:** The exploration skill and the key system — discovery mechanics, the key as an instanced item, the instanced-item architecture itself (a commodity/unique split this document introduces on behalf of the whole game), key trading via unique-item listings, combat-key reconciliation, and hidden-realm unlocks as recorded direction. This document supersedes `exploration-and-keys-vision-TODO.md`, which is retired.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't yet support, that is a design-doc work item (§8), not a license to improvise. Siblings: **Skills and Goods** (owns exploration's economic frame: the producer of access, §4.1 there), **Market Vision** (owns the order book this document's keys explicitly *cannot* use, and the escrow/collection patterns its listings reuse), **Combat Vision** (whose §7.2 deferred key ownership here — this document now pays that bill and patches it), **Realm & World Vision** (the realms keys are scoped to). The planned **XP Curve** vision owns exploration's leveling numbers.

**Changes from the rough draft:** Realm-wide bonus discoveries (access type 1) **cut** from v1 (§7.1 — offline-resolution complexity; recorded as deferred, not rejected). The key ratified as a fully self-contained instanced item — the key *is* the node; yield lives on the key, and multiple keys from one discovery are independent (§3.2). The instanced-item architecture designed: a commodity/instance table split with a shared item-template namespace (§4). Combat keys walked back from permanent to session-scoped and unified into this item family (§5, patching combat-vision §7.2). Hidden-realm unlocks scoped as content-authored reveals, recorded as direction, deferred (§7.2). Key trading committed to v1 via a fixed-price unique-item listing surface, searchable by realm and resource type (§6). Notoriety settled as flavor carried by artifacts, not a mechanic (§2.4). Exploration availability settled as ordinary tag-gated content with no visiting dependency (§2.2).

---

## 1. The elevator pitch

Exploration turns **time and long, patient cycles into access itself**: keys to resources that don't otherwise exist. A discovery conjures a new lode, a hidden grove, a monster-infested cave — embodied in a **key**, an instanced artifact that carries its discoverer's name forever, holds its own finite yield, and can be sold on a dedicated market before its first use binds it to a holder.

Exploration is the game's prestige skill: cycles are far longer than other skills, discoveries are rare, and leveling is deliberately slow. Its notoriety is not a mechanic but a consequence — the explorer's name travels on every key they sell and every trophy on a mantel. Economically, exploration is the **renewable-demand loop for access**: keys deplete, so exploration never saturates, the same way upkeep keeps goods demand perpetual. The explorer's product is literally purchasable access — the cleanest realization of the adventurer who feeds the settled world.

---

## 2. The exploration skill

### 2.1 The action loop

Exploration actions run under the existing cycle framework: repeated search cycles with a discovery drop table. Two properties distinguish them, both content knobs rather than engine changes:

- **Cycles are much longer than other skills'** — exploration is measured in expeditions, not swings of a pickaxe.
- **Discoveries are rare** — most cycles yield only xp (and perhaps minor incidental drops); the discovery itself is a low-chance roll.

**Optional boost consumables:** exploration actions may accept optional inputs (supplies, charts, lures) that improve discovery chance or shape the loot table. This is a small new engine wrinkle — today's input machinery is mandatory-inputs-only — recorded in §8.

### 2.2 Availability and gating

- **Where:** exploration happens in any realm whose content offers exploration actions — ordinary tag-gated availability, exactly like every other skill. No visiting dependency: under the interim presence rule you explore the realm you live in, and the frontier-ranging fantasy strengthens automatically when visiting ships. Nothing here blocks on it.
- **Gates:** exploration actions carry small **cross-skill level requirements** — gathering and combat skill minimums (you must be able to survive and recognize what you find). A new gate type for the engine (§8), deliberately small.
- **Tier interaction:** higher tiers of the player's gathering and combat skills **adjust the discovery loot table** — a master miner notices what a novice walks past. Shape and numbers are content design over the drop-table machinery.

### 2.3 Discoverable resources: the authored generative space

Discoveries are **generative in play, authored in content** — preserving the content-is-data pillar. A new content type, the **discoverable resource template**, defines the generative space: resource kind, yield range, key-count range, eligible realm tags, flavor. A successful discovery **instantiates a template with rolled parameters** — the engine never invents content; it rolls within spaces the designer authored.

The number of keys generated per discovery is rolled from the template (potentially skewed by the discoverer's skills). Because yield lives on each key (§3.2), key count × yield roll is the content designer's direct handle on a discovery's total economic value.

### 2.4 Prestige without a mechanic

Exploration's notoriety is **flavor delivered through artifacts, not a reputation system**. The discoverer's name is denormalized onto every key (§3.3) — on the listing when it sells, in the tooltip forever after, on the trophy it becomes when depleted. Realm announcements ("Alice discovered the Deepvein Motherlode") are presentation-layer. Nothing to build, nothing to balance; being well-known is a consequence of doing famous things.

---

## 3. Keys

### 3.1 What a key grants

A key grants its holder access to actions on a discovered resource that does not otherwise exist in the realm: gathering cycles on a rare lode, or combat sessions in a discovered location. Access is **private to the key-holder** — a key is a claim, not a civic gift. (The civic variant — realm-wide bonuses — is deferred, §7.1.)

### 3.2 The key *is* the node

There is no separate node entity behind a key. Each key is **fully self-contained**: it stores the resource definition (rolled from the template) and its own **remaining yield**. Consequences, all intended:

- **Multiple keys from one discovery are independent.** They share flavor and provenance, but each carries its own budget. A discovery yielding three 500-cycle keys has authored 1,500 cycles of total access into the world.
- **A key's value is readable.** Remaining yield is inspectable — on a listing, before purchase. No caveat-emptor problem where a buyer's key was secretly mined out by someone else.
- **Depletion is local arithmetic.** Each gated cycle decrements the key's own counter; no shared-pool coordination, no cross-character contention on a node row.

### 3.3 Key lifecycle

1. **Created** by a discovery roll (or combat drop, §5): an item instance (§4) with provenance `{discoverer id + denormalized name, discovered_at, realm_id}` and state `{resource, remaining_yield}`. Denormalizing the name means the trophy never dangles if characters are ever renamed or deleted — the same durable-history pattern as `market_matches`.
2. **Tradeable while unused.** An unused key may be listed on the unique-item market (§6) any number of times.
3. **Bound on first use.** *First use* is precisely: **starting an action gated by the key.** Not acquisition, not inspection. The bound flag is set in the same transaction that starts the action, and it is one-way. A bound key is untradeable forever.
4. **Depleted** when its yield reaches zero (gathering) or its session ends (combat, §5). A depleted key **remains in inventory as a trophy** until the player explicitly discards it. Trophies occupy an inventory slot like any distinct item — keeping the mantel costs shelf space, which is a real and intended choice.

### 3.4 Realm change deactivates keys — with one grace

Keys are scoped to the realm they were discovered in. When that realm's development node transitions (morphing or regression), **the realm's keys are marked depleted** — access is realm-state-scoped, never permanent, in deliberate compliance with design.md §10.

**The grace rule:** a key whose owner has an active action currently running against it survives the transition; the key dies when that action stops *for any reason* (completion, exhaustion, the player stopping it, relocation). This slots into the existing `finalize_realm` transition machinery.

---

## 4. Instanced items: the commodity/unique split

Keys are the game's first **non-fungible items**, and they force an architecture decision this document makes on behalf of the whole game (discharging combat-vision §9.9's watch item — the future enchanting system's rolled-stat gear lands on this same table).

### 4.1 Two tables, one item concept

The commodity path is untouched: `inventories(character_id, item_id, quantity)` — fungible, stackable, order-book-tradeable, the hot path every resolve and conservation test sweeps. Alongside it, an **item instance** table: per-row identity, an owning character (nullable, for listing escrow and system ownership — the NPC-estate precedent), a one-way bound flag, denormalized provenance, and a state payload (remaining yield for keys; rolled stats for future gear).

**Instances are still items.** Every instance references a content item template carrying name, tags, tier, and icon like any other item. The template schema gains one flag: `instanced: true`.

### 4.2 The separation rule

**An instanced item may never appear in a quantity-bearing context** — no stacking, no commodity drop-table slots, no order book. Content validation enforces this at boot: an instanced item_id in a commodity context is a load error. The two worlds cannot bleed into each other by accident.

Why a split rather than one unified table: commodities are the hot path — resolves, conservation sweeps, the matcher's index. Instances are rare, cold, and stateful. Taxing every quantity row with nullable instance columns (or exploding to row-per-unit) would burden the 99% case for the 1%. Two tables with a shared template namespace give each its natural shape.

### 4.3 Inventory rule

**Each item instance occupies one inventory slot**, same as a distinct commodity stack — one rule for "distinct thing = one slot." Keys as physical cargo also future-proofs the carried/stored split (design.md §13.7): a key is carried like anything else.

---

## 5. Combat keys — unified (patches Combat Vision §7.2)

Combat vision §7.2 deferred key ownership here; ratified reconciliation:

- **Permanent combat keys are walked back.** Combat vision's "permanent keys as the safe v1 subset" is superseded — there are no permanent keys. All keys expire.
- **Combat keys are the same item family.** Same instance table, same provenance and discoverer tag, same trade-then-bind lifecycle, same realm-change deactivation and grace rule. Whether a combat key arrives from an exploration discovery or a monster drop table, the item is identical.
- **Session-scoped depletion:** a combat key persists while its holder's combat session at the keyed location runs, and depletes when that session ends — the key's state holds a session marker rather than a yield counter. This is severe by design; **drop rates are the tuning knob**, not the expiry rule. A rarer key that grants one full overnight session is a legible, tunable prize.
- **Loot-table keys keep their discoverer tag** — the character whose kill dropped the key is its "discoverer." Combat is a second faucet into the same key economy, exactly as combat's economic-role table already promised ("keys to further combat/gathering access" on the feeds side).

### 5.1 The two expiry models, named

The system deliberately ships both expiry shapes the TODO asked about: **exhaustion-based** (gathering keys: N cycles) and **session-based** (combat keys: one engagement). Pure wall-clock time expiry is used by neither — avoiding the offline-math wrinkle that got type 1 cut (§7.1). Every key's remaining life is a function of *use*, which lazy resolution handles natively.

---

## 6. Trading keys: the unique-item market

Keys cannot trade on the global order book — matching is per `item_id` in quantity, and every key is distinct. Rather than amputate the explorer's sellable product (half the economic point), v1 ships a **minimal unique-item listing surface**:

- **Fixed-price, buyout-only.** No matching engine, no partial fills, no bids. The instance is escrowed into the listing at creation (owner set to system — the nullable-owner pattern); purchase transfers it and pays the seller; cancellation returns it.
- **Tax and slots reuse the established machinery.** Sales pay the flat global tax to the hosting realm, same as book matches. Listings occupy the seller's `order_slots` cap — market presence stays one bounded resource across both surfaces.
- **Browsable and searchable** by realm and resource type — "show me keys in realm Y for woodcutting" — with each listing displaying provenance (discoverer name), resource, and **remaining yield**. The listing browser *is* the map-seller's storefront: an explorer's reputation is literally visible in the market.
- **Only unused keys may be listed** (binding is checked at listing creation; bound or depleted keys are refused).

Conservation extends naturally: an instance is at all times in exactly one of — a character's inventory, listing escrow, or (as a trophy) inventory-depleted state. Same property-test discipline as the gold/goods invariant.

---

## 7. Deferred, with reasons

### 7.1 Realm-wide bonus discoveries — cut from v1

The rough draft's access type 1 (a discovery granting a limited-time realm-wide gathering bonus) is **cut**. Reason, recorded so the door stays open honestly: a realm-scoped modifier expiring by wall-clock creates a **global time boundary that every affected character's lazy resolve must segment at** — resolvable in principle (the engine already segments at level-ups) but it makes one character's offline math a function of realm-history-over-time, a real complexity step and an offline-gains tuning hazard. If it returns, it returns as its own decision with that cost priced in. Its loss also unifies the design: **every discovery outcome is a key** — one concept, no special cases.

### 7.2 Hidden-realm unlocks — direction, not v1

"Alice discovered a mountain pass to a new realm" is ratified as **direction**: realms cannot be generated (they are authored content with map positions, development graphs, and edge costs), so the mechanism is **content-authored realms that ship dormant/hidden, with exploration as the reveal** — a content-defined edge or realm flipping live, credited to a discoverer. This makes world growth a content-update-plus-exploration event, which is exactly the right shape. It is world-content machinery (dormant realms, map reveal, announcements), not key machinery, and is **explicitly non-blocking** for everything above. Deferred to content design plus a small design-doc work item when scheduled.

---

## 8. The economic-role test

| | Eats | Feeds |
|---|---|---|
| **Exploration** | time (long cycles), optional boost consumables (manufacturing/alchemy demand), gathering + combat skill investment (gates) | keys — access to rare gathering and combat content; listings on the unique-item market (tax revenue to realms); trophies; xp |

The renewable-demand property holds by construction: every key depletes, so access must be perpetually re-discovered — exploration never saturates. And because keys are tradeable before binding, exploration feeds *other players'* gameplay, not just the explorer's own: the §6 test passes on both sides of the market.

---

## 9. What this changes in the design doc (work items, not yet decisions)

Roughly in order of when they bite:

1. **Item instances** — the instance table (identity, nullable owner, one-way bound flag, denormalized provenance, state JSON), the `instanced: true` template flag, boot-time validation of the separation rule (§4.2), and the one-instance-one-slot inventory rule. *The load-bearing item; shared with future enchanting (discharges combat-vision §9.9).*
2. **Discoverable resource templates** — new content type: the authored generative space (resource kind, yield range, key-count range, eligible realm tags, flavor) and the discovery roll that instantiates it. Extends design.md §13.8 from "watch item" to a concrete shape.
3. **Key-gated actions** — actions whose availability requires a specific held instance; per-cycle yield decrement on the key; depletion as a stop reason; the binding transaction on action start (§3.3).
4. **Realm-transition key sweep** — mark realm's keys depleted on node transition, with the active-action grace rule (§3.4); extends the existing `finalize_realm` machinery.
5. **Unique-item listings** — escrow via nullable instance owner, fixed-price purchase, tax-to-hosting-realm at sale, `order_slots` shared cap, search by realm/resource type, instance conservation property tests (§6).
6. **Cross-skill level gates on actions** — small extension to `can_start` (§2.2).
7. **Optional chance-modifying inputs** — optional per-cycle consumables that adjust the drop table rather than gate the action (§2.1); a small but genuinely new input semantic.
8. **Combat-vision patch** — §7.2 rewritten per §5 here: no permanent keys, session-scoped expiry, unified item family. (Combat content may not ship permanent keys in the interim; the safe subset is now *no* keys until this lands.)
9. **Watch item — dormant realms/edges** for hidden-realm reveals (§7.2); build nothing that assumes all authored realms are live at boot.

**Sequencing:** items 1–2 are prerequisites for everything else; item 5 ships with exploration v1 (ratified: if exploration is in, key trading is in); item 8 is a documentation patch that should land immediately.

---

## 10. Open questions

1. **Exploration cycle lengths and discovery rates.** How long is an expedition, how rare a find? Content design, with the XP Curve vision owning the leveling pace that makes exploration "significantly slower."
2. **Gate levels.** Which gathering/combat levels gate which exploration actions, and how do tiers skew the loot table (§2.2–2.3)? Content design.
3. **Key-count and yield ranges per template.** The total-access-value knob (§2.3). Content/balance.
4. **Boost consumable design.** What the optional inputs are and how much they help (§2.1). Content design over work item #7.
5. **Combat-key drop rates.** The severity-tuning knob for session-scoped keys (§5). Content/balance.
6. **Listing durations and defaults.** Do unique-item listings expire like book orders (presumably yes, same job, same collectable pattern)? Default durations? Small design-doc surface within work item #5.
7. **Trophy presentation.** Depleted keys sit in inventory (§3.3) — is there ever a dedicated trophy display (estate shelf?), and does that interact with estate storage designs? Deferred to estate-storage/QoL territory; nothing blocks on it.
8. **Hidden-realm reveal mechanics.** The full shape of §7.2 when scheduled: how a dormant realm is hinted at, what the discovery action looks like, one-time-ness, credit and announcement. Owned by a future content-update design.
9. **Discovery announcements.** Realm-wide announcement presentation ("Alice discovered...") — client/UX design; no engine surface beyond reading provenance.
