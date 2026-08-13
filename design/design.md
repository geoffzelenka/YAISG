# Yet Another Idle Skilling Game — Technical Design Document

**Version:** 0.6 (ratification + market-model revision)
**Scope:** Code architecture and implementation plan only. Game content (specific items, action tables, balance numbers, realm definitions) is deferred to the content design document. All systems load content from data, not code.

**What changed in v0.6:**
1. **Ratified** the six open items carried out of Phase 4 (§12 log #18–23).
2. **Absorbed the v0.5 implementation reality** (Phase 4 as shipped): estate forms, the realm development graph, decoupled estate ownership, the map pack, nine served content packs, path-cost relocation, resolved-caps API (§5, §6, §7).
3. **Rewrote the market design** (§5.4, §5.5, §6.2, §8.3) to the order-book + realm-stores model per `market-vision.md` v1.0, superseding the escrowed-listings design. Phase 5 prompts must be written against *this* version, not v0.3–0.5.
4. Added §13, a **work-item ledger** tracking engine changes implied by the vision documents (`realm-vision.md` v0.4, `skills-and-goods-vision.md` v0.2, `market-vision.md` v1.0) that are accepted in principle but not yet scheduled.
5. Revised the non-goals list (§10) where visions moved the line (multiple estates, exploration permanence).

**Version policy:** this document stays at v0.6 until the remaining vision documents (**Combat**, **XP Curve**, **Exploration & Keys**, **Visiting**) exist and have been aligned. Vision-driven engine implications land in the §13 ledger in the meantime; only ratified decisions move into the body.

---

## 1. Overview

A multiplayer, web-based idle skilling game in the genre of Melvor Idle, Idle Clans, and Ironwood RPG. Players train skills in real time via timed action cycles, accumulate resources, and trade with other players.

**Differentiator:** Players choose a *realm* in which to establish their *estate*. Realms are regions of one shared, living map: they specialize, develop along a content-defined graph, and must be sustained by their residents' economy. Estates express the player's relationship to the map along a mobility ↔ rootedness axis.

### 1.1 Design pillars (engineering implications)

1. **Server-authoritative.** All progression math happens on the server. The client is a view; client timers are cosmetic.
2. **Content is data.** Skills, actions, items, recipes, realms, development graphs, estate forms, and modifiers are defined in versioned content files (JSON) loaded by the server. The engine knows *mechanics*; it never hardcodes *content*. Corollary (proven through Phase 4): **new sources are content; new types are engine changes.** This rule now governs modifiers, caps, and (per §13) availability tags.
3. **Offline progress by design.** Progress is computed from timestamps, not per-player loops. Realm-scale world processes (upkeep ticks, store decay, inter-realm balancing — future) run in the single scheduled-job slot (§8.3); realms are few, so discrete ticks are cheap and the pillar holds.
4. **Simple first, swappable later.** SQLite → PostgreSQL (CI matrix already runs both), monorepo services → separate deployments.

---

## 2. Technology choices

Unchanged from v0.3 (Python 3.12 + FastAPI, SQLAlchemy 2.x + Alembic, SQLite→PostgreSQL, separate auth service with RS256 + JWKS, React 18 + Vite + TS, TanStack Query, Tailwind, REST + JSON). One addition:

| Concern | Decision | Rationale |
|---|---|---|
| Scheduled world processes | **APScheduler in-process** (existing §8.3 slot) grows from "listing expiry" to the world-tick host: order expiry, store decay/upkeep ticks (Phase 5.5), inter-realm balancing (Phase 5.5) | Realms are few; discrete ticks are cheap; no per-player timers introduced. Revisit (external scheduler) only if job runtime threatens request latency. |

---

## 3. System architecture

Unchanged from v0.3 (client → auth service + game API → SQL DB; content files read at boot; no per-player background workers). Repository layout unchanged. The engine purity rule stands: `engine/` is pure functions `(state, content, now) → (new_state, results)` with injected RNG.

---

## 4. Core gameplay loop (server-authoritative skilling)

Unchanged from v0.3 as implemented in Phase 3, including the ratified refinements (log #1–9): segmented level-up resolution, offline cap ends the action after granting only in-budget cycles, backwards-clock no-op, at-most-once reward feed, overflow precedence. The per-cycle reward step remains a `CycleRewardStrategy` so Phase 6 combat swaps in a resolver without framework changes.

`effective_cycle_time` / `effective_xp` / `effective_drops` now resolve modifier and cap sources from: the realm's **current development node**, the character's **estate form**, and installed **non-inert estate upgrades** (v0.5, shipped in 4.1). Arithmetic unchanged (additive within type; `extra_drop_chance_pct` multiplies base chance by `1 + total/100`, clamped [0,1]; cycle time and XP truncate after applying the summed percentage).

---

## 5. API design (Game service)

Errors use the uniform envelope `{error: {code, message}}` with stable machine-readable codes.

### 5.1 Meta / content
- `GET /content/manifest` — content version + per-pack hashes; strong ETags, `If-None-Match` → 304.
- `GET /content/{pack}` — **nine served packs** (ratifies log-#18 supersession of the original five): `skills`, `items`, `realms`, `upgrades`, `caps`, `map`, `estate_forms`, `development`, `projects`. Content endpoints are unauthenticated (log #5). Drop rates exposed (log #3). The XP curve affects the version hash but is not a public pack (log #5).
- `GET /map` — unauthenticated map/graph view (v0.5); realm treasuries are never exposed.

### 5.2 Character & profile
- `POST /characters` — create character (name, starting realm). New characters' estates start as `form.camp` (v0.5).
- `GET /characters/me` — full profile including **resolved caps as `{base, effective}`** (v0.5). Triggers resolve; may persist derived-state repairs.
- `GET /characters/me/inventory`
- `GET /characters/me/relocate/preview` — non-mutating relocation cost preview (v0.5).
- `POST /characters/me/relocate` — cost = `path_cost(origin, destination) × estate form's relocation_cost`; charged up-front; instant and delayed paths; stops the active action with final rewards; second relocation while pending → `ESTATE_BUSY` (log #22).

### 5.3 Skilling & combat
Unchanged (available / start / poll / stop, all resolving lazily; combat group empty until Phase 6).

### 5.4 Global player market — **order book (supersedes the v0.3 listings design)**

One global order book per good. Goods and gold move instantly on match; there is no per-realm player-market price fragmentation. Both sides post orders.

**Model.**
- **Buy order** `{item_id, quantity, unit_price}` — full gold cost escrowed at creation.
- **Sell order** `{item_id, quantity, unit_price}` — goods escrowed at creation.
- **Order slots.** Every order occupies a slot with lifecycle **create → fill/cancel → collect → free**. The slot holds outgoing escrow, accumulates incoming fills (goods for buys; gold net of tax for sells), and receives cancellation remainders. Nothing enters inventory or wallet except through **collection**; a filled-but-uncollected order still occupies its slot. Consequences the engine relies on: inventory caps gate *collection*, never fills (the drop-overflow discard rule **never** applies to purchased goods); partial fills accumulate in the slot with no ceremony; if located storage ever exists, collection is the single attachment point for a location rule.
- **Matching is continuous** with price-time priority: a new order sweeps crossing resting orders best-price-first, oldest-first within a price, trading **at the maker's price**; any remainder rests at the taker's price. Implemented as one transaction per insert with row locks on swept orders. No clearing windows.
- **Tax:** flat, content-defined, global rate taken from the **seller's** proceeds per match, at match time, credited to `realm_state.treasury` of the realm where the seller's order was placed (the seller's physical realm at order creation). This is the treasury's first writer, as reserved in Phase 4.
- **Slot cap:** the former `market_listings` cap generalizes to **`order_slots`**, covering both sides (rename in caps content + resolution; same cap machinery).
- **Access gate:** all global-market endpoints require the character's current realm to carry the **market-access tag** (granted/lost via development nodes per §7.3). Error code `NO_MARKET_ACCESS`. *Prerequisite:* tag emission engine work (§13.1).

**Endpoints.**
- `GET /market/book/{item_id}?depth=` — aggregated book view (price levels + quantities, both sides)
- `GET /market/orders/me` — my slots with statuses and pending fills
- `POST /market/orders` — `{side, item_id, quantity, unit_price}` → escrow, match, rest remainder; response reports immediate fills
- `POST /market/orders/{id}/cancel` — remainder moves to the slot's collectable state
- `POST /market/orders/{id}/collect` — move fills/refunds to inventory/wallet (gated by inventory caps), free the slot when emptied
- `GET /market/history/me`

**Expiry:** orders expire (default duration from content); expiry transitions the order to `collectable` — remaining escrow joins any fills awaiting collection, and the slot stays occupied until collected. Processed by the scheduled job (§8.3), which also purges `closed` orders past a retention window (`market_matches` is the durable history).

**Conservation invariant (property-tested):** every unit of gold and goods is at all times in exactly one of — inventory/wallet, slot escrow, slot fills, or realm treasury (tax). Concurrency tests must cover two takers racing for the same maker.

### 5.5 Realm market — **stores, reference prices, treasury-bounded bids (supersedes static `market_offers`)**

Each realm's market is a *place* (presence-gated, §7.6) with two faces:

- **It buys** what its upkeep quotas and active projects demand; purchased goods are consumed (the economy's primary sink).
- **It sells** goods its identity produces **out of its stores** — never minted. Self-limiting by store level.

**Pricing, three layers:**
1. **Reference prices** — content property per good (per-tier defaults with per-good overrides), validated at boot. Fixed in v1; solves cold start and anchors solvency accounting later.
2. **Bid curve** — bid = f(reference price, store level): near-floor at full stores, climbing as stores drain. (Ask-side equivalent for realm sales must stay above the realm's own bid — no in-place spread milking.) Exact curve: content/balance, small engine surface.
3. **Treasury** — hard budget constraint. A realm bids only with gold its economy earned (tax, later escheat). No minting; unfunded demand is visible as starving stores at attractive nominal prices.

**Stores:** per-good inventory levels on realm state. Phase 5 builds the **read side** (stores exist, seeded by content/cold-start; bids computed from them); decay/upkeep consumption and estate-production crediting land in Phase 5.5.

**Endpoints.**
- `GET /realms/{id}/market` — store levels, current bids/asks (the signal layer; visibility scope per market-vision §7.7 — v1 leans full visibility)
- `POST /realms/{id}/market/trade` — `{item_id, quantity, side}`; **presence-gated**: interim rule until visiting exists is *current realm = home realm* (residents only). Invariant recorded: **no remote realm-market trading, ever.**

The v0.5 `realms.market_offers` content field is repurposed/replaced by reference prices + identity-produced goods lists; the Phase 5 prompts must confirm and migrate its shape (carried from the Phase 4 report's recommendation).

### 5.6 Estate & realm
As shipped in v0.5:
- `GET /estates/me`; `POST /estates/me/upgrades/{upgrade_id}` (`UNKNOWN_UPGRADE` / `NO_FREE_SLOT` / `ALREADY_INSTALLED` / `MISSING_INPUTS`; last-slot row-lock); `POST /estates/me/transform` (`INVALID_TRANSFORMATION` / `MISSING_INPUTS` / `ESTATE_BUSY` / `WOULD_ORPHAN_UPGRADES`).
- `GET /realms`, `GET /realms/{id}`; `POST /realms/{id}/contribute` — clamped contributions, item conservation, single-effect completion under races; `REALM_TRANSITIONING` when the node is departing (log #21); contributions are **not residence-restricted** (log #23).
- Edge awards serialized; regression/non-outgoing edges rejected; no awards during a pending transition (`INVALID_EDGE_AWARD`, log #21). Lazy idempotent `finalize_realm` wired into character resolve.

### 5.7 Auth service
Unchanged (RS256 + JWKS, rotating refresh tokens, family revocation = all of a user's tokens, log #6).

---

## 6. Data model

### 6.1 Auth DB — unchanged.

### 6.2 Game DB (reflects v0.5 as shipped + Phase 5 shapes)

```
players             (id, auth_user_id UNIQUE, created_at)
characters          (id, player_id UNIQUE, name, name_normalized UNIQUE,
                     realm_id, home_estate_id, created_at)
character_skills    (character_id, skill_id, xp, level)
active_actions      (character_id PK, action_id, started_at, last_resolved_at, meta JSON)
inventories         (character_id, item_id, quantity)
currency            (character_id PK, gold, premium)          -- premium still dormant
reward_log          (id, character_id, action_id, cycles, xp JSON, items JSON,
                     details JSON, resolved_at, claimed_at NULL)

-- Estates (v0.5): ownership decoupled from identity; transfer/escheat-ready
estates             (id PK, owner_character_id NULL-able-by-design, realm_id,
                     form_id, level, upgrade_slots, status,
                     relocating_to_realm_id NULL, relocation_completes_at NULL,
                     data JSON)                                 -- log #19
estate_upgrades     (estate_id, slot_index, upgrade_id, purchased_at)
estate_ownership_history (estate_id, character_id, from_at, to_at NULL)

-- Realms as development-graph state (v0.5)
realm_state         (realm_id PK, current_node_id, treasury,
                     pending_transition JSON NULL, ...)
realm_edges         (realm_id, edge_id, progress JSON, status)
realm_projects      (realm_id, project_id, contribution_totals JSON, status)
realm_contributions (id, realm_id, character_id, item_id, quantity, contributed_at)
realm_stores        (realm_id, item_id, quantity)               -- Phase 5 (read side)

-- Global player market (Phase 5; REPLACES market_listings/market_trades)
market_orders       (id, character_id, side, item_id, unit_price,
                     quantity,               -- original listed quantity (immutable)
                     quantity_remaining,     -- unfilled units still on the book (side-neutral)
                     escrow_gold_remaining,  -- buy orders: gold still escrowed for unfilled qty
                     fill_items,             -- buy orders: goods received, awaiting collection
                     fill_gold,              -- sell orders: net-of-tax proceeds, awaiting collection
                     status,                 -- open | collectable | closed (see lifecycle below)
                     realm_id, created_at, expires_at, closed_at NULL)
                     -- partial index on status='open' (item_id, side, unit_price, created_at)
                     -- for the matcher; closed rows are purge candidates
market_matches      (id, maker_order_id, taker_order_id,
                     buyer_character_id, seller_character_id,   -- denormalized so history
                     item_id, quantity, unit_price, tax_gold,   -- survives order purging
                     matched_at)
```

**Order lifecycle and slots.** The order row *is* the slot — there is no separate
slots table. `status` walks: **open** (resting/matching on the book) →
**collectable** (fully filled, cancelled, or expired: off the book, slot still
held by uncollected fills/refunds) → **closed** (collected; `closed_at` set; slot
freed). Slot enforcement: `COUNT(orders WHERE character_id AND status != 'closed')
< order_slots (effective)`, checked under the insert's transaction. A partially
filled open order is both on the book *and* holding collectable fills; early
collection of accumulated fills is allowed without closing the order. The
scheduled job (§8.3) purges `closed` rows past a retention window;
`market_matches` is the durable trade history (hence the denormalized character
ids). An explicit slots table is only warranted if slots ever become individually
upgradeable/named — count-based is the v1 rule.

Dormant-by-design structures (built in v0.5, first readers scheduled): `realm_state.treasury` → Phase 5 tax; estate-form `upkeep_profile` / `production_profile` → Phase 5.5; regression edges → Phase 5.5 upkeep gauge; `currency.premium`; estate transfer/escheat endpoints (schema ready via nullable ownership + history).

**Verify before Phase 5 content:** NPC estates (cold-start seeding, §13.5) should be representable as estates with a null/system owner — the v0.5 ownership schema is believed to tolerate this; confirm with a fixture test.

### 6.3 Content file schema
As shipped (nine packs, strict frozen Pydantic, referential integrity, canonical hashing). Phase 5 additions: per-good **`reference_price`** (per-tier defaults + overrides), the global **tax rate**, order default duration, and the `order_slots` cap rename. §13 items (item `tier`, tag emission from sources) extend this further when scheduled.

### 6.4 SQLite → PostgreSQL rules — unchanged; both-DB CI matrix is live.

---

## 7. Realms, estates, and modifiers

### 7.1 Sources and resolution (as shipped, v0.5)
Modifiers, caps, and availability resolve per character from: the realm's **current development node**, the **estate form**, and installed **non-inert upgrades**. Additive within type; inert status derived per-resolve, never persisted. Caps API exposes `{base, effective}`.

### 7.2 Caps
`offline_hours`, `inventory_slots`, **`order_slots`** (renamed from `market_listings`, now covering both order sides), `estate_upgrade_slots`. Enforcement points unchanged, plus: order creation (slot cap) and order **collection** (inventory caps). A future estates-count cap remains anticipated (multiple estates, §10).

### 7.3 Development graph
Realm identity (tags, modifiers, cap bonuses — log #7) is a function of the realm's current node in the content-defined graph. Transitions (morphing) advance via project completion and edge awards; **regression edges exist in content but remain dormant until the Phase 5.5 upkeep gauge drives them.** The **market-access tag** is granted by early-tier nodes and lost on regression past them — this is the frontier/decay mechanism for global-market access (§5.4). Depends on §13.1 tag emission.

### 7.4 Estate forms and transformation
Forms are content-defined types determining base caps, bonus profiles, relocation cost class, and (dormant) upkeep/production profiles. Transformation rules as ratified: `WOULD_ORPHAN_UPGRADES` blocks a transform whose destination capacity (excluding installed-upgrade bonuses) can't hold installed upgrades (log #20); camp = 4 slots (global 2 + form 2).

### 7.5 Relocation
Cost = path over the map graph (`path_cost`, tie-break gold then time) × the form's `relocation_cost`. Charged up-front; instant and delayed variants; the estate retains **origin identity during relocation** and a second relocation is blocked (`ESTATE_BUSY`) until completion (log #22). Estates are persistent; upgrades may go inert in the destination, never lost.

### 7.6 Presence (interim)
Until the visiting design exists, a character's *current* realm equals their *home* realm. Everything presence-gated (realm-market trades §5.5; the seller-realm attribution for tax §5.4) uses this rule and must be written against a `current_realm(character)` helper so visiting swaps in without a sweep.

### 7.7 Market tax note
`market_tax_pct` **no longer exists as a per-realm stacking modifier type.** Tax is a single flat global rate in content, credited to the hosting realm (§5.4). If a realm-level tax-efficiency perk is ever wanted, it returns as a new decision, not by resurrecting the modifier.

---

## 8. Cross-cutting concerns

### 8.1 Security & anti-cheat — unchanged (server validation, CSPRNG-seeded per-resolve RNG, JWT middleware). Game-API mutation rate limiting remains deferred to Phase 7.

### 8.2 Transactions & concurrency
Unchanged principles, with the market rewritten: order insert = one transaction (escrow, sweep with row locks on makers in price-time order, write matches + tax, rest remainder); cancel/collect = one transaction each; cross-realm operations lock realms in sorted-ID order (log-established rule from 4.3) — apply the same to any multi-realm balancing later.

### 8.3 Background jobs (the world-tick slot)
One APScheduler in-process scheduler hosting, in order of arrival: **order expiry** and **closed-order purge** (retention window, Phase 5), **store decay + realm upkeep ticks + estate-production reconciliation** (Phase 5.5), **inter-realm balancing** (Phase 5.5). Realm-scale only; per-character math stays lazy.

### 8.4 Testing strategy
Unchanged, extended: conservation property tests over the four-state gold/goods invariant (§5.4); matching-priority tests (price-time, maker price); two-taker race tests on both engines; store/bid computation unit tests against fixture curves.

### 8.5 Observability — unchanged; add counters for matches, tax credited, collections.

---

## 9. Client design
Unchanged shell/strip/polling architecture. Phase 5 adds: global-market panel (book view, my orders/slots with collect actions, fills feed) and realm-market panel (stores + bid/ask signal display, trade form, presence/access states). The map view (v0.5) grows store/treasury-health signals per market-vision §7.7's visibility decision.

---

## 10. Explicit non-goals for v1 (revised)

- WebSockets / real-time push.
- **Exploration** — deferred to its own vision (`exploration-and-keys-vision-TODO.md`). **Revision:** do *not* build the previously sketched permanent per-character unlocks table; discoveries are expected to be realm-scoped and expiring. Nothing interim may assume unlock permanence. Sidebar slot stays reserved.
- **Multiple characters** per account, deletion/rename — unchanged.
- **Multiple estates per character** — *downgraded from non-goal to deferred-yes* (the tycoon archetype, realm-vision §3.5). v1 still enforces one; nothing may be built that assumes 1:1-forever (the v0.5 ownership schema already complies). Needs its cap type + "home estate" designation when scheduled.
- **Visiting / travel** — deferred; presence interim rule per §7.6.
- **Tutorial island** — deferred; noted as upkeep- and market-exempt when built.
- **Upkeep, decay, solvency, estate passive production, inter-realm balancing** — Phase 5.5, not v1-Phase-5.
- Premium currency mechanics; guilds/chat/friends; rich combat beyond the cycle skeleton; admin tooling; horizontal scaling; real content/balance.

---

## 11. Implementation plan (revised from Phase 5 onward)

Phases 0–4: **complete** (see status reports; v0.5 shipped).

**Phase 5 — Markets (rewritten; do not use pre-v0.6 prompt sketches).**
5.A Prereq: tag emission from availability sources (§13.1) + market-access tag in content.
5.B Global order book: migrations (`market_orders`, `market_matches`), matching engine (pure, test-first, price-time priority at maker price), order/collect/cancel endpoints, flat tax → treasury, order-slot cap, expiry job, conservation + race tests.
5.C Realm market: reference prices in content, `realm_stores` (read side + cold-start seeding), bid/ask curve function, presence-gated trade endpoint, signal endpoints.
5.D Client: global-market and realm-market panels; map signal layer.

**Phase 5.5 — World dynamics.** Upkeep quotas and store decay ticks, estate upkeep/production lazy resolution + reconciliation, solvency accounting, decay state machine, regression-edge coupling, inter-realm balancing. (Requires markets; blocked on the upkeep-mechanics design pass, §13.4.)

**Phase 6 — Combat skeleton.** Monster content shape, combat `CycleRewardStrategy`, consumables as cycle inputs (shape to be confirmed by the Combat vision, §13.6). Client Combat panel.

**Phase 7 — Hardening.** Game-API rate limiting, market conservation property suite at scale, k6 load sanity, observability counters. (Both-DB CI already done.)

---

## 12. Resolved design decisions (log)

1–9. *(v0.3–0.4, unchanged: offline cap semantics; single currency + dormant premium; drop rates exposed; persistent estates; exploration deferred; reward feed at-most-once; `extra_drop_chance_pct` semantics; overflow precedence; unauthenticated content endpoints; refresh-token family = user; project tiers may declare cap_bonuses; segmented level-up resolution; backwards clock no-op.)*
10–17. *(v0.5, per Phase 4: source-resolution arithmetic unchanged; GET /map unauthenticated; treasury reserved for Phase 5 market tax; estate forms/ownership/development-graph shapes as shipped.)*

**Ratified in v0.6:**
18. **Served packs are nine** (`skills, items, realms, upgrades, caps, map, estate_forms, development, projects`), superseding the original five-pack rule.
19. **`estates.relocating_to_realm_id` + `relocation_completes_at`** are part of the §6.2 schema.
20. **`WOULD_ORPHAN_UPGRADES`** transform rule: destination capacity check excludes installed-upgrade bonuses (v1 rule).
21. **No edge awards during a pending transition** (`INVALID_EDGE_AWARD`); contributions to a departing node fail cleanly (`REALM_TRANSITIONING`) before consuming goods.
22. **Origin identity during relocation**; second relocation blocked (`ESTATE_BUSY`).
23. **Contributions are not residence-restricted** — confirmed as intended: civic giving is open to non-residents; presence gating applies to *market* trade (§5.5), not to projects. Revisit only if remote contribution proves exploitable.
24. **Player market is a global order book** with continuous price-time-priority matching at maker price, order slots with explicit collection, flat seller-side hosted-realm tax (supersedes the escrowed-listings design end to end).
25. **Realm markets: stores + fixed reference prices + treasury-bounded bids**; presence-gated with the interim residents-only rule; **no remote realm-market trading, ever**.
26. **`market_tax_pct` retired as a modifier type**; tax is flat global content.
27. **`market_listings` cap renamed/generalized to `order_slots`**, covering both order sides.
28. **Inventory caps gate order collection, never fills**; the drop-overflow discard rule never applies to market goods.
29. **The order row is the slot.** No separate slots table; slot occupancy = count of non-`closed` orders vs. the `order_slots` cap. Lifecycle `open → collectable → closed`; collection closes and frees; closed rows are purged after a retention window, with `market_matches` (denormalized character ids) as the durable trade history.

---

## 13. Work-item ledger (vision-implied engine changes, accepted in principle, not yet scheduled)

The gate between "vision" and "build": items leave this ledger only by entering a phase in §11 with a ratified shape.

| # | Item | Source | Bites | Status |
|---|---|---|---|---|
| 13.1 | **Tag emission from all availability sources** (development nodes, estate forms, upgrades) through the same resolution/inert pass as modifiers and caps | skills-and-goods §3.4/§7 | **Phase 5.A** (market-access tag) and any facility-gated content | Scheduled (5.A) |
| 13.2 | **Item `tier` content property** + input-class tag convention (`class.log.t1`); convergent refining is a content convention to document in the pipeline | skills-and-goods §3.1–3.3 | Content-design time; near-zero engine work | Accepted |
| 13.3 | **Proficiency**: optional per-skill threshold table feeding `cycle_time_pct` from level-vs-tier (one generic source hook; existing modifier type). Yield bonus explicitly *not* included absent a new decision | skills-and-goods §2.3/§7 | With tiered content | Accepted |
| 13.4 | **Upkeep/decay/solvency processing model**: realm ticks + store decay in the job slot; estate upkeep/production resolved lazily on character resolve, reconciled at tick; solvency status feeding a decay state machine; regression-edge coupling | realm-vision §7, market-vision §8 | Phase 5.5; needs a dedicated design pass first | Blocked on design pass |
| 13.5 | **NPC estates as cold-start content** (null/system owner, production profiles) | market-vision §3.4/§8 | Content time; **verify schema tolerance now** (fixture test) | Verify in 5.B |
| 13.6 | **Consumables as combat cycle inputs** — expressible today; shape (per cycle vs. per damage) owned by the Combat vision | skills-and-goods §4.2/§7 | Phase 6 | Blocked on Combat vision |
| 13.7 | **Carried vs. stored inventory split** — build nothing that prevents it; collection (§5.4) is the designated seam | market-vision §8 | Visiting/estate-storage designs | Watch item |
| 13.8 | **Expiring realm-scoped availability** (exploration keys) — build nothing that assumes permanent unlocks | exploration TODO | Exploration vision | Watch item |
| 13.9 | **Visiting / current-location concept** — `current_realm()` helper is the interim seam (§7.6) | realm-vision §2.8 | Own design doc, after Combat vision | Blocked on vision |
| 13.10 | **Estate transfer / escheat / succession endpoints** — schema ready; mechanics owned by realm-vision §6.9 residuals | realm-vision §3.6 | Post-5.5 | Blocked on vision residuals |
| 13.11 | **Tutorial island** — restricted starting realm, upkeep/market-exempt, scripted one-way graduation | realm-vision §2.4 | Content + small engine flags | Accepted, unscheduled |

**Vision-document dependency map** (what must exist before which build step): Combat vision → Phase 6 content · Upkeep-mechanics design pass (within realm-vision residuals) → Phase 5.5 · Visiting design → full presence rules + hauler activation + 13.9 · Exploration & Keys vision → 13.8 · XP Curve vision → tier thresholds (13.2/13.3 numbers).
