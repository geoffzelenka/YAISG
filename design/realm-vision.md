# Yet Another Idle Skilling Game — Realm & World Vision Document

**Version:** 0.7 (absorbs the inter-realm economy pass; aligned to `market-vision.md` v1.3 and `visiting-and-travel-vision` v0.3)

**Changes from 0.6:** Absorbs `inter-realm-economy-vision.md` v0.6, which was chartered to close this document's §6.4, §6.5 and §6.6 and has closed rather more than that.

**One supersession.** §4.3 said a broke realm *"posts real but unfunded demand, and its stores visibly starve at attractive nominal prices."* Superseded: **a realm never posts a bid it cannot pay for**, because an unfillable bid is a false advertisement to any hauler who loads cargo against it. A broke realm publishes a non-executable **need** instead. The section's thesis — prices carry information, haulers profit by reading them — is strengthened, since every published price is now one a player can act on.

**Two sections concretized.** §3.4's estate decay "follows the same philosophy as realm decay" is now literal — the *same four-stage machine*, same accumulator, same reversibility, with the same self-limiting property (each shed step lowers the estate's own upkeep, so it composts to a zero-upkeep shell rather than spiralling). §3.6's estate solvency now settles in **goods** rather than gold, with reference prices demoted to the *reporting* unit — which is what makes §2.5's specialization rule generate genuine cross-industry demand instead of an estate quietly eating its own output. Estates also gain the **larder**, a prepaid upkeep buffer that finally gives a departing player a lever over their estate's survival.

**Six open questions closed:** #1 (transport cost — one shared `haul_cost`), #4 (upkeep mechanics, in full), #5 (treasury seeding, and *yes* treasuries may fund projects), #6 (balancing, in full), #13's residual (near-zero scale, discharged structurally), and #14 clarified against the larder. **One question deliberately left open and deferred:** what estate and realm decay actually *shed* at the Failing stage, pending a design pass on realm upgrades (§3.4).

**Changes from 0.5:** Settlements from the visiting-vision review and design-chat ratifications. (1) **Project contributions are presence-gated:** contributing to a realm project requires being physically in the realm (`current_realm`), superseding the Phase 4 permissive rule (contributions open to anyone from anywhere, Phase 4 deviation #3 / design log #23). A visitor standing in the realm may contribute; a remote benefactor may not — developing a distant realm now requires someone to carry the goods there, which is the hauler's frontier loop working as intended. Behaviorally identical to residence-gating under the interim presence rule; diverges (in the visitor-friendly direction) when travel lands. §6.3 updated. (2) **Visiting scope settled** by visiting-vision v0.2: visitors gather, craft, use communal facilities, and fight at full rate with no visitor malus; travel costs time and supplies as a skill-driven journey; there is no stay duration and **no obligation to return home** — the standing cost of absence is the estate's bonuses, while upkeep and solvency continue. §6.1's travel half and §6.3 updated with pointers. (3) **Mobile-estate relocation routes through the Travel journey** (visiting-vision v0.2 §8.7); fixed forms keep the Phase 4 gold-cost path.
**Scope:** The world itself — realms, estates, upkeep and decay, the estate lifecycle, and the player archetypes these create. **Trade mechanics are no longer owned here:** `market-vision.md` v1.0 is authoritative on the global player market (order book, slots, tax) and the realm markets (stores, bid curves, treasury constraint). This document retains the *world-side* framing of the economy — why the sinks exist, how realms live and die — and defers mechanism to the Market Vision wherever the two touch. Siblings: **Market Vision** (`market-vision.md`, demand/trade side), **Skills and Goods** (supply side), and the planned **Combat** and **XP Curve** documents.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` describes *how the engine and services achieve it* and is authoritative on mechanics; where a vision implies a mechanic the design doc doesn't yet support, that is a design-doc work item, not a license to improvise. The future content design document turns vision into concrete realms, skills, items, and numbers.

**Changes from 0.4:** Applied the supersessions listed in `market-vision.md` §9. §3.5 splits the trader/hauler into two archetypes (the hauler now works realm-market arbitrage and frontier supply; the pure order-book trader is new). §4 is rewritten around the ratified architecture: one global, instant, location-less order book (§4.1); flat seller-side tax credited to the hosting realm (§4.2); the three-layer realm-market price model — reference prices, store-driven bid curve, treasury as hard constraint (§4.3); realm **stores** as the visible pantry that estate production credits directly (§4.6); inter-realm balancing narrowed to the NPC floor, its "preserves trader gradients" rationale deleted (§4.5). §2.8 visiting updated for the presence rule on realm markets and the losable market-access tag. §5 reinforcement bullets reworded accordingly. §6 open questions pruned: items settled by market-vision v1.0 or by the Phase 4 build are marked settled with pointers; residuals live in market-vision §7. §7 work items updated for what Phase 4 shipped and what market-vision §8 now owns. Two questions raised during this patch were ratified in review: **frontier realm markets** (§6.13 — every realm operates a realm market at every stage; frontier ones are merely thin) and **visibility** (§6.15 — full visibility of the book and all realms' market state; settles market-vision §7.7). *Changes from 0.3:* estate lifecycle (§3.6), developer/tycoon archetype, multiple-estates leaning yes. *Changes from 0.2:* the two-market economy, tax → treasury → procurement, estate passive production, inter-realm balancing, tiered goods. *Changes from 0.1:* living realms — morphing, upkeep, decay/regression, visiting, the adventurer role.

---

## 1. The elevator pitch

An idle skilling game where **where you live is the biggest choice you make — and the places themselves are alive**. The world is a map of realms, each with an economic identity that its residents *create and must sustain*. Your estate is your home in that world, and its form expresses your relationship to the map: a nomad's wagon that moves cheaply but roots shallowly, or a great workshop that anchors you to one realm and rewards you deeply for committing to it.

Progression is therefore three intertwined arcs: the familiar idle-game arc of skill levels and better recipes; a geographic arc of exploring the map and choosing where to belong; and a communal arc of building a realm up — and keeping it fed — alongside its other residents.

---

## 2. The world: a living map of realms

### 2.1 One world, many places

Realms are not parallel servers or disconnected menu options — they are **regions of a single shared map**. The map gives the world legibility (players can point at where they live), makes travel meaningful, and gives the communal layer a canvas: a realm's rise *and its decline* are visible on the map to everyone. With the player market now a single location-less book (market-vision §2.1), the map earns its economic keep through the realm markets: presence-gated trading (§4.3), store and treasury differentials that pay haulers to travel (market-vision §5.1), the market-access frontier (§2.8, market-vision §2.6), and distance-scaled transport costs in the NPC balancing layer (§4.5).

### 2.2 Realms are specializations, not tiers

Each realm has an economic identity built from a coherent skill cluster. Illustrative archetypes (real content deferred to content design):

- **Agrarian realm** — farming and cooking; abundant food resources, bonuses to growing and preparing.
- **Mountain realm** — mining, smelting, and metal crafting; ore-rich, forge-friendly.
- **Forest realm** — lumberjacking, milling, carpentry; timber economy end to end.
- **Industrial realm** — weak gathering bonuses, but strong crafting bonuses and the best market access; it *imports* raw materials and exports finished goods.
- **Barren / wild realm** — a realm that has regressed or never developed: few economic bonuses, but dangerous fauna, unprospected resources, and room to build. Frontier, not wasteland — this is where adventurers go and where the next boomtown starts.

Two principles govern realm design:

1. **Horizontal, not vertical — among the developed.** Developed realms differ in *what* they're good at, not in raw power level; a late-game farmer and a late-game smith are peers with different portfolios. Development *stage* is the vertical axis (wild → developing → developed), and it belongs to realms, not players — and it moves in both directions (§2.6, §2.7).
2. **No realm is complete — and the more developed, the less complete.** Every specialization leaves gaps other realms fill, and specialization *deepens* dependency: an industrial stronghold consumes far more food and raw material than it can ever produce (§2.5). This interdependence is what makes the world an economy rather than a price board.

### 2.3 Realms are communities

A realm's residents share its communal progression: contributing resources to realm projects advances the realm and improves its bonuses for everyone there. Choosing a realm is choosing *who you're building with* — and who you're keeping the lights on with (§2.5).

### 2.4 The tutorial island

New players begin on a **tutorial island**: a small, self-contained realm exposing a compact set of skills and a starter estate. Its arc teaches the game's core loop *and its core theme* — the capstone of the tutorial is building the means to leave (a rowboat, in the current imagining: the player's first "estate" is literally their vehicle to the wider world). Graduating from the island is the moment the real choice — *where do I go, and what do I become?* — is put in front of the player.

The tutorial island is one-way and low-stakes: nothing built there is meant to be a long-term asset, and players should feel pulled onward, not anchored. It is also exempt from upkeep, decay, and the markets (market-vision §3.4) — the living-world pressure begins on the mainland.

### 2.5 Upkeep: the world's appetite

Everything built must be fed. As a realm develops, it accrues **upkeep quotas** — recurring consumption of food, materials, tools, and other goods. Estates carry their own upkeep (§3.4). Upkeep is the game's primary **economic sink**: a world that only generates resources inflates into meaninglessness; a world that eats them has real prices, real scarcity, and real work for every industry.

The defining rule: **specialization increases upkeep in *other* industries.** A forest realm's mills run on food and iron tools; an industrial realm devours food and raw materials wholesale. The more a realm (or estate) narrows its identity, the more it must import to survive — so the most advanced places are the most dependent on the rest of the world, and no one gets to opt out of the economy by going tall.

How upkeep is actually *fed* — realm stores, the treasury, the bid curve, and estate production — is the economic architecture of §4 and, mechanically, of market-vision §3.

### 2.6 Morphing: realms become what their residents do

Realm identity is **earned, not assigned**. A realm's development path follows its residents' actual activity: a forest realm where woodcutting gives way to mills and workshops *becomes* an industrial realm over time. Realm projects are the mechanism — which projects a community completes steers which identity the realm grows into.

This makes the map a record of player history. The industrial heartland was once a forest; old residents remember cutting the trees that became its first mills. Content design defines the **development graph** — which archetypes can morph into which, via what projects — and players choose the route. *(The engine side landed in Phase 4: realm identity is a node in a content-defined development graph, with projects driving edge progress and transitions.)*

### 2.7 Decay and regression: nothing is permanent

If a realm misses its upkeep quotas, it enters **decay**: communal upgrades degrade or shut down, bonuses weaken, and the realm's tier can slip. A realm abandoned outright **regresses along the development graph** — an industrial stronghold crumbles into a dangerous barren realm; given enough time, the forest returns. Regression is the reverse traversal of the same graph that morphing climbs.

Decay is not (only) punishment — it is the world's self-balancing pressure and its renewal cycle:

- It keeps thriving realms *hungry*, sustaining demand for every industry forever.
- It solves the runaway-leader problem naturally: the realm that races ahead in tier races ahead in appetite.
- It re-creates frontier. Ruins and regrown wilds are the adventuring, prospecting, and resettlement content of the future — the world composts its past into new opportunity.
- Its most legible single consequence: a realm that decays past the node granting the **market-access tag falls off the global economy entirely** — no listing, no buying, no tax revenue (market-vision §2.6). Communal neglect has a price everyone can name.

The tuning intent (numbers deferred): decay should be a *slow, visible slide with ample warning*, not a cliff. Realm **stores** are that warning made concrete — a pantry everyone can watch drain (market-vision §3.2). A healthy community comfortably meets upkeep — indeed, at low tiers, resident estates cover it passively (§4.6) — and decay is what happens to genuine neglect and abandonment, not to a quiet weekend.

### 2.8 Visiting: acting away from home

Relocating your estate is not the only way to experience another realm. A player may **visit** other realms — traveling there to act without moving home. Visiting is the natural mode of the **adventurer**: fighting the dangerous fauna of wild realms, exploring uncharted regions, prospecting for undiscovered resources.

Visiting also carries a new economic load since market-vision v1.0: **realm-market trading is local — it requires being physically at the realm** (market-vision §3.5), and the invariant is recorded as permanent: no remote realm-market trading, ever. Trading at a foreign realm's market is therefore exactly what visiting enables, and the hauler archetype (§3.5) cannot fully activate until travel/visiting exists. The global order book, by contrast, is reachable from any realm carrying the market-access tag — no travel needed, but frontier realms without the tag are off the book entirely (market-vision §2.6).

The home/away distinction keeps rootedness meaningful: production and estate bonuses live at home; visiting offers what home cannot — danger, discovery, first pick of the frontier, and the far side of an arbitrage run. The production line is now settled (visiting-vision v0.2, §6.3 here): visitors act at **full rate with no malus** — availability is the current realm's tags — and what distinguishes residents is investment (their estate's located bonuses), not permission. Contributions to realm projects require presence.

---

## 3. Estates: your relationship to the map

### 3.1 The mobility ↔ rootedness axis

The estate is not just a bonus rack; it is the player's answer to "how do I want to inhabit this world?" Estate forms sit on a spectrum:

- **Mobile end** — a tent, a trader's wagon, a boat. Cheap and easy to relocate; thin bonuses, thin upkeep, little or no production. This is the estate of the wanderer, the hauler, the adventurer ranging out of a light camp — someone who follows opportunity across the map.
- **Rooted end** — a farmstead, a forge-hall, a mill, a workshop. Expensive or slow to move (perhaps effectively permanent); deep bonuses to the industries it's built for, real passive production into the local stores (§4.6) — and correspondingly deep upkeep (§3.4). This is the estate of the specialist and the community pillar.

The design intent: **mobility and depth trade off against each other**, and the trade should be a genuine dilemma at every stage of the game. Relocation cost is not a flat fee — it is a *property of the estate form*. Moving a wagon is trivial; moving a manor should be a project (or mean rebuilding). *(Phase 4 shipped this: estate forms with transformation paths, form-dependent relocation cost over map paths, instant and delayed relocation.)*

### 3.2 Estates and realms interact

An estate's bonuses land hardest when its specialty matches its realm's (a forge-hall in the mountain realm), stay partially useful elsewhere, and may go inert where the realm can't support them at all. This makes the pairing of estate form × realm the player's build identity — the idle-game equivalent of a character class, but chosen through economics and geography rather than a menu at creation.

### 3.3 Estates grow

Within a form, estates progress: more upgrade slots, better bonuses, more production, higher caps (offline time, storage, market presence — the order-slot cap of market-vision §2.4 is a natural estate-progression axis). Progressing a rooted estate is a very-long-term goal on par with maxing a skill. Transformation between forms exists (Phase 4: content-defined transformation paths, with the WOULD_ORPHAN_UPGRADES guard); the remaining questions are content-shape ones (§6.2).

### 3.4 Estates eat too

Estate upkeep mirrors realm upkeep at personal scale: a tent needs almost nothing; a forge-hall needs fuel, food for its hands, and materials for repair — largely goods *outside its own specialty*, per the specialization rule (§2.5). Estate decay follows the same philosophy as realm decay: slow, visible, recoverable — upgrades going dormant before anything is lost — so that upkeep is a standing reason to engage with the markets, not an anxiety mechanic that punishes taking a break.

*(Concretized in 0.7 by inter-realm-economy §7.6.)* "Follows the same philosophy" is now literal: estates run the **same four-stage machine as realms**, on the same deficit accumulator, with the same reversibility — Fed, Strained (signal only), Faltering (upgrades dormant, nothing lost), Failing (shedding), terminal shell. The property that makes realm decay safe transfers with it: **each shed step lowers the estate's own upkeep**, so a degrading estate walks its draw down until the local economy can support what remains. An estate cannot spiral to nothing; it composts to a **zero-upkeep shell** and stops, exactly as a regressing realm composts to frontier. Players also get a lever they previously lacked: the **larder**, a prepaid upkeep buffer with no withdrawal path, so a player planning a long absence can provision the estate before leaving.

**Still open, deliberately:** *whether anything is ever truly lost* — the exact question this section flagged. It is **deferred pending a design pass on realm upgrades**, because the answer depends on a system whose shape is not settled. The leading direction is to roll back **tiers within upgrades** before rolling back the estate's form at all, which would make loss graduated rather than binary. Five constraints already travel with the question (inter-realm-economy §6.7).

### 3.5 The playstyles the axis creates

The estate spectrum, the map, and the economy combine into distinct archetypes — none of them a class picked from a menu, all emergent from where a player puts their estate(s) and effort (the vision test in §5 applies to each: every archetype must feed the economy, not run parallel to it). *(This section is rewritten per market-vision §5 — the old trader/hauler hybrid is superseded.)*

- **The producer** — rooted estate matched to a specialized realm; deep bonuses, deep production, pillar of a community. Sells surplus on the global book at world prices and feeds the local stores through estate production — the always-on foundation of the realm's metabolism.
- **The hauler** — mobile estate, physically moves goods toward hunger. Two loops, both anchored in the presence rule (market-vision §3.5): **realm arbitrage** — buy from a realm market selling cheap out of full stores, travel, sell into a starving realm's scarcity-inflated bids; decay literally pays the hauler to fix it — and **frontier supply runs** — realms without market access import everything in someone's carried inventory, and provisioning them is pure hauler work that self-obsoletes once the realm earns the tag and the frontier moves on. The counterparty is the world itself.
- **The trader** — distinct from the hauler: works the global order book itself — spreads, timing, order-slot management. No travel required; the book is their realm.
- **The adventurer** — lives light, travels far, fights and prospects the frontier; buys consumables at world prices anywhere with access and sells discoveries and spoils into the same book (maps, ore veins located, monster drops the industries want) — feeding the economy going and coming.
- **The developer (tycoon)** — the endgame industrialist who builds up estates *across* the world to promote its development: founding a farmstead to anchor a frontier realm's food base, raising a mill where a forest realm is trying to morph industrial, then moving on and doing it again. The realm-market signal layer — store levels and treasury health across the map — doubles as the tycoon's prospectus. Their monument is not a number on a character sheet but a map dotted with working estates they built — possible precisely because a well-built estate can sustain itself after its builder moves on (§3.6). This playstyle is the strongest argument for allowing **multiple estates per player** (the schema already permits it), likely gated behind meaningful cost so it remains an endgame pursuit.

### 3.6 The estate lifecycle: solvency, abandonment, succession

Estates are semi-autonomous economic entities with their own balance sheet. An estate's production credits the realm's stores (§4.6); its upkeep is drawn from the same local economy. *(Amended 0.7:)* estates transact in **goods** both ways — production credits the realm's stores, upkeep draws from them — which is what makes the specialization rule of §2.5 generate real cross-industry demand rather than an estate quietly eating its own output. **Reference prices become the reporting unit rather than the mechanism**: an estate is *mechanically* solvent when its larder or the local stores could supply its upkeep this tick, and its reported figure (*"net +12g/day at reference prices"*) is what the owner reads and what a tycoon prospects with. When production covers upkeep, the estate is **solvent** — and a solvent estate **keeps operating whether or not its owner is present**. Estate viability is therefore emergent from the local economy, not an ownership flag: a well-matched forge-hall in a booming mountain realm hums along untended, while the same building in a starving realm slides toward insolvency.

- **Abandonment follows the ordinary decay rules** (§3.4) — there is no special "abandoned" punishment. An estate whose owner departs simply stops receiving active top-ups; if it was built well enough to be self-sustaining, it stands. If not, it decays exactly as a neglected occupied estate would: upgrades going dormant, then degrading, the shell remaining.
- **Succession:** a player moving to a new realm need not build from nothing — they can **buy into an existing abandoned estate** and move in, inheriting its form, level, and whatever survived decay. Fully-decayed derelicts plausibly revert to the realm itself, which sells them (a second treasury revenue stream alongside market tax, and how "ruins" become "fixer-uppers"). Whether purchase happens from the departed owner, the realm, or both is a design-doc decision (§6).
- **The world this builds:** the map accretes a fabric of standing property — working estates of active residents, self-sustaining legacies of departed builders, decaying shells awaiting new owners, and ruins feeding the frontier cycle (§2.7). Moving to a realm means arriving somewhere with *history and housing stock*, not a blank lot. NPC-seeded estates at world start are the same fabric laid down by content instead of players (market-vision §3.4).

One tension to tune deliberately (flagged in §6): if solvency is too easy, the world fills with immortal ownerless estates and the decay/renewal cycle stalls. The intended lever is economic, not arbitrary — realm bids fall as stores fill, so a glut of identical ownerless producers depresses their own revenue toward insolvency. Whether that self-correction suffices, or absentee estates additionally run at reduced efficiency, is an open tuning question.

---

## 4. The economy: two markets and a ladder of goods

*(This section is the world-side summary. `market-vision.md` v1.0 is authoritative on every mechanism named here.)*

### 4.1 Two markets, two functions

- The **global player market** is *circulation*: a single worldwide **order book** per good, with both buy and sell orders, continuous price-time matching, and instantaneous, location-less movement of goods and gold (market-vision §2). It is gold-conserving and maximizes liquidity and price discovery even at small population — the deliberate cost being that player-side prices are one-per-world, with no inter-realm gradients. It is where inter-realm interdependence actually clears — the forest realm's timber finds the industrial realm's mills.
- The **realm markets** are *metabolism*: each realm's procurement arm, and a *place* — trading with one requires being there (market-vision §3.5). A realm buys what its upkeep and projects demand (goods sold to it are consumed — the sink) and sells what its identity produces **out of its stores**, never minted (market-vision §3.1).

The two markets differentiate along upkeep. Players trade with each other to *rearrange* the world's goods; they trade with realms to *sustain* the world itself.

### 4.2 The tax → treasury → procurement loop

Realm markets buy with gold from the **realm treasury**, and the treasury's primary revenue is now concrete: a **flat, content-defined, seller-side tax on every global-book match, credited to the realm where the seller's order was placed** (market-vision §2.5). The loop closes:

> prosperous trade → tax revenue → funded treasury → realm market bids well for upkeep goods → upkeep met → realm thrives → more trade.

And its dark mirror: a ghost town has no tax base, its treasury runs dry, its bids weaken, upkeep slips, decay begins. Realm health is *emergent from economic activity*, not a designer dial. Gold is recycled, not minted — the treasury spends what players' commerce put in — keeping the faucet/sink balance honest. Escheat of fully-decayed estates (§3.6) is a planned second revenue stream.

### 4.3 Realm market prices are signals

Realm pricing is a three-layer model (market-vision §3.3): **reference prices** from content anchor the scale and solve cold start; the **bid curve** climbs as a good's stores drain — a realm deep in deficit bids desperately, a well-fed one bids low; and the **treasury is the hard budget constraint** — and *(amended 0.7)* **a realm never posts a bid it cannot pay for.** A bid is an executable, funded offer; a broke realm publishes a non-executable **need** instead, so its starvation stays fully visible without pretending to be tradeable (market-vision §3.3, inter-realm-economy §5.5). This strengthens the section's own thesis: every price a hauler reads is now one they can act on. Prices therefore carry information: haulers profit precisely by reading them and moving goods toward hunger — decay creates its own rescue incentive, no quest required — and tycoons read the same signals to site the next estate.

### 4.4 Projects vs. upkeep: two ways to give

The realm's two intake channels split cleanly by theme: **the realm market feeds the present** (upkeep, mercenary path — sell goods, take gold), while **contributions build the future** (projects, civic path — give goods, earn recognition/standing rather than gold). Both are sinks; they differ in what the player gets back and what the realm does with the goods.

### 4.5 Inter-realm balancing: the NPC floor

Periodically through the day, realm markets **balance unmet needs against each other**: a realm running a surplus can cover another realm's deficit, treasury to treasury, with goods paying a **transport cost that scales with distance**. With the player book location-less, this layer is the *only* place distance-scaled goods movement exists mechanically — it is where map topology earns its economic keep. *(The old rationale — that transport costs preserve player-market price gradients for traders — is obsolete; no such gradients exist.)*

The balancing network is deliberately second-choice: transport costs must keep NPC imports strictly inferior to local supply and to hauler runs, so the network is a floor under the world — cushioning frontier and decaying realms without rescuing them or eating the hauler's lunch. Cadence, ordering, cost destination, and import caps remain open (market-vision §7.8, inheriting §6.6 here).

### 4.6 Estates produce into the metabolism

Rooted estates don't only grant their owner bonuses — they **credit their realm's stores directly with passive production**, scaled by form, level, and realm match (market-vision §3.2). A farmstead in the agrarian realm quietly tops up the local pantry whether or not its owner is online.

This is the load-bearing leniency mechanism: **a realm's low-tier upkeep should be met largely by its residents' estates' passive production.** A populated realm sustains its foundations automatically; nobody's weekend away starves the town. Active player effort — skilling, trading, hauling — is what covers the *higher-tier* appetite that development brings (§4.7). Estate production also gives every resident a stake in realm health that requires zero daily ritual: your farmstead is a citizen even when you aren't.

### 4.7 The ladder of goods

*(Unchanged; market-vision §3.2 reads from it.)* Items produced through skilling and estates are **tiered**. As realms and estates develop, their upkeep climbs the ladder — but *additively*, never abandoning the bottom rungs:

- A developing realm needs tier-1 goods (grain, logs, ore).
- A developed realm needs tier-2 and tier-3 goods (tools, worked metal, fine food) **and still consumes tier-1 in volume** — the smiths still eat bread.
- Low-tier demand is perpetual, so early-game production never becomes worthless and new players are always economically relevant.
- High-tier demand is where scarcity and skill matter, so veteran production is always distinguished.

Combined with §4.6, the ladder produces the intended difficulty curve of the living world: **tier-1 upkeep is passively covered by resident estates; each rung above it demands progressively more deliberate play and market coordination.** Specialization (§2.5) determines *which* rungs a realm can self-supply and which it must import — the industrial stronghold makes its own tier-3 tools but imports even its bread.

---

## 5. How the pieces reinforce each other

- **Specialized realms** create supply and demand gaps → the **global order book** becomes the connective tissue of the world economy, with both sides of every gap visible as orders.
- **Upkeep** makes those gaps permanent and gives the **realm markets** their purpose → demand never saturates; goods have somewhere to *go*; stores and bids make need legible.
- **The tax–treasury loop** ties realm health to real trading activity → thriving is earned, decline is legible, and gold recycles instead of inflating.
- **The map** makes need geographic even though player trade is not → presence-gated realm markets, store/treasury differentials, and the access frontier give **mobile estates** a livelihood (haulers move goods toward hunger), while the NPC balancing floor keeps distance priced into the world's own logistics.
- **Losable market access** makes the global economy something a community keeps, not something it is given → upkeep matters viscerally, and the frontier is simply the set of realms off the book — which is exactly where hauler supply runs and tycoon groundwork matter most.
- **Rooted estates** deepen realm specialization *and passively feed the realm's stores* → their owners are the communal layer's most invested contributors and its always-on foundation.
- **The estate lifecycle** turns individual effort into durable world fabric → solvent estates outlive their builders (the tycoon's legacy), derelicts become newcomers' fixer-uppers and the treasury's escheat revenue, and relocation gains a soft landing (buy in, don't start over).
- **The goods ladder** keeps every tier of production relevant forever → new players matter to old realms; veterans chase the scarce top rungs.
- **Morphing** gives communities a shared long-term project with real authorship → the map records player history.
- **Decay and regression** balance the whole system and **manufacture frontier** → which gives **adventurers** somewhere to matter → whose discoveries feed the settled realms' appetites.
- **The tutorial island** teaches the core loop in miniature, then pushes the player into the real version of the choice.

The test for any future feature: does it strengthen at least one of these loops without flattening the trade-offs (mobility vs. depth, specialization vs. self-sufficiency, growth vs. upkeep, local supply vs. imports) that make the choices meaningful?

---

## 6. Open questions (to resolve in design/content docs)

*Settled items are retained, struck to their residue, so numbering stays stable across references.*

1. **Map topology.** Partially settled by Phase 4: a content-defined map graph with per-edge costs exists and drives relocation pricing. **Travel settled by visiting-vision v0.2:** player travel takes both time *and* supplies — each edge is a cycle with per-edge supply inputs, under a Travel skill that speeds it. **Settled (0.7)** by the inter-realm economy pass: one shared `haul_cost(a,b)` over the map graph serves the balancing layer, the pairwise **landed cost** that picks a seller, and caravan attrition. The travel-cost premium in realm bids derives from a separate per-realm **remoteness** — reframed as *terrain* rather than centrality, computed from a realm's own incident edges weighted by neighbour development, so roads and settlement lower it.
2. **Estate forms and ownership.** Largely settled: content-defined forms with transformation paths shipped in Phase 4 (with the orphaned-upgrades guard); ownership history and `home_estate_id` are in the schema. Still open: the cost/cap structure that keeps multiple estates endgame, and the exact home-vs-holdings rules.
3. ~~**Visiting scope.**~~ **Settled (0.6, by visiting-vision v0.2).** Visitors gather, craft, use communal facilities, and fight **at full rate — no visitor malus**; the cost of acting away from home is the absence of your own estate's bonuses plus the travel paid to get there. **Contributions to realm projects are presence-gated** — a visitor standing in the realm may contribute; nobody may contribute remotely (supersedes the Phase 4 permissive rule / design log #23). Visiting has travel costs (time + supplies per edge, Travel skill) but **no stay duration and no obligation to return** — indefinite absence from a fixed estate is legal, with upkeep and solvency running at home. Realm-market trading while visiting: yes — that's the point.
4. ~~**Upkeep mechanics shape.**~~ **Settled (0.7) by the inter-realm economy pass**, which is now authoritative. Cadence is **hourly discrete ticks with quotas authored per day**, resolved lazily and idempotently (`resolve_realm`) with the scheduled job as a liveness driver rather than the mechanism. Decay runs on a **value-weighted deficit accumulator** — a gauge measured in tick-equivalents of total starvation — through four stages, with **Strained deliberately signal-only** so the community gets a warning window before anything is taken. Estate production is credited to stores as assumed, and estates draw upkeep from those same stores in goods; reference prices become the *reporting* unit for solvency. **Residual, deferred:** what the Failing stage actually sheds (§3.4), pending a realm-upgrades pass.
5. **Treasury details.** **Largely settled (0.7).** No seed mint; cold start is a content-built solvent world with NPC estates — now promoted from a cold-start tool to a **standing mechanism**, so any development node may declare natural production and a wild realm has something to sell. Frontier seeding is a layered no-mint stack: sell your own production, earn from balancing imports, collect tax once access is earned, plus optional **player patronage** (gifting gold to a treasury). **Treasuries may fund projects** — yes, bounded by a per-tick rate derived from a content horizon, which keeps the realm a floor under a project rather than a substitute for its community. Still open: escheat mechanics as a revenue stream (§6.9).
6. ~~**Inter-realm balancing rules.**~~ **Settled (0.7).** Cadence is **daily — deliberately much slower than upkeep**, because that gap is the hauler's head start. Clearing is **demand-pull**: the needy realm shops, ordered by deficit severity, choosing the source with the lowest **landed cost**, and never paying more per delivered unit than its own bid. Transport cost is neither burned nor escrowed but taken in **goods attrition** — gold moves treasury-to-treasury and the caravan simply arrives light, which makes NPC imports structurally inferior to hauler runs without a tuning number to maintain. Attrition is a **modifier with map-edge scope**, so realm upgrades and roads reduce it while world events (bandits on a pass) raise it until players clear them. Imports are capped to restore a realm to its **reserve line and no further**, at a fixed trickle per run, so the realm stays visibly hungry and the hauler's wage survives the rescue.
7. **Morphing/regression graph.** How many archetypes, what transitions, and how much is player-steered (project choice) vs. automatic (activity-driven)? Can a community *deliberately* regress or re-specialize a realm? (The graph machinery exists as of Phase 4; this is now purely a content-design question plus the activity-driven trigger question.)
8. **Goods tiering.** Settled in direction by Skills and Goods §3.1: tier is a formal item content property. Residuals (tier count, thresholds, upkeep composition per stage) belong to the XP Curve and content docs.
9. **Estate succession mechanics.** Settled in principle (§3.6). Open: who sells (departed owner via listing? realm after escheat? both, at different decay stages)? Pricing (realm-set from estate value? auction?)? Does escheat require a defined "abandoned" trigger (owner inactivity window) or purely full decay? And the solvency-tuning question from §3.6: does bid-curve self-correction suffice, or do absentee estates run at reduced efficiency?
10. **Population dynamics.** Is there a minimum viable population for a realm's *active* layer (projects, morphing) even when its passive layer (estate production) persists, and does the game need soft incentives to spread players across the map?
11. **Tutorial island scope.** Which skills does it expose, and does the rowboat literally become the player's first mobile estate on the mainland, or is it consumed by the crossing?
12. **Realm identity depth.** Do realms differ *mechanically* (unique actions, unique upgrades) or only *numerically* (tags + modifiers)? Development nodes changing tag sets is now the established mechanism; content design decides how far to push uniqueness.
13. **Frontier realm markets.** **Settled:** every realm operates a realm market at every development stage — the market-access tag gates only the *global book* (market-vision §2.6). What distinguishes a frontier market is not existence but *thinness*: with few residents there is little upkeep demand, a near-empty treasury, and near-empty stores, so its bids are weak-but-real and its asks nearly nonexistent. The hauler's frontier loop therefore has a counterparty from day one, and it strengthens organically as settlement grows the realm's appetite and tax base — no special-case mechanics. ~~Residual~~ **Discharged (0.7):** the inter-realm economy pass enumerates every near-zero case and makes the structural guarantee that **no formula divides by the upkeep draw** — the bid curve's domain is `store/cap`, a realm needing nothing has a deficit ratio of zero by definition, and a realm with no funds simply has no bid rather than a degenerate one.
14. **Carried vs. stored inventory.** *(New in 0.5, open — and still open in 0.7.)* The hauler loop assumes goods are physically carried between realms, but the engine has a single location-less inventory. Nothing needs building yet; nothing may be built that *prevents* a carried/stored split later (market-vision §8 watch item). **Note the one thing that looks like an exception and is not:** the estate **larder** (§3.4) accepts upkeep goods but has **no withdrawal path**, so goods entering it have been *spent*, not *stored* — the estate cannot be used as a warehouse and no carried/stored split is created. Interlocks with estate storage and visiting.
15. **Visibility scope.** **Settled: full visibility.** Players can view (not trade) the global book and every realm's store levels, bids, and health from anywhere — trading remains gated (access tag for the book, physical presence for realm markets), but *information* is free. Rationale: the signal layer is the recruiting mechanism for haulers and tycoons and should be maximally readable; a single world-visible state is also simpler to simulate, serve, and present than per-player fog. Fog-of-war/scouting is off the table for v1 and would be an additive feature if ever wanted. (Settles market-vision §7.7 in its leaned direction — patch that doc's next revision.) Treasury *balances* remain non-exposed per the Phase 4 rule; realm health and bid behavior are the public signals.

---

## 7. What this changes in the design doc (work items, not yet decisions)

Status pass against the Phase 4 build and market-vision v1.0:

**Landed (Phase 4):**
- **Estate forms** as content-defined types with caps, bonus profiles, relocation cost class, and transformation paths. ✅
- **Estate ownership decoupled from characters** — own PK, ownership history, `home_estate_id`; transfer/escheat endpoints still future. ✅ (schema) / ⏳ (endpoints)
- **Map/topology data** in content; relocation cost = path cost × form's relocation class. ✅ (transport cost for balancing will reuse the same graph — ⏳)
- **Realm archetype as state** — development graph nodes, project-driven transitions, treasury column (dormant). ✅

**Owned by market-vision §8 (Phase 5 and later; listed here only for the world-side stake):**
- **Order book replaces listings**; tax → treasury at match time (the dormant treasury column's first writer); market-access tag gating (prerequisite: tag emission from development nodes/upgrades, skills-and-goods §7); realm **stores** on `realm_state` with bid computation from (reference price, store level, treasury); reference prices in content; presence checks on realm-market trades (interim rule: current realm = home realm); NPC estates as content for cold start (verify the ownership schema tolerates a system owner — expected yes).

**Remaining in this document's scope:**
- **Estate solvency accounting.** Per-estate production and upkeep settled against reference prices, with solvency status feeding the decay state machine. The estate schema's dormant `upkeep_profile`/`production_profile` columns reserve the room. *(Lands with the upkeep/decay phase, ~5.5.)*
- **Upkeep, decay, and balancing processing.** Realm store decay, repricing, and inter-realm balancing run in the scheduled-job slot (design.md §8.3); estate upkeep and passive production resolve lazily on character resolve, reconciled realm-side at tick time. *(Phase 5.5; the "no timers" pillar's biggest test.)*
- **Item tiers** as a content property feeding upkeep composition rules. *(Content-design time; owned by Skills and Goods §7.)*
- **Visiting.** Per-character location ≠ home realm, availability keyed to location, travel costs — now a hard prerequisite for the hauler archetype (§6.3) and interlocked with Exploration (design.md §10). *(Post-5.5 or alongside it; the presence-check interim rule buys time.)*
- **Tutorial island flow**: a starting realm with restricted availability, upkeep- and market-exempt, with a scripted one-way graduation step.

None of these threaten the core architecture; all fit the "new sources are content, new types are engine changes" rule. Sequencing pressure now concentrates on Phase 5 (market-vision's list) and Phase 5.5 (upkeep/decay/solvency, which this document owns).
