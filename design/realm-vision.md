# Yet Another Idle Skilling Game — Market Vision Document

**Version:** 0.4 (draft; economic balance expected to need tinkering)
**Scope:** The world economy — realms, estates, the two markets, upkeep and decay, and the player archetypes these create. This is one of a planned family of vision documents; siblings to come: **Economic Goods** (the item/tier catalog philosophy), **Combat**, and **XP Curve** (progression pacing). Where visions overlap (e.g., goods tiers appear here in §4.7 but belong in depth to the Economic Goods vision), this document states the economic *role* and defers the details.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` describes *how the engine and services achieve it* and is authoritative on mechanics; where a vision implies a mechanic the design doc doesn't yet support, that is a design-doc work item, not a license to improvise. The future content design document turns vision into concrete realms, skills, items, and numbers.

**Changes from 0.3:** New §3.6 defines the estate lifecycle — solvency, abandonment, succession: abandoned estates follow the decay rules but keep operating while their own production covers their upkeep; players can buy into abandoned estates when moving; the **developer/tycoon** endgame playstyle (building up estates across the world) joins the archetypes (§3.5), effectively settling multiple-estates-per-player toward *yes*. Open questions and work items updated. *Changes from 0.2:* the two-market economy, tax → treasury → procurement, estate passive production, inter-realm balancing with transport costs, the tiered-goods ladder. *Changes from 0.1:* living realms — morphing, upkeep, decay/regression, visiting, the adventurer role.

---

## 1. The elevator pitch

An idle skilling game where **where you live is the biggest choice you make — and the places themselves are alive**. The world is a map of realms, each with an economic identity that its residents *create and must sustain*. Your estate is your home in that world, and its form expresses your relationship to the map: a nomad's wagon that moves cheaply but roots shallowly, or a great workshop that anchors you to one realm and rewards you deeply for committing to it.

Progression is therefore three intertwined arcs: the familiar idle-game arc of skill levels and better recipes; a geographic arc of exploring the map and choosing where to belong; and a communal arc of building a realm up — and keeping it fed — alongside its other residents.

---

## 2. The world: a living map of realms

### 2.1 One world, many places

Realms are not parallel servers or disconnected menu options — they are **regions of a single shared map**. The map gives the world legibility (players can point at where they live), makes travel meaningful (distance and terrain matter — including for goods, §4.5), and gives the communal layer a canvas: a realm's rise *and its decline* are visible on the map to everyone.

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

The tutorial island is one-way and low-stakes: nothing built there is meant to be a long-term asset, and players should feel pulled onward, not anchored. It is also exempt from upkeep and decay — the living-world pressure begins on the mainland.

### 2.5 Upkeep: the world's appetite

Everything built must be fed. As a realm develops, it accrues **upkeep quotas** — recurring consumption of food, materials, tools, and other goods. Estates carry their own upkeep (§3.4). Upkeep is the game's primary **economic sink**: a world that only generates resources inflates into meaninglessness; a world that eats them has real prices, real scarcity, and real work for every industry.

The defining rule: **specialization increases upkeep in *other* industries.** A forest realm's mills run on food and iron tools; an industrial realm devours food and raw materials wholesale. The more a realm (or estate) narrows its identity, the more it must import to survive — so the most advanced places are the most dependent on the rest of the world, and no one gets to opt out of the economy by going tall.

How upkeep is actually *fed* — the realm market, treasury, and estate production — is the economic architecture of §4.

### 2.6 Morphing: realms become what their residents do

Realm identity is **earned, not assigned**. A realm's development path follows its residents' actual activity: a forest realm where woodcutting gives way to mills and workshops *becomes* an industrial realm over time. Realm projects are the mechanism — which projects a community completes steers which identity the realm grows into.

This makes the map a record of player history. The industrial heartland was once a forest; old residents remember cutting the trees that became its first mills. Content design defines the **development graph** — which archetypes can morph into which, via what projects — and players choose the route.

### 2.7 Decay and regression: nothing is permanent

If a realm misses its upkeep quotas, it enters **decay**: communal upgrades degrade or shut down, bonuses weaken, and the realm's tier can slip. A realm abandoned outright **regresses along the development graph** — an industrial stronghold crumbles into a dangerous barren realm; given enough time, the forest returns. Regression is the reverse traversal of the same graph that morphing climbs.

Decay is not (only) punishment — it is the world's self-balancing pressure and its renewal cycle:

- It keeps thriving realms *hungry*, sustaining demand for every industry forever.
- It solves the runaway-leader problem naturally: the realm that races ahead in tier races ahead in appetite.
- It re-creates frontier. Ruins and regrown wilds are the adventuring, prospecting, and resettlement content of the future — the world composts its past into new opportunity.

The tuning intent (numbers deferred): decay should be a *slow, visible slide with ample warning*, not a cliff. A healthy community comfortably meets upkeep — indeed, at low tiers, resident estates cover it passively (§4.6) — and decay is what happens to genuine neglect and abandonment, not to a quiet weekend.

### 2.8 Visiting: acting away from home

Relocating your estate is not the only way to experience another realm. A player may **visit** other realms — traveling there to act without moving home. Visiting is the natural mode of the **adventurer**: fighting the dangerous fauna of wild realms, exploring uncharted regions, prospecting for undiscovered resources. It may extend to limited economic activity (trading at a realm's market while passing through).

The home/away distinction keeps rootedness meaningful: production and estate bonuses live at home; visiting offers what home cannot — danger, discovery, and first pick of the frontier. Where exactly the line sits (can a visitor gather? at what penalty?) is a design-doc decision (§6).

---

## 3. Estates: your relationship to the map

### 3.1 The mobility ↔ rootedness axis

The estate is not just a bonus rack; it is the player's answer to "how do I want to inhabit this world?" Estate forms sit on a spectrum:

- **Mobile end** — a tent, a trader's wagon, a boat. Cheap and easy to relocate; thin bonuses, thin upkeep, little or no production. This is the estate of the wanderer, the arbitrageur, the adventurer ranging out of a light camp — someone who follows opportunity across the map.
- **Rooted end** — a farmstead, a forge-hall, a mill, a workshop. Expensive or slow to move (perhaps effectively permanent); deep bonuses to the industries it's built for, real passive production into the local economy (§4.6) — and correspondingly deep upkeep (§3.4). This is the estate of the specialist and the community pillar.

The design intent: **mobility and depth trade off against each other**, and the trade should be a genuine dilemma at every stage of the game. Relocation cost is not a flat fee — it is a *property of the estate form*. Moving a wagon is trivial; moving a manor should be a project (or mean rebuilding).

### 3.2 Estates and realms interact

An estate's bonuses land hardest when its specialty matches its realm's (a forge-hall in the mountain realm), stay partially useful elsewhere, and may go inert where the realm can't support them at all. This makes the pairing of estate form × realm the player's build identity — the idle-game equivalent of a character class, but chosen through economics and geography rather than a menu at creation.

### 3.3 Estates grow

Within a form, estates progress: more upgrade slots, better bonuses, more production, higher caps (offline time, storage, market presence). Progressing a rooted estate is a very-long-term goal on par with maxing a skill. Whether a player can *transform* an estate between forms (wagon → cottage → workshop) versus starting a new one is an open design question (§6).

### 3.4 Estates eat too

Estate upkeep mirrors realm upkeep at personal scale: a tent needs almost nothing; a forge-hall needs fuel, food for its hands, and materials for repair — largely goods *outside its own specialty*, per the specialization rule (§2.5). Estate decay follows the same philosophy as realm decay: slow, visible, recoverable — upgrades going dormant before anything is lost — so that upkeep is a standing reason to engage with the markets, not an anxiety mechanic that punishes taking a break. Exact leniency (grace periods, whether anything is ever truly lost) is a design-doc decision with idle-game-friendly defaults.

### 3.5 The playstyles the axis creates

The estate spectrum, the map, and the economy combine into distinct archetypes — none of them a class picked from a menu, all emergent from where a player puts their estate(s) and effort (the vision test in §5 applies to each: every archetype must feed the economy, not run parallel to it):

- **The producer** — rooted estate matched to a specialized realm; deep bonuses, deep production, pillar of a community.
- **The trader/hauler** — mobile estate, lives on the price gradients that transport costs preserve (§4.5), moves goods toward hunger.
- **The adventurer** — lives light, travels far, fights and prospects the frontier, sells discoveries and spoils to the settled world (maps, ore veins located, monster drops the industries want).
- **The developer (tycoon)** — the endgame industrialist who builds up estates *across* the world to promote its development: founding a farmstead to anchor a frontier realm's food base, raising a mill where a forest realm is trying to morph industrial, then moving on and doing it again. The tycoon's monument is not a number on a character sheet but a map dotted with working estates they built — possible precisely because a well-built estate can sustain itself after its builder moves on (§3.6). This playstyle is the strongest argument for allowing **multiple estates per player** (the schema already permits it), likely gated behind meaningful cost so it remains an endgame pursuit.

### 3.6 The estate lifecycle: solvency, abandonment, succession

Estates are semi-autonomous economic entities with their own balance sheet. An estate's production sells into the realm market (§4.6); its upkeep is bought from the same market. When production revenue covers upkeep cost, the estate is **solvent** — and a solvent estate **keeps operating whether or not its owner is present**. Estate viability is therefore emergent from the local economy, not an ownership flag: a well-matched forge-hall in a booming mountain realm hums along untended, while the same building in a starving realm slides toward insolvency.

- **Abandonment follows the ordinary decay rules** (§3.4) — there is no special "abandoned" punishment. An estate whose owner departs simply stops receiving active top-ups; if it was built well enough to be self-sustaining, it stands. If not, it decays exactly as a neglected occupied estate would: upgrades going dormant, then degrading, the shell remaining.
- **Succession:** a player moving to a new realm need not build from nothing — they can **buy into an existing abandoned estate** and move in, inheriting its form, level, and whatever survived decay. Fully-decayed derelicts plausibly revert to the realm itself, which sells them (a second treasury revenue stream, and how "ruins" become "fixer-uppers"). Whether purchase happens from the departed owner, the realm, or both is a design-doc decision (§6).
- **The world this builds:** the map accretes a fabric of standing property — working estates of active residents, self-sustaining legacies of departed builders, decaying shells awaiting new owners, and ruins feeding the frontier cycle (§2.7). Moving to a realm means arriving somewhere with *history and housing stock*, not a blank lot.

One tension to tune deliberately (flagged in §6): if solvency is too easy, the world fills with immortal ownerless estates and the decay/renewal cycle stalls. The intended lever is economic, not arbitrary — realm-market prices shift with supply and need, so a glut of identical ownerless producers depresses their own revenue toward insolvency. Whether that self-correction suffices, or absentee estates additionally run at reduced efficiency, is an open tuning question.

---

## 4. The economy: two markets and a ladder of goods

### 4.1 Two markets, two functions

- The **player market** is *circulation*: player-to-player, gold-conserving, moving goods across the world to whoever values them most. It is where inter-realm interdependence actually clears — the forest realm's timber finds the industrial realm's mills.
- The **realm market** is *metabolism*: each realm's procurement arm. It exists to feed the realm — its demand is real, generated by the realm's current upkeep quotas and active project needs, not designer-invented price lists. Goods sold to the realm market are consumed by upkeep and leave the world: this is the sink.

The two markets differentiate along upkeep. Players trade with each other to *rearrange* the world's goods; they trade with realms to *sustain* the world itself.

### 4.2 The tax → treasury → procurement loop

Realm markets buy with gold from the **realm treasury**, and the treasury's revenue is the realm's **market tax** on player-market trades conducted there (the `market_tax_pct` modifier, now with a destination). The loop closes:

> prosperous trade → tax revenue → funded treasury → realm market bids well for upkeep goods → upkeep met → realm thrives → more trade.

And its dark mirror: a ghost town has no tax base, its treasury runs dry, its bids weaken, upkeep slips, decay begins. Realm health is *emergent from economic activity*, not a designer dial. Gold is recycled, not minted — the treasury spends what players' commerce put in — keeping the faucet/sink balance honest.

### 4.3 Realm market prices are signals

Because realm-market bids come from need and treasury, prices carry information: a realm deep in deficit with gold to spend bids desperately; a well-fed realm bids low. Traders and haulers (the mobile-estate archetype) profit precisely by reading these signals and moving goods toward hunger — decay creates its own rescue incentive, no quest required.

### 4.4 Projects vs. upkeep: two ways to give

The realm's two intake channels split cleanly by theme: **the realm market feeds the present** (upkeep, mercenary path — sell goods, take gold), while **contributions build the future** (projects, civic path — give goods, earn recognition/standing rather than gold). Both are sinks; they differ in what the player gets back and what the realm does with the goods.

### 4.5 Inter-realm balancing and transport cost

Periodically through the day, realm markets **balance unmet needs against each other**: a realm running a surplus can cover another realm's deficit, treasury to treasury. But goods crossing the map pay a **transport cost that scales with distance** — which is the crucial damper. Without it, one rich realm would flood every new frontier market and prop up every decaying neighbor, flattening the map's meaning. With it:

- Nearby realms form natural economic regions; distance creates persistent price gradients.
- Frontier and decaying realms are *cushioned but not rescued* by the NPC network — genuine recovery still needs players, and the arbitrage gap that transport cost preserves is exactly the mobile trader's livelihood.
- Map topology (§2.1) earns its keep economically, not just for player travel.

Inter-realm balancing is deliberately the *second-choice* mechanism: local players selling locally should always out-compete NPC imports paying transport. The network is a floor under the world, not a replacement for its players.

### 4.6 Estates produce into the metabolism

Rooted estates don't only grant their owner bonuses — they **produce goods passively into their realm's market**, scaled by form, level, and realm match. A farmstead in the agrarian realm quietly supplies food to the local metabolism whether or not its owner is online.

This is the load-bearing leniency mechanism: **a realm's low-tier upkeep should be met largely by its residents' estates' passive production.** A populated realm sustains its foundations automatically; nobody's weekend away starves the town. Active player effort — skilling, trading, hauling — is what covers the *higher-tier* appetite that development brings (§4.7). Estate production also gives every resident a stake in realm health that requires zero daily ritual: your farmstead is a citizen even when you aren't.

### 4.7 The ladder of goods

Items produced through skilling and estates are **tiered**. As realms and estates develop, their upkeep climbs the ladder — but *additively*, never abandoning the bottom rungs:

- A developing realm needs tier-1 goods (grain, logs, ore).
- A developed realm needs tier-2 and tier-3 goods (tools, worked metal, fine food) **and still consumes tier-1 in volume** — the smiths still eat bread.
- Low-tier demand is perpetual, so early-game production never becomes worthless and new players are always economically relevant.
- High-tier demand is where scarcity and skill matter, so veteran production is always distinguished.

Combined with §4.6, the ladder produces the intended difficulty curve of the living world: **tier-1 upkeep is passively covered by resident estates; each rung above it demands progressively more deliberate play and market coordination.** Specialization (§2.5) determines *which* rungs a realm can self-supply and which it must import — the industrial stronghold makes its own tier-3 tools but imports even its bread.

---

## 5. How the pieces reinforce each other

- **Specialized realms** create supply and demand gaps → the **player market** becomes the connective tissue of the world economy.
- **Upkeep** makes those gaps permanent and gives the **realm market** its purpose → demand never saturates; goods have somewhere to *go*; prices mean something.
- **The tax–treasury loop** ties realm health to economic activity → thriving is earned, decline is legible, and gold recycles instead of inflating.
- **The map** makes the gaps geographic → transport costs preserve price gradients → **mobile estates** have a livelihood (haulers move goods toward hunger), and market access is a realm trait worth specializing in.
- **Rooted estates** deepen realm specialization *and passively feed the realm's base upkeep* → their owners are the communal layer's most invested contributors and its always-on foundation.
- **The estate lifecycle** turns individual effort into durable world fabric → solvent estates outlive their builders (the tycoon's legacy), derelicts become newcomers' fixer-uppers and the treasury's escheat revenue, and relocation gains a soft landing (buy in, don't start over).
- **The goods ladder** keeps every tier of production relevant forever → new players matter to old realms; veterans chase the scarce top rungs.
- **Morphing** gives communities a shared long-term project with real authorship → the map records player history.
- **Decay and regression** balance the whole system and **manufacture frontier** → which gives **adventurers** somewhere to matter → whose discoveries feed the settled realms' appetites.
- **The tutorial island** teaches the core loop in miniature, then pushes the player into the real version of the choice.

The test for any future feature: does it strengthen at least one of these loops without flattening the trade-offs (mobility vs. depth, specialization vs. self-sufficiency, growth vs. upkeep, local supply vs. imports) that make the choices meaningful?

---

## 6. Open questions (to resolve in design/content docs)

1. **Map topology.** Settled: topology matters, and now carries transport costs for goods (§4.5) as well as player travel. Open: graph of adjacent realms with per-edge costs vs. 2D distance layout; whether player travel takes *time* (an action?) or only resources.
2. **Estate forms and ownership.** Fixed set of content-defined forms with transformation paths, or a single estate that accumulates traits? Multiple estates per player is now *leaning yes* (the tycoon, §3.5, plus the adventurer's home-plus-wagon) — open: the cost/cap structure that keeps it endgame, and whether one estate is designated "home" (the residence that determines your realm) while others are holdings.
3. **Visiting scope.** Settled: visiting exists, anchored by adventuring. Open: can visitors gather or craft, and at what penalty? Can they sell to a foreign realm's market or contribute to its projects? Does visiting have a duration or supply cost that mobile estates reduce?
4. **Upkeep mechanics shape.** Quota cadence (continuous drain vs. periodic windows — inter-realm balancing "periodically throughout the day" suggests discrete ticks); concrete decay stages and reversal costs; how estate passive production is accounted (credited against realm quotas directly, or sold into the realm market at its bid?).
5. **Treasury details.** Starting treasuries for new/frontier realms (no tax base yet — seed capital? bootstrap exemption like the tutorial island's?); whether treasuries can fund projects too or only upkeep; tax rate as fixed content vs. community-adjustable.
6. **Inter-realm balancing rules.** Clearing cadence and ordering (who buys first?); how transport cost is computed and where it goes (burned? paid to a hauler system that players could later replace?); hard caps on how much of a realm's deficit imports may cover.
7. **Morphing/regression graph.** How many archetypes, what transitions, and how much is player-steered (project choice) vs. automatic (activity-driven)? Can a community *deliberately* regress or re-specialize a realm?
8. **Goods tiering.** How many tiers; whether tier is an item property in content (likely) or emergent from recipe depth; how upkeep quota composition shifts per development stage.
9. **Estate succession mechanics.** Settled in principle (§3.6): abandoned estates follow decay rules, solvent ones keep operating, newcomers can buy in. Open: who sells (departed owner via listing? realm after escheat? both, at different decay stages)? Pricing (realm-set from estate value? auction?)? Does escheat require a defined "abandoned" trigger (owner inactivity window) or purely full decay? And the solvency-tuning question from §3.6: does price self-correction suffice, or do absentee estates run at reduced efficiency?
10. **Population dynamics.** With the estate lifecycle absorbing the departed-players question, what remains: is there a minimum viable population for a realm's *active* layer (projects, morphing) even when its passive layer (estate production) persists, and does the game need soft incentives to spread players across the map?
11. **Tutorial island scope.** Which skills does it expose, and does the rowboat literally become the player's first mobile estate on the mainland, or is it consumed by the crossing?
12. **Realm identity depth.** Do realms differ *mechanically* (unique actions, unique upgrades) or only *numerically* (tags + modifiers)? Morphing suggests at least tag-set changes per development stage; content design decides how far to push uniqueness.

---

## 7. What this changes in the design doc (work items, not yet decisions)

The v0.4 engine supports the static version of this vision (realm tags, modifier stacking, realm tiers, inert upgrades, relocation-with-cost, market tax as a modifier type). The genuinely new engineering concepts implied here, roughly in order of how soon they bite:

- **Estate forms** as content-defined types that determine base caps, bonus profiles, upkeep profiles, production profiles, and relocation cost class. *(Bites in Phase 4, which builds estates and relocation.)*
- **Estate ownership as transferable, and estates decoupled from characters.** The lifecycle (§3.6) means estates outlive their owner's residence and can change hands — `estates.character_id` becomes nullable-or-historical ownership rather than identity, with a transfer/escheat path, and multiple-estates-per-player needs its cap type. The v0.4 schema's foresight (estates have their own PK) pays off here, but Phase 4 should not build anything that assumes character↔estate is 1:1 and permanent. *(Bites in Phase 4 at the schema level; transfer/escheat endpoints themselves can wait for a later phase.)*
- **Estate solvency accounting.** Per-estate production and upkeep settled against the realm market (revenue vs. cost), with a solvency status feeding the decay state machine. *(Lands with the upkeep/decay phase, but the estate schema should reserve room for it.)*
- **Map/topology data** in realm content, and relocation/travel/transport cost as a function of origin, destination, and (for relocation) estate form. *(Also bites in Phase 4's relocation endpoint; transport cost reuses the same distance data.)*
- **Realm archetype as state.** Realm identity (tags, modifiers, available actions, upkeep composition) becomes a function of the realm's current node in a content-defined development graph — `realm_state` grows an archetype/stage dimension plus a **treasury** balance, and morphing/regression are transitions on it. *(Shapes how Phase 4 stores realm tier.)*
- **Market tax routed to treasury.** The existing `market_tax_pct` modifier gains a destination: taxed gold credits `realm_state.treasury` instead of vanishing. *(Bites in Phase 5's market implementation — cheap to build then, expensive to retrofit.)*
- **Upkeep, decay, and balancing processing.** Time-driven world processes, which test the "no timers" pillar. Likely resolution: realm upkeep ticks, realm-market repricing, and inter-realm balancing all run in the existing scheduled-job slot (design doc §8.3 — realms are few, discrete daily/hourly ticks are cheap and match "periodically throughout the day"); estate upkeep and passive production resolve lazily on character resolve (same timestamp math as offline progress) with realm-side crediting reconciled at tick time.
- **Realm market as dynamic system.** Phase 5's realm market changes character: offers derive from upkeep needs + treasury rather than static content price lists. Static content defines *base* prices and elasticity; state supplies need and budget.
- **Item tiers** as a content property feeding upkeep composition rules.
- **Visiting.** A per-character "current location ≠ home realm" concept, action availability keyed to location, and travel costs. Interlocks with the deferred Exploration feature (design doc §10) — exploration's unlocks table and the adventurer role are probably designed together.
- **Tutorial island flow**: a starting realm with restricted availability, upkeep-exempt, with a scripted one-way graduation step.

None of these threaten the core architecture; all fit the "new sources are content, new types are engine changes" rule. Sequencing pressure: the first three shape **Phase 4** (estates, relocation, realm state) and should be decided at least at the schema level before its prompts are written; treasury routing and the dynamic realm market shape **Phase 5** and should be decided before markets are built. Upkeep/decay/balancing can land as a post-Phase-5 phase of their own once both markets exist to feed them.
