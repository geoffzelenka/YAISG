# Yet Another Idle Skilling Game — Inter-Realm Economy Vision Document

**Version:** 0.7 (the gold supply pass. **The no-mint pillar is amended, not abandoned** — one authorized faucet, community-gated, self-throttling. Opens R31–R36)

**Changes from 0.6:** The pass overturns this document's own most-repeated sentence. *Nothing here mints gold* was load-bearing, and it was **wrong in one direction**: a conserved supply is not a stable supply, and the design as written had one unaccounted faucet, no sink at all, and a fixed realm price scale that cannot deflate alongside the player one.

- **New §8.6** states the actual problem. The threat is not scarcity — a pure deflation self-corrects in nominal terms — it is that `reference_price` is a content constant anchoring every realm quote. The player book can deflate; the realm market cannot. As gold-per-unit-of-activity falls, realm bids stay nominally fixed while book prices slide beneath them, opening a **structural arbitrage that widens forever** and drains treasuries into player wallets. The correction to the framing: goods are not infinite in *stock* (the world eats them constantly), but goods **flow** is unbounded, and flow is what gold must service. The design target is therefore **gold scaling with economic activity**, not with time or with account count.
- **New §8.7 — the mint**, ratified as a realm upgrade. It adds precious metals to the realm's draw vector and coins consumed bullion into the treasury. It reuses the bid curve, the presence gate, the funded-bid rule, the vote, and the maintenance draw, and introduces **no player-facing endpoint and no fixed-price vendor**. Its most important property is emergent rather than authored: because seigniorage is `K × reference − bid_paid` and the bid climbs as bullion drains, **the faucet throttles itself to the world's actual precious-metal production** and shuts off entirely when bullion is scarce. That is the activity-scaling §8.6 asks for, obtained for free.
- **New §8.8** records the rejection of **player-facing coin drops**, with the accepted substitute: combatants drop **bullion goods**, which feed the mint. Combat gains a second economic surface without becoming a faucet, and combat's stated identity as a gathering skill with risk survives intact.
- **New §8.9 — the drain side.** A faucet with no sink relocates the problem rather than solving it. `K < 1` makes the same mechanism a **net sink**, so one knob sets direction; a dormant `tax_burn_pct` ships at zero as the emergency dial.
- **New §8.10** weakens the conservation invariant **correctly**: total gold changes only through authorized mint writes; every other path conserves. Still fully testable, and it promotes **world gold supply to a first-class metric** from day one.
- ⚠ **Character-creation starting gold is reclassified** as what it always was — a per-account mint of the wrong shape, invisible to every economy document. **R36 stays open, and splits:** that it may not be *minted* follows from the invariant; *how much a new character should have* is a separate onboarding question, and the lean is **zero** — nothing a starting character does costs gold, so the first sale can be the opening move.
- §1, §8.1, and §14's non-goals are amended; §10, §11, §12, §14, §16, and §17 gain entries.

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

*(Amended in 0.7.)* **Gold is minted in exactly one place, and a community has to build it.** A realm that has voted itself a mint eats precious metals like it eats bread, and coins what it eats into its own treasury — so the world's money supply grows out of the world's mining, at a rate the world's miners set. Everywhere else, gold only changes hands. Nothing here rescues a realm that nobody helps. And nothing here can pay a player to stand still.

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

## 8. Treasury seeding, the gold supply, and the frontier bootstrap

*(Retitled in 0.7. §8.1–8.5 answer "where does **this realm's** gold come from." §8.6–8.10 answer the question that turns out to sit underneath it: "where does **the world's** gold come from." The first four sources were correct and remain correct; they were just all redistribution, and a closed circuit with a leak is not a monetary system.)*

### 8.1 The actual problem

The chicken-and-egg is sharper than realm §6.5 states it. A frontier realm has no market access, so it collects no tax, so its treasury is empty, so its bids are unfunded, so no hauler is paid to supply it, so it never develops the node that grants access. Content seeding (market §3.4) solves the world's *opening* position and says nothing about realms that develop later, or regress and need to recover.

No mechanism here may mint gold. So the frontier's first gold must be *earned* or *transferred*, and there are exactly four honest sources.

*(Amended in 0.7: a fifth exists, and it is the only mint in the game — a realm that has built one coins its own bullion (§8.7). It is deliberately **not** a bootstrap tool. A mint is a mid-chain upgrade with a maintenance draw and a bullion appetite; a frontier realm can afford none of it, and if it could, the bootstrap problem this section solves would have been solved by printing money. The four sources below remain the frontier's entire answer.)*

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

### 8.6 Conservation is not stability

*(New in 0.7. This section overturns the pillar every prior version of this document asserted.)*

**The premise was that a conserved gold supply is a safe gold supply. It is not, and the design as written did not even conserve.** Three findings, in ascending order of severity.

**The supply is not actually fixed — it grows in the wrong shape.** Character creation writes a `currency` row seeded from a config constant. That is newly created gold, per account, forever, and it is the only genuine faucet the game currently has. No economy document accounts for it. It scales with *accounts registered* — including accounts that register, trade, and leave — which correlates with nothing the economy needs money for.

**There is no gold sink whatsoever.** Every candidate turns out to be a transfer. The upgrade-vote fee goes *to* a treasury (realm §2.12). Project kickoff costs go to a treasury. Realm-market purchases move treasury gold *into* player hands. Fixed-form relocation cost is a transfer. And §9.3 chose goods-attrition over a gold burn on the explicit grounds that a burn is "a deflationary leak with no counterparty, in an economy that cannot mint." Goods have six sinks; gold has none.

**The decisive failure is the fixed price scale, not scarcity.** A pure deflation is survivable on its own terms: nominal prices fall, hoards gain real value, trade continues at smaller numbers. What kills that self-correction is `reference_price`. It is content-authored and static by ratified decision (§16 #3), and it anchors `bid_max`, `bid_min`, the spread, the gauge weights, and the procurement allocation. **The player book can deflate; the realm market cannot.** So as gold per unit of activity falls, realm bids stay nominally fixed while book prices slide beneath them, and selling to a realm becomes unconditionally better than selling to a player — an arbitrage that is structural, one-directional, and widens forever. It drains treasuries into player wallets, which is precisely the inverse of the loop in realm §4.2. The divergence telemetry of §16 #3 would report it faithfully and a designer would be repricing the entire catalogue every few months to chase it.

**The correction to the framing, which matters for choosing a faucet.** Goods are not infinite in *stock* — the world eats them constantly through upkeep draw, project contribution, caravan attrition, combat consumables, spoilage, and store overflow. What is unbounded is goods **flow**, and flow is what a money supply has to service. The design target is therefore not "gold grows over time" and certainly not "gold grows per account," but:

> **The gold supply should scale with economic activity, and nothing else.**

That criterion rejects wall-clock faucets, per-account faucets, and per-kill faucets, and it is the reason §8.7 takes the shape it does.

### 8.7 The mint: a realm upgrade that coins its own bullion

*(New in 0.7. R31.)*

**A mint is a realm upgrade.** It is proposed by a resident, paid for by a vote fee, decided by the estates standing in the realm, built through the ordinary project machinery, and it carries a permanent maintenance draw like every other upgrade (realm §2.11, §2.12). Everything a community pays for a lumber yard, it pays for a mint.

What the upgrade does is add **precious metals to the realm's draw vector** — bullion becomes something the realm eats. Every mechanism that follows is one this document already specifies:

- The realm bids for bullion **on the ordinary bid curve** (§5.1), priced by its own store level, its remoteness multiplier, and its treasury allocation.
- The bid is **funded or absent** (§5.5). A broke realm's mint publishes a need and coins nothing.
- Selling bullion to it is **presence-gated** like every other realm-market trade (market §3.5).
- Bullion sits under the ordinary **reserve and cap** rules, so a mint realm holds a runway of unstruck metal exactly as it holds a runway of grain.

At each tick the mint consumes its drawn bullion out of stores and credits the treasury:

```
coined[r]   = Σ_g  consumed[r,g] × reference_price[g] × K[g]
```

where `K[g]` is the **coinage multiple** — the one new content knob, and the only place in the game where gold comes into existence.

**The rule that makes this safe: the mint pays the treasury, never the player.** A player selling bullion is paid the ordinary floating bid, the same as selling grain. There is no fixed-price vendor anywhere in the loop. This is not a stylistic preference — a content-constant price quoted directly to players sitting next to a free market is an infinite-money loop the instant the book price falls below it, and it is the single most common way an MMO economy dies. Three further reasons the treasury is the right destination:

1. **It scales the faucet to production, not to population.** Gold enters as procurement budget, which is spent back out on upkeep goods, which is exactly the flow that needed servicing.
2. **It is community-gated.** No mint exists that a realm did not vote for and does not pay maintenance on. "Which realms have mints" becomes a genuinely consequential political question, and a good one to fight over.
3. **It cannot pay a player to stand still**, preserving §1's third promise. Every coin still reaches a player through a trade.

**The self-throttling property, which is the best thing about this design and was not authored.** Net gold created per unit of bullion is:

```
seigniorage = reference_price × K  −  bid_paid
```

and `bid_paid` climbs along the bid curve as bullion stores drain. So:

- **Bullion abundant** → stores near cap → bid near `bid_min` → seigniorage wide → the mint coins freely.
- **Bullion scarce** → stores near empty → bid near `bid_max` → seigniorage narrows to zero and then goes negative → **the mint stops being a faucet and becomes a sink.**

With `bid_min = 0.3` and `bid_max = 2.2`, a `K` of around 1.2 makes the mint strongly net-positive on a full pantry and net-negative on an empty one. **The money supply therefore tracks the world's actual mining output automatically**, with no rate limiter to tune and no designer in the loop — which is the §8.6 criterion satisfied by the mechanism's own shape rather than by a cap bolted onto it.

Two further guards, both cheap:

- **`K[g]` is authored as a multiple of `reference_price[g]`, never as an absolute.** A standalone coinage price would be a second, silently disagreeing price scale for the same good, and the two would drift apart the first time a designer repriced one and not the other.
- **Bullion is not exempt from anything.** It spoils at zero like a metal should, it counts toward the deficit gauge like every other unmet draw, and a mint realm that cannot feed its mint accrues gauge and decays — a realm can absolutely starve its own treasury by over-committing to coinage, which is the correct and thematically exact punishment.

**A mint's tier scales its draw**, not its `K`. A bigger mint eats more bullion; it does not conjure more gold per ingot. This keeps `K` a global economic constant rather than a per-upgrade balance surface, and it means mint capacity is bounded by what the world can dig up.

### 8.8 Why combat does not drop coins

*(New in 0.7. R32 — a rejection with an accepted substitute.)*

Coin drops on combat loot tables were considered and are **rejected**. Three reasons, the third specific to this game:

1. **It contradicts combat's stated economic identity.** Combat's whole design premise is that it is a gathering skill with risk attached — it produces leather, bones, and monster parts for the industries and buys back bread, potions, and ammunition (combat §1, §8). Coin drops let combat self-fund, which *decouples* it from the economy rather than coupling it, and quietly deletes the reason a combat player ever visits a market.
2. **It is a faucet nobody governs.** Every other gold path in the design runs through a realm that voted for it and pays maintenance on it. A drop-table faucet is set by content, fires everywhere at once, and has no community, no cost, and no off switch short of a content patch.
3. **This is an idle game.** Combat resolves offline over segmented absences. A coin-drop faucet runs while players sleep, which scales the money supply with **subscription-hours**, not with economic contribution — the exact failure mode §8.6 rules out.

**The accepted substitute, which gets the theme for free: combatants drop bullion.** A bandit's coin purse, a hoard-guardian's silver, ore from a cave-dwelling thing. These are ordinary goods on ordinary drop tables — no new mechanism, no new item behaviour — and they feed the mint through the same market every other good travels. Combat becomes a genuine second supply line into the world's money supply without being a faucet, monster parts gain a high-value tier, and the loop closes through a realm rather than around it.

The consequence worth naming: **bullion becomes a contested good with two production paths** (mining and combat), which is the first item in the catalogue where a gatherer and an adventurer are direct competitors in the same book. That is a feature, and it is the kind of thing the goods ladder has been short of.

### 8.9 The drain side

*(New in 0.7. R33.)*

A faucet with no sink relocates the problem from deflation to inflation, and this document has been burned once already by assuming a monetary property rather than mechanizing it. Three answers, in order of how much they cost:

- **`K < 1` runs the mint backwards.** If the world's gold supply ever runs hot, lowering the coinage multiple below 1 turns every mint in the world into a net gold *sink* — realms pay more for bullion than they coin from it, burning treasury gold against a real good. **One knob sets the direction of the entire monetary system**, using a mechanism that already exists, is already community-gated, and is already self-throttling. This is the primary lever and it needs no new engine surface.
- **Churn is the natural drain**, and it is the same drain that motivated this pass — players leave and their wallets stop circulating. It scales with population, which is roughly the right shape, but it is uncontrolled and unobservable. It should be *measured* (§8.10) and never *relied on*.
- **`tax_burn_pct`, shipped dormant at zero.** A fraction of the global-book tax destroyed rather than credited to the hosting realm. It costs one line at the tax-credit site and it is the emergency dial that does not require a mint anywhere in the world to be effective. Ship the knob now; leaving it at zero forever is a fine outcome, and needing it in six months without having built it is not.

**What is deliberately *not* a sink:** anything that burns a player's gold as a fee. Every existing gold cost in the design is a transfer to a treasury, and that is correct — the vote fee is doing three jobs (anti-spam, sink-shaped pressure, treasury revenue) and converting it to a burn would cost the third for no monetary benefit that `K` cannot deliver more precisely.

### 8.10 The conservation invariant, weakened correctly

*(New in 0.7. R34.)*

Market §2.3's property test — every unit of gold is at all times in exactly one of wallet, slot escrow, slot fills, or realm treasury — is this economy's most valuable test, and it does not have to be given up. It weakens to:

> **Total world gold changes only through an authorized mint write. Every other path conserves.**

Still a single property, still exhaustively testable, and strictly more informative than the old one because a violation now names its cause. Concretely:

- Mint writes are the **only** credits with no matching debit, and they occur at exactly one call site in `resolve_realm`.
- Every mint write is journalled: `(realm_id, tick, item_id, units_consumed, bid_paid, coined, K)`. The journal is what makes the supply auditable after the fact rather than merely bounded in principle.
- **World gold supply becomes a first-class metric from day one** — total, and split by pool (player wallets / escrow / treasuries). In a system with this many interacting rates, the single number most worth being able to graph is how much money exists and where it is sitting. It costs a sum query and it is the instrument that would have caught the character-creation faucet years earlier.

⚠ **Character-creation starting gold is reclassified** (R36, **open**). It is a mint, it has always been a mint, and no economy document has ever counted it. **The item splits into two questions that were being answered as one:**

**(a) May a new character's gold be minted? No — and this half is not open.** Whatever the amount turns out to be, it either comes from somewhere or it is the second uncounted faucet in a design that just spent a section removing the first. This falls out of §8.10's invariant rather than needing its own argument.

**(b) How much gold should a new character have? Open, and the lean is zero.** *(0.7.)* A full wallet at creation is an inherited convention, not a requirement this game has. Nothing a starting character does costs gold: gathering is free, skilling is time, travel is paid in supplies (visiting §4.1), the estate arrives with them, and the tutorial realm is market-exempt anyway (realm §2.4), so there is nowhere to spend it before graduation. **The first thing a new player does is produce something and sell it** — which is the economy's entire thesis delivered as the opening move, rather than a lump sum that quietly teaches the opposite. It also makes the tutorial's market exemption legible: you are not poor, you are somewhere that has not started trading yet.

**The one real constraint zero imposes, and it is cheap.** A player with no gold and no sale is stuck, so the graduation realm must **guarantee a funded bid for something a level-1 character can produce**. That is a content requirement — the mainland entry realm draws a low-tier good that its own starting gathering actions yield — plus a boot validation to keep it true as content changes. Note it is a guarantee about the *first* sale only; after that the ordinary market applies and the player can absolutely make bad choices.

**If a stipend is wanted anyway**, it is a **transfer from the tutorial realm's treasury**, seeded at content time like every other opening balance (market §3.4). That satisfies (a) at any amount, and it gives the tutorial realm a role in the ledger rather than an exemption from it. The remaining fallback — keep the amount and route it through the authorized-mint journal — is acceptable only as a stopgap, because it makes the supply *visible* without making it *governed*.

The one unacceptable option is the status quo, where the game's only faucet is a config constant that no economic reasoning in any document knows about.

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
| Mint realm with empty bullion stores | Consumes nothing, coins nothing. Bullion is an ordinary unmet draw: it accrues gauge and its bid climbs. A mint nobody supplies is dead weight with a maintenance bill — the intended pressure (§8.7). |
| Mint realm too broke to bid for bullion | No bullion bid exists (§5.5); a **need** is published. The faucet is off precisely where a treasury bailout would be most tempting, which is correct: a mint is not a bootstrap tool (§8.1). |
| `bid_paid > reference × K` (bullion scarce) | Seigniorage is negative and the mint runs as a net gold **sink**. Permitted and not guarded — this is the self-throttle, not an error (§8.7). |
| `K` set below 1 globally | Every mint in the world is a net sink. A deliberate monetary state, not a degenerate one (§8.9). |
| Mint upgrade shed by decay | Bullion leaves the draw vector with the tag; coining stops; the realm's gold supply contribution ends. No special case — identical to any other shed upgrade (§6.7). |
| Bullion in stores when the mint is shed | Becomes a zero-draw good: `idle_cap`, reserve 0, fully sellable (§3.3). The realm liquidates its unstruck metal, which is exactly what a town that lost its mint would do. |
| Two mint realms bidding for the same bullion | Ordinary competition on one global book. No coordination, no clearing rule, no new mechanism. |

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
- **The mint is a draw, not a faucet primitive** → it inherits the curve, the reserve, the cap, the funded-bid rule, the gauge, the vote, and the maintenance bill without a line of new economic machinery → the game's money supply is governed by the same seven mechanisms that govern its bread supply, and there is no second system to keep in sync.
- **Seigniorage is priced against a curve that steepens as bullion drains** → the faucet widens when metal is abundant and closes when it is scarce → the money supply tracks the world's mining output on its own, and the thing that would otherwise be the most dangerous number in the design has no rate limiter because it does not need one.
- **Bullion is minted by miners and by monsters, and coined only by realms** → a gatherer and an adventurer compete in the same book, and both are paid by a community that voted to want what they carry → combat pushes on the money supply the way §9.3's bandits push on freight: through the economy, never around it.
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
| `K[g]` — coinage multiple | **Global**, per bullion good | 1.2 | **The direction and strength of the entire monetary system.** `> 1` faucet, `< 1` sink (§8.7, §8.9). Authored as a multiple of `reference_price[g]`, never absolute. Deliberately not per-upgrade. |
| Mint `draw[bullion]` by tier | Per upgrade tier | — | Mint capacity. A bigger mint eats more metal; it never coins more gold per ingot. |
| Which goods are bullion | Per item (content flag) | — | Which metals a mint will eat. Feeds mining *and* combat drop tables (§8.8). |
| `tax_burn_pct` | Global, **dormant at 0** | 0 | Emergency gold sink independent of any mint existing (§8.9). Ship the knob, leave it at zero. |
| Starting gold at character creation | Config constant | **0** | ⚠ Currently an unaccounted mint. Pending R36(b) — **lean is zero**, with the first sale as the opening move; any non-zero value is a tutorial-treasury transfer, never a mint. |

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

**The gold supply (§8.6–8.10), scheduled with the realm-upgrades pass:**
- ⚠ **The no-mint pillar is amended in design.md.** The rule becomes *gold is minted only by an authorized mint write*, not *gold is never minted*. This sentence appears in several places and every one of them needs the same edit (§17).
- ⚠ **Mint coining in `resolve_realm`** — one call site, after the store draw, consuming bullion already debited by the ordinary draw and crediting `treasury`. `coined = Σ consumed × reference_price × K`. **The only credit in the codebase with no matching debit**, and it must stay that way; a second such site is a bug by definition.
- **Mint journal** — `(realm_id, tick, item_id, units_consumed, bid_paid, coined, K)`, append-only. Makes the supply auditable rather than merely bounded.
- ⚠ **Conservation property test rewritten** (§8.10) — total gold changes only by the journalled sum; every other path conserves. Extends market §2.3's test rather than replacing it, and the concurrency tests inherit it unchanged.
- **World gold supply metric** — total and per-pool (wallets / escrow / treasuries), on design.md §8.5's counter surface. **Ship with the first mint, not after.**
- **Content: bullion flag on items**, `K[g]` per bullion good, mint upgrade definitions with per-tier bullion draw and maintenance draw. Boot validation: `K` authored as a multiple, not an absolute; every bullion good has a reference price (already required); no upgrade may declare `K` locally.
- **`tax_burn_pct`** — one line at the tax-credit site in the match handler, config-driven, **default 0**. Cheap now, a redesign later.
- ⚠ **Combat drop tables gain bullion goods** (§8.8) — content only, no engine work, but it is a cross-document hand-off to the Combat vision and the goods ladder.
- ⚠ **Character-creation starting gold** (R36) — (a) it may not be minted, whatever the amount; (b) amount open, **lean zero**. If zero: a **boot validation that the graduation realm draws a good a level-1 character can produce**, so the first sale is always available. If non-zero: a debit from the tutorial realm treasury. Either way, touches Phase 2's `POST /characters` path and its tests.
- **Watch item — mint realms and the divergence telemetry.** Bullion is the one good whose reference price now has a second consumer (`K`), so a reference-price patch on a bullion good silently moves the money supply. The telemetry should flag bullion goods distinctly.

**Content-time:**
- **NPC estates promoted from cold-start tool to standing mechanism** — nodes may declare natural production (design.md §13.5, expanded). Verify the null/system-owner fixture test, still outstanding.

**Non-goals reaffirmed:** no realm buying on the global book; no remote realm-market trading, ever; no realm debt; **no gold minted anywhere except a built, voted, maintained mint consuming real bullion (§8.7)** — in particular no player-facing gold faucet, no fixed-price vendor for any good, and no coin drops; no withdrawal from a larder.

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

### Raised in v0.7 — the gold supply pass

| # | Decision | Status |
|---|---|---|
| R31 | **The mint.** A realm upgrade that adds bullion to the draw vector and coins consumed bullion into the **treasury** at `reference_price × K`. Reuses the bid curve, funded-bid rule, presence gate, vote, reserve/cap, gauge, and maintenance draw. No player-facing endpoint, no fixed-price vendor (§8.7) | 🔲 **Open** |
| R32 | **No combat coin drops.** Rejected on three grounds; combatants drop **bullion goods** instead, feeding the mint through the ordinary market (§8.8) | 🔲 **Open** — rejection plus substitute |
| R33 | **`K < 1` is the primary gold sink**, plus a dormant `tax_burn_pct` at zero as an independent emergency dial (§8.9) | 🔲 **Open** |
| R34 | **Conservation invariant weakened, not dropped** — total gold changes only through a journalled mint write; world gold supply becomes a first-class metric (§8.10) | 🔲 **Open** |
| R35 | **`K` is global per bullion good, and mint tier scales draw rather than `K`** — coinage is an economic constant, not a per-upgrade balance surface (§8.7) | 🔲 **Open** |
| R36 | ⚠ **Character-creation starting gold is an unaccounted mint.** Splits in two: **(a) it may not be minted** — settled by R34's invariant, not separately arguable; **(b) how much a new character should have** — **open, lean zero**, with the first sale as the opening move and a guaranteed funded bid at the graduation realm as the only cost (§8.10) | 🔲 **Open** — (b) only; the one item that is a live bug rather than a design choice |

**Sequencing:** R31, R32, and R35 are **blocked on the realm-upgrades design pass**, the same pass that owns R29/R30 — a mint is an upgrade, and its tiers, slots, prerequisites, and vote weighting are that pass's vocabulary. R33's `tax_burn_pct`, R34, and R36 are **independent and shippable now**, and R34's metric in particular should land before the first mint does, since its whole value is being able to see the supply move. **R36(b) is an onboarding question wearing monetary clothes** — it should be decided by whoever owns the tutorial flow, not by this pass; what this document owns is only the constraint that the answer cannot be minted.

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

11. **Does the mint change what §16 #3 concluded about reference prices?** *(Opened 0.7.)* Reference prices stay fixed — that decision is not reopened, and the mint is an argument *for* it, since a manipulable reference price on a bullion good would be a manipulable money supply. But bullion now has **two consumers of the same constant** (the bid curve and `K`), so a routine repricing patch moves the world's gold supply as a side effect. The likely answer is a content-authoring rule rather than a mechanism: bullion reference prices are repriced only deliberately, and `K` is re-derived in the same change. Worth a boot-time warning.
12. **How many mints should a world have?** *(Opened 0.7.)* Nothing in the design caps it, and nothing should — a community that wants one and can feed it should get one. But the aggregate supply growth rate is `Σ over mints`, so the number of mints is a balance surface that emerges from player politics rather than content authoring. The instrument, not the cap, is the answer: watch the supply metric (§8.10) and move `K`. Recorded as a watch item because the failure mode is slow and the correction is global.
13. **Should bullion be spendable as gold?** *(Opened 0.7.)* Rejected in passing but worth recording so it is not re-proposed as a convenience: bullion is a good, not a second currency. Letting players pay in metal would create a parallel money supply with its own price, a conversion surface between the two, and an immediate arbitrage against every fixed constant in the design. The whole point is that metal becomes money only by passing through a community that built the means to do it.

---

## 17. What this changes in sibling documents

*(Following the precedent of market-vision §9. Retained as the record of what changed and why; these are patches those documents must absorb, not changes this document may make unilaterally.)*

### 17.1 Supersessions

**`market-vision.md` §3.3, layer 3 (the treasury as hard constraint).** The sentence *"A realm with empty coffers posts real but unfunded demand — its stores visibly starve even at attractive nominal prices"* is superseded. A realm with empty coffers posts **no bid**; it publishes a non-executable **need**, and its stores visibly starve at no price at all (§5.5).

- **What survives:** everything the section was actually for. The treasury remains a hard budget constraint. No gold is minted. Starvation remains fully visible. The dark-mirror loop — ghost town → no tax base → dry treasury → weak bids → upkeep slips → decay — is intact, with "weak bids" reading as "absent bids," which is a stronger signal rather than a weaker one.
- **What changes:** only the mechanism of visibility. The section assumed demand had to be expressed as a price to be seen; the bid/need split lets it be seen without pretending to be tradeable.
- **Patch shape:** replace the clause; add a pointer to §5.5–5.6 here.

**`realm-vision.md` §4.3 (realm market prices are signals).** The clause *"a broke realm posts real but unfunded demand, and its stores visibly starve at attractive nominal prices"* is superseded identically, and for the same reasons. The section's thesis — *prices carry information, and haulers profit by reading them* — is strengthened, since every published price is now one a hauler can act on.

**The no-mint pillar, across four documents.** *(Added 0.7.)* The claim *no gold is ever minted* is asserted in **market-vision §3.1 and §3.3**, **realm-vision §4.2** (*"Gold is recycled, not minted — the treasury spends what players' commerce put in — keeping the faucet/sink balance honest"*), this document's own §1 and §8.1, and design.md's summary of all three. Every instance is superseded by the same replacement:

> **Gold is minted in exactly one place: a realm that has built a mint, coining bullion it bought and consumed (§8.7).**

- **What survives, and it is nearly everything.** No *player* is ever paid gold from nothing. No mechanism creates gold as a reward. The treasury remains a hard budget constraint, the funded-bid rule is untouched, and realm markets still buy with money that came from somewhere real. Realm §4.2's actual thesis — that realm health is emergent from economic activity rather than a designer dial — is **strengthened**, because the money supply now emerges from activity too.
- **What changes.** Realm §4.2's parenthetical about "keeping the faucet/sink balance honest" was doing the work of an argument it never made: conservation was treated as sufficient, and §8.6 shows it is neither sufficient nor, given character-creation gold, actually true. That clause should be replaced rather than softened.
- **Patch shape:** replace the absolute claim in each location with the one-line rule above and a pointer to §8.6–8.10. Market §3.1's *"never minted"* on the **goods** side is a different claim and stands unchanged — realms sell only from stores, and that has nothing to do with gold.

**`combat-vision.md` §8 (the economic-role test)** — an addition, not a supersession. The Feeds column gains **bullion** alongside monster parts, leather, and bones (§8.8), and the section should record explicitly that **combat drops no gold, by decision** (R32), with the reasoning, so it is not proposed again as a quality-of-life improvement. Combat's identity as a gathering skill with risk attached is the thing being protected, and it is that document's own framing.

**`skills-and-goods-vision.md`** — bullion enters the goods ladder as a gathering output with **two production paths** (mining and combat drop tables), which is a first for the catalogue and worth naming there. Its consumer is a realm upgrade rather than a refining chain, so it does not disturb the gather → refine → manufacture structure; it hangs off it.

**Neither supersession touches:** market §2.7 (full visibility — reads stay location-free and ungated), the Phase 4 treasury-balance rule (still not exposed as a raw figure, though R23 accepts it as inferable from the procurement allocation), §9.2's no-debt rule (never violated by either design), or the presence gate on realm-market trade.

### 17.2 Pointers and hand-offs (added in 0.5)

Not supersessions — additions those documents should absorb so the citation graph stays honest.

**`visiting-and-travel-vision.md` §5.3** — a pointer, not an amendment. The estate larder (§7.5) is a **prepaid upkeep buffer with no withdrawal path**, which is deliberately *not* estate storage: goods entering a larder have been spent, not stored, so no carried-versus-stored split appears and design.md §13.7 stays a watch item. §5.3's "one player inventory, no estate storage, no located goods" rule stands unchanged and should not be reopened.

**`visiting-and-travel-vision.md` — `map_edge_state` ownership.** This document introduces mutable map-edge state as attrition's first writer (§9.3, R19) and hands **document ownership to the Travel vision**, which owns the map and has the most anticipated readers: travel time, per-edge supply cost, and the impassable-at-low-tier edges already in its §9.1. Two constraints travel to it: **persistence must be a first-class column** (R26 separates standing terrain from transient events), and **remoteness reads the persistent subset only** (§4.2).

**`realm-vision.md` §3.4** — its open clause *"whether anything is ever truly lost is a design-doc decision with idle-game-friendly defaults"* is answered by §7.6 and R29, pending sign-off. §3.6's succession language ("whatever survived decay") is what the recommendation is built to honour.

**`realm-vision.md` §6.4, §6.5, §6.6 and `market-vision.md` §7.2, §7.6, §7.8** — the residuals consolidated into this pass are discharged. Those entries should be struck to pointers here.

### 17.3 Sequencing note

*(0.7: the no-mint supersession has a wider blast radius than the funded-bid one — it touches market-vision, realm-vision, combat-vision, skills-and-goods, and design.md, and this document is downstream of the first two. The same rule applies with more force: land the patches in one revision, because a half-patched citation graph on the question "can gold be created" is worse than either answer.)*

The two superseded documents are currently *upstream* of this one in the citation graph — this document cites them as authoritative on the three-layer price model. Until they are patched, a reader following the references finds two documents disagreeing about what a broke realm shows. Land the patches in the same revision that absorbs this pass into `design.md` v0.7, rather than after.
