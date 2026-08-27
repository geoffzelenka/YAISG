# Yet Another Idle Skilling Game — Realm & World Vision Document

**Version:** 0.12 (the estate pass: surrender pricing, the death of abandonment, and fixed estates that do not move)

**Changes from 0.11:** One section rewritten, one added, and a ratified rule in a sibling document retired.

**Abandonment is deleted as a concept** (§3.6). Ownership and solvency are independent, and the decay machine already covers every combination — so there is no abandoned state, no inactivity window, no absent-owner flag, and no special punishment. **Estates are never truly abandoned; they simply may decay when nobody provides the upkeep.** An estate stops being yours in exactly three ways: surrender, escheat, or never. This deletes the "abandoned trigger" half of §6.9 rather than answering it.

**Surrender: the realm is the buyer of last resort** (§3.6). A player who no longer wants an estate gives it to the realm, which pays what it can. Valuation is **derived, not authored** — `V` = the estate's replacement cost from its form's and *held* upgrades' content costs, goods converted at reference prices — because an independently authored sale price would drift from build cost and open a goods-laundering arbitrage. Two constants do two different jobs: **`L[form]`, the liquidity discount** (the price of rootedness, steep for fixed forms, near zero for mobile ones) and **`m_est`, a global estate spread** (the realm's market-making margin, deliberately not the goods spread `m`). The realm buys at `V × (1 − L)` and resells at `V × (1 − L) × (1 + m_est)`, so round-tripping loses exactly the spread, by construction.

**Payment is bounded; the path is not.** `payout = min(V × (1 − L), discretionary_treasury)`, where discretionary treasury is what sits above a new treasury reserve line — upkeep procurement outranks real estate. A broke realm pays **nothing** and still takes the estate: no gold is minted, not even one ceremonial coin (§6.24). The ordering is the point — **nothing gates the player's ability to leave on the realm's ability to pay.** Escheat becomes the same code path with the payment step skipped.

**The liquidity discount flows to the buyer, not the treasury**, so used property is genuinely cheaper than new — which hands the mature-world arrival problem a free answer: a newcomer at month eighteen cannot out-earn incumbents but can buy a discounted fixer-upper no incumbent wants.

**Fixed estates do not move** (§3.7, new). §3.1's parenthetical — *moving a manor should be a project, or mean rebuilding* — is now the whole rule. A player leaving surrenders in place and receives a floor mobile estate. **This supersedes visiting-vision §2 and §8.7's third branch** (*fixed forms keep the Phase 4 gold × `relocation_cost` path*), which now has no users; `relocation_cost` as a per-form gold class is retired, closing one of the document set's unexplained gold flows. The cost of moving is now sunk investment rather than a fee, which is a better statement of §3.1's dilemma and naturally progressive. The world-side property is the one that matters: **buildings never leave the map with their owners**, so a player leaving realm A creates the on-ramp for whoever arrives next.

**Three rulings §3.7 requires:** transformation may move **up** the rootedness axis only, validated at boot (or a forge-hall becomes a wagon and drives away); the floor mobile estate is free and unconditional, and **estate-less is not a legal state**; and the larder rides with the building, since it has no withdrawal path.

**One promotion:** multiple-estate holding (§6.2) moves from nice-to-have to **prerequisite** — with fixed estates unable to relocate, it is the only thing that makes the tycoon archetype coherent.

**Two new open questions (§6.24–§6.25):** the no-mint floor recorded as a general principle, and whether a realm's willingness to buy should depend on how many of that form it already holds.

**Changes from 0.10:** One promise paid off, one read-side system added, and two things declined on the record.

**Access is the reward, and there is no contributor reward mechanic** (§2.15, new). §4.4 had promised project contributors "recognition/standing rather than gold" since 0.2 — an unbuilt mechanic that the 0.8 upgrades pass built a whole project system around without ever supplying. It is not being built. A project's return to the people who paid for it is **the access the completed project grants**, and the free-rider objection is answered by systems already in the document rather than by a new one: benefit is proportional to commitment (§3.1), maintenance is socialized while only the one-off is individually borne (§2.11), and the realm is a floor under every project (§2.10). Any reward proportional to contribution would convert gold into privilege inside the one system §2.12 was shaped to resist. §4.4 is amended accordingly.

**The realm history** (§2.15). What replaces "recognition" is a permanent, publicly readable record of *the place*: completed projects in order with their initiators and full contributor rosters, upgrades taken and the votes that took them, tiers shed to decay, identities morphed through. Deliberately **per-project and never aggregated** — a top-N-by-value ranking would recreate the wealth-to-standing conversion through the back door — valued at reference prices, and **surviving shedding**, so decay composts the build and not the memory. This is what §2.6 meant by *the map records player history*.

**A realm details page** (§2.15), the history's live counterpart: what the realm is, and what it is currently doing — active project with remaining requirement and stall/build state, and any open vote with its close time. Promoted from UX to mechanism, because under abstention-by-default a vote is only protected by its duration if it can be *found*.

**Ballots are secret; participation is not** (§2.12, §2.15). How a player voted is permanently confidential; **that** they voted is public and enters the history. If silence is the safeguard's weak point, visible participation is the pressure that counteracts apathy — accountable for not showing up, never for how you decided. **Only the outcome is published, never the tally**, because weight is inferable from estate form and tier and a three-voter frontier realm's split identifies every ballot.

**No in-game chat and no guild layer** — declined, with reasons (§2.15). Real-time player text is a moderation obligation that scales with success rather than with the feature's value. Coordination happens out of band; the game supplies something worth organizing about and a shared surface to point at. The cost is accepted rather than hand-waved: with no in-game campaign channel, **findability and generous duration are the only two protections** abstention-by-default has left (§6.17).

**Two new open questions (§6.22–§6.23):** whether a realm's estate roster is public, which ballot secrecy now depends on; and tax attribution, since market-vision §2.5 credits tax where an *order was placed*, so a visitor who uses a realm's facilities and lists from home pays the builder nothing — which undercuts both §2.11's traffic-is-tax-base rationale and §2.15's access-is-the-reward argument at exactly the point they are weakest.

**Changes from 0.9:** Two rulings, both of which simplify the system rather than add to it.

**Abstention is the default position.** A resident who does not vote has not voted — silence is neither approval nor obstruction, and only **cast** weight counts toward an outcome. This closes 0.9's flagged failure mode outright: no threshold is ever measured against total franchise, so the absentee estates a settled realm inevitably accumulates (§3.6) cannot freeze its development. A realm is governed by whoever shows up, and departure costs the departed their voice rather than costing the realm its future. §6.17's quorum question is settled.

**One consequence promoted to the front, because it is now load-bearing:** if silence doesn't count, **vote duration is the entire protection** against a small clique passing an upgrade while the realm sleeps. It stops being a tuning detail and becomes the mechanism that makes abstention safe (§2.12, §6.17) — long enough that a daily-login player reliably sees a vote before it closes. A **cooldown after a failed vote** is the companion guard, or the initiation fee is all that stands between a realm and someone re-rolling the same vote until they catch a quiet hour.

**A player votes once, however many estates they hold in the realm**, carrying the weight of their heaviest. Stacking property inside one realm buys no extra voice — which keeps wealth from converting into votes, pushes the tycoon toward breadth across the map (the archetype §3.5 actually wants), and keeps the electorate a set of *people* rather than a set of buildings. This closes both of §6.20's residuals and refines 0.9's framing: **weight comes from the estate, but the ballot belongs to the player.** The design-doc consequence is that the franchise keys at `player_id` and resolves by max-per-player rather than sum-of-rows (§7).

**Changes from 0.8 (in 0.9):** One ratification, and it supersedes two things 0.8 shipped as leans.

**The franchise belongs to the estate, not the character, and it is weighted** (§2.12). Mobile forms carry **1**; a fixed form carries **10** at tier 1 and **+1 per tier** above it. The 10:1 cliff between fixed and mobile prices political voice in the currency the game already uses for rootedness, and the near-flat curve above it means the cliff is *commitment*, not *wealth* — a tier-5 forge-hall outweighs a tier-1 homestead by 1.4×, not 5×. That compression removes the need for any per-estate vote cap. **NPC-seeded estates hold no franchise.**

**Two supersessions.** 0.8's implicit one-resident-one-vote reading is replaced by the table above. And 0.8's **tier-scoped frontier electorate is deleted outright** — it solved a problem that does not exist, since visiting-vision §2 establishes that mobile-estate characters *relocate rather than visit* and therefore live in a frontier realm from the moment they arrive. The frontier governs itself under the ordinary rule.

**Why this is the right shape, briefly:** residency is instantaneous and nearly free for mobile forms, so a character-attached vote could be bought for the price of a travel journey — while the players with the most at stake in an upgrade are precisely the ones who cannot cheaply acquire residency elsewhere. Estate-attached weighting inverts that: acquiring a heavy vote and committing to the realm are the same act. It also dissolves §6.20's tenure-cooldown question and answers the multiple-estates case (each estate votes where it stands).

**Two residuals promoted, not closed:** quorum should almost certainly be measured on weight **cast** rather than total franchise, or a bloc of legacy estates belonging to departed owners could silently freeze a settled realm forever (§6.17); and whether a player's several estates in *one* realm sum their weight, where the lean is to count only the heaviest (§6.20).

**Changes from 0.8:** Absorbs the **realm upgrades, projects and events** notes. This is the design pass 0.7 said it was waiting for, and it lands in a new subsection cluster, **§2.9–§2.14**, which is the mechanism behind §2.3 (realms are communities), §2.6 (morphing) and §2.7 (decay). Numbering elsewhere is untouched, per this document's stability rule.

**The pass in one line:** *you cannot upgrade a realm; you can only make it upgradeable, and then ask it.* Projects are paid communal builds that grant the realm **tags**; a **realm upgrade** — a tier up or a morph — becomes available when the tag set is present and is taken by a **vote of the residents**.

**The deferred question is closed.** 0.7 left exactly one question open on purpose: *what the Failing stage actually sheds*, "pending a design pass on realm upgrades." Answered in §2.14: realm decay sheds **realm-upgrade tiers, most recent first** — reverse-acquisition order being the only sequence that cannot strand a prerequisite. Each shed step withdraws that upgrade's tags *and* its maintenance draw, preserving 0.7's self-limiting property exactly. §3.4's estate lean (roll back tiers within upgrades before the form) is promoted from lean to symmetry.

**One structural delta for the design doc.** A realm's identity is currently a pure function of its **current development node**. Projects break that: the realm now holds an **ordered stack of acquired upgrades** alongside its node, contributing tags, modifiers and upkeep draw of their own. This is the largest engine implication in the pass (§7).

**Four things this closes or concretizes elsewhere:** §2.5's specialization rule gains its authoring handle (an upgrade's maintenance sits *outside* the industry it serves, so a realm's appetite becomes a record of its own choices); §4.2 gains a third treasury revenue stream (the non-refundable vote fee); §4.4 is rewritten around the project demand overlay and the stores-fund-projects rule; §6.6's "realm upgrades and roads reduce attrition" gets its concrete instance (the militia).

**Six new open questions (§6.16–§6.21):** project-slot contention and griefing, vote thresholds/quorum/electorate, disposition of a failed project's goods, whether upgrades can be deliberately dismantled, who counts as a resident, and project authorship density.

**Changes from 0.6 (in 0.7):** Absorbs `inter-realm-economy-vision.md` v0.6, which was chartered to close this document's §6.4, §6.5 and §6.6 and has closed rather more than that.

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

*(Mechanism in §2.9–§2.14.)* Two properties of that mechanism make "community" more than a label. **Only one project may be active in a realm at a time**, so a realm's build queue is a single shared focus rather than a set of parallel private errands — which project to start is a conversation. And a **realm upgrade is taken by a vote**, so the moments that actually change the map require consent from the people who will live with the result.

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

*(Amended 0.8.)* "Residents' actual activity" is now specific: activity is spent through **projects**, and each completed project **adds progress to some development edges and subtracts from others** (§2.13). A forest realm whose community keeps building sawmills drifts toward industry; one that builds granaries and replants drifts agrarian. The morph itself is not automatic even so — the drift makes an upgrade *available*, and the realm still has to vote for it (§2.12). Authorship is deliberate at the moment it matters and emergent everywhere else.

### 2.7 Decay and regression: nothing is permanent

If a realm misses its upkeep quotas, it enters **decay**: communal upgrades degrade or shut down, bonuses weaken, and the realm's tier can slip. A realm abandoned outright **regresses along the development graph** — an industrial stronghold crumbles into a dangerous barren realm; given enough time, the forest returns. Regression is the reverse traversal of the same graph that morphing climbs.

Decay is not (only) punishment — it is the world's self-balancing pressure and its renewal cycle:

- It keeps thriving realms *hungry*, sustaining demand for every industry forever.
- It solves the runaway-leader problem naturally: the realm that races ahead in tier races ahead in appetite.
- It re-creates frontier. Ruins and regrown wilds are the adventuring, prospecting, and resettlement content of the future — the world composts its past into new opportunity.
- *(Settled 0.8.)* What decay actually **takes** is now concrete: it sheds **realm-upgrade tiers, most recent first**, each step withdrawing that upgrade's tags and its maintenance draw (§2.14). Decline is the community's own build history running backwards — the lumber yard closes before the road does — and every step of it is rebuildable by exactly the mechanism that built it.
- Its most legible single consequence: a realm that decays past the node granting the **market-access tag falls off the global economy entirely** — no listing, no buying, no tax revenue (market-vision §2.6). Communal neglect has a price everyone can name.

The tuning intent (numbers deferred): decay should be a *slow, visible slide with ample warning*, not a cliff. Realm **stores** are that warning made concrete — a pantry everyone can watch drain (market-vision §3.2). A healthy community comfortably meets upkeep — indeed, at low tiers, resident estates cover it passively (§4.6) — and decay is what happens to genuine neglect and abandonment, not to a quiet weekend.

### 2.8 Visiting: acting away from home

Relocating your estate is not the only way to experience another realm. A player may **visit** other realms — traveling there to act without moving home. Visiting is the natural mode of the **adventurer**: fighting the dangerous fauna of wild realms, exploring uncharted regions, prospecting for undiscovered resources.

Visiting also carries a new economic load since market-vision v1.0: **realm-market trading is local — it requires being physically at the realm** (market-vision §3.5), and the invariant is recorded as permanent: no remote realm-market trading, ever. Trading at a foreign realm's market is therefore exactly what visiting enables, and the hauler archetype (§3.5) cannot fully activate until travel/visiting exists. The global order book, by contrast, is reachable from any realm carrying the market-access tag — no travel needed, but frontier realms without the tag are off the book entirely (market-vision §2.6).

The home/away distinction keeps rootedness meaningful: production and estate bonuses live at home; visiting offers what home cannot — danger, discovery, first pick of the frontier, and the far side of an arbitrage run. The production line is now settled (visiting-vision v0.2, §6.3 here): visitors act at **full rate with no malus** — availability is the current realm's tags — and what distinguishes residents is investment (their estate's located bonuses), not permission. Contributions to realm projects require presence.

### 2.9 Projects and upgrades: the realm's active layer

*(New in 0.8 — the realm-upgrades design pass. §2.3, §2.6 and §2.7 say what a realm's authorship should feel like; this cluster says how it works.)*

Realms are how players shape the map, and the shaping has a long arc: an ancient forest becomes a mixed-use timber town, the cleared land becomes meadow and then farmland, and the farm town's trade becomes industry. That arc is built out of two nested systems, and the distinction between them is load-bearing.

- A **project** is a discrete communal build — *establish trade routes*, *raise the capital from hamlet to walled city*, *cut a lumber yard*, *raise a militia*. It is paid for in goods, gold and time by the people standing in the realm, and on completion it grants the realm **tags**, permanently (until shed).
- A **realm upgrade** is a change to the realm's position on the development graph — a **tier up** (same identity, deeper) or a **morph** (a different identity entirely). An upgrade cannot be bought or built directly. It becomes *available* when the realm holds a required set of tags, and it is *taken* by a **vote of the residents**.

So projects are the currency of realm change and the upgrade is the act of change: **you cannot upgrade a realm; you can only make it upgradeable, and then ask it.** Every tier of every realm on the map is a stack of finished projects and a vote somebody called.

**Vocabulary warning: realm upgrades are not estate upgrades.** Estate upgrades are bought by an owner and installed into that estate's slots (§3.3). Realm upgrades belong to the realm, are never installed by anyone, and are held and lost communally. The two systems share a word and nothing else; always qualify it.

**And one note on "flags."** The design notes call what a project grants a *flag*. That is the same thing this document and `design.md` already call a **tag** — the vocabulary that gates availability and carries the market-access rule. Using one word keeps realm upgrades inside the existing tag-emission machinery rather than inventing a parallel one (§7).

### 2.10 The project lifecycle

**Offered.** Content authors projects against development nodes, so a realm sees only the projects its current identity and tier can attempt. Each project declares a **contributor scope** (residents only, or residents and visitors), a **kickoff cost**, a **total cost** in goods and gold, a **build time**, and what it grants.

**Kicked off.** Any eligible player pays the kickoff cost to open the project. **Only one project may be active in a realm at a time.** This is the pacing constraint of the whole communal layer, and it is a feature rather than a limitation: a scarce project slot is what turns "what should we build" into a question the realm has to actually answer together. It is also the pass's most obvious griefing surface (§6.16).

**Contributed to.** Anyone within scope may contribute toward the total. Two gates now stack, and they are independent:

- **Presence, always.** Contributing requires physically being in the realm (§6.3, settled 0.6). Developing a distant realm means someone carried the goods there — the hauler's frontier loop working as intended.
- **Residency, per project.** Each project separately declares whether visitors count. A tightly civic project (the realm's own capital) may be residents-only; a project the realm wants outside help with (a road, a garrison) opens to anyone standing there.

The second gate needs one guard rail: a frontier realm has few or no residents, so **its early projects must be visitor-open or the realm can never start** (§6.17).

**Funded by the realm itself, at a trickle.** The treasury may fund a project's gold, bounded by a per-tick rate derived from a content horizon — settled in 0.7 (§6.5). 0.8 adds the goods analogue: **the realm's stores may release goods into an active project, but only from surplus above the reserve line, and at the same kind of bounded rate.** Two properties fall out and both are wanted: a well-fed realm builds visibly faster than a hungry one, and **a realm can never eat its own upkeep to build**, because the reserve line is untouchable. *(The design notes call this the realm's larder; the realm's word for its pantry is **stores**. The estate **larder** remains an estate-only structure with no withdrawal path (§3.4), and nothing here creates one — see §6.14.)*

**Building.** When the full cost is delivered, the project takes a **build time** before it completes. The delay is doing real work: it stops a wealthy realm from converting a stockpile into instant tiers, it gives the realm a legible "under construction" state, and it puts a floor under how fast the map can change. *(Phase 4 already has the analogous machinery for transitions — `pending_transition`, with edge awards rejected while one is live.)*

**Complete.** The tags land on the realm, the maintenance draw they carry switches on (§2.11), and the project awards **edge progress** on the development graph (§2.13).

**Languishing, then failed.** A project that stops receiving contributions does not sit open forever. It **languishes** on a stall gauge and eventually **fails**, freeing the slot. This deliberately reuses realm decay's philosophy (§2.7) rather than inventing a second failure model: a gauge rather than a deadline, a signal-only warning stage before anything is at risk, ample time, and full reversibility — a single contribution resets the stall. The thematic point is that an over-ambitious project is a real communal risk, not just a slow one; the mechanical point is that the realm's one slot cannot be occupied indefinitely by a dead build. What happens to goods already contributed is genuinely open (§6.18).

### 2.11 What tags do — and what they cost

A tag has two effects, and the second is the one that makes the system honest.

**Tags unlock and improve what everyone in the realm can do.** The forest realm completes its lumber yard, and now *anyone acting in that realm* can refine logs into planks, up to the tier of the lumber yard. This is availability resolved from the realm's tags — which means it extends to **visitors** as well as residents, since availability keys off the realm you are standing in (§2.8). Communal facilities are therefore a realm's advertisement: a well-built realm draws traffic, and traffic is tax base. Other tags are pure modifiers rather than unlocks — a militia that lowers caravan attrition, which §6.6 already anticipated as an **edge-scoped modifier** that realm upgrades and roads can reduce.

**Tags eat.** Every project's grant carries a **maintenance cost** added to the realm's ongoing goods draw — the lumber yard needs generic metal tools and food for its hands, forever. This is the authoring handle §2.5's specialization rule has been missing: **an upgrade's maintenance should sit outside the industry it serves.** The sawmill is fed by the farm and the forge; the forge is fed by the farm and the mine.

The consequence is worth naming plainly, because it is the thesis of the whole living-world layer: **a realm's appetite is a record of its own choices.** Nobody assigned the industrial stronghold its enormous bread bill. It built the things that eat.

### 2.12 The vote

An upgrade with its prerequisite tags in place is *available*, not *taken*. Taking it works like this:

1. Any resident may **initiate** the upgrade vote, paying a gold fee into the realm's treasury.
2. The **estates standing in the realm as of the moment of initiation** approve or disapprove, each carrying a **vote weight**.
3. If it passes, the upgrade process begins. If it fails, nothing happens — **and the realm keeps the gold either way.**

The non-refundable fee is doing three jobs at once: it is an anti-spam cost on calling votes, it is a genuine gold sink, and it is a **third standing revenue stream for the treasury** alongside market tax and escheat (§4.2). It should scale with the tier of the upgrade being called, so that trivial early votes are cheap and calling a realm's tier-4 industrialization is a serious act.

**Weight comes from the estate; the ballot belongs to the player.** *(Ratified 0.9, refined 0.10; supersedes 0.8's one-resident-one-vote reading and its tier-scoped frontier exception.)* A realm's electorate is the set of **players holding estates in it**, and how loudly each speaks is a property of the property:

| Estate | Weight |
| --- | --- |
| Any mobile form (tent, wagon, boat, camp) | **1** |
| Fixed form, tier 1 | **10** |
| Fixed form, each tier above the first | **+1** (10% of base) — tier 2 = 11, tier 3 = 12, … |

**A player votes once, however many estates they hold there** (ratified 0.10), carrying the weight of their **heaviest** estate in the realm. Stacking property inside one realm buys no additional voice — which is the right answer for three reasons: it stops wealth converting directly into votes and undoing the flattening the near-flat tier curve was chosen for; it pushes the tycoon toward *breadth* across the map, which is the archetype §3.5 actually wants; and it keeps the electorate a set of people rather than a set of buildings, which is what makes the vote read as a community deciding rather than a shareholders' meeting.

Two ratios carry the rest of the design, and both are deliberate:

- **10:1 between fixed and mobile.** It takes ten wagon-dwellers to outweigh a single homesteader. Political voice is priced in exactly the currency the game already charges for rootedness — you cannot cheaply acquire a say in a realm you are not committed to, because the thing that makes your vote heavy is the thing you cannot easily move (§3.1). The wagon-dweller still counts; they simply do not decide.
- **Nearly flat above that.** A tier-5 forge-hall carries 1.4× a tier-1 homestead, not 5×. The cliff is *commitment*, not *wealth*. This is what removes the mega-estate concern raised against weighting in general: an endgame industrialist cannot buy a realm's future outright, they can only earn a slightly louder voice than the neighbour who moved in last month. **No separate cap on any one player's share is needed** — the compression and the one-ballot rule are the cap.

**NPC-seeded estates hold no franchise** (ratified 0.9). Content-authored estates are a standing mechanism rather than a cold-start crutch since 0.7 (§6.5), and letting them vote would let the system ratify its own upgrades. They produce, they consume, they do not govern. *(Under the one-ballot rule this is nearly self-enforcing — they have no player behind them — but it should be an explicit rule rather than an accident of implementation.)*

**The default position is abstention** (ratified 0.10). A resident who does not vote has not voted: silence is neither approval nor obstruction, and only **cast** weight counts toward the outcome. This is the correct default and it closes the failure mode 0.9 flagged — a settled realm accumulates estates whose owners have moved on (§3.6), and any rule that read silence as a "no," or that measured a threshold against *total* franchise, would let a bloc of absentee farmsteads freeze a living community's development permanently. Under abstention-by-default, a realm is governed by the people who show up, and departure costs the departed their voice rather than costing the realm its future.

**The consequence, stated plainly, because it is the load-bearing one:** if silence doesn't count, then **vote duration is the entire protection** against a small clique passing an upgrade while the realm sleeps. The window must be long enough that a daily-login player reliably sees a vote before it closes — this is not a tuning detail but the mechanism that makes abstention safe, and it should be authored generously and probably scaled by the tier of the upgrade at stake (§6.17). A failed vote likely also wants a cooldown before the same upgrade can be re-called, or the initiation fee is the only thing standing between the realm and someone re-rolling the same vote until they catch a quiet hour.

**The snapshot still matters**, and it snapshots weights as well as membership: eligibility *and* weight are fixed at initiation, so neither relocating a bloc in nor levelling an estate mid-vote can move the result.

**Ballots are secret; participation is not** *(ratified 0.11)*. How a player voted is permanently confidential. **That** they voted is public and enters the realm's history alongside the initiator, and only the **outcome** is published — passed or failed, never the tally. See §2.15 for the reasoning and for the small-electorate case that rules out publishing the split.

**Why a vote at all**, when nothing else in the game has governance? Because an upgrade is the one action that changes everyone else's bonuses, everyone else's upkeep, and in the case of a morph, everyone else's *build*. A rooted specialist chose their realm partly for what it is; letting a single wealthy player morph it out from under them is the failure mode the vote exists to prevent. It also gives the project stack a ratification step, so the community's accumulated work converts to identity only when the community says so.

**The frontier needs no special case.** 0.8 proposed a tier-scoped electorate to keep empty realms upgradeable; it is unnecessary and has been deleted. A mobile-estate character who travels to a frontier realm **lives there on arrival** (visiting-vision §2 — mobile forms relocate, they never visit), so the hauler or tycoon who opens a frontier is a resident with a vote from the moment they park. A realm with genuinely no estates in it has nobody to call a vote and nothing built to vote on. The frontier governs itself by whoever showed up, exactly as intended, and it does so under the same rule as everywhere else.

### 2.13 What upgrades do: tiering, morphing, and the tier-3 ratchet

An upgrade either **tiers the realm up** along its current identity or **morphs it** into another kind. Both traverse the same development graph; morphing is just a sideways edge.

**Every project moves the needle in both directions.** Each completed project **adds progress to some development edges and subtracts from others.** Sawmills push a forest realm toward industry and away from pasture; granaries and replanting push it the other way. Edge weight is therefore the accumulated *direction* of a community's building, and what an upgrade vote ratifies is a drift the realm has already been living.

**The low-tier loop is a feature, not an exploit.** Players will plant trees and cut them down, walking a realm from forested to plains and back. That loop should stay cheap and legible: it is the clearest possible tutorial in the idea that *the map is yours to author*, and it costs the world nothing, because low-tier realms are shallow by definition.

**The tier-3 ratchet.** Above roughly tier 3, horizontal change should become very hard — and structurally, not by a rule that announces itself:

- High-tier upgrades require **deep tag sets**, and the tags a rival identity demands are largely incompatible with the ones you hold. Morphing sideways at depth therefore means **shedding** upgrades first — dismantling the lumber yard to become farmland — and shedding is expensive by construction (§6.19).
- **Content simply stops authoring horizontal edges** above the threshold. The graph narrows as it deepens.
- Everything above the ratchet is **sunk communal investment**, and the vote is a vote to throw it away. Politics finishes the job the graph starts.

Regression is this same machine in reverse and needs no separate design (§2.7, §2.14).

### 2.14 What decay sheds — the deferred question, closed

Version 0.7 left precisely one question open on purpose: **what the Failing stage of decay actually sheds**, deferred "pending a design pass on realm upgrades." This is that pass, and the answer follows from the structure above.

**Realm decay sheds realm-upgrade tiers, most recent first.**

- **Reverse-acquisition order is not a stylistic choice — it is the only safe one.** Later upgrades are built on prerequisite tags granted by earlier ones, so LIFO is the sole shed sequence guaranteed to leave the realm in a legal state. Any other order can strand an upgrade whose prerequisites just vanished. (This is the realm-side twin of the estate's `WOULD_ORPHAN_UPGRADES` guard.)
- **Each shed step withdraws that upgrade's tags *and* its maintenance draw**, which preserves 0.7's load-bearing property exactly: a decaying realm walks its own appetite down until the local economy can support what remains. It cannot spiral to nothing. It composts down its own build history, tier by tier, to frontier, and stops.
- **Everything shed is rebuildable by the mechanism that built it** — the same project chain, re-run. That is what makes shedding safe to be *real* rather than cosmetic: loss is graduated, legible, and reversible by play, so it can have teeth without being an anxiety mechanic (§2.7's tuning intent).
- **The estate side becomes symmetry rather than lean.** §3.4's leading direction — roll back tiers within upgrades before touching the estate's form — is now the same rule the realm runs, on the same four-stage machine. Both shed the newest layer first; neither destroys the shell.

One residual, deliberately small: whether shedding is clean or leaves **rubble** — a derelict tag requiring a cheap clearing project before rebuilding (§6.19). It interlocks with deliberate dismantling, since both need the same "remove an upgrade" path.

### 2.15 The record: what a contributor gets, and what the realm remembers

*(New in 0.11. §4.4 promised project contributors "recognition/standing rather than gold," which read as an unbuilt mechanic. It is not one. This section says what the return actually is, and what the realm publishes about how it got there.)*

**Access is the reward.** A project's return to the people who paid for it is the thing the project builds — the lumber yard they can now use, the road that shortened their edges, the market access that put them on the global book, the tier that deepened every bonus they act under. There is **no contributor reward mechanic**: no standing score, no title, no bonus, no claim on the realm. Recording that as a decision rather than an omission, because the alternative is worse in a specific way — any reward proportional to contribution converts gold into privilege inside the one system this document deliberately built to resist that (§2.12's near-flat weight curve exists precisely so wealth cannot buy a realm's future), and any reward *not* proportional to contribution is a participation trophy that nobody optimizes for anyway.

The obvious objection is the free-rider one: why fund a public good rather than wait for a neighbour to fund it? Three answers, all of which are already true in the systems above and only needed stating:

- **Benefit is proportional to commitment, and commitment is what the map already charges for.** A rooted forge-hall extracts vastly more from a lumber yard over its life than a passing wagon does. Wherever one player's expected benefit exceeds the whole cost, that player builds it alone and everyone else free-rides — and that is a *fine* outcome, because the builder wanted it anyway and the realm got it. The mobility↔rootedness axis (§3.1) does the work a contributor reward would otherwise have to do, which is why the rooted specialist is the communal layer's most invested contributor (§5) without needing to be paid to be one.
- **The ongoing cost is socialized; only the one-off is borne individually.** A project's maintenance draw (§2.11) is paid from communal stores, fed by whoever sells into the realm market. Contributors buy the asset; the realm feeds it.
- **The realm is a floor under every project.** Treasury gold and above-reserve stores trickle in regardless (§2.10, §4.4), so no project depends on a single benefactor and no contribution is wasted on something that could never finish.

**One thing this does not fix, named honestly.** Access is non-excludable to **visitors**, who use a realm's tags at full rate with no malus (§2.8, §2.11) and pay nothing toward the maintenance draw. §2.11 justifies communal facilities partly as advertisement — traffic is tax base — but tax credits the realm where a *sell order was placed* (market-vision §2.5), so a visitor who refines here and lists from anywhere else contributes nothing, and with a flat global rate they are indifferent to where they list. If the reward for building is access, the reward leaks exactly where the pass wanted it strongest. Two levers exist and neither is spent: **contributor scope** (§2.10 already lets a project declare itself residents-only, so a realm may at least make outsiders buy in to get in) and **tax attribution**, which is the stronger fix and belongs to market-vision (§6.23).

**The realm history.** What replaces "recognition" is a record, and it is a record of *the place*, not a ranking of people. Every realm carries a permanent, publicly readable **history**: the projects it has completed, in order, each with its initiator and its full contributor roster; the upgrades it has taken and the votes that took them; the tiers it has shed to decay; the identities it has morphed through. This is what §2.6 meant by *the map records player history* and what §3.5 promised the tycoon as a monument — legible from anywhere under the full-visibility rule (§6.15), so a builder's work is visible to a world they have long since left.

Three properties, each deliberate:

- **Per-project, never aggregated.** The history lists who built what; it does not compute a top-N-by-value ranking of a realm's residents. An aggregate leaderboard would recreate exactly the wealth-to-standing conversion this section just declined, and it would do it through the back door.
- **Contributions are valued at reference prices.** Contributions are goods and gold and need a common unit for display; reference prices are already the reporting unit for solvency (inter-realm §7.3) and no new concept appears. Reference prices are fixed content, so a historical entry does not silently re-value itself.
- **The record survives shedding.** If decay takes a lumber yard and a later community rebuilds it, the original builders stay listed, and the shedding is itself an entry. Decay composts the build, not the memory — which costs nothing and makes loss feel like history rather than erasure.

**The realm details page.** The history's live counterpart. A realm's page shows what it *is* (node, held upgrades, tags, health band, store levels, bids) and what it is **currently doing**: whether a project is active, who kicked it off, its total cost and remaining requirement per good, its stall gauge if it is languishing, its build countdown if it is funded — and whether a vote is open, on what, and when it closes. This is not merely UX. Under abstention-by-default, **vote duration is the entire protection** (§2.12), and duration only protects anyone if the vote is *findable*; the details page is where it is found. It is also the hauler's and the tycoon's instrument — a realm mid-build bidding hard for stone is a market event with a story attached (§4.4), and the page is where the story is readable.

**What the vote publishes.** The split is deliberate and it pairs with abstention-by-default:

- **How a player voted is confidential.** Permanently, not merely during the vote.
- **That a player voted is public**, and logged to the realm's history alongside the initiator. If silence is the safeguard's weak point, then making *participation* visible is the pressure that counteracts apathy — a resident can be held to account for not showing up, never for how they decided. It costs nothing to build: §7 already specifies abstention as the *absence of a ballot row*, so the participation log is the set of ballot rows and the choice column simply has no endpoint that reads it.
- **Only the outcome is published, not the split.** Passed or failed, with the roster — never the tally. Weight is inferable from estate form and tier, so in a three-voter frontier realm a published 11–1 identifies both ballots exactly. Frontier realms are where votes matter most and where anonymity fails hardest, so the tally stays private everywhere rather than being conditioned on a population threshold nobody would trust.

Ballot secrecy is therefore only as strong as the privacy of the weight table, which raises a question this document has not previously had to ask: whether a realm's **estate roster** — who holds what form at what tier — is publicly readable. Full visibility (§6.15) covers the book, stores, bids and health; it says nothing about estates. Open, and now load-bearing (§6.22).

**No in-game chat, and no guild layer.** Recorded as a decision, not a gap. Real-time text between players is a moderation obligation — reporting, escalation, appeals, minors, staffing — that this project has no appetite to carry, and the obligation scales with success rather than with the feature's value. The communal layer is therefore coordinated **out of band**: players organize wherever players already organize, and the game's job is to give them something worth organizing *about* and a shared surface to point at. That surface is the details page and the history. The consequence must be accepted rather than hand-waved: without an in-game campaign channel, a vote cannot be argued in-game, which makes the **findability** of an open vote and the **generosity** of its duration the only things standing between abstention-by-default and rule-by-whoever-happened-to-log-in (§6.17). Both are now protections rather than conveniences. Asynchronous, non-conversational signals — a vote-is-open indicator, a project-needs-goods indicator, surfaced on the map rather than only inside the realm — are the additive design space here, and they carry no moderation surface because they emit no player-authored text.

---

## 3. Estates: your relationship to the map

### 3.1 The mobility ↔ rootedness axis

The estate is not just a bonus rack; it is the player's answer to "how do I want to inhabit this world?" Estate forms sit on a spectrum:

- **Mobile end** — a tent, a trader's wagon, a boat. Cheap and easy to relocate; thin bonuses, thin upkeep, little or no production. This is the estate of the wanderer, the hauler, the adventurer ranging out of a light camp — someone who follows opportunity across the map.
- **Rooted end** — a farmstead, a forge-hall, a mill, a workshop. Expensive or slow to move (perhaps effectively permanent); deep bonuses to the industries it's built for, real passive production into the local stores (§4.6) — and correspondingly deep upkeep (§3.4). This is the estate of the specialist and the community pillar.

The design intent: **mobility and depth trade off against each other**, and the trade should be a genuine dilemma at every stage of the game. Relocation cost is not a flat fee — it is a *property of the estate form*. Moving a wagon is trivial; moving a manor should be a project (or mean rebuilding). *(Phase 4 shipped this: estate forms with transformation paths, form-dependent relocation cost over map paths, instant and delayed relocation.)*

*(Extended 0.9.)* The axis now prices a third thing alongside bonuses and upkeep: **political voice**. Realm-upgrade votes are weighted by the estate, 10:1 in favour of fixed forms over mobile ones (§2.12), so what you can say about a realm's future is set by how hard it would be for you to leave it. The wagon-dweller trades a say in the map for the freedom to go anywhere on it — which is the same bargain the form already makes everywhere else, extended to the one system where communities decide things.

### 3.2 Estates and realms interact

An estate's bonuses land hardest when its specialty matches its realm's (a forge-hall in the mountain realm), stay partially useful elsewhere, and may go inert where the realm can't support them at all. This makes the pairing of estate form × realm the player's build identity — the idle-game equivalent of a character class, but chosen through economics and geography rather than a menu at creation.

### 3.3 Estates grow

Within a form, estates progress: more upgrade slots, better bonuses, more production, higher caps (offline time, storage, market presence — the order-slot cap of market-vision §2.4 is a natural estate-progression axis). Progressing a rooted estate is a very-long-term goal on par with maxing a skill. Transformation between forms exists (Phase 4: content-defined transformation paths, with the WOULD_ORPHAN_UPGRADES guard); the remaining questions are content-shape ones (§6.2).

### 3.4 Estates eat too

Estate upkeep mirrors realm upkeep at personal scale: a tent needs almost nothing; a forge-hall needs fuel, food for its hands, and materials for repair — largely goods *outside its own specialty*, per the specialization rule (§2.5). Estate decay follows the same philosophy as realm decay: slow, visible, recoverable — upgrades going dormant before anything is lost — so that upkeep is a standing reason to engage with the markets, not an anxiety mechanic that punishes taking a break.

*(Concretized in 0.7 by inter-realm-economy §7.6.)* "Follows the same philosophy" is now literal: estates run the **same four-stage machine as realms**, on the same deficit accumulator, with the same reversibility — Fed, Strained (signal only), Faltering (upgrades dormant, nothing lost), Failing (shedding), terminal shell. The property that makes realm decay safe transfers with it: **each shed step lowers the estate's own upkeep**, so a degrading estate walks its draw down until the local economy can support what remains. An estate cannot spiral to nothing; it composts to a **zero-upkeep shell** and stops, exactly as a regressing realm composts to frontier. Players also get a lever they previously lacked: the **larder**, a prepaid upkeep buffer with no withdrawal path, so a player planning a long absence can provision the estate before leaving.

~~**Still open, deliberately:** *whether anything is ever truly lost*~~ — **settled (0.8) by the realm-upgrades pass** (§2.14), which is the pass this question was deferred pending. The leading direction is confirmed and now shared with the realm side: **shedding rolls back tiers within upgrades, newest first, before touching the estate's form at all.** Loss is graduated rather than binary; the form and the shell survive; and each shed step lowers the estate's own draw, which is the property that keeps the machine self-limiting. The realm-side argument for reverse-acquisition order applies here verbatim — later upgrades sit on earlier prerequisites, so LIFO is the only sequence that cannot orphan one, and the estate already has the guard for it (`WOULD_ORPHAN_UPGRADES`, design §7.4). The five constraints from inter-realm-economy §6.7 are satisfied by this shape; residual tuning (how many tiers per stage, how fast) is a numbers question for the content pass.

### 3.5 The playstyles the axis creates

The estate spectrum, the map, and the economy combine into distinct archetypes — none of them a class picked from a menu, all emergent from where a player puts their estate(s) and effort (the vision test in §5 applies to each: every archetype must feed the economy, not run parallel to it). *(This section is rewritten per market-vision §5 — the old trader/hauler hybrid is superseded.)*

- **The producer** — rooted estate matched to a specialized realm; deep bonuses, deep production, pillar of a community. Sells surplus on the global book at world prices and feeds the local stores through estate production — the always-on foundation of the realm's metabolism.
- **The hauler** — mobile estate, physically moves goods toward hunger. Two loops, both anchored in the presence rule (market-vision §3.5): **realm arbitrage** — buy from a realm market selling cheap out of full stores, travel, sell into a starving realm's scarcity-inflated bids; decay literally pays the hauler to fix it — and **frontier supply runs** — realms without market access import everything in someone's carried inventory, and provisioning them is pure hauler work that self-obsoletes once the realm earns the tag and the frontier moves on. The counterparty is the world itself.
- **The trader** — distinct from the hauler: works the global order book itself — spreads, timing, order-slot management. No travel required; the book is their realm.
- **The adventurer** — lives light, travels far, fights and prospects the frontier; buys consumables at world prices anywhere with access and sells discoveries and spoils into the same book (maps, ore veins located, monster drops the industries want) — feeding the economy going and coming.
- **The developer (tycoon)** — the endgame industrialist who builds up estates *across* the world to promote its development: founding a farmstead to anchor a frontier realm's food base, raising a mill where a forest realm is trying to morph industrial, then moving on and doing it again. The realm-market signal layer — store levels and treasury health across the map — doubles as the tycoon's prospectus. Their monument is not a number on a character sheet but a map dotted with working estates they built — possible precisely because a well-built estate can sustain itself after its builder moves on (§3.6). This playstyle is the strongest argument for allowing **multiple estates per player** (the schema already permits it), likely gated behind meaningful cost so it remains an endgame pursuit.

### 3.6 The estate lifecycle: solvency, surrender, succession

*(Rewritten in 0.12. The heading previously read "solvency, abandonment, succession"; abandonment has been deleted as a concept — see below.)*

Estates are semi-autonomous economic entities with their own balance sheet. An estate's production credits the realm's stores (§4.6); its upkeep is drawn from the same local economy. *(Amended 0.7:)* estates transact in **goods** both ways — production credits the realm's stores, upkeep draws from them — which is what makes the specialization rule of §2.5 generate real cross-industry demand rather than an estate quietly eating its own output. **Reference prices become the reporting unit rather than the mechanism**: an estate is *mechanically* solvent when its larder or the local stores could supply its upkeep this tick, and its reported figure (*"net +12g/day at reference prices"*) is what the owner reads and what a tycoon prospects with. When production covers upkeep, the estate is **solvent** — and a solvent estate **keeps operating whether or not its owner is present**. Estate viability is therefore emergent from the local economy, not an ownership flag: a well-matched forge-hall in a booming mountain realm hums along untended, while the same building in a starving realm slides toward insolvency.

**There is no abandonment** *(0.12)*. The concept is deleted rather than defined. Ownership and solvency are independent axes, and the decay machine (§3.4, §7.6) already covers every combination: an estate whose owner stopped playing and an estate whose owner is standing beside it are the same object under the same rules, differing only in whether anyone is topping it up. No inactivity window, no absent-owner flag, no special punishment — an estate that was built well enough to sustain itself stands indefinitely, and one that wasn't degrades exactly as a neglected occupied estate would. **Estates are never truly abandoned; they simply may decay when nobody provides the upkeep.** *(This retires the "abandoned" trigger half of §6.9 outright.)*

An estate therefore stops being yours in exactly three ways, and the list is exhaustive:

- **Surrender** — deliberate, terminal, sometimes paid (below).
- **Escheat** — involuntary, terminal, unpaid: full decay hands the shell to the realm.
- **Never** — you keep it, wherever you are and whatever state it is in.

#### Surrender: the realm as buyer of last resort

A player who no longer wants an estate **surrenders it to the realm**, which takes ownership and pays what it can. Naming it a surrender rather than a sale is deliberate, because the payment may be nothing and the mechanic still has to work in that case.

**The valuation.** `V` is the estate's replacement cost — what it would take to build this exact thing today — derived from content rather than authored as a second number:

```
V = form.gold_cost + Σ held_upgrade.gold_cost
  + Σ_g (form.goods_cost[g] + Σ held_upgrade.goods_cost[g]) × reference_price[g]
```

Derivation matters. An independently authored sale price would drift from build cost the first time an upgrade is re-tuned, and the drift is an arbitrage: goods are priced by a curve that walks down as stores fill (§4.3), so a *flat* buyer of the same goods embodied in a building becomes a sale channel that never degrades. Deriving `V` closes that the way `ask = bid × (1 + m)` closes it for goods — structurally, not by vigilance. Note also that `V` sums over **currently held** upgrades, and decay *withdraws* upgrades (§2.14, §3.4), so a degraded estate prices itself downward with no separate depreciation rule and a terminal shell is worth its bare form.

**The two constants.** They do different jobs at different scopes and must not be conflated:

| Symbol | Scope | Job |
| --- | --- | --- |
| `L[form]` — **liquidity discount** | Per estate form, content | The price of rootedness. How much of `V` cannot be recovered. Near zero for mobile forms; steep for high-tier fixed ones. |
| `m_est` — **estate spread** | Global | The realm's market-making margin. The analogue of the goods spread, and deliberately *not* the same constant. |

```
realm_buys_at  = V × (1 − L[form])
realm_sells_at = V × (1 − L[form]) × (1 + m_est)
```

The sell price is a markup on the realm's own buy price, which makes buying a derelict and surrendering it straight back lose exactly `m_est` in every realm at every valuation. *(Naming: the goods merchant spread `m` is already taken — inter-realm §12. These are different constants and should never look alike in a formula.)*

**What `L` has to be large enough to do**, stated as a checkable constraint: **`L[form]` must exceed the deepest discount to reference price at which a player can reliably acquire that form's build goods.** Otherwise estate-building becomes a goods-laundering channel — buy inputs below reference on the book, embody them in a building, surrender the building at a valuation computed *at* reference.

**And `L` is doing thematic work, not only arithmetic.** A guaranteed exit de-risks rootedness, and §3.1 is built on rootedness being risky. So `L` is **the price of rootedness denominated in gold**, which is why it is a property of the *form* and why it should run opposite to mobility: a wagon liquidates near cost because it was never a commitment; a high-tier forge-hall liquidates at a fraction because it was. The axis already prices bonuses, upkeep and political voice (§3.1); this makes it price exit from the same content property.

**Payment is bounded by what the realm has, and the floor is zero.**

```
payout = min( V × (1 − L[form]), discretionary_treasury )
```

where `discretionary_treasury` is whatever sits above the treasury's own reserve line — because upkeep procurement outranks real estate, or a realm could buy a manor and then starve. A prosperous realm pays its full price; a struggling one pays what it has; **a realm with nothing pays nothing and still takes the estate.** No gold is minted, not even ceremonially: the no-mint rule is absolute in four documents and an exception this small is the kind that gets read as precedent (§6.24).

The ordering is the important part. **The surrender path is unconditional; only the price varies.** Nothing anywhere gates the player's ability to leave on the realm's ability to pay, and the only affordability check lives inside the payment step, whose failure mode is a smaller number. This also means **escheat and surrender are one code path** — escheat is a surrender the owner did not choose, at zero — which collapses a surface §6.9 has been carrying as unowned.

**What the player is really buying is release from upkeep.** Someone cutting loose a rooted estate in a dying realm is primarily trying to stop feeding it, and they get that in full regardless of price. The gold is incidental in exactly the case where it is absent, which is why the mechanic still works there.

**The realm never takes an estate the owner has not either surrendered or fully lost to decay.** Stated explicitly as a guard, because "the realm acquires derelicts" plus "the realm always accepts a surrender" is one bad reading away from a realm helping itself to a solvent absentee's farmstead.

**Two properties fall out, both wanted.** The buyback figure is public under full visibility (§6.15), so *what a realm will pay you to leave* becomes a health signal with a different character from stores and bids — the only public number pricing what a realm thinks its own property is worth. And a decaying realm accumulates surrendered estates for nothing; those estates decay like everything else, shedding upgrades and walking their draw down to zero-upkeep shells (§7.6's stability property), so this is a stock of derelicts rather than a spiral. A realm that recovers is then sitting on property it acquired at zero and may resell at `V × (1 − L) × (1 + m_est)` — which makes **a realm's ruins its capital**, and a fifth entry in inter-realm §8's no-mint bootstrap stack.

#### Succession, and the housing stock

A player moving to a new realm need not build from nothing: they can **buy into an existing estate** — from the realm, at its posted resale price, or from another player. The realm is the **floor** under this market, not the market itself, exactly as the realm market is a floor under goods and the NPC layer is a floor under trade. Third instance of one architectural role.

**The liquidity discount flows to the buyer, not the treasury.** The realm resells at a markup on what it paid, so used property is genuinely cheaper than new. This is a deliberate choice over the alternative (`realm_sells_at = V`, capturing the whole discount as revenue), and the reason has little to do with estates: a player arriving in a settled world at month eighteen cannot out-earn incumbents, but they *can* buy a discounted fixer-upper no incumbent wants. That is the on-ramp §2.4's tutorial island cannot provide, priced by a constant that had to exist anyway. The cost of the choice, named: the seller's loss is neither burned nor banked but transferred to whoever buys next, so it leaves the gold ledger entirely.

Escheated derelicts drop out of the same formula with `V × (1 − L)` acquired at zero, so their whole sale price is revenue — which is why escheat reads as a treasury stream (§4.2) and surrender does not.

**The world this builds:** the map accretes a fabric of standing property — working estates of active residents, self-sustaining legacies of departed builders, decaying shells awaiting new owners, and ruins feeding the frontier cycle (§2.7). Moving to a realm means arriving somewhere with *history and housing stock*, not a blank lot. NPC-seeded estates at world start are the same fabric laid down by content instead of players (market-vision §3.4).

One tension to tune deliberately (flagged in §6): if solvency is too easy, the world fills with immortal ownerless estates and the decay/renewal cycle stalls. The intended lever is economic, not arbitrary — realm bids fall as stores fill, so a glut of identical ownerless producers depresses their own revenue toward insolvency. Whether that self-correction suffices, or absentee estates additionally run at reduced efficiency, is an open tuning question (§6.9). A related one: whether the realm's willingness to buy should be conditional on how many of that form it already holds (§6.25).

### 3.7 Fixed estates do not move

*(New in 0.12. This supersedes visiting-vision §2/§8.7's fixed-form relocation path.)*

§3.1 always said it: *"Moving a wagon is trivial; moving a manor should be a project (or mean rebuilding."* The parenthetical is now the whole answer, and the rest of the sentence is retired.

**A fixed estate never relocates.** A player leaving the realm **surrenders it in place** (§3.6), receives a floor mobile estate, and travels as a mobile character. Visiting-vision's split stands unchanged — mobile forms relocate, fixed forms visit — but the third branch it carried, *fixed forms keep the Phase 4 gold × `relocation_cost` path*, now has no users and is deleted. That retires `relocation_cost` as a per-form gold class along with the delayed-relocation columns for fixed forms, which also closes one of the document set's unexplained gold flows: relocation gold was being charged with no stated destination.

Presence gating means the surrender necessarily happens before departure, so the sequence has no remote step and needs no new rule.

**The cost of moving is now denominated in sunk investment rather than gold**, which is a better expression of §3.1's dilemma than a fee ever was — and naturally progressive, since a tier-1 homestead's `V` is small and a tier-5 forge-hall's is not. Estates acquire their own version of the tier-3 ratchet (§2.13) by the same logic and with no separate mechanism.

**The world-side property is the one that matters most: buildings never leave the map with their owners.** Fixed estate stock is monotonically non-decreasing except through decay. That is what turns §3.6's "fabric of standing property" from an aspiration into a structural guarantee — and it means a player leaving realm A *creates the on-ramp for whoever arrives at realm A next*.

Three rulings this requires:

- **Transformation may move up the rootedness axis, never down.** Phase 4 shipped content-defined transformation paths that preserve the estate in place. Wagon → homestead is settling, and it is good, because it creates a building. **Homestead → wagon must not exist**, or the whole thing leaks: transform your forge-hall into a wagon and drive away, and the building vanishes from the world instead of entering the housing stock. Coming down the axis is a surrender. This is a **content authoring constraint with a boot-time validator**, not a convention — it is exactly the edge an author adds for symmetry without seeing the consequence.
- **The floor mobile estate is free and unconditional.** Same principle as the payment floor: the transition cannot gate on affordability, or a player surrendering in a broke realm is stranded with no estate at all. Phase 4 already grants `form.camp` to new characters; reuse it. **Estate-less is not a legal state**, and the camp is the guarantee.
- **The larder transfers with the building.** Inter-realm §7.5 is firm that a larder has no withdrawal path — goods entering it are spent, not stored — and that rule is load-bearing for the carried-versus-stored watch item (§6.14). So a stocked larder goes with a surrendered estate. That is a real sting for a player who provisioned before deciding to leave, and it must be surfaced in the confirmation rather than discovered. What it must never become is a refund.

**Political standing resets on arrival.** Franchise transfers to the realm at surrender (§2.12's NPC-estate rule now has a second source of system-owned estates), and the player shows up somewhere new carrying a camp's weight of 1. Rebuilding voice in a new realm takes the same commitment it took the first time — the axis working, not a penalty.

**One archetype consequence, and it is load-bearing.** The tycoon (§3.5) builds across the map and moves on. Under this model they never relocate anything — they leave legacies and start fresh, which fits the archetype better than relocation did. But it means **multiple-estate holding is now what makes the archetype coherent at all**: without it, "build up a realm and move on" means surrendering your work every time. §6.2's multiple-estates question is promoted from a nice-to-have to a prerequisite.

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

And its dark mirror: a ghost town has no tax base, its treasury runs dry, its bids weaken, upkeep slips, decay begins. Realm health is *emergent from economic activity*, not a designer dial. Gold is recycled, not minted — the treasury spends what players' commerce put in — keeping the faucet/sink balance honest. Escheat of fully-decayed estates (§3.6) is a planned second revenue stream, and *(new in 0.8)* the **non-refundable fee for calling an upgrade vote** (§2.12) is a third — small, bursty, and thematically exact: the realm is paid for the trouble of deciding its own future, whichever way it decides. Project **kickoff costs** flow the same way. Note that all three secondary streams are counter-cyclical to tax in a useful way: a realm busy building or busy dying earns from activity that has nothing to do with its trade volume.

### 4.3 Realm market prices are signals

Realm pricing is a three-layer model (market-vision §3.3): **reference prices** from content anchor the scale and solve cold start; the **bid curve** climbs as a good's stores drain — a realm deep in deficit bids desperately, a well-fed one bids low; and the **treasury is the hard budget constraint** — and *(amended 0.7)* **a realm never posts a bid it cannot pay for.** A bid is an executable, funded offer; a broke realm publishes a non-executable **need** instead, so its starvation stays fully visible without pretending to be tradeable (market-vision §3.3, inter-realm-economy §5.5). This strengthens the section's own thesis: every price a hauler reads is now one they can act on. Prices therefore carry information: haulers profit precisely by reading them and moving goods toward hunger — decay creates its own rescue incentive, no quest required — and tycoons read the same signals to site the next estate.

### 4.4 Projects vs. upkeep: two ways to give

The realm's two intake channels split cleanly by theme: **the realm market feeds the present** (upkeep, mercenary path — sell goods, take gold), while **contributions build the future** (projects, civic path — give goods, get the thing built). Both are sinks; they differ in what the player gets back and what the realm does with the goods. *(Amended 0.11: this section previously said the civic path earned "recognition/standing rather than gold," which implied a reward mechanic that does not exist and will not be built. **The access the completed project grants is the whole return** — see §2.15 for the argument and for what the realm publishes instead.)*

*(Expanded 0.8, per §2.9–§2.14.)* The two channels are not sealed off from each other, and the couplings are deliberate:

- **A project raises the realm's own demand.** An active project's outstanding cost sits on top of the upkeep draw as a **demand overlay**, so a realm mid-build bids harder for exactly the goods its build needs. A hauler reading the signal layer sees not just where the world is hungry but *what the world is trying to become* — and a stone shortage across three realms building roads is a market event with a story.
- **The realm's surplus feeds its own project, at a trickle.** Treasury gold (§6.5) and stores above the reserve line (§2.10) both release into the active project at a bounded rate. This is what keeps the realm a *floor* under a project rather than a substitute for its community — and the reserve line is what stops a realm from starving itself to build.
- **Completion raises upkeep permanently.** Every finished project adds maintenance to the draw (§2.11), so building is not a one-time payment but a subscription. This is the single most important tuning surface in the living-world layer: it is what makes §4.7's ladder climb, and it is what a community is really voting on in §2.12.

The dark version closes the loop: a realm that over-builds relative to its population subscribes to an appetite it cannot feed, slides into decay, and sheds the newest upgrade — which is to say the system charges ambition its real price and then hands back the change.

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
- **One project slot per realm** turns building into a shared decision rather than parallel private errands → the communal layer produces conversation, and the **upgrade vote** gives that conversation a binding moment.
- **Vote weight is a property of the estate** → the mobility ↔ rootedness axis extends into governance: political voice costs exactly what committing to a realm costs, so a realm's future is decided by the people who cannot cheaply leave it.
- **Every upgrade carries maintenance outside its own industry** → growth is a subscription, ambition is priced, and §2.5's specialization rule finally has an authoring handle instead of a designer's promise.
- **Projects publish their outstanding cost as realm demand** → a realm's *intentions* become a market signal, and haulers get paid to supply construction booms as well as famines.
- **Decay sheds the newest upgrade tier first** → decline is the community's own build history running backwards, self-limiting by construction and rebuildable by the same play that built it.
- **Decay and regression** balance the whole system and **manufacture frontier** → which gives **adventurers** somewhere to matter → whose discoveries feed the settled realms' appetites.
- **The tutorial island** teaches the core loop in miniature, then pushes the player into the real version of the choice.

The test for any future feature: does it strengthen at least one of these loops without flattening the trade-offs (mobility vs. depth, specialization vs. self-sufficiency, growth vs. upkeep, local supply vs. imports) that make the choices meaningful?

---

## 6. Open questions (to resolve in design/content docs)

*Settled items are retained, struck to their residue, so numbering stays stable across references.*

1. **Map topology.** Partially settled by Phase 4: a content-defined map graph with per-edge costs exists and drives relocation pricing. **Travel settled by visiting-vision v0.2:** player travel takes both time *and* supplies — each edge is a cycle with per-edge supply inputs, under a Travel skill that speeds it. **Settled (0.7)** by the inter-realm economy pass: one shared `haul_cost(a,b)` over the map graph serves the balancing layer, the pairwise **landed cost** that picks a seller, and caravan attrition. The travel-cost premium in realm bids derives from a separate per-realm **remoteness** — reframed as *terrain* rather than centrality, computed from a realm's own incident edges weighted by neighbour development, so roads and settlement lower it.
2. **Estate forms and ownership.** Largely settled: content-defined forms with transformation paths shipped in Phase 4 (with the orphaned-upgrades guard); ownership history and `home_estate_id` are in the schema. Still open: the cost/cap structure that keeps multiple estates endgame, and the exact home-vs-holdings rules. **Promoted in 0.12 from nice-to-have to prerequisite:** with fixed estates unable to relocate (§3.7), multiple-estate holding is the only thing that makes the tycoon archetype (§3.5) coherent — without it, "build up a realm and move on" means surrendering your work every time. Transformation paths also gain a hard constraint: **up the rootedness axis only, validated at boot** (§3.7).
3. ~~**Visiting scope.**~~ **Settled (0.6, by visiting-vision v0.2).** Visitors gather, craft, use communal facilities, and fight **at full rate — no visitor malus**; the cost of acting away from home is the absence of your own estate's bonuses plus the travel paid to get there. **Contributions to realm projects are presence-gated** — a visitor standing in the realm may contribute; nobody may contribute remotely (supersedes the Phase 4 permissive rule / design log #23). Visiting has travel costs (time + supplies per edge, Travel skill) but **no stay duration and no obligation to return** — indefinite absence from a fixed estate is legal, with upkeep and solvency running at home. Realm-market trading while visiting: yes — that's the point.
4. ~~**Upkeep mechanics shape.**~~ **Settled (0.7) by the inter-realm economy pass**, which is now authoritative. Cadence is **hourly discrete ticks with quotas authored per day**, resolved lazily and idempotently (`resolve_realm`) with the scheduled job as a liveness driver rather than the mechanism. Decay runs on a **value-weighted deficit accumulator** — a gauge measured in tick-equivalents of total starvation — through four stages, with **Strained deliberately signal-only** so the community gets a warning window before anything is taken. Estate production is credited to stores as assumed, and estates draw upkeep from those same stores in goods; reference prices become the *reporting* unit for solvency. ~~**Residual, deferred:** what the Failing stage actually sheds (§3.4), pending a realm-upgrades pass.~~ **Fully settled (0.8):** Failing sheds **upgrade tiers, newest first** — realm-side in §2.14, estate-side in §3.4, one rule on one machine. Reverse-acquisition order is forced rather than chosen (it is the only sequence that cannot orphan a prerequisite), each step withdraws the shed upgrade's tags *and* its maintenance draw, and nothing is destroyed that the original project chain cannot rebuild. Residual: rubble vs. clean shedding (§6.19), and shed-rate tuning at content time.
5. **Treasury details.** **Largely settled (0.7).** No seed mint; cold start is a content-built solvent world with NPC estates — now promoted from a cold-start tool to a **standing mechanism**, so any development node may declare natural production and a wild realm has something to sell. Frontier seeding is a layered no-mint stack: sell your own production, earn from balancing imports, collect tax once access is earned, plus optional **player patronage** (gifting gold to a treasury). **Treasuries may fund projects** — yes, bounded by a per-tick rate derived from a content horizon, which keeps the realm a floor under a project rather than a substitute for its community. Still open: escheat mechanics as a revenue stream (§6.9).
6. ~~**Inter-realm balancing rules.**~~ **Settled (0.7).** Cadence is **daily — deliberately much slower than upkeep**, because that gap is the hauler's head start. Clearing is **demand-pull**: the needy realm shops, ordered by deficit severity, choosing the source with the lowest **landed cost**, and never paying more per delivered unit than its own bid. Transport cost is neither burned nor escrowed but taken in **goods attrition** — gold moves treasury-to-treasury and the caravan simply arrives light, which makes NPC imports structurally inferior to hauler runs without a tuning number to maintain. Attrition is a **modifier with map-edge scope**, so realm upgrades and roads reduce it while world events (bandits on a pass) raise it until players clear them. Imports are capped to restore a realm to its **reserve line and no further**, at a fixed trickle per run, so the realm stays visibly hungry and the hauler's wage survives the rescue.
7. **Morphing/regression graph.** ~~How much is player-steered vs. automatic?~~ **Settled in shape (0.8):** steering is **entirely project-mediated** — activity matters only insofar as it is spent through projects, each of which adds and subtracts development-edge progress (§2.13) — and the transition itself is **never automatic upward**: it requires an available tag set plus a passed vote (§2.12). Regression *is* automatic, driven by the decay gauge. A community can therefore deliberately re-specialize a realm at low tier and only with real demolition at high tier (the §2.13 ratchet). **Still open, and now purely content-design:** how many archetypes, which edges exist at which tiers, and where exactly the horizontal-change threshold sits (the notes say "around tier 3" — that is a content dial, and the ratchet should be structural enough that the exact number is not load-bearing).
8. **Goods tiering.** Settled in direction by Skills and Goods §3.1: tier is a formal item content property. Residuals (tier count, thresholds, upkeep composition per stage) belong to the XP Curve and content docs.
9. **Estate succession mechanics.** ~~Largely settled (0.12, §3.6).~~ Pricing is answered: `V × (1 − L[form])` to buy, `× (1 + m_est)` to resell, payment bounded by discretionary treasury with a floor of zero. Who sells is answered: the realm is the *floor*, player-to-player sale is the market. The **"abandoned" trigger question is deleted rather than answered** — there is no abandoned state, so escheat keys purely on full decay. **Still open:** the solvency-tuning question — does bid-curve self-correction suffice to keep the renewal cycle moving, or do absentee estates additionally need reduced efficiency? And the shape of player-to-player estate sale, which is a listing surface this document does not own (the unique-item listing machinery of exploration-and-keys §6 is the obvious reuse — an estate is an instanced, non-fungible, realm-scoped object, which is exactly what that surface was built for).
10. **Population dynamics.** Is there a minimum viable population for a realm's *active* layer (projects, morphing) even when its passive layer (estate production) persists, and does the game need soft incentives to spread players across the map?
11. **Tutorial island scope.** Which skills does it expose, and does the rowboat literally become the player's first mobile estate on the mainland, or is it consumed by the crossing?
12. **Realm identity depth.** Do realms differ *mechanically* (unique actions, unique upgrades) or only *numerically* (tags + modifiers)? Development nodes changing tag sets is now the established mechanism; content design decides how far to push uniqueness.
13. **Frontier realm markets.** **Settled:** every realm operates a realm market at every development stage — the market-access tag gates only the *global book* (market-vision §2.6). What distinguishes a frontier market is not existence but *thinness*: with few residents there is little upkeep demand, a near-empty treasury, and near-empty stores, so its bids are weak-but-real and its asks nearly nonexistent. The hauler's frontier loop therefore has a counterparty from day one, and it strengthens organically as settlement grows the realm's appetite and tax base — no special-case mechanics. ~~Residual~~ **Discharged (0.7):** the inter-realm economy pass enumerates every near-zero case and makes the structural guarantee that **no formula divides by the upkeep draw** — the bid curve's domain is `store/cap`, a realm needing nothing has a deficit ratio of zero by definition, and a realm with no funds simply has no bid rather than a degenerate one.
14. **Carried vs. stored inventory.** *(New in 0.5, open — and still open in 0.7.)* The hauler loop assumes goods are physically carried between realms, but the engine has a single location-less inventory. Nothing needs building yet; nothing may be built that *prevents* a carried/stored split later (market-vision §8 watch item). **Note the one thing that looks like an exception and is not:** the estate **larder** (§3.4) accepts upkeep goods but has **no withdrawal path**, so goods entering it have been *spent*, not *stored* — the estate cannot be used as a warehouse and no carried/stored split is created. Interlocks with estate storage and visiting.
15. **Visibility scope.** **Settled: full visibility.** Players can view (not trade) the global book and every realm's store levels, bids, and health from anywhere — trading remains gated (access tag for the book, physical presence for realm markets), but *information* is free. Rationale: the signal layer is the recruiting mechanism for haulers and tycoons and should be maximally readable; a single world-visible state is also simpler to simulate, serve, and present than per-player fog. Fog-of-war/scouting is off the table for v1 and would be an additive feature if ever wanted. (Settles market-vision §7.7 in its leaned direction — patch that doc's next revision.) Treasury *balances* remain non-exposed per the Phase 4 rule; realm health and bid behavior are the public signals.

*(New in 0.8, from the realm-upgrades pass.)*

16. **Project-slot contention.** One active project per realm (§2.10) is the pass's best pacing decision and its most obvious griefing surface: whoever pays the kickoff cost first occupies the realm's only slot, and a hostile or merely foolish choice blocks everyone until it languishes out. Candidate mitigations, not mutually exclusive: make the kickoff cost real enough to hurt; let a project be **cancelled** by the same body that could vote an upgrade, or by unanimity of contributors; require a vote to *start* projects above some tier (which folds project selection into the governance system that already exists rather than inventing a second one); or shorten the languish window specifically for projects with zero contributions after kickoff. The last is the cheapest and probably the first thing to build. *(0.11 adds a fifth, already paid for: **attribution.** The realm history logs who kicked off a project, and a failed project stays logged with its initiator (§2.15). That is accountability rather than prevention, so it retires none of the four above — but in a small persistent electorate it does real work, and it costs nothing beyond a record that now exists anyway. Its strength depends on reputation being durable, which depends on the unowned player-vs-character question: `characters.player_id` is UNIQUE today, so a name means a person; if multiple characters per player ever ship, both the history and the initiator log dilute.)* Interlocks with §6.18 (what happens to the goods) and §6.20 (who votes).
17. **Vote parameters.** **Electorate settled (0.9):** weight from the estate, ballot from the player, one ballot per player at their heaviest local estate, snapshotted at initiation, NPC estates excluded, no frontier special case (§2.12). **Quorum settled (0.10):** the default position is **abstention**, and only cast weight counts — no threshold is ever measured against total franchise, which is what stops absentee legacy estates freezing a realm. **Still open, and the residual list is now short but sharp:**
    - **Vote duration**, which abstention-by-default promotes from a detail to the system's main safeguard (§2.12). Long enough that a daily-login player reliably sees a vote before it closes; probably scaled by upgrade tier. This is the number to get right. *(0.11: with in-game chat declined (§2.15), duration is no longer the *main* safeguard but one of exactly two — the other being **findability**, since a vote nobody can be told about must be one they can stumble onto. The realm details page is the minimum; a map-level open-vote indicator is the cheap upgrade, and neither emits player-authored text.)*
    - **A cooldown after a failed vote** before the same upgrade may be re-called. Without one, the initiation fee alone stands between the realm and someone re-rolling the same vote until a quiet hour lands it — which is exactly the exploit abstention-by-default opens.
    - **Threshold shape:** simple majority of cast weight throughout, or supermajority for morphs and majority for tier-ups? The asymmetry matches how much is at stake — a tier-up deepens what everyone chose, a morph replaces it.
    - **Tie-breaking**, and whether a floor of absolute cast weight is wanted in populous realms (distinct from a quorum against franchise, which is ruled out).
18. **Disposition of a failed project's goods.** Three options. **Consumed** — thematically clean (they were given, and the world ate them), maximally punishing, and it makes contributing to a doomed project strictly worse than doing nothing, which will visibly chill early contribution. **Refunded pro-rata** — the contribution ledger exists and would support it, but it makes projects risk-free and undercuts §2.10's "over-ambition is a real communal risk." **Rolled into the realm's stores** — the lean: a failed project becomes a donation to upkeep rather than a burn, contributors are not punished for optimism, and the goods stay in the realm they were carried to. The watch-out on the lean is that it quietly creates a *gold-free* path to feed a realm's stores, which competes with selling into the realm market; whether that is a leak or a welcome civic alternative to the mercenary path (§4.4) needs deciding before it ships.
19. **Dismantling and rubble.** Is there a deliberate path to remove a realm upgrade — needed for high-tier horizontal morphs (§2.13) — and does it cost goods, refund a fraction, or merely take time? Does *shedding* (involuntary, §2.14) leave **rubble**: a derelict tag that must be cleared by a cheap project before that upgrade can be rebuilt? Rubble makes decline feel physical and gives returning players something to do, at the cost of an extra state to author for every upgrade. Both halves want the same underlying "remove an upgrade" mechanism, so decide them together.
20. ~~**Who counts as a resident?**~~ **Settled (0.10).** The question assumed residency was a character property needing a tenure cooldown to stop vote-buying; weighting prices commitment directly, so no cooldown is needed — a newly-arrived wagon votes immediately and counts for 1, which is the correct amount. Residency itself stays as it is (`home_estate`'s realm, design §7.6). Both 0.9 residuals are now closed: **(a)** a player holding several estates in one realm votes **once**, at their heaviest (§2.12) — stacking buys nothing; **(b)** a departed owner's estate no longer poses a quorum problem, because non-voting *is* abstention and never enters a denominator (§6.17). **One small residual:** should a **terminal shell** (fully shed, zero-upkeep, §2.14) still carry a fixed form's weight if its owner returns to vote? It is a building nobody has fed in months. The tidy answer is that weight reads the estate's *current* state, so a shell has decayed toward the mobile end politically as well as economically — but this only matters in the rare case of a returning absentee, and it can wait for the decay content pass.
21. **Project authorship density.** How many projects does a node offer at once — a handful of parallel choices, or one obvious next step plus optional side-builds? Does every node offer at least one morph path, or are some identities terminal by design? This is content-design work, but it determines whether the one-slot rule reads as *focus* or as *queue*, so it should be decided before the first content pass rather than discovered during it.

*(New in 0.11, from the civic-reward pass.)*

22. **Is a realm's estate roster public?** Ballot secrecy (§2.12, §2.15) holds only as long as vote weight cannot be reconstructed, and weight is a function of estate form and tier. §6.15's full-visibility ruling covers the global book and every realm's stores, bids and health; it is silent on estates. Publishing the roster makes the realm legible as a *community* — a tycoon prospecting a frontier, a newcomer sizing up neighbours — which is exactly the recruiting readability the signal layer is for. Keeping it private protects the ballot. The likely resolution is asymmetric: publish **counts and aggregate weight** (how many estates, how much franchise, what the mobile/fixed mix is), withhold the **per-player mapping** — which serves the prospecting use case, since what a tycoon needs is whether a realm has people, not which people. Decide before the vote endpoints ship, because the cheap implementation leaks by default.

23. **Tax attribution and the visitor free ride.** §2.11 sells communal facilities on the promise that traffic is tax base, and §2.15's "access is the reward" leans on the same promise. Neither survives market-vision §2.5 as written: tax credits the realm where the **sell order was placed**, so a visitor who uses a realm's lumber yard and lists from home pays the builder nothing, and a flat global rate leaves them indifferent to where they list. Candidate fixes, in ascending cost: leave it and delete the traffic-is-tax-base rationale (honest, but concedes the free ride); credit tax to the realm the seller is **standing in at match time** rather than at order creation (small change, but resting orders now have a moving attribution and the seller can move it deliberately); or give facility use itself a local hook — a per-cycle fee into stores or treasury for acting under a tag you do not hold residency under, which is the only option that charges the actual free ride but introduces the visitor malus §2.8 spent a whole ratification removing. **Owned by market-vision**, since the mechanism is tax attribution; recorded here because this document is where the promise is made.

*(New in 0.12, from the estate pass.)*

24. **The no-mint floor, and whether it ever bends.** 0.12 rules that a realm with an empty treasury takes a surrendered estate for **nothing** rather than minting a single ceremonial coin. The ruling is not in doubt; what is worth recording is the general form it established, because this is the second decision in two passes to come out cleaner by refusing to bend the invariant: **when the world cannot afford a transaction, the transaction degrades to zero rather than borrowing against nothing** — the same shape as no realm debt (inter-realm §9.2) and as a broke realm publishing a need instead of a bid (§4.3). Any future mechanic that wants to pay a player from a treasury inherits this pattern. Recorded as a principle, not an open question; listed here so it is findable.

25. **Should the realm's willingness to buy depend on what it already holds?** §3.6 flags the failure mode where the world fills with immortal ownerless estates and renewal stalls; a guaranteed exit at a known price makes over-building *safer*, which pushes toward it. The goods analogue would be a quantity walk — the realm pays less for the fortieth identical farmstead, exactly as the bid curve integrates over quantity (inter-realm §5.2). That is more machinery than this needs on day one, and there is a cheaper version: the realm simply **declines** to buy when it already holds more than some count of that form, which is a refusal rather than a price. The refusal must not gate the *surrender* — the player still gives the estate up (§3.6's unconditional-path rule), the realm simply pays nothing for it. Content/balance once the shape is chosen.

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

**New in 0.8 — the realm-upgrades pass (this document's scope, mostly Phase 5.5-adjacent):**

- **The structural delta: realm identity is no longer a single node pointer.** `realm_state.current_node_id` gains an **ordered stack of held realm upgrades**, each contributing tags, modifiers, and a slice of the upkeep draw vector. Everything else in this list follows from that one change. Ordering must be *acquisition* order and must be durable, because it is what §2.14's shed sequence reads.
- **Tags from realm upgrades route through §13.1 tag emission**, not a parallel path — same resolution pass as development nodes, estate forms, and estate upgrades. This is also where §13.8's watch item (*build nothing that assumes permanent unlocks*, from exploration keys) earns its keep: realm-upgrade tags are permanent-until-shed, which is a third lifetime alongside permanent and expiring. The emission pass should carry a source and a lifetime per tag from the start.
- **Upkeep draw becomes composite.** Phase 5.5 plans a per-node draw vector; it now needs to be *node vector + one vector per held upgrade*, summed. No new mechanism, but the shape must land in 5.5 rather than be retrofitted.
- **`projects` content pack extensions:** contributor scope (residents / residents+visitors), kickoff cost, total cost, build time, granted tags, maintenance vector, and signed development-edge weights (§2.13 requires subtraction, not only addition).
- **`realm_projects` gains a real status machine** — offered → active → funded → building → complete, plus languishing → failed — with the stall gauge modelled on the decay accumulator rather than a deadline (§2.10), and resolved lazily through the same `resolve_realm` tick.
- **Realm governance is new surface entirely:** a votes table with an initiation-time **resident snapshot**, ballots, thresholds, and expiry; the initiation fee crediting the treasury; and the tag-prerequisite check that makes an upgrade offerable. Nothing in the current schema anticipates this. *(0.9–0.10 additions:)* the snapshot captures **weight as well as membership**, so the ballot table stores a resolved weight rather than recomputing at close; **`vote_weight` becomes a property on estate forms in content** (mobile forms 1, fixed forms 10) with the per-tier increment as engine arithmetic over the estate's own progression level; **the franchise is keyed at `player_id`, not `character_id`** — one ballot per player at their heaviest local estate, which is why the resolution query groups by player and takes a max rather than summing rows (today `characters.player_id` is UNIQUE so the two are equivalent, but keying at the player level costs nothing now and is the only version that survives multiple characters per player); **abstention is the absence of a ballot row**, never a stored value, so tallies read cast weight by construction and no code path can accidentally denominate against total franchise; and NPC-owned estates need a **franchise flag** — the first mechanic that has to distinguish system-owned estates from player-owned ones, so verify the ownership schema's system-owner path (Phase 5 item) exposes something testable.
- **Stores may release goods into an active project** above the reserve line at a bounded rate — the goods twin of the settled treasury-funds-projects rule, and the same shape.
- **Project demand overlays the bid computation** (§4.4) so an active build raises the realm's bids for what it needs. Already listed in Phase 5.5 scope as "the project demand overlay"; 0.8 specifies what feeds it.
- **Two supersessions for `design.md`'s log:** **#23** ("contributions are not residence-restricted") was already superseded by 0.6's presence rule; 0.8 adds the second, independent axis — a **per-project residency flag** — so the final rule is *presence always, residency per project*. And **§7.3**'s "realm identity is a function of the realm's current node" is superseded by the ordered-upgrade-stack delta above.

**New in 0.11 — the civic-reward pass (mostly read-side, and cheaper than it looks):**

- **A realm event log.** One append-only `realm_events` table is the whole of §2.15's history: `(realm_id, occurred_at, event_type, actor_player_id, payload)`, with types for project kicked off / completed / failed, upgrade vote initiated / closed, upgrade taken, tier shed, node changed. Every writer already exists as a transaction boundary in the pass above — the log is a row appended inside work the engine is doing anyway, not a new subsystem. It is **append-only and never rewritten by decay**, which is what makes the record survive shedding.
- **Contribution rosters are a projection, not new state.** `realm_contributions` already exists (Phase 4). The history's per-project roster is a read over it, valued at reference prices at render time; nothing is denormalized and no aggregate-per-player view is built (deliberately — §2.15).
- **A realm details endpoint.** Node, held upgrade stack, tags, health band, store levels and bids, active project with per-good remaining requirement and stall/build state, open vote with its close time, and the history. Location-free and readable by anyone, per §6.15. Largely an assembly of reads the pass already requires; the **open-vote close time must be in it** — under §2.15 this is the surface that makes vote duration protective rather than decorative.
- **The ballot choice column has no reader.** Enforce it at the API boundary rather than by convention: vote endpoints expose participation (the set of ballot rows) and, after close, the outcome — never the tally, never a per-ballot choice. Worth a test that asserts the absence, since this is a rule that erodes quietly when someone builds an admin view.
- **A map-level open-vote / project-needs indicator** is the one additive coordination surface §2.15 permits, and it emits no player-authored text. Client work, but it should be scoped alongside the details page rather than after it, since with chat declined it is half of the abstention safeguard.
- **Explicit non-goal for `design.md`:** no in-game chat, no guild layer, no player-authored text surfaces of any kind. Recorded so it is a decision with reasons rather than a hole a later phase quietly fills.

**New in 0.12 — the estate pass:**

- **Estate surrender endpoint**, and it is the same path as escheat: transfer ownership to the realm (`owner → system`), flip the franchise flag off (§2.12), compute `payout = min(V × (1 − L[form]), discretionary_treasury)`, debit the treasury, grant the floor mobile form if the character now has no estate. Escheat calls it with the payout step skipped. **One mechanism, two entry points** — build it that way rather than converging two later.
- **`V` is computed, never stored.** Deriving it from `form.gold_cost + Σ held_upgrade.gold_cost` plus goods costs at reference prices is what keeps the surrender price and the build cost from drifting apart (§3.6). Held upgrades only, so decay prices itself. Content already declares both cost vectors; nothing new is authored except the two constants.
- **Two new content constants:** `liquidity_discount` as a property of each **estate form**, and a global `estate_spread`. Neither may reuse the goods spread `m` (inter-realm §12) — different job, different scope, and a shared name will eventually be a shared value by accident.
- **The treasury gains a reserve line.** Stores have one (`R × draw`); the treasury does not, and estate purchase is the first thing that must sit below it — upkeep procurement outranks real estate. This is a small addition to the Phase 5.5 tick, but it must land *with* the surrender endpoint or a realm can buy a manor and starve.
- **`relocation_cost` is retired for fixed forms** (§3.7), along with their delayed-relocation columns. Deletion, not addition — but it supersedes visiting-vision §8.7's third branch and the Phase 4 path, so `design.md`'s log needs the entry.
- **Transformation-path validator:** boot-time content check that no transformation moves an estate *down* the rootedness axis (fixed → mobile). Requires a form ordering or a boolean `is_fixed` in content; the check is trivial and the failure it prevents is not (§3.7).
- **Estate-less is not a legal state.** Assert it: any path that removes a character's last estate grants the floor mobile form in the same transaction.
- **The larder rides with the estate** on surrender and escheat (§3.7). No withdrawal path is created; the confirmation surface must state what is being given up.
- **Public buyback figure.** The realm details endpoint (§7, 0.11) gains what the realm would currently pay for a given form — a health signal, and free, since it reads treasury state the formula already needs. Treasury *balances* stay unexposed per the Phase 4 rule; this is a derived offer, not a balance.
- **Watch item — player-to-player estate sale.** Not built here, but the realm-as-floor design assumes it eventually exists. The unique-item listing surface (exploration-and-keys §6) is the natural reuse: instanced, non-fungible, realm-scoped, escrow-on-list. Build nothing that assumes estates are only ever transferred between a player and the system.

**Remaining in this document's scope:**
- **Estate solvency accounting.** Per-estate production and upkeep settled against reference prices, with solvency status feeding the decay state machine. The estate schema's dormant `upkeep_profile`/`production_profile` columns reserve the room. *(Lands with the upkeep/decay phase, ~5.5.)*
- **Upkeep, decay, and balancing processing.** Realm store decay, repricing, and inter-realm balancing run in the scheduled-job slot (design.md §8.3); estate upkeep and passive production resolve lazily on character resolve, reconciled realm-side at tick time. *(Phase 5.5; the "no timers" pillar's biggest test.)*
- **Item tiers** as a content property feeding upkeep composition rules. *(Content-design time; owned by Skills and Goods §7.)*
- **Visiting.** Per-character location ≠ home realm, availability keyed to location, travel costs — now a hard prerequisite for the hauler archetype (§6.3) and interlocked with Exploration (design.md §10). *(Post-5.5 or alongside it; the presence-check interim rule buys time.)*
- **Tutorial island flow**: a starting realm with restricted availability, upkeep- and market-exempt, with a scripted one-way graduation step.

None of these threaten the core architecture; all fit the "new sources are content, new types are engine changes" rule. Sequencing pressure now concentrates on Phase 5 (market-vision's list) and Phase 5.5 (upkeep/decay/solvency, which this document owns).
