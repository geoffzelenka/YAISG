# Yet Another Idle Skilling Game — Visiting & Travel Vision Document

**Version:** 0.2 (ratification patch)

**Changes from 0.1:** Three ratifications from design-chat review. (1) **Relocation unification ratified** (was §8.7's proposal, question #2): mobile-estate relocation runs as a Travel journey — time from edges + Travel level, supplies from the form's travel profile — and the gold-cost instant/delayed variants are retired for mobile forms; the Phase 4 gold × `relocation_cost` path remains for fixed-form moves. A client work item is added (§8.9): a mobile-estate character who starts a *visit* journey is warned that relocating may be what they want, since for them visiting means leaving their estate — bonuses and all — behind by choice rather than by form. (2) **No obligation to return home** (question #5): staying away from a fixed estate indefinitely is explicitly legal — the standing cost is the absence of the estate's bonuses while upkeep and solvency continue at home; no timer, no penalty escalation. (3) **Project contributions are presence-gated** (ratified alongside this document's review, superseding the Phase 4 permissive rule / design log #23): contributing to a realm project requires being physically in the realm — §5.1 updated. Question #6 (remote estate interaction) remains open pending multiple estates.
**Scope:** Travel between realms and the distinction between a character's *current* realm and their *home* realm — the Travel skill, how journeys are priced and resolved, what a visitor can and cannot do, how estate bonuses and caps behave away from home, and the mobile/fixed estate split that routes mobile-estate movement through relocation and fixed-estate movement through visiting. This is the document design.md §13.9 has been waiting on: it replaces the interim presence rule (`current realm = home realm`) with the real one.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't yet support, that is a design-doc work item (§8), not a license to improvise. Siblings: **Market Vision** (owns the presence-gated realm markets and the tax rule this document cites), **Realm & World Vision** (the map graph journeys run over; the estate forms and relocation this document builds on), **Skills and Goods** (the economic-role test Travel must pass), **Combat** and **Exploration & Keys** (the activities visiting exists to enable). The planned **XP Curve** vision owns Travel's leveling numbers.

**Changes from the rough draft:** Pitch reframed from "find a better realm" to **act where you don't live** (§1). Mobile-estate movement routed through the existing relocation machinery; visiting is the new surface for fixed-estate characters only (§2). **Travel becomes a skill** that levels (§3). Fixed-estate travellers also pay to travel (§4.2). Estate storage removed — one player inventory plus market escrow slots, full stop (§5.3). Caps ratified as player-attached regardless of location; only modifiers and tags are location-bound (§5.2). No visitor malus: the only penalty for acting away from home is the absence of your estate's bonuses (§5.1). Tax attribution cited from market-vision §2.5 rather than restated (§5.4).

---

## 1. The elevator pitch

**Act where you don't live.** The world is a map of realms, and a character may travel to one they don't call home — to sell into a starving realm's desperate bids, hunt its fauna, explore its frontier, or tend an estate they built there. Visiting is how the trader, the hunter, the speculator, and the developer do their work: every one of those archetypes acts in realms they don't reside in, and until now the engine could not tell the difference between where you are and where your house is.

Travel is itself a skill. Journeys cost time and supplies; active travellers get faster. The road is not free — but it is the only way to reach a realm market, which is the only counterparty that pays you to move goods toward hunger.

---

## 2. Two ways to move: relocate or visit

A character's movement mode is determined by the **form of their home estate**:

- **Mobile forms (tent, wagon, boat) relocate.** The estate moves with the character; the home realm changes. **Ratified (0.2):** mobile relocation runs **as a Travel journey** — time from the route's edges scaled by Travel level, supplies from the form's travel profile per edge — replacing the Phase 4 gold-and-timer path *for mobile forms*. The journey's arrival is the relocation's completion; `ESTATE_BUSY` and origin-identity-during-relocation semantics carry over unchanged, and the active-action-replacement rule (§8.8) means departure stops any other action by construction. A mobile-estate character never "visits": when they arrive, they live there. If one nonetheless starts a plain visit journey, the client warns them (§8.9) — for a mobile form, visiting means voluntarily leaving the estate behind, which is almost never what the wagon-dweller wants.
- **Fixed forms keep the Phase 4 relocation path.** Gold × `relocation_cost` over `path_cost`, instant and delayed variants — moving a farmstead is a purchase and a project, not a journey.
- **Fixed forms (farmstead, forge-hall, mill) visit.** The estate stays; the home realm does not change; the character's **current realm** diverges from their home realm for the duration. This is the new surface.

The split is the mobility ↔ rootedness axis (realm-vision §3.1) expressed in movement terms: the wagon-dweller brings their bonuses and production everywhere and pays for it in feed and planks; the forge-hall owner travels light and cheap but leaves everything that makes them strong behind. Both are genuine dilemmas, which is the point.

**Settled:** the two-mode split is load-bearing. Everything below assumes it.

---

## 3. Travel is a skill

### 3.1 The journey as an action

A journey is an **action under the existing cycle framework**: the player picks a destination realm, the route is the cheapest path over the map graph (reusing `path_cost`), and **each edge of the route is one cycle**. Completing a cycle moves the character to the next realm on the route. Consequences, all intended:

- **There is no "between realms" state.** A character is always *in* a realm; a long journey is a sequence of short stays at waypoints. The presence rule stays simple (`current_realm` is always a real realm), and a journey interrupted for any reason leaves the character at the last realm reached, not stranded in a void.
- **Offline travel just works.** Lazy resolution advances the character edge by edge; a player who logs off mid-journey arrives while away, the action ends with stop reason `arrived`, and the welcome-back summary reports where they are and what the road cost.
- **Supplies are per-cycle inputs** via the existing input-consumption machinery. Run out mid-route and the journey stops at the current waypoint (`inputs_exhausted`) — the honest-stop philosophy, with a realm market or global-book access plausibly available to restock.

### 3.2 Leveling

Travel earns xp per completed edge, scaled by the edge's base time cost — long roads teach more. Higher Travel level reduces journey cycle time through the existing `cycle_time_pct` machinery (Travel level as a modifier source on travel actions, the same generic level-derived hook proficiency needs, design.md §13.3). Active travellers get faster; the hauler who runs the same route for weeks runs it quicker than the settler who leaves home once a season.

What tiers grant beyond speed — access to edges marked impassable at low tier, reduced supply costs, a larger cargo cap — is left to content and the XP Curve vision (§9).

### 3.3 The economic-role test

| | Eats | Feeds |
|---|---|---|
| **Travel** | time (edge cycles), travel supplies per edge (food, and for mobile forms fodder/materials — agrarian and manufacturing demand), xp-gated route access | **presence** — the prerequisite for realm-market trade, foreign combat and exploration, tending remote estates; supply demand that scales with how much the world's players move |

Travel passes the test by being the skill that makes the hauler and adventurer *possible*; its own sink is the supply profile, which like combat's consumables scales with activity.

---

## 4. Travel costs

### 4.1 Edges own the base cost

Each map edge carries (already, from Phase 4) a base time cost, and gains a **supply-cost modifier** — a multiplier on the traveller's per-edge supply profile. A mountain pass is slow and hungry; a river road is neither.

### 4.2 The traveller owns the profile

The per-edge supply profile comes from the character's movement mode:

- **Fixed-estate visitors** travel on a **base travel profile** — light rations, content-defined, cheap. Visiting is never free (otherwise the rooted player gets mobility for nothing and the axis collapses), but it is deliberately inexpensive relative to hauling an estate.
- **Mobile-estate relocators** travel on the **form's travel profile** — a wagon needs extra food, fodder, planks — which is how "moving house" stays costlier than "going somewhere" even when the journey is the same.

Speed follows the same asymmetry: a form may carry a speed modifier (a laden wagon is slower than a walker), and the Travel skill's speed bonus applies to both.

---

## 5. Being away from home

### 5.1 What a visitor can do — no visitor malus

Availability while visiting is **the current realm's node tags** (plus the character's mobile estate's tags, if they have one — which by §2 means they aren't visiting). At full rate. A visitor may gather where the realm's resources are, use its communal facilities (they are tags — skills-and-goods §3.4), fight at its combat locations, explore its frontier, contribute to its projects (**presence-gated as of 0.2**: contributing requires standing in the realm — a visitor can, a remote benefactor cannot; this supersedes the Phase 4 permissive rule and is what routes frontier development through physical hauling), and — the point of the whole document — **trade at its realm market**.

There is **no separate visitor penalty.** The cost of acting away from home is exactly the absence of your own estate's bonuses (§5.2) plus the travel you paid to get there. A flat visitor malus was considered and rejected: it would mostly punish the hauler the economy is trying to recruit.

### 5.2 Bonuses are located; caps travel with you

The resolution rule, stated once so it covers home estates, mobile estates, and the tycoon's remote holdings alike:

> **An estate's modifiers and tags apply to a character only when the character is in that estate's realm.** An estate's **cap bonuses apply to the character regardless of location.**

Modifiers and tags are properties of a place — a forge-hall helps you smith *at* the forge-hall. Caps are properties of the player — your pack does not shrink, and your offline budget does not shorten, because your house is two realms behind you. Caps persisting also avoids the over-cap-mid-trip and stingier-offline-math hazards that location-bound caps would create exactly when a player is idling through a long absence.

Inert status (upgrade realm-tag mismatch) is unchanged and orthogonal: it is evaluated against the estate's realm, not the character's location.

### 5.3 Inventory: one pack, plus escrow

There is **one player inventory**, carried everywhere, plus the market escrow slots (order slots and unique-item listings). No estate storage, no located goods. The hauler's cargo is whatever is in their pack; market fills are collected from the slot wherever they stand (market-vision §2.3 already made collection the location-free delivery point). The carried/stored watch item (design.md §13.7) stays a watch item — nothing here builds it and nothing here forecloses it.

### 5.4 Markets while away

- **Realm market:** tradeable only at the realm you are physically in — the permanent invariant (market-vision §3.5). Visiting is what makes trading at a foreign realm possible at all.
- **Global book:** reachable iff the **current** realm carries the market-access tag. Visiting a frontier realm takes you off the book for the duration.
- **Tax attribution** is unchanged and cited, not restated: tax on a sell order is credited to the realm the seller was physically in when the order was created (market-vision §2.5). Under this document that is the seller's *current* realm at creation, which may be a realm they are visiting — hosting visitors' trade is a revenue strategy, as intended.

---

## 6. How the pieces reinforce each other

- **Presence-gated realm markets + travel** → the hauler exists: store/treasury differentials pay someone to move, and the Travel skill makes the frequent mover the fastest mover.
- **Located bonuses, travelling caps** → rootedness keeps its meaning (your power is at home) without visiting becoming a trap (your capacity comes along).
- **Mobile = relocate, fixed = visit** → the estate-form choice decides *how you move*, not just how much you pay to — the axis gains a second dimension for free.
- **No visitor malus** → realms are places anyone can act in; what distinguishes residents is investment, not permission — which is what makes the developer's remote estates and the speculator's foreign trades worth doing.
- **Supplies as per-cycle inputs** → movement is a demand sink scaling with activity, and running short stops you somewhere real rather than nowhere.
- **Global-book access by current realm** → the frontier is something you can *walk into*, and the off-book feeling the Market Vision promised becomes a thing visitors experience directly.

---

## 7. Deferred, with reasons

- **Estate storage / located goods.** Cut from this document entirely (§5.3). Revisit only with a dedicated estate-storage design; collection remains the seam.
- **Visiting as a mobile-estate option** (park the wagon, go light). Not in v1 — mobile means it moves with you. Revisit if a real need appears.
- **Tutorial-island travel.** The rowboat graduation is one-way and scripted (realm-vision §2.4, §6.11); it is not a Travel-skill journey and is exempt from this document's rules.

---

## 8. What this changes in the design doc (work items, not yet decisions)

1. **`current_realm` becomes real state** — a character's location column, initialized to home, advanced by travel cycles; the `current_realm()` helper (design.md §7.6) stops returning home. Every presence-gated check already routed through the helper switches over with no sweep; audit that nothing bypassed it.
2. **Travel skill + travel actions** — a skill in content; journey actions generated from a destination over the map graph (each edge a cycle; per-edge supply inputs; xp per edge; stop reasons `arrived` / `inputs_exhausted`). The per-cycle effect (advance location) is a third `CycleRewardStrategy` alongside skilling and combat.
3. **Edge supply-cost modifier** on map edges (content); **travel profiles** on estate forms and a base profile in caps/config (content).
4. **Location-aware source resolution** — estate modifiers and tags apply iff `estate.realm_id == current_realm`; cap bonuses always apply. Small change to the resolve pass; the arithmetic is untouched.
5. **Availability keyed to current realm** (not home) — development-node tags and combat/exploration locations resolve from where the character stands; market-access gate reads current realm.
6. **Travel level as a modifier source** — the generic level-derived hook shared with proficiency (design.md §13.3); whichever lands first builds it.
7. **Relocation unification — ratified (0.2):** route **mobile-estate relocation through the Travel journey** (time from edges + Travel level, supplies from the form's profile) and retire the gold-cost instant/delayed variants for mobile forms; keep the Phase 4 gold × `relocation_cost` path for fixed-form moves. The journey's `arrived` stop completes the relocation; `ESTATE_BUSY`, origin identity, and residence-cache sync semantics carry over from the Phase 4 machinery.
8. **Watch:** nothing here may assume a character's active action is independent of location — travel *is* the active action, and starting one replaces any other, so departure stops the current action by construction.
9. **Client warning for mobile-form visits (0.2):** when a mobile-estate character initiates a visit journey (not a relocation), warn that their estate stays behind — relocating may be what they intend. Client work; no engine rule prevents the visit.
10. **Presence-gated contributions (0.2):** realm-project contribution requires `current_realm(character) == realm_id`, enforced in the contribution endpoint alongside the existing clamping logic. Behaviorally identical to the shipped rule under the interim presence rule; becomes real presence when work item #1 lands.

---

## 9. Open questions

1. **Travel tiers.** Beyond speed: impassable-at-low-tier edges, supply discounts, cargo cap? Owned by content + XP Curve vision.
2. ~~**Relocation unification**~~ **Ratified (0.2):** mobile-estate relocation routes through the Travel journey; gold-cost variants retired for mobile forms; fixed forms keep the Phase 4 path. See §8.7, §8.9.
3. **Travel xp formula.** Per edge scaled by base time, or by supplies consumed, or both? Does repeating the same edge pay less? XP Curve vision.
4. **Base travel profile contents and edge modifiers.** Content/balance.
5. ~~**Visiting duration.**~~ **Confirmed (0.2):** no duration or cost to *stay*, and the player is **not bound to return** — staying away from a fixed estate indefinitely is legal. The standing cost is exactly the absence of the estate's bonuses while its upkeep and solvency continue at home (realm-vision §3.6); no timer, no escalation, no forced recall.
6. **Remote estate interaction.** Can a visitor purchase upgrades or transform an estate from elsewhere? Lean: yes for the tycoon's holdings in the realm they're standing in, no for estates elsewhere — confirm once multiple estates are scheduled.
7. **Client presentation.** Map shows current vs home; journey progress on the action strip; a "you are away from home" state in Estate/Profile — client design.
