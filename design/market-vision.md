# Yet Another Idle Skilling Game — Market Vision Document

**Version:** 1.0 (supersedes the market portions of `realm-vision.md` §4; see §9 for the exact paragraphs invalidated)
**Scope:** The trade side of the world economy — the global player market (order book, order slots, tax), the realm markets (stores, reference prices, treasury-constrained bids), how the two interlock, and the player archetypes this shapes. Sibling visions: **Market Vision / realm-vision.md** (realms, estates, upkeep, decay — still authoritative on everything outside §4), **Skills and Goods** (supply side), and the planned **Combat** and **XP Curve** documents.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't yet support, that is a design-doc work item (§8), not a license to improvise. The future content design document turns this vision into concrete goods lists, prices, tax rates, and decay curves.

**Provenance:** v1.0 consolidates the two-market economy of realm-vision.md v0.4 §4 with the order-book draft (`market-vision.md` rough draft) and the decisions ratified in the design chat: full order book with buy and sell orders; **continuous matching** (price-time priority, taker at maker's price); pure global book with instantaneous goods travel; order-slot escrow and explicit collection; treasury as hard budget constraint with content-defined reference prices for cold start; flat seller-side global tax; market access as a losable realm development tag; the hauler redefined as a realm-market arbitrageur and frontier supplier.

---

## 1. The elevator pitch

Two markets, two jobs. The **global player market** is one worldwide order book where players discover prices and trade with each other — goods move instantly, buyers and sellers both post orders, and every trade pays a small tax to the realm that hosted it. The **realm markets** are the world's metabolism: each realm buys what its upkeep hungers for and sells what its identity produces, out of stores that visibly fill and drain, at prices that rise with scarcity — but only ever with gold its own economy earned.

Players trade with each other to *rearrange* the world's goods; they trade with realms to *sustain* the world itself.

---

## 2. The global player market

### 2.1 One book, whole world

There is a single global order book per good. Goods and gold move instantly on match — no transport time, no located goods, no per-realm price fragmentation on the player side. This is a deliberate trade-off: it maximizes liquidity and price-discovery quality at the population scales of a growing game, and it concedes that *player-market* price gradients between realms will not exist. Geography's economic meaning lives elsewhere (§4, §5) — in realm-market spreads and in the edges of the market-access network — not in the player book.

### 2.2 A full order book: buy and sell orders

Both sides of the market post orders; neither side is a price-taker by construction.

- **Buy order:** the player names a good, a quantity, and a unit price. The gold to cover the full order moves into the order's escrow at creation.
- **Sell order:** the player names a good, a quantity, and a unit price. The goods move from inventory into the order's escrow at creation.
- **Cancellation** returns the remaining escrow — to the order slot (§2.3), not directly to inventory.
- **Fulfillment** pays the seller the order's value **less tax** (§2.5) and delivers goods to the buyer — again, into their order slot.

Buy-side expression is what makes price discovery real: without it, buyers are at the mercy of whatever sellers happen to offer, and the demand information the treasury-and-signals layer (§3) wants to exist stays invisible.

**Matching is continuous.** Every new order either *makes* or *takes*: if it crosses one or more resting opposing orders, it fills immediately against them — best price first, oldest first within a price (price-time priority), trading **at the maker's price** — and any unfilled remainder rests on the book at the taker's own price. If it crosses nothing, it rests. There are no clearing windows; fills happen the moment orders meet. A player posts an order, or fills one — often both in a single action when a large order sweeps several resting ones. (Batch auctions were considered and rejected: continuous matching is the familiar experience, and the maker-price rule keeps it fair — you never pay more or receive less than the price you posted.)

### 2.3 Order slots: escrow in, fills in, collect out

Every order lives in an **order slot** — a small escrow container with an explicit lifecycle: **create → fill and/or cancel → collect → free.**

- The slot holds the outgoing escrow (gold for buys, goods for sells), accumulates incoming fills (goods for buys, gold-net-of-tax for sells), and receives any remainder on cancellation.
- The player **collects** from the slot to move fills and refunds into their inventory and wallet. Nothing enters inventory without collection.
- **A completed-but-uncollected order still occupies its slot.** Collection is what frees it. This keeps the lifecycle simple and makes collection light, healthy housekeeping — the slot cap gently rewards engagement over fire-and-forget.

The slot pattern quietly solves several problems at once:

- **Inventory caps never touch the order book.** Fills always succeed regardless of the buyer's inventory state; *collection* is what inventory space gates. No overflow rule ever applies to purchased goods (the engine's drop-overflow discard rule would be unacceptable here). Cancellations are equally safe.
- **Partial fills need no ceremony.** A buy for 1,000 logs filled by six sellers accumulates in one slot; the player collects when they please. Tax is applied per match, at match time.
- **Location seams close.** The book and the slots are location-less; collection delivers into the player's carried inventory wherever they stand. If located storage ever exists (estate warehouses, the visiting design), collection is the single point where a location rule would attach.
- **Conservation gets easier to state.** Every unit of gold and goods is at all times in exactly one of: inventory/wallet, slot escrow, slot fills, or realm treasury (tax). That is the property test.

### 2.4 Order slots are a capped resource

Players have a limited number of concurrent order slots — the existing `market_listings` cap (design.md §7.1) generalized to cover both order sides. The cap serves its original anti-manipulation purpose (bounding how much of a book one player can occupy) and is a natural progression axis: estate upgrades and realm perks can grant more slots.

### 2.5 Tax: flat, seller-side, credited to the hosting realm

Every match pays a **flat, content-defined global tax rate** out of the seller's proceeds, credited to the **treasury of the realm where the seller's order was placed** — that is, the realm the seller was physically in when they created the order.

- Flat, because with one global book, per-realm tax competition would only produce a race to list from the cheapest realm — noise, not gameplay.
- Seller-side, because it is the simplest conserving rule; shifting or splitting incidence later is a one-line content decision, not a redesign.
- Credited to the hosting realm, because this is the treasury's primary revenue (realm-vision §4.2's loop, now with a concrete mechanism): realms with market access collect tax from the trading activity of their residents and visitors. Hosting a market *is* a revenue strategy.

### 2.6 Access is earned — and losable

The global market is reachable only from realms carrying a **market-access tag**, granted by an early-tier development node or realm upgrade (per the facilities-via-tags convention, skills-and-goods §3.4). Two consequences, both intended:

- **Frontier realms start off the book.** Venturing into the wilderness means leaving the global economy behind — everything a frontier realm imports arrives in someone's carried inventory (§5.2). This is the added risk the rough draft wanted, expressed through an existing mechanism.
- **Access can be lost.** A realm that decays past the node that grants the tag falls off the global economy — no listing, no buying, no tax revenue — which is among the most legible and frightening consequences of communal neglect this game can offer. Frontier is not a special case; it is simply the set of realms that haven't earned, or have lost, the tag.

---

## 3. The realm markets

### 3.1 Function: sink and engine

Each realm operates a market with two faces:

- **It buys** the goods its upkeep quotas and active projects demand. Goods sold to a realm are consumed — they leave the world. This is the economy's primary sink.
- **It sells** goods its identity produces (a forest realm offers logs and woodwork), **out of its stores** — never minted from nothing. Realm sales are self-limiting: a realm can only sell what its stores hold, so NPC supply can cushion but never flood.

The realm market is how goods keep moving *toward need* even when no player is on the other side of the trade.

### 3.2 Stores: the realm's pantry

Each realm maintains **stores** per good — inventory levels that **decay over time** as upkeep consumes them. Stores are the concrete, visible expression of the upkeep quota: a full pantry is a healthy realm; a draining one is a realm in trouble, and everyone can watch it drain.

Estate passive production (realm-vision §4.6) **credits the realm's stores directly**. This is the load-bearing leniency mechanism restated in store terms: a populated realm's low-tier stores are topped up automatically by its residents' estates, so decay is a slow, visible slide with ample warning — not a treadmill that punishes a quiet weekend.

The realm's demand climbs the goods ladder with its tier, additively (realm-vision §4.7): a tier-2 realm needs *more* tier-1 goods than a tier-1 realm did, plus tier-2 goods on top. Low-tier demand is perpetual by design.

### 3.3 Prices: reference-anchored, scarcity-driven, treasury-bounded

Realm-market pricing has three layers, each with a distinct job:

1. **Reference prices (content).** The content designer defines an expected value per good — likely per tier with per-good overrides. Reference prices solve the cold-start problem (a fresh world has no trade history to discover prices from), give the bid curve a scale, and serve as the accounting unit for estate solvency settlement (realm-vision §3.6). Whether reference prices ever update from live trade data, or remain fixed content, is an open tuning question (§7.2) — fixed is the v1 assumption, since the scarcity multiplier does the dynamic work.
2. **The bid curve (mechanism).** What a realm offers for a good is a function of the reference price and the good's store level: floor-ish near full stores, climbing as stores drain. A realm deep in deficit bids desperately; a well-fed realm bids low. Prices are *signals* — traders profit precisely by reading them (§5.1).
3. **The treasury (hard constraint).** The bid curve says what the realm is *willing* to pay; the treasury says what it *can* pay. A realm with empty coffers posts real but unfunded demand — its stores visibly starve even at attractive nominal prices. **No gold is ever minted.** The realm spends only what player commerce (tax, §2.5, plus future revenue streams like escheat) put in. The dark-mirror loop from realm-vision §4.2 survives intact: ghost town → no tax base → dry treasury → weak effective bids → upkeep slips → decay.

### 3.4 Cold start: a seeded world, not a seeded mint

A fresh world needs goods and gold already in circulation, or the loops of §3.3 deadlock before players arrive to fuel them. The tool for this is **content, not engine**: the designer populates a balanced opening world in which some realms carry NPC estates whose passive production feeds stores from day one, and whose notional early revenue seeds realm treasuries. Reference prices anchor everything until genuine price discovery takes over. A pure-treasury economy works from the start because the start was *built solvent* — no bootstrap mint, no permanent exemptions.

(The tutorial island remains upkeep- and market-exempt per realm-vision §2.4 — the living-world pressure begins on the mainland.)

### 3.5 Presence: realm-market trading is local

**Trading with a realm's market requires being physically at that realm.** The global book is location-less; the realm markets are the opposite — they are *places*. This line is what makes the hauler a playstyle instead of a menu (§5.1), and it must not be crossed casually: shipping remote realm-market access, even as a convenience feature, would permanently delete the archetype.

Consequence: the hauler cannot fully activate until travel/visiting exists (realm-vision §2.8, §6.1/§6.3 — still open). That is acceptable sequencing — realm markets can ship serving residents first — but the dependency is now load-bearing and recorded (§8).

---

## 4. Inter-realm balancing: the NPC floor

Realm-vision §4.5 survives with sharpened purpose: periodically, realm markets balance unmet needs against each other, treasury to treasury, with goods paying a **transport cost that scales with distance**. With the player book gone frictionless, this layer is now the *only* place where distance-scaled goods movement exists mechanically — map topology earns its economic keep here.

The balancing network remains deliberately second-choice: transport costs must keep NPC imports strictly inferior to local supply and to hauler runs, so the network is a floor under the world, cushioning frontier and decaying realms without rescuing them or eating the hauler's lunch. Cadence, ordering, cost destination, and import caps remain open (realm-vision §6.6).

---

## 5. The players this economy creates

### 5.1 The hauler, redefined

The original hauler read *player-market* price gradients preserved by transport costs. Those gradients no longer exist — the player book has one price worldwide. The hauler's livelihood moves to two loops the new architecture creates naturally, both anchored in physical presence (§3.5):

- **Realm arbitrage.** Buy from a realm market selling cheap out of full stores; travel; sell into a starving realm's scarcity-inflated bids. The spread is generated by differential store levels and treasury health — *decay literally pays the hauler to fix it*. The counterparty is the world itself: this is players-versus-world gameplay, and the realm-market signal layer (§3.3) is its user interface.
- **Frontier supply runs.** Realms without market access (§2.6) import *everything* in someone's carried inventory. Provisioning an establishing frontier realm is pure hauler gameplay — and it self-obsoletes per location: once the realm develops access, the run dries up and the frontier has moved. Haulers are the players who bootstrap realms *into* the global economy, then move on.

### 5.2 The other archetypes, unchanged but sharpened

- **The producer** sells surplus on the global book at world prices and feeds the local stores through estate production — the always-on foundation of §3.2.
- **The trader** (distinct from the hauler now): works the global book itself — spreads, timing, order-slot management. No travel required; the book is their realm.
- **The adventurer** buys consumables at world prices anywhere with access, and sells monster parts and discoveries into the same book — participating in the economy going and coming (skills-and-goods §4.2).
- **The developer/tycoon** reads store levels and treasury health across the map to decide where the next estate is needed — the realm-market signal layer doubles as their prospectus.

---

## 6. How the pieces reinforce each other

- **The full order book** makes both supply and demand visible → prices carry real information → every downstream signal (realm bids, arbitrage spreads, tycoon prospecting) has an honest anchor.
- **Instant global goods** concentrate liquidity in one book → price discovery works even at small population → the game economy functions from early days rather than after some critical mass.
- **Order slots** buffer every market interaction → inventory caps, partial fills, and cancellations never produce loss or edge-case rules → and the slot cap turns market presence into a bounded, upgradeable resource.
- **The flat hosted tax** ties treasury revenue to real trading activity → realm health is earned from commerce, not dialed by designers → and gold recycles instead of minting.
- **Stores + reference prices + treasury constraint** turn realm health into a visible, readable state → decay signals its own rescue price → haulers and tycoons are recruited by the market itself, no quests required.
- **Losable market access** makes the global economy something a community keeps, not something it is given → decay threatens the most valuable connection a realm has → upkeep matters viscerally.
- **The access frontier** creates market deserts at the map's edges → carried-inventory supply runs give haulers irreplaceable work → which bootstraps new realms onto the book → which moves the frontier and renews the loop.
- **Presence-gated realm markets** keep geography meaningful in a world of instant player trade → travel and location stay load-bearing → the visiting design has an economic reason to exist.

The standing test from realm-vision §5 applies: any future market feature must strengthen at least one of these loops without flattening the trade-offs that make choices meaningful.

---

## 7. Open questions

1. **Reference price dynamics.** Fixed content values (v1 assumption) vs. slow-moving averages of actual trade. If they ever update, define the smoothing and the bounds.
2. **Bid curve shape.** The concrete function from (reference price, store level) → bid, and the ask-side equivalent for realm sales. Content/balance work with a small design-doc surface.
3. **Order expiry.** Do orders expire (the current listing design says yes, with an expiry job)? If so, expiry presumably moves remaining escrow to the slot's collectable state — confirm, and pick default durations.
4. **Tax rate value and incidence.** The number itself; whether buy-side or split incidence is ever wanted (mechanically trivial to change).
5. **Slot cap numbers and sources.** Base count, and which estate upgrades / realm perks grant more.
6. **Realm sale prices.** Realms sell from stores — at reference price, at a store-level-driven ask, or at a fixed markup? Must stay above the realm's own bid to prevent a player milking the spread in place.
7. **Visibility scope.** Can players view (not trade) the global book and other realms' store/bid levels from anywhere? Full visibility maximizes the signal layer's recruiting power; fog rewards scouting. Leans toward full visibility for v1 (the map already shows realm health).
8. **Inherited opens.** Inter-realm balancing rules (realm-vision §6.6); treasury seeding details beyond §3.4's content approach (realm-vision §6.5); estate-production accounting shape (credited to stores directly per §3.2 — confirm against upkeep-mechanics design, realm-vision §6.4).

---

## 8. What this changes in the design doc (work items, not yet decisions)

Roughly in build order:

- **Order book replaces listings.** The Phase 5 player-market design (escrowed sell listings, partial buys against listings) is superseded. New shape: `market_orders(id, character_id, side, item_id, unit_price, quantity_remaining, escrow_gold, filled_items_qty, filled_gold, status, realm_id, created_at, expires_at)` plus **continuous matching** (§2.2: on insert, sweep resting opposing orders in price-time priority at maker prices, inside one transaction with row locks on the swept orders; remainder rests) and collection endpoints. Conservation property tests extend to both escrow kinds and the slot states; concurrency tests must cover two takers racing for the same maker. *(Bites at the start of Phase 5 — the existing Phase 5 prompt sketches must be rewritten, not amended.)*
- **Tax → treasury at match time.** Each match credits `realm_state.treasury` for the seller-order's `realm_id`. The dormant treasury column (Phase 4) gets its first writer here, as planned. *(Phase 5.)*
- **Market-access tag.** Global-market endpoints gated on the character's current realm carrying the access tag. Depends on the tag-emission engine work item already recorded (skills-and-goods §7) — tags must flow from development nodes before this ships. *(Phase 5, with the tag work as a prerequisite.)*
- **Realm stores.** `realm_state` (or a child table) grows per-good store levels; decay processed in the scheduled-job slot alongside upkeep ticks (realm-vision §7's processing model); estate production credits stores at reconciliation. Bid computation reads (reference price, store level, treasury). *(Phase 5 for the read side; decay processing lands with the upkeep phase, 5.5.)*
- **Reference prices in content.** A per-good (or per-tier with overrides) `reference_price` content property, validated at boot. *(Phase 5.)*
- **Presence checks on realm-market trades.** Requires the character-location concept from the visiting design; until it exists, "current realm = home realm" is the interim rule and residents-only is the interim behavior. Record the invariant now: **no remote realm-market trading, ever.** *(Interim rule Phase 5; full rule with visiting.)*
- **Carried inventory as cargo.** The hauler loop assumes players physically carry goods between realms; no engine concept distinguishes carried from stored today (there is only one inventory). Nothing needs building yet, but nothing should be built that *prevents* a carried/stored split later — flagged for the estate-storage and visiting designs. *(Watch item.)*
- **NPC estates as content.** Seeded estates with production profiles but no owning player — the cold-start tool of §3.4. Likely just estates with a null/system owner, which the Phase 4 ownership-history schema should already tolerate — verify. *(Content-design time; verify schema now.)*

---

## 9. What this supersedes in realm-vision.md

To be patched in the next realm-vision revision (bump past v0.4):

- **§3.5 "The trader/hauler"** — rewritten per §5.1/§5.2 here: the hauler works realm-market arbitrage and frontier supply, not player-market gradients; the pure global-book trader splits off as their own archetype.
- **§4.1 "Two markets, two functions"** — survives in spirit; the player market is now explicitly one global, instant, location-less order book (§2.1 here).
- **§4.2 "The tax → treasury → procurement loop"** — survives; tax mechanism concretized as flat, seller-side, hosted-realm-credited (§2.5 here).
- **§4.3 "Realm market prices are signals"** — survives, concretized into the three-layer model (reference price / bid curve / treasury bound, §3.3 here).
- **§4.5 "Inter-realm balancing and transport cost"** — survives with narrowed framing: the *"transport cost preserves the mobile trader's arbitrage gap"* rationale is obsolete (no player-market gradients exist); the layer's purpose is now solely the NPC floor (§4 here).
- **§4.6 "Estates produce into the metabolism"** — survives; "produce into the realm's market" is concretized as "credit the realm's stores" (§3.2 here).
- **§4.7 "The ladder of goods"** — unchanged, referenced here (§3.2).
- **§5 reinforcement bullets** mentioning transport-cost price gradients and the map's player-market economics — to be reworded per §6 here.
- **§6.5 / §6.6 open questions** — partially settled (treasury seeding approach, tax rate flatness); residuals inherited into §7.9 here.
