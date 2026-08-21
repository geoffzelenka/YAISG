# Yet Another Idle Skilling Game — Inter-Realm Economy Vision Document

**Version:** 0.6 (R29/R30 deferred to a realm-upgrades pass; the decay effect layer becomes an explicit seam. **No open ratifications remain in this document's scope** — ready for design.md v0.7 absorption)

**Changes from 0.5:** One deferral, handled as a seam rather than a gap. **R29 and R30 are parked pending a design pass on realm upgrades** — the question of what decay sheds depends on a system whose shape (tiers, slots, costs, prerequisites) is still open, and answering it from inside an economy document would bake assumptions the upgrades pass then has to work around.
- **New §6.7** records the deferral, the leading direction, and **five constraints that travel forward** so the upgrades pass inherits boundaries rather than a blank page: shedding must reduce upkeep, the terminal state must have zero upkeep, recovery is the ordinary forward path, nothing below Faltering may be irreversible, and the gauge does not reset on a shed step.
- **The leading direction — roll back tiers within upgrades before rolling back the realm's own tier, estates identically** — is captured with its implications. It lengthens the warning slide from a handful of steps to dozens, makes loss graduated rather than binary, and **may dissolve R30 rather than answer it**: if a tier-1 upgrade occupies the same slot as a tier-3, tier rollback never changes slot occupancy and the orphaned-upgrade state is unreachable by construction.
- **The Failing row is marked provisional** in both decay tables (§6.5, §7.6); everything else in both is settled.
- **The seam:** `shed(entity, magnitude)` as a pluggable effect handler. The stage machine, gauge, thresholds, transitions, signal layer, and recovery path all ship now. §14 flags that the Failing effect must not be inlined.

**Status:** every scope item of the pass is decided and **no ratification items remain open**. One question is deferred with an explicit seam and a constraint set; it does not block the `design.md` v0.7 absorption.

**Changes from 0.4:** The closing pass. R26–R28 approved as written, and the last four open questions settled:
- **Estate decay now mirrors the realm machine** (new §7.6) — same four stages, same accumulator, same reversibility, effects mapped onto upgrades instead of nodes. The unification carries §6.6's stability property with it: each uninstalled upgrade lowers the estate's own upkeep, so a degrading estate walks its draw down to a **zero-upkeep shell** and stops, exactly as a regressing realm composts to frontier. Two residuals fall out: **R29** (is anything truly lost) and **R30** (uninstall before shrinking capacity, so decay cannot manufacture an orphaned-upgrade state).
- **Reference prices stay fixed, with divergence telemetry** — a windowed volume-weighted book price compared per good against the content reference, so drift is visible and patched deliberately. Observability, not a mechanic.
- **Players travel safe, for now** — the §9.3 asymmetry stands as a feature, deferred rather than closed, with two guards recorded so nothing assumes cargo is permanently safe *or* at risk.
- **`map_edge_state` designed general from the start**, with persistence as a first-class column (R26 depends on it) and ownership passing to the Travel vision.

**Status:** every scope item of the pass is decided. The only open ratifications are R29 and R30, both narrow consequences of the estate-decay unification, and neither blocks the `design.md` v0.7 absorption.

**Changes from 0.3:** All outstanding ledger items resolved. The substantive change is structural, from the R21 review: **v0.2–0.3 were asking one per-realm number to do two incompatible jobs.**
- **§4 restructured.** **Remoteness is now terrain** — hard to traverse, mountainous, swampy, roadless — computed from the realm's own **incident edges** weighted by neighbour mass, replacing the whole-map gravity sum. It sets the local *price level*. Choosing *between sellers* is a separate, inherently pairwise quantity, **landed cost** (§4.3), which was already in §9.2 since v0.1 but never connected to the remoteness discussion. A per-realm scalar cannot express "the neighbour at 25 beats the realm three edges out at 24"; the pair can.
- **R21 dissolved rather than decided.** With a local measure, absolute normalization has no global-drift failure mode — a realm has bounded neighbours, edge costs have floors, and a swamp stays a swamp. Remoteness now falls only where someone actually built a road or a neighbour grew.
- **New volatility guard (R26).** Remoteness reads **persistent** edge modifiers only. R19's bandit events change *attrition and journeys*, never a realm's standing price level — otherwise every price board in the world twitches when a spawn table fires.
- **§9.2 answers a question the document never asked:** clearing is **demand-pull** — the needy realm shops, surplus realms never seek buyers — with the reasoning recorded (R27), plus a new **willingness-to-pay ceiling**: a realm never pays more per delivered unit than its own bid. Without it, severity ordering drives desperate realms into arbitrarily bad freight.
- **R23 resolved:** funded quantities published exactly, bands retained as the map-level summary. Both, each doing its own job.

**Changes from 0.2:** One correction, with consequences. **A realm may no longer publish a bid it cannot pay for** — the v0.2 rule (following market §3.3) let a broke realm show a price with zero affordable quantity, which is a false advertisement to any hauler who acts on it. §5.5 is rewritten around a **bid/need split**: a *bid* is executable and fully funded at the quantity shown, a *need* is a published, explicitly non-executable deficit, and a realm with no funds has no bid at all. This forced two additions and one recorded conflict:
- **New §5.6, the procurement allocation** — how one treasury is divided across many simultaneous hungers, by the same value weighting the deficit gauge already uses. v0.2 never specified this, and without it the first seller of the day drains the purse and every other published bid evaporates mid-session. Needed regardless of the funded-bid rule.
- **New §17, supersessions** — the funded-bid rule overturns ratified text in **market-vision §3.3** and **realm-vision §4.3**, both of which state that a broke realm posts real but unfunded demand. Their *intent* (starvation stays visible) is preserved through published needs; their *mechanism* is superseded and both documents need patching.
- **R23 (new):** publishing funded quantities makes treasury inferable, which collides with the Phase 4 never-expose rule and blunts what R16's bands were approved to do. Three options in §5.6; lean is to retire treasury secrecy for the procurement figure.
- §3.2 gains the companion rule (`UNFUNDED_DEMAND` alongside `NO_DEMAND`); §10 gains three degenerate rows; §5.7 narrows the health band's job now that bid credibility is structural rather than signalled.

**Changes from 0.1:** All sixteen ratification items from the v0.1 ledger received a decision. Fourteen approved as written; two amended, both in the direction of more dynamism:
- **R3 amended — remoteness is a live, relational, development-weighted value.** The static content-load scalar is replaced by a **gravity model over the map graph weighted by each realm's economic mass**, persisted as derived state and recomputed on node transitions — no downtime, no restart. *(Superseded in 0.4: the whole-map sum narrows to local incident edges — see the 0.4 notes above.)* As a wilderness realm develops, its neighbours become measurably less remote. §4.1 rewritten; one residual handed back (§15, R21).
- **R12 amended — caravan attrition accepts modifiers.** Cargo loss is a modifier-typed value with **map-edge scope**, so realm upgrades reduce it and world events (bandits on a road) raise it until players clear them. §9.3 rewritten; this is the pass's largest new engine surface and the economy's first hook for combat and exploration content.
- **§9.4 revised:** the NPC ceiling now sustains a realm to its reserve line rather than half of it, and the per-run volume cap becomes a **fixed trickle in days of consumption** rather than a fraction of the deficit — the deeper the crisis, the longer the floor takes, so the player advantage grows with severity.
- **§5.5 gains the behavioural read** the bands were approved on, plus the cascade risk as a watch item.
- **New: the estate larder (§7.5)** — a prepaid upkeep buffer letting a player provision their estate before a long absence. Restructures the store draw order (§6.2) around the reserve line, superseding v0.1's flat "estates first" rule with something better.
- **Open questions 1, 2, 4, and 5 settled**; #3 rewritten in plain terms after review found it unclear; #6 reclassified as a balance watch item; #9 folded into R3.

**Scope:** The realm side of the world economy as a running system — how a realm eats, what it will and won't sell, what it pays, how distance enters its prices, how it decays when it goes hungry, how estates settle against it, where a frontier realm's first gold comes from, and how the NPC balancing floor moves goods between realms. This document owns everything `design.md` §13.4 called the "upkeep-mechanics design pass," plus the two directions ratified in `market-vision.md` v1.2 (excess-only realm sales, travel-cost-aware bids) and the residuals consolidated into this pass (market-vision §7.2, §7.6, §7.8; realm-vision §6.4, §6.5, §6.6, §6.13).

**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't support, that is a design-doc work item (§14), not a license to improvise. Siblings: **Market Vision** (`market-vision.md` v1.2 — authoritative on the global book, the order-slot lifecycle, tax, and the three-layer price model this document makes concrete), **Realm & World Vision** (`realm-vision.md` v0.6 — realms, estates, decay philosophy, the goods ladder), **Visiting & Travel** (`visiting-and-travel-vision.md` v0.2 — the map journeys and per-edge supply costs the transport model reuses; **§7.5 here requires a patch to its §5.3**), **Skills and Goods** (supply side), **XP Curve**, **Combat** and **Exploration & Keys** (which §9.3 now gives an economic surface to). The future content design document turns this vision into concrete quotas, curve endpoints, cadences, and reserve multiples.

**Provenance:** This pass was the sole remaining blocker on the `design.md` v0.7 revision. It takes as given: no gold is ever minted and the treasury is a hard constraint (market §3.3); realm markets are presence-gated for trade and fully visible for reads (market §2.7, §3.5); realms sell only excess (market §3.1); realm bids price in travel cost (market §3.3); realm ticks live in the scheduled-job slot and per-character work stays lazy (design.md §8.3); the NPC floor cushions without out-competing haulers (market §4).

---

## 1. The elevator pitch

A realm is a stomach with a wallet. Every tick it eats a fixed diet, and everything else follows from that one number: what it will pay, what it refuses to sell, how long it has before things start going dark, and how far a hauler will travel to feed it.

The whole system is built out of a single derived quantity — the realm's **daily draw** per good. Reserve, storage cap, bid curve, ask, solvency gauge, decay stage, estate feeding priority, project contribution rate, and NPC import ceiling are all expressed as multiples of it. There is one price-level multiplier for distance, one spread constant between what a realm pays and what it charges, and one deficit accumulator that drives everything downstream. A player looking at a realm sees a pantry with a line drawn across it — *below this line is not for sale, and not for feeding private estates* — and a price that climbs as the pantry empties. A player looking at the map sees that line drawn higher, and those prices set richer, the further out they go — and sees the map's distances **shrink as the frontier gets settled**.

Nothing here mints gold. Nothing here rescues a realm that nobody helps. And nothing here can pay a player to stand still.

---

## 2. The primitives everything else is built from

Five derived quantities, defined once. Every mechanism below is stated in terms of them, which is what keeps the knob count down and the degenerate cases enumerable (§10).

**2.1 Draw.** `draw[r,g]` — realm `r`'s consumption of good `g` per day, authored in content on the development node, applied per tick as a fraction. Authoring per-day and ticking per-hour means the cadence is a config number rather than a content re-authoring. The draw vector is the realm's identity expressed as appetite; the goods ladder (realm §4.7) is content authoring the full vector at each node rather than deltas, so a node's tier-1 draw visibly exceeds its predecessor's. **Active projects add a temporary overlay to the draw** (§3.5).

**2.2 Reserve.** `reserve[r,g] = R × draw[r,g]`, a **runway in days**. The reserve line does three jobs, and the unification is deliberate: stores at or below it are **not for sale at any price** (§3), are **not available to feed private estates** (§6.2), and are **not available to commit to projects** (§3.5). It is the realm's line between what it has and what it can spare.

**2.3 Cap.** `cap[r,g] = C × draw[r,g]`, a **pantry ceiling in days of runway**, with `C > R`. The cap does the "stop buying" job: a realm will not buy past it, and stores clamp there. For goods with no draw, the cap comes from a content floor instead (§3.3).

**2.4 Haul cost.** `haul_cost(a, b)` — a single scalar cost of moving one unit of goods between two realms, the summed edge weights along the cheapest path over the map graph, derived from the existing Phase 4 `path_cost` plus the per-edge supply modifier the Travel vision added (visiting §4.1). **One function, three consumers:** the remoteness model (§4), the NPC balancing layer's sourcing (§9.2), and its attrition (§9.3). This prevents the map from acquiring several disagreeing notions of distance.

**2.5 Price level.** `M[r] = 1 + P × remoteness(r)`, a per-realm multiplier applied to *both* sides of the realm's quotes (§4). `remoteness(r) ∈ [0,1]` is live derived state, recomputed when the world's shape changes (§4.1).

---

## 3. Excess-only sales

### 3.1 The reserve line

A realm quotes an ask on good `g` only for `surplus = max(0, store[r,g] − reserve[r,g])`, and can never be traded below its reserve. A realm never starves itself to serve a customer, and "buying a realm dry" is impossible by construction — the deeper claim market §3.1 was reaching for.

`R` is a **runway in days**, which is the unit that makes the number arguable: "this realm keeps a week in the pantry" is a sentence a content designer can defend, where "this realm reserves 340 grain" is not. Illustrative: `R = 7`, `C = 30`, so a realm sells only out of the top three-quarters of its pantry range.

**Global default with a per-development-node override.** Reserve runway is a caution trait, which is properly an identity property — a frontier outpost hoards, a trade-hub node runs lean because resupply is cheap. It resolves through the same source-resolution pass as modifiers and caps (design.md §7.1), so the engine cost is a lookup. The guidance to content design is to leave it global unless there is a *reason*, since a per-realm reserve is a knob that silently changes what the map looks like to a hauler.

**Pending transitions raise the reserve.** When `realm_state.pending_transition` is set, the effective draw is `max(current_node.draw[g], pending_node.draw[g])`. Without this, a realm sells its pantry the day before its appetite doubles, and the first thing a newly-developed realm does is starve. One line, and it removes a whole class of "the realm bankrupted itself on moving day" bug reports.

### 3.2 Realms do not buy what they do not need

**No draw, no bid.** A realm quotes a bid on `g` only where `draw[r,g] > 0` (including the project overlay, §3.5). Attempting to sell a good the realm has no appetite for fails cleanly (`NO_DEMAND`) rather than trading at a floor price.

**No funds, no bid** *(0.3)*. The companion rule: a realm publishes a bid only where it has treasury allocated to honour it (§5.5, §5.6). Appetite and funding are both necessary, and neither alone produces a tradeable offer — `NO_DEMAND` when the realm does not want the good, `UNFUNDED_DEMAND` when it wants it and cannot pay.

This is load-bearing in a way that is easy to miss: without it, every realm is an infinite gold sink for junk, and the treasury — which no mechanism refills except real commerce — is drained by players dumping whatever is cheapest on the global book. With it, the only routes into a realm's stores are estate production (§7), the NPC balancing layer (§9), and player sales of goods the realm actually eats. That closure is what makes the store level an honest signal.

### 3.3 Goods the realm never consumes

**Fully excess, but capped in storage.** For `draw[r,g] = 0`: `reserve = 0` (everything is sellable, down to the last unit) and `cap[r,g] = idle_cap`, a content floor. This is the forest realm's timber: it eats none of it, it sells all of it, and its warehouse still has a roof.

Production credited above the cap is **lost** — the store clamps, and the signal layer shows the good at capacity. This is deliberate: a realm sitting at cap is visibly advertising "come buy this," and the loss is the pressure that makes someone show up. It is also a quiet, honest sink on overproduction in a well-developed realm.

The graceful-degradation consequence matters (§10): the bid curve's domain is `store/cap`, never `store/draw`, so a zero-draw good never divides by zero — it simply has no bid side at all.

### 3.4 Everything above the reserve is sellable

No separate "identity goods" sell-list. Any good above its reserve can be bought from the realm. This is simpler than a curated list, avoids goods getting stranded in stores with no exit, and costs nothing — identity already determines what is ever *in* surplus, because identity determines what the local estates produce (§7) and what the realm's own draw eats. A separate list would restate the same fact in a second place, where it could disagree.

### 3.5 Projects: the realm as a slow contributor of last resort

*(Settles v0.1 open questions #1 and #2 in the direction ratified in review: realms may help fulfil their own projects, and treasuries may fund them, on the condition that the per-tick rate is bounded.)*

An active project creates a **demand overlay** on the draw vector, and the overlay is expressed as a *rate*, which is what makes the whole thing fall out cleanly:

```
overlay_draw[g] = remaining_requirement[g] / T_unaided
```

`T_unaided` is a content horizon in days — how long the realm would take to complete this project entirely on its own. That single number does all the work:

- **It creates demand.** The overlay adds to `draw`, so the realm now bids for project inputs it may not otherwise eat, and reserve and cap scale with it. Project goods get a real market, funded by treasury, exactly as design.md §5.5 always said they should.
- **It is also the commit rate.** The realm commits `overlay_draw[g]` per tick from stores **above the reserve line**, so buying and committing are the same number and the store does not silently accumulate goods with no exit.
- **It self-damps.** Player contributions reduce `remaining_requirement`, which lowers the overlay, which lowers the bid. A project the community is actively feeding does not also get bid up by its own realm.
- **It bounds the risk.** `T_unaided` is the "does the realm delete player contribution as a verb?" dial, and it should be set so unaided completion takes a large multiple of assisted completion — the realm is a floor under the project, not a substitute for the community.

Two closures worth stating. **This is not a remote-contribution loophole:** the realm commits its own goods on its own schedule and no player can direct it, so the presence gate on player contributions (realm §6.3) is untouched. And **a ghost town cannot develop itself**, because the overlay is funded by treasury, treasury comes from tax, and tax comes from player trade — the loop still requires people.

---

## 4. Travel-cost-aware pricing

### 4.1 Two jobs, two quantities — the split R21 forced

*(Rewritten in 0.4. The R21 review identified that v0.2–0.3 were asking a single per-realm scalar to do two incompatible jobs. It cannot, and the fix is to stop trying.)*

The two jobs:

| | Job | Shape | Answers |
|---|---|---|---|
| **Remoteness** `remoteness(r)` | Sets the local **price level** `M[r]` | Per-realm scalar | *How expensive is it to get anything into this place at all?* |
| **Landed cost** `landed(s→r)` | Chooses **between sources** | Pairwise | *Which of these two sellers is actually cheaper for me?* |

A per-realm scalar **cannot** express the second. The review's example makes this concrete: a neighbour selling at 25 should beat a realm three edges away selling at 24, and no property of the *buyer* alone can decide that — the answer lives in the pair. Conversely, a pairwise cost cannot set a price level, because a realm's prices must be one number, not one per counterparty.

Splitting them dissolves R21 rather than deciding it (§4.2), and it turns out the second half was already specified — it has been sitting in §9.2 as the NPC sourcing rule since v0.1, never connected to the remoteness discussion. §4.4 unifies them.

### 4.2 Remoteness is terrain, not centrality

**Reframed per R21:** remoteness is *hard to traverse* — mountainous, swampy, roadless, undeveloped — not *far from the economic centre*. This is a better fit for what the premium is paying for, and it is the reading the review asked for: a realm bearing a genuine physical cost to supply is a realm that should carry a higher price level.

The model narrows from a whole-map gravity sum to a **local accessibility** measure over the realm's own incident edges:

```
local_access(r) = Σ_{n ∈ neighbours(r)} mass(n) / edge_cost(r, n)
remoteness(r)   = clamp( 1 − local_access(r) / A_ref , 0, 1 )
```

`mass(n)` is the content-declared economic weight of neighbour `n`'s current development node; `edge_cost` is the base map edge cost plus **persistent** modifiers only (see the guard below). Three channels lower a realm's remoteness, and each is something players do:

- **Better roads.** Development nodes and realm projects that reduce incident edge costs. A realm can *invest in being less remote*, which pairs directly with the caravan-attrition upgrades of R19 — the same road project improves both.
- **Neighbours growing.** A developing neighbour raises `mass(n)`, so **settling a wilderness realm measurably de-remotes the realms around it.** This preserves R3's intent and its example — the foothills city is not remote, because the mountain city is next door — through a one-hop relation rather than a global sum.
- **The realm's own development,** where its node improves its own approaches.

**Why local beats the v0.2 whole-map gravity sum.** The old model made a realm's price level depend on development happening anywhere on the map, which is both hard to explain and the source of R21's normalization problem. Local accessibility is *causally legible*: your prices fell because your roads improved or your neighbour grew, both of which someone visibly did. It is also cheaper — neighbours, not all-pairs shortest paths.

**Still rejected: live distance-to-nearest-*surplus*.** The v0.1 objection stands unchanged. Surplus-driven remoteness makes every quote a global computation over realms × goods; it is *unstable*, because a bid jumps when some distant realm crosses its reserve threshold for unrelated reasons; and it is unexplainable — "why did the price drop?" / "a realm you have never visited had a good harvest."

**The volatility guard, which matters more now that edges are mutable (R19).** `edge_cost` here reads base costs plus **persistent** modifiers (roads, development, permanent terrain) and **ignores transient event modifiers** (bandits, seasonal closures). Bandits on a pass raise *caravan attrition* and *travel cost*; they do **not** move a realm's standing price level. Without this guard, R19's event system would make every realm's price board twitch whenever a spawn table fired — reintroducing exactly the volatility that got live-surplus rejected. The separation is clean: **events change what a journey costs; development changes what a place costs.**

**Where it lives:** persisted derived state on `realm_state`, recomputed on any node transition (forward or regression, at `finalize_realm`), on any persistent edge-cost change, and refreshed by the tick job as a self-heal. Not a boot-time content cache — **no restart, no downtime**, which was R3's requirement. Exposed on `GET /map`.

**R21 resolved: absolute normalization, and the question dissolves.** `A_ref` is a fixed content constant. The v0.3 worry — that a maturing world drifts globally toward `M = 1` and the premium quietly stops existing — was an artefact of summing the whole map. A local measure has no such drift: a realm has a bounded number of neighbours, edge costs have floors, and a swamp stays a swamp. Remoteness now falls only where someone actually built something, which is the reward the design wanted, delivered without the runaway.

### 4.3 Landed cost: how a buyer chooses between sellers

The pairwise half, stated here as a first-class concept because §9.2 was quietly relying on it:

```
landed(s → r, g, q) = ask(s, g, q)  +  haul_cost(s, r) × q     ... per unit delivered:
landed_per_unit     = landed(s → r, g, q) / (q × (1 − attrition_pct(s → r)))
```

The review's example resolves directly: the neighbour asking 25 at haul cost 1 lands at 26; the realm three edges out asking 24 at haul cost 5 lands at 29. **The neighbour wins, and cheaper-but-further correctly loses.** Attrition (§9.3) makes the gap wider still, since the distant shipment also arrives lighter.

Two properties worth naming. **Landed cost is asymmetric** — `landed(A→B) ≠ landed(B→A)`, because the asks differ even when the haul cost does not; the hungry realm is the expensive one to sell *to* and the cheap one to buy *from*, which is the arbitrage gradient the whole economy runs on. And **it needs no new machinery**: `ask` is §5.1, `haul_cost` is §2.4, attrition is §9.3.

### 4.4 One map cost, three consumers

`haul_cost(a,b)` now visibly serves everything, which is the payoff for having insisted on a single function in §2.4:

| Consumer | Uses | Direction |
|---|---|---|
| **Remoteness** (§4.2) | Incident edge costs only, persistent modifiers only | Per-realm |
| **Landed cost** (§4.3) | Full path cost | Pairwise |
| **Attrition** (§9.3) | Full path cost, **including** transient event modifiers | Pairwise |

The one deliberate inconsistency is the third row's inclusion of event modifiers where the first excludes them — and it is the guard from §4.2, not an oversight. Prices are a property of places and should be stable; journeys are a property of the moment and should not be.

### 4.5 The premium applies to both sides

`M[r] = 1 + P × remoteness(r)` is a price *level*, not a spread adjustment — it moves the whole local price board and leaves the ratio between the two sides untouched. Illustrative `P = 0.4`.

Three reasons, in order of weight:

1. **It preserves the no-arbitrage margin by construction.** A multiplier common to both sides cancels out of the bid-vs-ask comparison entirely (§5.3). Bids-only inflation pushes the bid *toward* the ask precisely where the market is thinnest and the margin least defensible.
2. **A discount on remote asks would be a subsidy for stripping the frontier.** It pays players to extract cheaply from the realms the economy is trying to bootstrap, and drains exactly the stores the frontier's own treasury depends on selling (§8). It points goods the wrong way down the map.
3. **It reads correctly.** Everything is dear out here. You are paid well to bring goods to the frontier and you pay through the nose to buy anything there.

The ratified direction survives intact: remote realms' bids carry a premium, and that premium is the hauler's wage. The hauler's loop is unharmed, because its profit comes from the *scarcity* gradient (an empty realm bids far above a full one on the same price board) and the remoteness gradient adds to it in the correct direction: buy cheap from a well-stocked, central realm; sell dear into a hungry, remote one. The reverse trip is deeply unprofitable, which is the point.

### 4.6 Where the premium actually bites

An emergent result rather than a designed one, and a good one: **the premium's economic bite concentrates on off-book realms.**

A realm carrying market access has a competing frictionless supply channel — any resident can buy on the global book at world price and sell into the local bid without travelling. That is not a hole to be plugged; it is the metabolism working (gold flows tax → treasury → player, goods flow player → realm → destroyed, nothing minted), and it means an on-book realm's procurement cost is bounded near world price. Arbitrageurs refill its stores fast, walking its bid back down the curve, and its nominal premium is rarely paid in full.

A realm *without* access has no such channel. Everything it imports arrives in someone's pack. Its premium is paid in full, every time. So the travel premium's real job — recruiting haulers with money — lands exactly on the frontier, which is exactly where the hauler loop lives. It also sharpens the losable-access mechanic: falling off the book means your realm starts paying the remoteness premium for real.

---

## 5. The quote function and the no-arbitrage property

### 5.1 One curve

Let `f = store[r,g] / cap[r,g] ∈ [0,1]`.

```
bid_mult(f) = bid_min + (bid_max − bid_min) × (1 − f)^γ
bid(r,g)    = reference_price[g] × M[r] × bid_mult(f)
ask(r,g)    = bid(r,g) × (1 + m)
```

`γ > 1` gives the desperation shape: flat and cheap across most of the pantry range, spiking only as it empties. Illustrative `bid_min = 0.3`, `bid_max = 2.2`, `γ = 2`, `m = 0.25` — a full realm pays 0.3× reference and sells at 0.375×; an empty one bids 2.2× reference, treasury permitting.

**The ask is not an independent curve.** Defining it as a markup on the realm's own bid collapses two curves into one, makes the ask inherit the scarcity signal for free (a realm whose stores are draining stops being a cheap source at exactly the moment it starts getting hungry), and — see §5.3 — makes the no-arbitrage constraint a structural property rather than a thing to verify.

`m` is the realm's merchant margin, a global content default with a per-node override. A trade-hub identity running a tighter spread is a good content lever and costs nothing to support.

### 5.2 Quantity-aware pricing, from day one

**Realm trades are priced by integrating the curve over the traded quantity, not at spot.** Selling 500 grain into a starving realm does not fill 500 units at the empty-store price; it walks the curve up as the store fills, exactly as a large order sweeps an order book (market §2.2). Same on the ask side, walking down.

```
total = reference_price[g] × M[r] × cap[r,g] × ∫[f₀→f₁] bid_mult(f) df
```

For polynomial `bid_mult` this has a closed form — nobody should write a per-unit loop. The treasury clamp (largest `q` whose total is affordable) is a bounded integer binary search.

This is a Phase 5.C seam item (§13) because it is the one thing here that cannot be retrofitted cheaply: spot-priced and curve-integrated quotes differ in signature, response shape, and every test. Without it, the desperation price is a free money button — a single player sells the realm's entire daily quota at the empty-store rate.

### 5.3 No-arbitrage, by construction

The constraint — *every realm's ask must exceed its own travel-inflated bid, or a player mills the spread standing still* — is satisfied structurally rather than by verification, for three compounding reasons:

1. **The remoteness multiplier cancels.** `M[r]` is common to both sides, so travel-inflated bid vs. travel-inflated ask is just bid vs. ask.
2. **The markup is a scalar, so it commutes with the integral.** `∫ask = (1+m) × ∫bid` at *every* quantity, not merely at the margin. A round trip of any size loses exactly `m × ∫bid`. A two-independent-curves design would have had to prove this numerically across the whole state space, and would eventually have failed at some corner.
3. **The reserve gate blocks the profitable half anyway.** Below the reserve there is no ask at all, so the region where the bid is highest is the region where nothing can be bought.

The engine cannot express a crossed realm quote. That is worth more than a passing test.

### 5.4 The one arbitrage that does exist, named honestly

*(Reclassified from an open question to a balance watch item — it is a known, bounded phenomenon awaiting play data, not a question needing an answer.)*

A player can sell into a realm while it is hungry (high bid), wait for *other* players to over-supply it past its reserve, and buy the surplus back cheap. The realm's treasury is net down on the cycle.

This is bounded and it is not a mint: the curve integral prevents selling volume at the desperation price; the buy-back requires the store to be above reserve, which by then means the bid was long since low; and the profit is funded by the late suppliers' poor timing, not by created gold. It is, structurally, ordinary market-making — and the realm is a bad trader by design, because it is a metabolism rather than a merchant.

**The tuning lever is `R`.** A higher reserve runway means less is ever for sale and the loop has less to work with; the cost is that realm sales become rare and the hauler's cheap-source leg dries up. The escalation, if it proves real in play, is `ask ≥ reference_price × M[r]` — an ask floor at the world anchor — noting that the floor blunts the hauler's buy-side in the same motion, which is why it is not the default.

### 5.5 Every bid is funded: the bid/need split

*(Rewritten in 0.3. **This supersedes ratified text in two sibling documents** — see §17. Market §3.3 and realm §4.3 both state that a broke realm "posts real but unfunded demand" and that its stores "visibly starve even at attractive nominal prices." That is no longer the rule.)*

**A realm never posts a bid it cannot pay for.** The realm publishes two different things, and conflating them was the error in v0.2:

- **A bid is an executable offer.** It carries a price *and* a quantity, and the realm is good for both: every unit of the published quantity is backed by allocated treasury (§5.6) and by cap headroom. **A bid is always fillable at the quantity shown.** If the realm cannot fund a single unit, **there is no bid at all** — not a bid of zero quantity, not a greyed-out price. Nothing.
- **A need is a published deficit.** The coverage gap, shown with a notional value at reference price, marked explicitly non-executable. This is what a broke realm shows instead of a bid.

**Why this is stricter than the no-debt pillar requires, and right anyway.** Strictly, a displayed price with nothing behind it creates no obligation, so §9.2's no-credit rule was never violated — a trade against an unfunded bid partial-fills to zero and nothing is owed. But that is a technicality that protects the ledger and not the player. A hauler reads the signal layer, buys cargo, travels three realms, and discovers the price was decorative. **An unfillable bid is a false advertisement, and the signal layer's entire job is to be worth believing.** The no-debt pillar and the honest-signal principle point the same way; this rule serves both.

**What the superseded sections actually wanted survives.** Market §3.3's intent was that *starvation stays visible* — that a realm's inability to feed itself is legible to everyone. That is fully preserved, and arguably sharpened: "this realm needs 400 grain and cannot pay for any of it" is a clearer and more actionable statement than a phantom price that looks tradeable. What dies is only the misleading part. The dark-mirror loop of market §3.3 (ghost town → no tax base → dry treasury → weak bids → decay) is untouched; the weak bid simply becomes an *absent* bid, which is a stronger signal, not a weaker one.

**The knock-on benefit for the hauler loop.** Because published bid quantity is funded quantity, a hauler's run is never wasted by realm insolvency. Partial fills still happen — another player got there first between ticks — but that is ordinary market racing, the same thing the global order book does, and it is not the realm lying. The distinction matters: players tolerate losing a race and do not tolerate being misled.

### 5.6 The procurement allocation: one purse, many hungers

*(New in 0.3. Forced by §5.5, but needed regardless — v0.2 never said how a realm splits its treasury across simultaneous needs, and without a rule the first seller of the day drains the purse and every other bid evaporates mid-session.)*

At each tick, the realm divides its treasury across its unmet needs, using the **same value weighting as the deficit gauge** (§6.4):

```
weight[g]     = reference_price[g] × unmet_draw[g]
allocation[g] = treasury × weight[g] / Σ weight
funded_qty[g] = largest q where ∫bid over q ≤ allocation[g]     (§5.2)
```

Reusing the gauge's weighting is deliberate: the realm spends hardest on whatever is hurting it most, which is both the intuitive behaviour and the one that minimizes gauge accrual. It needs no new content knob.

Allocations are recomputed each tick and consumed by sellers between ticks. A realm holds back nothing — an unspent allocation simply returns to the pool at the next tick and is redistributed.

**The consequence, and the decision it forces (§15, R23).** A published funded quantity reveals treasury: quantity × price recovers the allocation, and summing across goods recovers the balance. That directly collides with the Phase 4 rule that treasuries are never exposed, and it means R16's coarse bands can no longer do the job they were approved for. Three ways out, in order of preference:

1. **Retire treasury secrecy for the procurement figure.** Publish funded quantities exactly; keep the raw balance out of every response but accept that it is inferable. Simplest, most honest, and the Phase 4 rule predates any reason to expose it. Health bands survive as the at-a-glance summary, not as a privacy device.
2. **Bucket published quantities coarsely.** The realm honours up to the bucket; the leak is bounded by bucket width. Costs precision in exactly the number a hauler most wants to be precise.
3. **Publish bid price and a fundedness band only, with quantity discovered at the trade.** Preserves secrecy fully, but re-opens the wasted-run problem in a smaller form — the hauler knows the realm can pay for *something* and not how much.

**Resolved (0.4): option 1, and the bands survive alongside it.** Review raised no objection to a realm's wealth being legible — that one realm holds a million gold and another twenty-five is public, useful information — and no objection to bands either. So both ship, each doing the job it is actually good at:

- **Funded bid quantities are published exactly.** This is the number that must be honest, because it is the one a hauler loads cargo against (§5.5). Precision here is the whole point.
- **The health band survives as the map-level summary**, not as a privacy device. It is what makes a map readable without opening thirty realm panels, and it is what distinguishes *no bid because fed* from *no bid because broke*.
- **The raw treasury balance stays out of every response**, per the Phase 4 rule, while being inferable from the procurement figure. That is an accepted, deliberate leak rather than an oversight.

Worth noting what actually leaks: the allocation is what a realm is **currently spending**, not what it holds. A realm with small needs may sit on gold it has not allocated, so the inference is closer to "this realm's current procurement budget" than "this realm's net worth.

### 5.7 What players do with the signal

**Exposed exactly:** prices, store quantities, per-good coverage, funded bid quantities (pending R23), published needs. **Exposed coarsely:** the treasury health band (five buckets, e.g. `flush / funded / tight / strained / broke`), carrying **hysteresis** — the threshold to leave a band sits above the threshold to enter it — so a realm hovering at a boundary does not flicker on every map view.

**What the band is for, now that bids are honest.** With unfunded bids gone, the band no longer has to warn players away from a lie. Its job narrows and clarifies: it is the **at-a-glance summary** that makes a map readable without opening every realm, and it is what distinguishes *no bid because the realm is fed* from *no bid because the realm is broke* — two states that look identical in the bid list and mean opposite things. Store level says *hungry*. The band says whether hunger is a **commercial** opportunity or a **civic** one:

- **Funded + starving** → the realm will pay well and can. Haulers go, now. This is the signal the economy exists to broadcast.
- **Broke + starving** → hauling there is charity. What the realm needs is a patron (§8.4), a project completed, or residents whose trade generates tax. Capital, not crates.
- **Funded + fed** → a cheap source. This is where the hauler buys.
- **Broke + fed** → stable but fragile; nothing to do, and nothing wrong yet.

**The bid's credibility is now structural, not signalled.** In v0.2 the band's job was to warn players off a bid that might not fill; under §5.5 that bid no longer exists, so the guarantee moved from the presentation layer into the mechanism — which is where it belonged. The band's remaining jobs are real but narrower: it makes the patronage endpoint targetable (you cannot aim a gift without knowing who is broke), it turns the map into the tycoon's prospectus in the specific way realm §3.5 promised, and it distinguishes the two silences — a realm with no bids because it is *fed* versus one with no bids because it is *broke* — which the bid list alone cannot do.

**Does it make players save the realm, or flee it?** Mostly neither on its own — it makes the choice *early and legible*, which is what realm §2.7's "slow, visible slide with ample warning" is for. Flight is expensive for exactly the players whose departure would hurt most (moving a rooted estate is a project, realm §3.1), so the cheaper response for a resident is usually to fix it. And the two-signal split means "broke" is not a death sentence a player should run from: a broke-but-fed realm is fine, and a funded-but-starving realm is an opportunity, not a warning.

**Watch item — the cascade risk.** Public health information can be self-fulfilling: a realm ticking to `strained` may trigger preemptive withdrawal, less trade, less tax, and a deeper strain. Four things dampen it, and they should be understood as load-bearing rather than incidental: bands are coarse, so small movements are invisible; hysteresis prevents flicker; treasury health and store health are **separate** signals, so no single number reads as doom; and regression is a stabilizer (§6.6), so the worst case is a realm becoming smaller, not a realm dying. If cascades appear in play, the first lever is coarser bands, not hidden ones — the answer to a bad signal is never a missing signal.

---

## 6. Upkeep mechanics

### 6.1 Cadence, and why the tick is lazy too

**Hourly ticks, quotas authored per day.** Realms are few, the per-tick work is arithmetic, and an hour is fine-grained enough that decay is a slide rather than a staircase while remaining coarse enough to be free. Content authors day-rates; the engine divides. Cadence becomes a config value nobody has to re-author content to change.

**`resolve_realm(realm, now)` is lazy and idempotent, exactly like `finalize_realm`.** The realm carries `last_tick_at`; resolution computes elapsed ticks and applies them in one catch-up pass. The scheduled job (design.md §8.3) is a **liveness driver**, not the mechanism: it exists to guarantee that decay and regression progress in realms nobody is reading. Any read path may resolve first.

This matters for correctness, not elegance: without it, a bid quoted at 03:00 by a late or crashed job reflects 02:00 stores, and the signal layer — which the entire hauler recruitment story rests on — lies. It is also the same pattern already proven in Phase 4.

### 6.2 The tick, in order — and who eats first

*(Restructured from v0.1's flat "estates draw before the realm" rule, which the estate larder (§7.5) improves on. The reserve line replaces the flat priority with a boundary.)*

1. **Estate production** credits stores (§7).
2. **Estate upkeep** draws from the estate's own **larder** first (§7.5).
3. **Estate upkeep** shortfalls draw from realm stores — **but only down to the realm's reserve line.**
4. **Realm upkeep** draws from stores, and *may* go below the reserve line: the reserve is a floor on what a realm will *spare*, never on what it will *eat*.
5. **Project commitment** (§3.5), only from stores above the reserve line.
6. **Spoilage** applies (§6.3).
7. **Caps clamp**; overflow is lost.
8. **Gauges update** — realm and per-estate (§6.4, §7.4).
9. **Decay state machine** advances or recovers (§6.5).
10. **Regression edge progress** accrues or drains (§6.6).

**The rule, stated once: estates have priority above the reserve line; the realm has priority below it.** This is strictly better than either flat ordering, and it is why:

- Above the line, estates eat first, which preserves v0.1's anti-spiral property. If the realm ate first, estates would starve, go dormant, stop producing, and deepen the shortage next tick — a spiral. Estates first means production is preserved and the realm absorbs the shortfall as a *slide*, with its own gauge as the warning.
- Below the line, the realm eats first, so private estates cannot consume a starving town's last grain. Communal survival outranks private production once things are genuinely bad.
- And the transition between the two regimes is exactly the moment a player should be stocking their larder — which is a lever they have, readable off a public signal, with a deadline they can see coming.

The reserve line now gates sales, estate feeding, and project commitment with one number. That unification is the reason to prefer it.

### 6.3 Store caps and spoilage

Consumption alone does not make demand perpetual: one heroic dump of a million grain buys a decade of runway and switches off a realm's grain market. Two bounds fix it, and both are useful independently.

- **Caps** (§2.3) bound the pantry. The realm will not buy past `cap`, and stores clamp there. This also gives the bid curve a well-defined domain.
- **Spoilage**, a per-good content rate defaulting to zero, applies a proportional per-tick loss. This makes food demand genuinely perpetual while ingots sit fine forever, and hands content design a clean dial on which goods have a *standing* market versus an occasional one. It is also a sink.

### 6.4 The solvency gauge: a value-weighted deficit accumulator

Not an instantaneous ratio. Per tick:

```
unmet_value    = Σ_g reference_price[g] × (tick_draw[g] − consumed[g])
total_value    = Σ_g reference_price[g] × tick_draw[g]
deficit_ratio  = unmet_value / total_value        (:= 0 when total_value = 0)

gauge += deficit_ratio                            if deficit_ratio > 0
gauge  = max(0, gauge − recovery_rate)            otherwise
```

The gauge's unit is **tick-equivalents of total starvation**, which is a phrase a player can be shown: *"this realm has been short the equivalent of three days."*

An accumulator rather than a threshold on a current value gets several things for free that the alternatives make you build. Grace periods are implicit — the counter must build before anything happens. The "which good is missing" problem answers itself, because value-weighting means missing an expensive input accrues faster than missing a cheap one, without a hand-authored weight vector. And min-over-goods (one missing good kills the realm) versus mean (a realm coasts while starving one input) stops being a dilemma, because *duration* carries the weight severity alone cannot.

Per-good coverage (`store / reserve`) stays exposed in the signal layer separately, because *which* good is short is precisely what a hauler needs to know.

### 6.5 The decay state machine

| State | Trigger | Effect |
|---|---|---|
| **Fed** | gauge = 0 | Normal operation. |
| **Strained** | gauge ≥ T1 | **Signal only — no mechanical effect.** Publicly visible on the map and realm panel. |
| **Faltering** | gauge ≥ T2 | Node modifiers scale down by a decay penalty; communal facility tags suspend. Fully reversible, nothing lost. |
| **Failing** | gauge ≥ T3 | *Provisional (§6.7)* — something is shed, at a rate proportional to the gauge. v0.5 said "regression edge progress accrues"; the leading candidate is now **upgrade-tier rollback first**, with node regression as the last resort. |
| **Regressed** | shedding exhausted | Node swaps backward through the existing transition machinery. |

**Strained must stay purely cosmetic.** It is the recruitment stage — the window in which the signal layer summons haulers and the community notices, before anything is taken away. A realm that suffers the moment it dips is a realm whose players learn to hoard rather than trade.

Recovery walks back down: below `T3`, accrued shedding progress *drains* at a content rate rather than being lost or refunded, so a rescued realm re-climbs from where it fell to. Only completion is irreversible — and even then, the forward path is the ordinary morphing route through projects, which is the renewal cycle working.

**The first four rows are settled; the fourth row's *effect* is not.** See §6.7 — this is a seam, not a blocker.

### 6.6 Regression coupling, and why it is a floor rather than a death spiral

**The stability property, stated explicitly because everything rests on it: regression reduces appetite.** The new node's draw vector is smaller, so coverage jumps the moment the swap lands, the gauge stops accruing, and the realm stabilizes at its reduced identity. Decay is self-limiting. A realm cannot spiral to nothing; it composts down to frontier and stops.

Two invariants make that guarantee real, and both are checkable rather than hoped for:

- **Every regression chain's base node has zero upkeep.** A wild realm has nothing built to feed. With zero draw, `deficit_ratio` is 0 by definition and the gauge can never accrue — the terminal state is provably terminal. **Boot-time content validation item.**
- **The gauge does not reset on regression** — it drops to a partial value. The realm is still hungry the morning after; it just has less to be hungry about.

Engine coupling: `award_edge_progress` currently rejects regression edges. It gains a **system-driven path** usable only by the tick — players can never award regression progress, in either direction. The swap reuses `finalize_realm` unchanged, which is also where `remoteness` recomputes (§4.1). Per design log #21, the gauge must not award during a pending transition; it holds and accrues. A forward transition in flight is **not** cancelled by decay — it completes, and the gauge resumes driving afterwards.

---

### 6.7 What decay sheds: deferred to the realm-upgrades pass

*(Deferred in 0.6. R29 and R30 are parked, not answered — the question belongs downstream of a design pass on realm upgrades that has not happened yet, and answering it here would be guessing at a system whose shape is still open.)*

Everything about the decay machine is settled **except what happens at the Failing stage.** The gauge (§6.4), the four stages, the thresholds, the signal-only recruitment window, the reversibility, and the terminal guarantees (§6.6) all hold regardless. What is open is the *granularity* of what gets shed and whether it is ever permanently lost.

**The leading candidate, from the deferral discussion: roll back tiers before rolling back tiers.** Decay walks down the *tiers within* upgrades first, and only when that is exhausted does it touch the realm's node — and estates follow the identical strategy at their own scale.

```
Failing (realm):   shed upgrade tiers, one step at a time
                   → tiers exhausted → node regression edge accrues → node swaps back
Failing (estate):  shed upgrade tiers, one step at a time
                   → tiers exhausted → form/level rolls back → shell
```

**Why this looks better than what v0.5 proposed, without committing to it:**

- **It lengthens the slide substantially.** A realm with a dozen upgrades at three tiers each has thirty-odd shedding steps before its node is threatened. Every one is a visible warning and a hauler-recruitment window, which is what §2.7's "ample warning" philosophy is actually asking for.
- **It makes loss graduated rather than binary.** Losing a tier is a setback; losing an upgrade outright is a punishment. The idle-game-friendly default is the former.
- **It may dissolve R30 entirely.** My v0.5 rule (uninstall before reducing capacity, so decay cannot manufacture an orphaned-upgrade state) exists only because whole-upgrade removal interacts with slots. If a tier-1 upgrade occupies the same slot as a tier-3, **tier rollback never changes slot occupancy and the orphan state is unreachable by construction** — a better answer than an ordering rule, arrived at from a different direction. Worth confirming against whatever the upgrades pass decides about slots.
- **It preserves the stability property** (§6.6), provided the content invariant below holds.

**Constraints the upgrades pass must honour, whatever it decides.** These are load-bearing here and should not be re-litigated downstream:

1. **Shedding must reduce upkeep.** §6.6's guarantee — decay is self-limiting because *regression reduces appetite* — depends on each shed step lowering the draw. Content invariant: an upgrade's tier-`N` upkeep must exceed its tier-`N−1` upkeep, boot-validated, the same check shape as R11's base-node rule.
2. **The terminal state must have zero upkeep.** A bare node and a bare estate shell cost nothing to hold. This is what makes the bottom provably terminal.
3. **Recovery is the ordinary forward path.** Rebuilding a shed tier is an ordinary purchase, at ordinary cost. No repair mechanic, no penalty, no separate currency.
4. **Nothing below the Faltering stage may be irreversible.** Signal-only and dormancy stages must remain lossless.
5. **The gauge does not reset on a shed step** — it drops to a partial value, so a realm that sheds once and is still starving keeps sliding.

**Suggested for the pass, not decided here:** shed order across multiple upgrades. Value-weighted — shed the tier carrying the most upkeep first — would maximise relief per step and reuse the deficit gauge's existing weighting (§6.4), which would keep the knob count flat. Cheapest-first and player-designated order are the alternatives.

**This is a seam, not a blocker.** The state machine, gauge, thresholds, stage transitions, signal layer, and recovery path are all buildable now; only the effect invoked at Failing is unresolved. Building it as a **pluggable effect handler** — the stage machine calls `shed(entity, magnitude)` and the upgrades pass supplies the implementation — costs nothing today and avoids a rewrite later. Same discipline as the Phase 5.C seam (§13).

---

## 7. Estate-side accounting

### 7.1 Estates tick with their realm

Estate passive production does not depend on the character's actions at all — that is its entire purpose (realm §4.6). Making it lazy on the owner's resolve means an absent owner's estate *stops*, which contradicts realm §3.6 outright: *"a solvent estate keeps operating whether or not its owner is present."* And the reconciliation such a design needs — computing what should have been credited and diffing it — requires the realm tick to do the estate sweep anyway. The lazy version collapses into the realm-side version plus a correction pass that exists only to undo the laziness.

The "no per-character timers" pillar survives intact, because the pillar is about not running background work *per character*. An estate is not a character; it is realm furniture with a production profile, and design.md §1.1 pillar 3 already blesses realm-scale batch work in the job slot. The sweep is pure arithmetic with no RNG and no cascade — one aggregate pass per realm, summable to one UPDATE per (realm, item).

**Character resolve reads estate state and does not advance it.**

### 7.2 Estates transact in goods, not gold

The estate holds no wallet. Each tick it **credits its production to the realm's stores** and **draws its upkeep goods** from its larder (§7.5) and then the realm's stores — real goods, both directions, through the same pantry everyone else trades against.

The alternative considered and rejected was netting upkeep against production at reference prices and crediting only the difference. It is tidier on paper and destroys the point: realm §2.5's rule is that *specialization increases upkeep in other industries*, and a forge-hall that quietly eats its own ingots generates no demand for bread. Goods-in-goods-out preserves the cross-industry draw, makes the goods ladder bite, and makes residency worth something — the town supplies its workshops.

It also makes realm §3.6's self-correction work through store levels rather than a price feedback loop: a glut of identical ownerless producers fills the local pantry, the pantry caps, production is lost to overflow, and the marginal estate stops being worth anything — without any part of the engine having to notice.

### 7.3 Reference prices become the reporting unit

Realm §3.6 settles estate solvency "at reference prices." Under §7.2 that becomes an **accounting and presentation layer rather than the mechanism**: an estate is *mechanically* solvent when its larder or the stores could supply its upkeep this tick, and its reported figure (*"net +12g/day at reference prices"*) is what the owner reads on the estate panel and what a tycoon prospects with.

### 7.4 Estate gauges, and the reconciliation seam that remains

Each estate carries its own deficit gauge on the same accumulator shape as §6.4, driving the estate decay stages of realm §3.4 (upgrades dormant → degrading, shell remaining). Same philosophy, same reversibility, personal scale.

With production realm-side, almost nothing needs reconciling on character resolve. What does: **estate mutations settle the estate's accrual to `now` before applying the change.** Installing an upgrade, transforming, or completing a relocation changes the production profile at a timestamp, and the accrual up to that timestamp belongs to the old profile. Same idempotent function, called at the mutation. That is the honest reconciliation seam, and it is the only one.

**Relocation:** an estate in transit produces **at its origin realm until arrival**, consistent with the origin-identity rule already ratified in design log #22. A mobile estate's larder travels with it.

### 7.5 The larder: provisioning an estate before a long absence

*(New in 0.2, from design-chat review. It closes a genuine agency gap and it needs a patch to visiting-vision §5.3 — see the caveat below.)*

Under §7.2 as originally written, a player had **no personal lever over their own estate's survival while away.** "I am going to be offline for a month — how do I protect my estate?" had no answer except "hope the realm stays healthy." That is the wrong shape for an idle game, where planned absence is a supported way to play, and it is the wrong shape for a design whose whole leniency story is *slow slide with ample warning* — a warning you cannot act on is not a warning.

**The estate larder is a prepaid upkeep buffer, not storage.**

- The owner **deposits** upkeep goods into the larder, presence-gated at the estate.
- Goods **only ever leave as upkeep consumption.** There is no withdrawal, ever.
- Capacity is `larder_days × the estate's own daily upkeep`, per form — a vacation buffer, not an immortality device. Illustrative: 30 days base, more on rooted forms, near-nothing on a tent.
- It is the estate's version of the realm's reserve, and it uses the same vocabulary deliberately.

**Why the no-withdrawal rule is not a nuisance but the whole point.** Visiting §5.3 settled that there is **one player inventory, no estate storage, no located goods** — and that decision is good and should not be reopened. The larder does not reopen it: because goods cannot come back out, the estate cannot be used as a warehouse to stash goods for later retrieval, no carried-versus-stored split appears anywhere, and the watch item at design.md §13.7 is untouched. What goes into the larder has been *spent*, not *stored*. **This distinction is the ratification question (§15, R17), and visiting-vision §5.3 should be patched with a pointer rather than amended in substance.**

**What it does to play, which is the reason to want it:**

- **Departure becomes an economic act.** A player planning a long absence goes shopping first — a burst of demand for upkeep goods, aimed at exactly the tier-1 and tier-2 goods the ladder wants perpetually relevant. "Provisioning before a trip" is a good verb for this game to have.
- **It converts a public signal into a private decision.** In a `flush`/`fed` realm you need no larder. In a `strained` one you very much do, and §6.2's reserve-line boundary tells you precisely when the realm will stop feeding you. The signal layer acquires a second audience: not just haulers deciding where to go, but residents deciding how much to leave behind.
- **It fixes the free-rider asymmetry.** An absent owner whose estate is net-negative (a parked wagon, say) is otherwise a quiet drain on a realm they are not helping. With a larder, a departing player can pay their own way — and one who does not is gambling visibly rather than free-riding invisibly.

**What it does not do:** it does not make an estate immortal (capacity is bounded in days), it does not exempt anyone from realm health (a realm below its reserve line stops feeding estates regardless, and the larder just buys time), and it does not create a second inventory system.

---

### 7.6 Estate decay: the realm machine at personal scale

*(Settled in 0.5, amended in 0.6: estate decay follows the realm's path — including its deferral. The unification is stronger than a stylistic echo, because the property that makes realm decay safe transfers with it.)*

The estate gauge (§7.4) drives the **same four-stage machine as §6.5**, on the same accumulator, with the same reversibility. Only the effects differ, because an estate has upgrades where a realm has nodes and tags.

| State | Trigger | Realm effect (§6.5) | Estate effect |
|---|---|---|---|
| **Fed** | gauge = 0 | Normal | Normal |
| **Strained** | gauge ≥ T1 | Signal only | **Signal only** — the owner sees a warning; nothing changes |
| **Faltering** | gauge ≥ T2 | Node modifiers scale down; facility tags suspend | **Upgrades go dormant** — bonuses stop, nothing lost, instantly reversible |
| **Failing** | gauge ≥ T3 | *Provisional (§6.7)* — sheds, leading candidate upgrade tiers before node | *Provisional (§6.7)* — **the same strategy at estate scale:** shed upgrade tiers first, form/level rollback last |
| **Terminal** | shedding exhausted | Node swaps back; base node has zero upkeep | **Shell** — base form, **zero upkeep**; escheat-eligible |

**The stability property transfers, which is the real reason to unify.** §6.6's guarantee is that *regression reduces appetite* — the realm stabilizes because its shrunken identity costs less to feed. The estate analogue is exact: **each shed step lowers the estate's upkeep**, so a degrading estate walks its own draw down until the local economy can support what remains. An estate cannot spiral to nothing either; it composts to a shell and stops.

Two invariants make that guarantee real, mirroring R11 one for one:

- **The base estate form has zero upkeep** — a bare shell costs nothing to keep standing. With zero draw its gauge can never accrue, so the terminal state is provably terminal. **Boot-time content validation, the same check as R11's base-node rule.**
- **The gauge does not reset on a shed step** — it drops to a partial value. The estate is still short the morning after; it just has less to be short of.

**What is deferred, and what is not.** The Failing row is provisional at both scales — R29 (is anything truly lost) and R30 (uninstall ordering versus capacity) are **parked pending a design pass on realm upgrades** (§6.7). Estates follow whatever that pass decides, because the unification is the point: one machine, one mental model, effects mapped per scale.

Everything else in this section is settled and buildable: the shared gauge, the four stages, the signal-only recruitment window, the reversibility, the zero-upkeep shell as a provably terminal state, and the appetite-reduction property that makes the whole thing self-limiting.

**One note the upgrades pass should carry forward:** if it adopts tier rollback, R30 likely dissolves rather than needing an answer — a tier-1 upgrade presumably occupies the same slot as a tier-3, so shedding a tier never changes slot occupancy and `WOULD_ORPHAN_UPGRADES` (log #20) stays unreachable by decay. That is a cleaner outcome than the ordering rule v0.5 proposed, and it is a reason to prefer the tier approach on correctness grounds as well as leniency ones.

**Recovery** walks back down identically: dormant upgrades reactivate the moment the gauge falls, and whatever was shed is rebuilt through the ordinary upgrade-purchase path — the estate's version of §6.5's "the forward path is the ordinary morphing route through projects." No special repair mechanic, no reversal cost beyond the original price.

**What this buys beyond consistency:** one gauge implementation, one state machine, one set of threshold constants, and one mental model a player learns once and applies to both scales. It also means the estate panel and the realm panel can render the same component.

---

## 8. Treasury seeding and the frontier bootstrap

### 8.1 The actual problem

The chicken-and-egg is sharper than realm §6.5 states it. A frontier realm has no market access, so it collects no tax, so its treasury is empty, so its bids are unfunded, so no hauler is paid to supply it, so it never develops the node that grants access. Content seeding (market §3.4) solves the world's *opening* position and says nothing about realms that develop later, or regress and need to recover.

No mechanism here may mint gold. So the frontier's first gold must be *earned* or *transferred*, and there are exactly four honest sources.

### 8.2 Selling its own production — the headline answer

**A realm's ask side is a revenue stream.** A frontier realm with any surplus of its identity goods sells to the haulers who come, and that is its first gold. The frontier pays for its imports with its exports — thematically right, and already fully specified by §3 and §5 with no new mechanism.

The remaining gap is a realm with no estates and therefore no production. That closes with something already in the ledger: **NPC estates with production profiles and a null/system owner** (design.md §13.5). A wild realm sits on unprospected resources and the land itself produces a trickle — which is exactly an ownerless estate under a different name. **Promote NPC estates from a cold-start tool to a standing content mechanism:** any development node may declare a natural-production profile. Note this mints *goods*, not gold, and goods are minted by every gathering action in the game — the no-mint rule concerns gold and is untouched.

### 8.3 The other three sources

- **Balancing revenue.** Under §9, importing realms pay exporting realms treasury-to-treasury at market prices. A frontier realm with surplus earns from the NPC network without a player visiting. A substantive argument for the paid-not-burned direction.
- **Tax**, once access is earned — the loop closing on itself.
- **Escheat**, later (realm §3.6), once there are estates to escheat. Tabled.

### 8.4 Player patronage

**A player may gift gold to a realm's treasury.** One endpoint, no new gold path (it is a transfer), and it is the tycoon archetype's missing verb — funding the frontier realm you intend to develop is exactly what realm §3.5's developer does, and today they can only do it by hauling crates.

It is not self-dealing: gifting gold and then selling your own goods back returns your own gold in exchange for goods you made, which is a loss. The only party who profits from a gift is *someone else*, which is the point. It also gives the treasury a manual rescue valve — a cheap safety net against a balance error in a system with this many interacting rates. It pairs directly with the health bands (§5.5), which are what make a gift targetable.

### 8.5 The floor is real, and that is correct

There is deliberately **no rescue mechanism**. A realm with nothing to sell, no visitors, and no patron genuinely cannot bid, and stays that way. That is realm §2.7's thesis — communal neglect has a price everyone can name — and the escape is not a bailout but regression: as the realm slides, its quotas shrink, until its natural production covers what remains and it stabilizes as frontier (§6.6). Nothing is ever permanently broken; it composts.

---

## 9. Inter-realm balancing: the NPC floor

### 9.1 Cadence is the hauler's head start

**Daily, or every N ticks — much slower than upkeep.** This is the most important lever for market §4's "cushion without eating the hauler's lunch," and worth naming as such: the gap between a realm entering deficit and the NPC layer touching it is the window in which the signal sits visible on the map and players get first crack. Make the floor fast and haulers arrive to find the job done.

### 9.2 Who searches whom: demand-pull clearing

*(The direction was never stated before 0.4 — the R21 review caught it. v0.1–0.3 described deficit-first ordering, which silently implied the answer without arguing for it.)*

**The needy realm shops. Surplus realms never go looking for buyers.**

Each balancing run: process deficit realms in **descending gauge order**; each in turn selects the source minimizing **landed cost per delivered unit** (§4.3) across all realms holding surplus of the good. Ties break by realm id, matching the sorted-ID locking rule established in design.md §8.2.

**Why demand-pull rather than supply-push.** Four reasons, and the first is decisive:

1. **The buyer bears every cost, so the buyer chooses.** The importer pays the gold, absorbs the attrition loss, and is bound by its own treasury. A seller optimizing a trade whose costs land entirely on someone else is the wrong party holding the decision.
2. **Severity is the natural priority.** The floor exists to stop realms decaying; ordering by gauge spends the network's capacity on whoever is closest to a decay stage. Supply-push has no comparable ordering principle — "whoever has the most stuff" is not a rescue priority.
3. **One pass, deterministic.** Demand-pull is a single loop over deficits. Push-and-pull together needs conflict resolution when both fire on the same pair.
4. **It matches the metabolism framing.** A realm procures what it lacks; it does not run a sales department.

**What supply-push would have been for, and why that gap stays open deliberately.** The case for push is the realm sitting at store cap losing production to overflow (§3.3) with no needy realm nearby to pull from it. Under demand-pull that production is simply wasted — and per §3.3, **that waste is the intended pressure.** A realm visibly at capacity is advertising for a player buyer, and the loss is what makes someone show up. Handing that to the NPC network would quietly delete a hauler opportunity to solve a problem the design wants left unsolved.

**The willingness-to-pay ceiling** *(new in 0.4, and a real gap in v0.1–0.3)*. A realm imports only if:

```
landed_per_unit(s → r, g)  ≤  bid(r, g)
```

The importer never pays more for a delivered unit than the good is worth to it on its own curve. Without this, the severity ordering would drive desperate realms into arbitrarily bad trades — a realm at gauge 4.0 would buy from the far side of the map at any price and empty its treasury on freight. With it, three good behaviours follow for free:

- **High attrition suppresses trade volume**, so R19's bandit events do not merely tax the network, they *thin* it — and the resulting unmet demand is exactly the hauler's opening.
- **Remote realms clear rarely**, reinforcing §9.4's note that the NPC floor is weakest at the frontier and that frontier supply is player work (§8).
- **The floor cannot bankrupt a realm** trying to save it.


**The balancing layer never touches the global book.** Realm-to-realm only. Letting realms buy on the book would put them in competition with players for supply and hand them teleporting logistics — deleting both the hauler's job and the map's economic meaning in one move.

**Exporters sell only from surplus,** using the identical reserve rule from §3. Excess-only is not a player-facing special case; it is how realms sell, full stop.

**No debt, ever.** The importer pays from treasury. A realm that cannot afford a shipment does not receive it. There is no credit facility, no deferred payment, and no negative treasury state in the schema.

### 9.3 Transport cost is taken in goods — and the loss rate is a modifier

*(Amended in 0.2. The goods-attrition model was approved; the amendment is that attrition becomes a **modifier-typed value with map-edge scope**, which turns a static balance number into a content and event surface.)*

The importer pays the exporter `ask_price × units_shipped` in gold, **treasury to treasury**. The shipment then loses a fraction of its units in transit: the caravan arrives with 78 of 100 crates.

```
attrition_pct = clamp( A × haul_cost(path)
                       + Σ edge_attrition_modifiers along the path
                       + destination realm's caravan_attrition modifiers ,
                       0, attrition_max )
```

**Why goods rather than gold.** This is the most direct possible answer to *"keep NPC imports strictly inferior to hauler runs"* — the inferiority is structural rather than a number needing constant tuning, it scales with distance automatically, and a player hauler beats it by simply delivering everything they carried. It avoids a gold burn (a deflationary leak with no counterparty, in an economy that cannot mint), keeps gold flowing toward productive realms where it funds frontier exporters (§8.3), and destroys goods, which is a sink the economy wants. The system-escrow alternative is functionally identical to a burn until something spends it, and nothing does. It is also legible: *"the caravan arrived with 78 of 100 crates"* is a sentence.

**Why making it modifiable is the best structural addition in this pass.** Attrition is the one number in the economy that is simultaneously (a) about a *place on the map*, (b) meaningful to every archetype, and (c) safe to move around. Two sources plug into it:

- **Realm upgrades and development nodes** reduce it — a caravanserai, a road project, a garrison. A realm can *invest in being less remote to supply*, which gives communal projects an economic payoff that is not just a modifier on skilling.
- **World events raise it, temporarily and locally.** Bandits on a mountain pass raise attrition on that edge until players clear them. This is the first mechanism in the design that lets combat and exploration content **push on the economy directly**, and the loop it creates engages three archetypes off one event:

> bandits infest an edge → NPC imports through it degrade → downstream realms' stores drain → their bids rise → **haulers earn more** (they carry their own cargo and are immune to caravan attrition) → **combat players** clear the road for a realm that will pay them → attrition falls, the floor is restored, the premium normalizes.

**The deliberate asymmetry: caravan attrition does not touch player cargo. Settled (0.5): players travel safe, for now.** A dangerous road makes NPC logistics worse and makes *players more valuable*, which is the correct direction for every loop in this document — and it is the whole point of the bandit event (a hauler's premium rises precisely because the caravan alternative degraded).

Two guards on the "for now," since this is deferred rather than closed:

- **Nothing may assume player cargo is permanently inviolable.** If a later Combat or Exploration design wants road risk, it should find a seam rather than a wall. The cheap preservation is to keep a journey's cargo conceptually addressable — the Travel journey already resolves per edge with per-edge inputs (visiting §3.1), which is the natural attachment point if risk is ever wanted.
- **Nothing may assume it is at risk either.** No mechanic here may price itself on the assumption that hauling is dangerous; the hauler's wage comes from store and remoteness gradients (§4), not from a risk premium.

**Engine surface, which is the cost of this feature and should be priced honestly:** a new modifier type (`caravan_attrition_pct`), a **new source scope** — map edges, where every existing modifier source is character-resolved (development node, estate form, upgrades) — and a small runtime table for edge conditions (`map_edge_state`), since the map is currently pure content with no mutable state. All three are in §14.

### 9.4 Import caps

*(Revised in 0.2 per review. The ceiling rises to the reserve line; the volume cap becomes a fixed trickle.)*

1. **Coverage ceiling.** Balancing may raise a realm's coverage **to its reserve line — the sustained level — and no further.** The reasoning is sound: at the reserve line the realm is fed, its gauge is zero, and it is not decaying, which is exactly what a *floor* should deliver. It is also self-limiting for free, because a realm at its reserve line has no urgent need and its bid has already walked down the curve; the floor does not need a separate rule to stop it filling the cap, since it stops wanting to.
2. **Volume per run: a fixed trickle, not a fraction of the deficit.** `npc_run_volume[g] = V × draw[g]`, where `V` is a number of **days of consumption**. (This is identical to "a percentage of cap-less-sustained": `X% × (C − R) × draw`, restated in the unit that makes it legible.) A percentage-of-deficit cap would rescue the *worst* crises fastest, which is backwards. A fixed trickle means **the deeper the crisis, the longer the floor takes, so the player advantage grows with severity** — precisely the property market §4 asks for.
3. **Treasury bound.** No debt (§9.2).
4. **Source reserve.** Exporters sell only from surplus (§9.2).

**One consequence worth naming:** because the floor is treasury-funded and treasury comes from tax, the NPC network is **strongest where players are already active** (well-connected, taxed realms cushion themselves out of their own trade revenue) and **weakest at the frontier** (an off-book realm has almost no treasury to spend). The floor therefore does not compete with haulers where haulers matter most. That is the right shape, and it fell out rather than being designed — but it means frontier bootstrapping continues to rest on §8, not on §9.

---

## 10. Degenerate cases and near-zero scale

Discharging realm §6.13's residual — thin frontier markets must degrade gracefully rather than hit divide-by-zero edges. The structural answer is that **no formula in this document divides by draw**; the enumerated cases:

| Case | Behavior |
|---|---|
| `draw = 0` | No bid quoted (`NO_DEMAND`). Cap from `idle_cap`, reserve 0, ask side fully active. |
| `cap = 0` | Impossible: content validation requires `idle_cap > 0`, so `f = store/cap` is always defined. |
| `total_value = 0` (realm needs nothing) | `deficit_ratio := 0` by definition. Gauge cannot accrue. Tutorial island and base wild nodes land here, and are thereby upkeep-exempt without a special case. |
| Treasury = 0 | **No bid exists** (§5.5). The deficit is published as a non-executable **need**; trades fail cleanly with `UNFUNDED_DEMAND`. Health band reads `broke`. |
| Treasury > 0 but funds < 1 unit of `g` | No bid for `g`. A bid is never published at a quantity the realm cannot honour; rounding down to zero means no bid, not a bid of zero. |
| Σ weights = 0 (nothing unmet) | Allocation undefined and unneeded — no unmet draw means no procurement. Guarded before division (§5.6). |
| Store = 0 | `f = 0`, bid at `bid_max`. No ask. No division. |
| Store at cap | Bid quoted at `bid_min` with zero purchasable quantity; overflow production lost; signal shows "at capacity." |
| No reference price | Impossible: boot validation requires one per item. |
| Realm with no neighbours (isolated node) | `local_access = 0` → remoteness 1.0, the maximum price level. Correct: a place nothing connects to is maximally hard to supply. No division occurs — the sum is empty, not a denominator. |
| All realms at base node (`mass` all minimal) | `local_access` is small everywhere; the whole map is remote, which is correct for a world nobody has built yet. |
| Edge cost → 0 | Guarded: content validation requires a positive floor on edge cost, so `mass(n)/edge_cost` cannot diverge. |
| No source passes the willingness-to-pay ceiling | No import that run. The realm stays in deficit, its gauge accrues, its bid rises — and next run more sources qualify. Self-correcting, and the interim is a hauler opportunity. |
| Attrition ≥ 100% | Impossible: clamped at `attrition_max` (< 1). A caravan never fully evaporates. |
| Empty larder, realm below reserve | Estate draws nothing, accrues its own gauge. The intended pressure, not an error. |
| Estate at base form (shell) | Zero upkeep by content validation → gauge cannot accrue → terminal and stable. Mirrors the base-node rule (R11). |
| Estate degrades with zero upgrades installed | Already terminal; nothing to uninstall. Gauge holds at its partial value and the shell persists. |
| Book too thin for a meaningful VWAP | Divergence telemetry suppresses the good rather than reporting noise (§14). |

---

## 11. How the pieces reinforce each other

- **One draw vector generates reserve, cap, curve domain, gauge, feeding priority, project rate, and import ceiling** → the balance surface is a dozen numbers instead of thirty → content design can reason about a realm by looking at what it eats.
- **The ask is a markup on the bid** → no-arbitrage is structural at every quantity → one fewer invariant to prove, and one fewer corner to eventually fail at.
- **Remoteness is a price level, not a spread** → the frontier is expensive on both sides → goods flow toward the frontier and are not stripped out of it, and the multiplier cancels out of every no-arbitrage check.
- **Remoteness is terrain, and roads are a project** → a realm can *invest in being less remote*, and settling a wilderness realm de-remotes its neighbours → **the frontier physically moves as players build**, and the hauler's self-obsoleting run (market §5.1) becomes a number on the map rather than a mood.
- **Price level is per-realm, source choice is pairwise** → a cheap distant seller correctly loses to a dearer neighbour → the map's geometry decides trade routes rather than a single centrality score, and no realm is "the cheap one" from everywhere at once.
- **Events move journeys, development moves places** → bandits thin the NPC network without shaking the world's price boards → R19's content hook is powerful *and* safe to fire often.
- **The willingness-to-pay ceiling** → the floor can never bankrupt a realm it is rescuing, and high-attrition routes simply stop clearing → the gap the caravan won't cover is priced, visible, and exactly the hauler's opening.
- **The treasury band splits one signal into two calls to action** → funded hunger recruits haulers, broke hunger recruits patrons and tycoons → and the bid keeps its credibility, which every other signal in the economy borrows against.
- **Market access supplies a frictionless alternative channel** → the travel premium's bite concentrates on off-book realms → the hauler's wage is highest exactly where the hauler is the only option, and losing access becomes viscerally expensive.
- **Estates transact in goods with the local pantry** → specialization generates cross-industry demand → population enters demand through estates rather than through a quota multiplier, and a glut of ownerless estates self-corrects through overflow without a price loop.
- **The reserve line gates sales, estate feeding, and project commitment** → one number tells a resident when the town will stop feeding their workshop → which is exactly when the larder is worth stocking, on a deadline they can see coming.
- **The larder makes departure an economic act** → planned absence becomes a shopping trip for tier-1 and tier-2 goods → the perpetual low-tier demand the goods ladder promises gains another standing customer.
- **Estates eat before the realm above the line, after it below** → decay is a slide in normal operation and communal survival wins in a crisis → both halves of realm §2.7's philosophy hold at once.
- **Regression reduces appetite, at both scales** → a realm composts to frontier and an estate composts to a shell, each stabilizing at a size its economy can feed → decay is self-limiting everywhere, renewal is a guarantee rather than a hope, and players learn one mental model instead of two.
- **The gauge is an accumulator** → grace periods, severity weighting, and recovery all fall out of one number → and the realm's condition is a sentence: *short the equivalent of three days*.
- **Caravan attrition is a modifier on the map** → roads become content → **bandits are an economic event**: NPC supply degrades, bids rise, haulers profit, and combat players get paid to fix it → three archetypes engaged by one spawn, and communal road projects gain a payoff that is not another skilling modifier.
- **The NPC caravan loses crates and trickles** → NPC imports are structurally worse than hauler runs and get relatively worse as the crisis deepens → the floor cushions without competing, with no tuning number to maintain.

The standing test from realm §5 and market §6 applies: any future mechanism here must strengthen at least one of these loops without flattening the trade-offs — mobility vs. depth, specialization vs. self-sufficiency, growth vs. upkeep, local supply vs. imports, presence vs. opportunity cost.

---

## 12. The balance surface (content knobs)

Everything below is content/balance and needs no ratification — the ratifiable question is only whether each knob *exists* and at what scope.

| Knob | Scope | Illustrative | Job |
|---|---|---|---|
| `draw[g]` (per day) | Per development node | — | The realm's diet. Everything derives from it. |
| `R` — reserve runway (days) | Global default + node override | 7 | Sales floor, estate-feeding floor, project-commit floor. Also the §5.4 lever. |
| `C` — cap runway (days) | Global default + node override | 30 | Pantry ceiling; bid curve domain. |
| `idle_cap[g]` | Global default + per-good | — | Storage for goods with no draw. |
| `spoilage_pct_per_day[g]` | Per good, default 0 | — | Which goods have standing markets. |
| `bid_min`, `bid_max`, `γ` | Global | 0.3, 2.2, 2 | Curve endpoints and desperation shape. |
| `m` — spread | Global default + node override | 0.25 | Merchant margin; the no-arbitrage constant. |
| `P` — remoteness premium | Global | 0.4 | How much the map costs. |
| `A_ref` — access reference | Global (absolute) | — | Normalizes local accessibility (§4.2). No longer a design question — R21 resolved. |
| `mass` — economic weight | Per development node | — | How much a realm counts as a *neighbour*. The de-remote-your-neighbours dial. |
| Edge cost reductions | Node / project / upgrade | — | Roads. The one lever a realm has over its own remoteness. |
| `T_unaided` — project horizon (days) | Per project | — | How slowly the realm helps itself. Guards player contribution as a verb. |
| `larder_days` | Per estate form | 30 | How long a departing player can provision for. |
| `T1/T2/T3`, `recovery_rate` | Global | — | Decay stage thresholds and healing rate. **Shared by realms and estates** (§7.6); per-scale overrides only if play demands them. |
| Shed dwell interval | Global | — | How slowly a Failing realm or estate sheds. The leniency dial; final shape pending §6.7. |
| Book-divergence alert threshold + min volume | Config | — | When a reference price is worth a designer's attention (§16 #3). |
| Health band thresholds + hysteresis | Global | 5 bands | Signal coarseness; the cascade damper (§5.7). |
| Procurement allocation weighting | Global (fixed) | — | Reuses the gauge's value weighting (§5.6); no separate knob by design. |
| Tick cadence, balancing cadence | Config | 1h, 24h | The hauler's head start. |
| `NPC_ceiling` (= reserve line) | Global | — | How much the floor cushions. |
| `V` — NPC run volume (days) | Global | — | The trickle rate. |
| `A`, `attrition_max` | Global | — | Baseline caravan loss and its ceiling. |
| Willingness-to-pay ceiling | Fixed rule (no knob) | — | Importer never pays above its own bid (§9.2). Deliberately not tunable. |
| `caravan_attrition_pct` sources | Node / upgrade / map edge | — | Roads, garrisons, bandits. |

---

## 13. The Phase 5.C seam

Phase 5.C ships before this document's outputs land. These six items make it a seam rather than a rewrite:

1. **`quote(realm, item, side, quantity, now)` as a pure engine function** over an explicit context struct — `(reference_price, store, cap, reserve, treasury, level_multiplier, spread_pct, curve_params)`. Phase 5.C supplies `reserve = 0`, `level_multiplier = 1.0`, cap from content. Later phases fill in real values. **No signature change.**
2. **Quantity-aware from day one** (§5.2). The one item that cannot be retrofitted — spot pricing and curve integration differ in signature, response shape, and every test.
3. **Ask computed as `bid × (1 + m)`**, with `m` in content at 5.C. The no-arbitrage property then holds from the first commit.
4. **`realm_state.remoteness` as a persisted derived column**, populated at 5.C by the local-accessibility model (§4.2) with `P = 0` so the multiplier is 1.0, and exposed on `GET /map`. Zero risk, and the client can build map shading early. *(Amended from v0.1's boot-time cache — the column must exist in 5.C even though nothing reads the value yet, or R3's live-update path becomes a migration later.)*
5. **`realm_state.last_tick_at`**, dormant-by-design (the established precedent — treasury, `upkeep_profile`, regression edges all shipped this way).
6. **Realm-market read shape settled now:** exact prices and store quantities, coarse treasury band, and — critically — **a bid is published only where funded, carrying its funded quantity** (§5.5, §5.6). Cheap to get right initially; awkward to walk back once clients render a price field that sometimes means nothing. 5.C can compute the allocation trivially (one good, or a flat split) and gain the real weighting in 5.5 without changing the response shape.

Also for 5.C: the ask side gates on `surplus = max(0, store − reserve)` with reserve pluggable. At `reserve = 0` this is "sell down to empty," which is 5.C's natural v1 behavior regardless — the gate costs nothing to install now.

---

## 14. What this changes in the design doc (work items, not yet decisions)

Roughly in build order. Items marked ⚠ change something design.md currently states.

**Phase 5.C (seam only, no new mechanics):**
- The six items in §13.
- ⚠ **§5.5's bid-curve line** gains the ask definition (`bid × (1+m)`) and the quantity-integration rule, superseding "exact curve: content/balance, small engine surface" — the *shape* is now fixed, only the constants are content.
- ⚠ **§5.5's realm-market endpoint** grows the treasury health band, and publishes bids **only where funded**, each carrying its funded quantity. No price field is ever returned for an unfunded need — needs are a separate, explicitly non-executable list.
- ⚠ **`UNFUNDED_DEMAND` error code** on the realm-market trade endpoint, distinct from `NO_DEMAND`: the realm wants the good and cannot pay, versus does not want it. Both fail before consuming goods, per the `REALM_TRANSITIONING` precedent (log #21).
- **Procurement allocation** (§5.6) — computed at tick, consumed by sellers between ticks, unspent portions returning to the pool. 5.C may ship a flat split; 5.5 supplies the gauge weighting. No response-shape change between them.

**Phase 5.5 (the body of this document):**
- **`resolve_realm(realm, now)`** — lazy, idempotent, catch-up over elapsed ticks; the scheduled job becomes a liveness driver. ⚠ Sharpens §8.3's framing from "ticks run in the job slot" to "ticks are lazy; the job guarantees liveness."
- **Content: per-node `draw` vectors**, reserve/cap runways, spoilage rates, curve constants, spread, remoteness premium and gravity constants, node `mass`, gauge thresholds, band thresholds, `T_unaided` per project, `larder_days` per estate form. Boot validation: reference price per item; `idle_cap > 0`; **every regression chain's base node has zero upkeep**; optional monotonicity check on the goods ladder.
- **`realm_stores`** grows caps and clamping; overflow-loss accounting.
- **Realm gauge** on `realm_state` (accumulator + state), plus per-estate gauges.
- **Decay state machine** and the node-modifier decay penalty — a scaling factor applied to the node's contribution in the existing source-resolution pass (§7.1), not a new source type.
- **System-driven regression edge awards** — `award_edge_progress` gains a tick-only path for regression edges; players still rejected in both directions. Reuses `finalize_realm` for the swap. Respects log #21.
- ⚠ **§13.4's estate line flips:** estate production and upkeep resolve **realm-side at the tick**, not lazily on character resolve. Character resolve reads, does not advance. The reconciliation seam narrows to estate *mutations* settling accrual to `now` first.
- **Estates draw from and credit to realm stores in goods** — the dormant `upkeep_profile` / `production_profile` columns get their first reader, as goods vectors. Draw order per §6.2, with the reserve line as the estate/realm priority boundary.
- **Decay state machine, shared by realms and estates** (§6.5, §7.6) — one gauge type, one stage enum, one threshold set, effects injected per scale. Buildable in full **except** the Failing-stage effect.
- ⚠ **`shed(entity, magnitude)` as a pluggable effect handler** (§6.7) — the seam left by the R29/R30 deferral. The stage machine, thresholds, transitions, signal layer, and recovery path ship now; the realm-upgrades pass supplies the handler. Costs nothing today, avoids a rewrite later. **Do not inline the Failing effect into the state machine.**
- **Boot validation carried forward regardless of that pass:** the base node and base estate form both have **zero upkeep** (R11 and its estate mirror), and each shed step must lower upkeep — an upgrade's tier-`N` upkeep exceeds its tier-`N−1` upkeep.
- **Reference-price divergence telemetry** (§16 #3) — per good, a windowed volume-weighted book price against the content reference, surfaced as a divergence ratio for content review. Extends design.md §8.5's counters. **Guard: suppress or flag low-confidence goods** — a thin book produces a noisy VWAP, and a divergence alert on three trades a week is worse than no alert. Minimum-volume threshold in config.
- ⚠ **`map_edge_state` designed general from the start** (§16 #9) — a keyed edge-modifier table with **persistence as a first-class column**, not an attrition-specific one, because R26's guard depends on separating standing terrain from transient events. Anticipated readers: attrition, travel time, per-edge supply cost, route blocking. **Ownership passes to the Travel vision**; this document is the first writer only.
- **Estate larder** — `estate_larder(estate_id, item_id, quantity)`, capacity from the form's `larder_days`, deposit endpoint presence-gated at the estate, **no withdrawal path** (§7.5). ⚠ Requires a pointer patch to visiting-vision §5.3 clarifying that a no-withdrawal upkeep buffer is not estate storage and does not open the carried/stored split (design.md §13.7 stays a watch item).
- **Project demand overlay** — effective draw = node draw + `Σ remaining/T_unaided` over active projects; realm self-commitment at the same rate from stores above reserve; players cannot direct it.
- **`haul_cost(a,b)`** — one function over the map graph, shared by remoteness, balancing sourcing, and attrition. Extends Phase 4's `path_cost` with the per-edge supply modifier from the Travel vision.
- ⚠ **`remoteness` as live derived state, local not global** — computed from the realm's **incident edges** weighted by neighbour `mass`, recomputed at `finalize_realm` on any node transition, on any persistent edge-cost change, and refreshed by the tick job as a self-heal. Not a content-load cache; update-without-downtime is the requirement (R3). *Cheaper than v0.2's all-pairs gravity model — neighbours only.*
- ⚠ **Two edge-cost readings, deliberately different** — `remoteness` reads base + **persistent** modifiers; `haul_cost` for landed cost and attrition reads base + **all** modifiers including transient event ones (R26). This must be an explicit parameter on the cost function, not a convention someone maintains by hand.
- **`landed_cost(source, dest, item, qty)`** — a pure function composing `ask`, `haul_cost`, and `attrition`; the sole sourcing comparator in balancing (§4.3, §9.2).
- **Willingness-to-pay ceiling** in the balancing job — skip any candidate whose landed cost per delivered unit exceeds the importer's own bid (§9.2, R28).
- **Inter-realm balancing job** — severity ordering, `haul_cost` sourcing, treasury-to-treasury payment, goods attrition, the four import caps of §9.4. Reuses the sorted-ID cross-realm locking rule (§8.2).
- ⚠ **New modifier type `caravan_attrition_pct`** — and, more significantly, a **new source scope: map edges.** Every current modifier source is character-resolved (development node, estate form, upgrades); edge modifiers are route-scoped and resolve during balancing, not during character resolve. This is the largest engine surface in the pass and should be scheduled deliberately.
- ⚠ **`map_edge_state`** — runtime state on map edges (active modifiers, expiry). The map is currently pure content with no mutable state; this is the table world events write to. Consumers beyond attrition (travel time, route blocking) are plausible but out of scope here.

**Endpoints:**
- ⚠ **`POST /realms/{id}/treasury/gift`** (§8.4) — new. Presence-gated like other realm-market mutations.
- ⚠ **`POST /estates/me/larder`** (§7.5) — new. Deposit only. Presence-gated at the estate's realm.
- **Realm market read** grows: per-good coverage, surplus, cap state, treasury health band, gauge/stage. Location-free per market §2.7.

**Content-time:**
- **NPC estates promoted from cold-start tool to standing mechanism** — nodes may declare natural production (design.md §13.5, expanded). Verify the null/system-owner fixture test, still outstanding.

**Non-goals reaffirmed:** no realm buying on the global book; no remote realm-market trading, ever; no realm debt; no gold minted anywhere in this document; no withdrawal from a larder.

---

## 15. Ratification ledger

### Resolved in the v0.2 review

| # | Decision | Status |
|---|---|---|
| R1 | Reserve = `R` days of draw; global default + per-node override; pending transitions raise it | ✅ Approved |
| R2 | No draw ⇒ no bid; zero-draw goods fully excess but storage-capped; all surplus sellable | ✅ Approved |
| R3 | Remoteness model | ⚠ **Amended** — live gravity model weighted by development mass, persisted as derived state, recomputed without downtime (§4.1). Residual → R21 |
| R4 | Remoteness as a symmetric price-level multiplier on both sides | ✅ Approved |
| R5 | Ask = bid × (1 + m); no-arbitrage structural | ✅ Approved |
| R6 | Curve-integrated (quantity-aware) pricing | ✅ Approved |
| R7 | Estate production and upkeep tick realm-side | ✅ Approved (flips design.md §13.4) |
| R8 | Estates transact in goods; reference prices are the reporting unit | ✅ Approved |
| R9 | Estate/realm feeding priority | ✅ Approved, **restructured** by §7.5 — estates first *above* the reserve line, realm first below it (§6.2) |
| R10 | Value-weighted deficit accumulator; four-stage machine; Strained is signal-only | ✅ Approved |
| R11 | Base nodes have zero upkeep; validated at boot | ✅ Approved |
| R12 | NPC balancing pays treasury-to-treasury, cost as goods attrition | ⚠ **Amended** — attrition accepts modifiers with map-edge scope (§9.3) |
| R13 | Player patronage endpoint | ✅ Approved |
| R14 | Store caps + optional per-good spoilage | ✅ Approved |
| R15 | Realm ticks lazy-resolvable; job as liveness driver | ✅ Approved |
| R16 | Exact price and quantity; treasury as a coarse band | ✅ Approved (§5.5) |

### Raised in v0.2 (all subsequently resolved — see below)

| # | Decision | Note |
|---|---|---|
| R17 | **Estate larder** — a prepaid upkeep buffer with **no withdrawal path**; capacity in days of the estate's own upkeep, per form | §7.5. Requires a pointer patch to visiting-vision §5.3; the no-withdrawal rule is what keeps design.md §13.7 a watch item rather than a build item |
| R18 | **NPC ceiling = the reserve line**, and per-run volume as a **fixed trickle in days** rather than a fraction of the deficit | §9.4 — approved in review; recorded here because it changes v0.1's numbers materially |
| R19 | **`caravan_attrition_pct` as a new modifier type with map-edge source scope**, plus `map_edge_state` for world events | §9.3, §14 — the pass's largest engine surface; worth scheduling deliberately rather than folding into 5.5 |
| R20 | **Project demand overlay ON**, expressed as `remaining / T_unaided`, with realm self-commitment at the same rate from stores above reserve | §3.5 — settles v0.1 opens #1 and #2 |
| R21 | **`A_ref` absolute or relative** — can the whole world become less remote, or is remoteness always relative to the current map? | §4.2 — lean absolute. The one genuinely open piece of R3 |
| R22 | **Population enters demand through estates, not quota scaling** — realm draw stays population-independent | §16 #4 — settles v0.1 open #4; recorded because it is a standing rule content design will lean on |

### Resolved in the v0.4 review

| # | Decision | Status |
|---|---|---|
| R17 | Estate larder — prepaid upkeep buffer, no withdrawal path | ✅ Approved |
| R18 | NPC ceiling = the reserve line; per-run volume as a fixed trickle in days | ✅ Approved |
| R19 | `caravan_attrition_pct` as a modifier type with map-edge scope, plus `map_edge_state` | ✅ Approved |
| R20 | Project demand overlay ON, `remaining / T_unaided`, realm self-commitment at the same rate | ✅ Approved |
| R21 | Remoteness model and normalization | ⚠ **Reframed** — remoteness is **terrain**, computed locally from incident edges (§4.2); source selection splits off as pairwise **landed cost** (§4.3). Absolute normalization; the drift question dissolves |
| R22 | Population enters demand through estates, not quota scaling | ✅ Approved |
| R23 | Treasury exposure under the funded-bid rule | ✅ **Resolved: publish funded quantities exactly**, retain bands as the map summary. Raw balance stays out of responses and is accepted as inferable (§5.6) |
| R24 | The funded-bid rule and its two sibling supersessions | ✅ Approved (§5.5, §17) |
| R25 | Procurement allocation reuses the gauge's value weighting, no separate knob | ✅ Approved |

### Resolved in the v0.5 review

| # | Decision | Status |
|---|---|---|
| R26 | Remoteness reads persistent edge modifiers only | ✅ Approved |
| R27 | Clearing is demand-pull only; overflow waste stays a player opportunity | ✅ Approved |
| R28 | Willingness-to-pay ceiling on NPC imports | ✅ Approved |

**Open questions closed in the same review:** #3 (reference prices stay fixed; divergence telemetry instead), #6 (players travel safe, deferred not closed), #7 (estate decay mirrors the realm machine, §7.6), #9 (`map_edge_state` designed general, ownership to the Travel vision).

### Deferred — blocked on the realm-upgrades design pass

| # | Decision | Status |
|---|---|---|
| R29 | **Is anything truly lost to decay?** | ⏸ **Deferred (0.6).** Belongs downstream of a realm-upgrades pass. Leading direction: roll back **tiers within upgrades** before rolling back the realm's tier, estates identically (§6.7) |
| R30 | **Shed ordering versus capacity reduction** | ⏸ **Deferred (0.6),** and **likely dissolved rather than answered** — if a tier-1 upgrade occupies the same slot as a tier-3, tier rollback never changes slot occupancy and the orphaned-upgrade state is unreachable by construction (§6.7) |

**Neither blocks absorption.** The decay machine ships as a **pluggable effect handler**: the stage machine calls `shed(entity, magnitude)` and the upgrades pass supplies the implementation. Five constraints travel forward with the deferral and should not be re-litigated downstream — shedding must reduce upkeep, the terminal state must have zero upkeep, recovery is the ordinary forward path, nothing below Faltering may be irreversible, and the gauge does not reset on a shed step (§6.7).

**Content/balance, no sign-off needed:** every number in §12; which goods spoil; per-node reserve and spread overrides; node `mass` values; NPC estate production profiles; decay penalty magnitude; band thresholds; tick and balancing cadences; which upgrades and events touch attrition.

---

## 16. Open questions

1. ~~**Project-driven demand.**~~ **Settled (0.2, R20):** the overlay is on. `overlay_draw[g] = remaining[g] / T_unaided` creates the bid *and* sets the realm's commit rate; it self-damps as players contribute; it cannot be directed by players, so the presence gate on contributions is untouched. §3.5.
2. ~~**May treasuries fund projects?**~~ **Settled (0.2, R20): yes**, bounded by the same per-tick rate. `T_unaided` is the dial that keeps the realm a floor under a project rather than a substitute for the community, and treasury funding still traces back to player-generated tax, so a ghost town cannot develop itself.
3. ~~**Reference price dynamics.**~~ **Settled (0.5): fixed, plus divergence telemetry.** Reference prices stay content-authored and static in v1 — predictable, un-manipulable, and stable underneath the gauge weights and decay thresholds that read them. Dynamic prices were rejected because they are manipulable in a specific and nasty way: a player could push a good's book price expressly to inflate realm bids and farm treasuries. **The monitoring instead:** per good, a windowed volume-weighted book price compared to the reference, surfaced as a divergence ratio, so a designer sees drift and patches content deliberately. This is observability, not a mechanic — the loop stays human and intentional. Work item in §14; thin-book noise guard noted there.

4. ~~**Population scaling of quotas.**~~ **Settled (0.2, R22):** realm draw stays population-independent; **population enters demand through estates.** More residents means more estates, which means more estate upkeep drawn from stores *and* more production credited to them. The consequence worth designing to: an estate form's **net** (production − upkeep) decides whether a resident is a net contributor to the pantry, which is a per-form content lever — and a parked mobile estate is net-negative, so nomads are a genuine, deliberate drain on the realms they sit in. Rooted estates thereby carry civic weight that mobile ones do not, which is the mobility↔rootedness axis paying off one more time.
5. ~~**Should on-book frictionless supply be dampened?**~~ **Settled (0.2): no.** Presence is still required to sell into a realm market, and standing in a realm has a real opportunity cost — the traveller is away from their estate's bonuses (visiting §5.2) and away from wherever else they might be earning. That cost is sufficient friction; nothing further is needed, and §4.4's concentration of the travel premium onto off-book realms is the intended outcome rather than a leak.
6. ~~**Should players ever face cargo risk on the road?**~~ **Settled (0.5): no — players travel safe, for now.** The §9.3 asymmetry stands as a feature: bandits degrade NPC caravans and leave player packs untouched, which makes players *more* valuable exactly when roads are dangerous. Deferred rather than closed, with two guards recorded in §9.3 — nothing may assume player cargo is permanently inviolable, and nothing may price itself on the assumption that hauling carries risk. If road risk is ever wanted, the Travel journey's per-edge resolution is the natural seam. Revisit owned by the **Combat** and **Exploration & Keys** visions.

7. ~~**Estate decay stage details.**~~ **Settled (0.5): estate decay mirrors the realm machine** — same four stages, same accumulator, same reversibility, effects mapped onto upgrades instead of nodes (§7.6). The unification carries §6.6's stability property with it: each shed step lowers the estate's own upkeep, so a degrading estate walks its draw down to a zero-upkeep shell and stops, exactly as a regressing realm composts to frontier. *(0.6: the Failing-stage effect is now deferred with its realm counterpart — see #10.)*

8. **Escheat as treasury revenue.** Tabled (realm §6.9). Named in §8.3 as a future stream; mechanics unowned.
9. ~~**Other consumers of `map_edge_state`.**~~ **Settled (0.5): design it general from the start.** Attrition is the first writer, not the only one. Known and anticipated readers: caravan attrition (§9.3), **travel time and per-edge supply cost** (visiting §4.1), **route blocking / impassable-at-low-tier edges** (visiting §9.1), and remoteness — which reads the **persistent subset only** (R26). The schema is therefore a general edge-modifier table keyed by modifier type, with **persistence as a first-class column** rather than an attrition-specific convention, because R26's guard depends on being able to separate standing terrain from transient events. **Document ownership passes to the Travel vision**, which owns the map and has the most readers; this document introduces the table and does not own it (§17).

10. **What decay actually sheds, at both scales.** *(Opened 0.6, deferring R29 and R30.)* The decay machine is settled except for the Failing-stage effect: what gets given up, in what order, and whether it is ever permanently lost. **Blocked on a design pass on realm upgrades**, since the answer depends on a system whose shape — tiers, slots, costs, prerequisites — is still open, and guessing at it here would bake assumptions into an economy document that the upgrades pass would then have to work around. The leading direction from the deferral discussion is **roll back tiers within upgrades first, then the realm's own tier last, with estates following the identical strategy** — which lengthens the warning slide considerably and may dissolve R30 outright (§6.7). Five constraints travel forward with the question so the pass inherits boundaries rather than a blank page; the seam is a pluggable `shed()` handler so nothing waits on the answer.

---

## 17. What this changes in sibling documents

*(Following the precedent of market-vision §9. Retained as the record of what changed and why; these are patches those documents must absorb, not changes this document may make unilaterally.)*

### 17.1 Supersessions

**`market-vision.md` §3.3, layer 3 (the treasury as hard constraint).** The sentence *"A realm with empty coffers posts real but unfunded demand — its stores visibly starve even at attractive nominal prices"* is superseded. A realm with empty coffers posts **no bid**; it publishes a non-executable **need**, and its stores visibly starve at no price at all (§5.5).

- **What survives:** everything the section was actually for. The treasury remains a hard budget constraint. No gold is minted. Starvation remains fully visible. The dark-mirror loop — ghost town → no tax base → dry treasury → weak bids → upkeep slips → decay — is intact, with "weak bids" reading as "absent bids," which is a stronger signal rather than a weaker one.
- **What changes:** only the mechanism of visibility. The section assumed demand had to be expressed as a price to be seen; the bid/need split lets it be seen without pretending to be tradeable.
- **Patch shape:** replace the clause; add a pointer to §5.5–5.6 here.

**`realm-vision.md` §4.3 (realm market prices are signals).** The clause *"a broke realm posts real but unfunded demand, and its stores visibly starve at attractive nominal prices"* is superseded identically, and for the same reasons. The section's thesis — *prices carry information, and haulers profit by reading them* — is strengthened, since every published price is now one a hauler can act on.

**Neither supersession touches:** market §2.7 (full visibility — reads stay location-free and ungated), the Phase 4 treasury-balance rule (still not exposed as a raw figure, though R23 accepts it as inferable from the procurement allocation), §9.2's no-debt rule (never violated by either design), or the presence gate on realm-market trade.

### 17.2 Pointers and hand-offs (added in 0.5)

Not supersessions — additions those documents should absorb so the citation graph stays honest.

**`visiting-and-travel-vision.md` §5.3** — a pointer, not an amendment. The estate larder (§7.5) is a **prepaid upkeep buffer with no withdrawal path**, which is deliberately *not* estate storage: goods entering a larder have been spent, not stored, so no carried-versus-stored split appears and design.md §13.7 stays a watch item. §5.3's "one player inventory, no estate storage, no located goods" rule stands unchanged and should not be reopened.

**`visiting-and-travel-vision.md` — `map_edge_state` ownership.** This document introduces mutable map-edge state as attrition's first writer (§9.3, R19) and hands **document ownership to the Travel vision**, which owns the map and has the most anticipated readers: travel time, per-edge supply cost, and the impassable-at-low-tier edges already in its §9.1. Two constraints travel to it: **persistence must be a first-class column** (R26 separates standing terrain from transient events), and **remoteness reads the persistent subset only** (§4.2).

**`realm-vision.md` §3.4** — its open clause *"whether anything is ever truly lost is a design-doc decision with idle-game-friendly defaults"* is answered by §7.6 and R29, pending sign-off. §3.6's succession language ("whatever survived decay") is what the recommendation is built to honour.

**`realm-vision.md` §6.4, §6.5, §6.6 and `market-vision.md` §7.2, §7.6, §7.8** — the residuals consolidated into this pass are discharged. Those entries should be struck to pointers here.

### 17.3 Sequencing note

The two superseded documents are currently *upstream* of this one in the citation graph — this document cites them as authoritative on the three-layer price model. Until they are patched, a reader following the references finds two documents disagreeing about what a broke realm shows. Land the patches in the same revision that absorbs this pass into `design.md` v0.7, rather than after.
