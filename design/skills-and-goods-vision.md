# Yet Another Idle Skilling Game — Skills and Goods Vision Document

**Version:** 0.2 (draft; expanded from the 0.1 outline)
**Scope:** The production side of the world economy — skill categories, the goods tier ladder, proficiency, facilities, and how combat and exploration participate as economic actors. This is a sibling of the **Market Vision** document (`realm-vision.md`), which owns the demand side (upkeep, markets, treasury); this document owns supply. The planned **Combat** and **XP Curve** vision documents will deepen two topics this one only frames economically.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't yet support, that is a design-doc work item (§7), not a license to improvise. The future content design document turns this vision into concrete skills, recipes, items, and numbers.

**Changes from 0.1:** Convergent refining (§3.3) settled; facilities-via-tags settled with an engine work item for tag emission from upgrades (§5, §7); proficiency settled as threshold-based and optional per skill (§2.3); tier thresholds settled as back-loaded on the XP curve (§3.2); combat's economic role defined (§4.2); exploration's per-realm, time-limited "key" concept **tabled** to its own future vision document (§4.1, see `exploration-and-keys-vision-TODO.md`); added the economic-role test (§6) and engine work items (§7).

---

## 1. The elevator pitch

Skills turn **time into goods**, and goods climb a **ladder of tiers** that the whole economy — upkeep, markets, realm development — reads from. Every skill category has a defined economic role: what it eats and what it feeds. Nothing produces into a void, and nothing consumes from nowhere. A skill that doesn't participate in the economy's loops is a design mistake by definition.

The production chain is the spine: **gathering → refining → manufacturing**, with combat as a risk-flavored producer-consumer alongside it and exploration as the future supplier of *access itself*.

---

## 2. Skills

### 2.1 Categories

Skills belong to categories with defined positions in the production chain:

- **Gathering** — turns time into basic goods. Mining yields ore; lumberjacking yields logs; farming yields grain. Inputs: none (or trivial tools). Gathering is where realm flavor lives (§3.3).
- **Refining** — turns gathered goods plus time into intermediate goods. Smelting turns ore into ingots; milling turns logs into planks. Refining is the **convergence point** where regional variants become commodities (§3.3).
- **Manufacturing** — turns refined goods into finished goods. Weaponcrafting takes ingots and planks and makes an axe. Finished goods are what upkeep quotas, combat supply, and estate construction ultimately demand.
- **Combat** — a producer-consumer hybrid: monsters carry drop tables (producing leather, bones, monster parts the industries want) while combat *consumes* manufactured and farmed goods as fuel (§4.2).
- **Exploration** — the future category that produces **access**: discovering new resource nodes. Deferred to its own vision document (§4.1).

The illustrative chain: mining (gather) → smelting (refine) → weaponcrafting (manufacture) → an axe that a realm's upkeep quota consumes or a combatant carries.

### 2.2 Category rules

1. **Every skill has an economic role.** Each skill's outputs must be inputs to something — a later production step, an upkeep quota, combat supply, or a market with real demand. The test in §6 applies to every proposed skill.
2. **Chains cross realms by design.** Per the Market Vision's specialization rule, a realm rarely hosts a full chain top to bottom. The gathering happens where the resource is; the refining and manufacturing happen where the facilities are. The player market is the connective tissue.
3. **Categories are content groupings, not engine types.** The engine sees actions with inputs, outputs, cycle times, and availability gates. Categories exist so content design and the UI stay coherent — and so the economic-role test can be applied per category.

### 2.3 Proficiency: mastery of the fundamentals

A player with high skill can work **faster** on things far below their level: a level-80 blacksmith makes level-10 items faster than a level-10 or level-25 smith does.

- **Threshold-based.** The bonus applies in steps, not a continuous per-level curve. The natural thresholds are the **tier boundaries** themselves (§3.2): working on a recipe one tier below your unlocked tier grants one step of bonus, two tiers below grants a larger one, and so on. One table serves both tier unlocks and proficiency.
- **Optional per skill, for content designers.** The proficiency table is an optional content block on a skill definition. Skills that define it get the behavior; skills that omit it don't. This is a content-designer knob, not a player-facing toggle — some skills may deliberately lack it where speed-scaling low-tier work would distort their economics.
- **Speed first; yield is a separate question.** v0.2 commits proficiency to cycle-time reduction (expressible through the existing `cycle_time_pct` modifier machinery as a level-derived source). Whether higher proficiency should also grant *more output per cycle* is deliberately left open (§8), because guaranteed extra yield needs a new modifier type (§7) and has larger economic consequences than speed.

**Why proficiency matters economically:** the Market Vision promises that low-tier demand is perpetual, so early-game production never becomes worthless. Proficiency is the supply-side half of that promise — it gives *veterans* a standing reason to produce tier-1 goods, because they are the world's most efficient producers of them. A max-level smith cranking out cheap tools for a realm's upkeep is playing correctly, not slumming.

---

## 3. Tiers and goods

### 3.1 Tier is a property of goods, read by everything

Goods carry a **tier** as a formal content property (settling the Market Vision's open question §6.8 in the direction it leaned). Tier is the shared vocabulary between systems:

- **Skills** unlock the production of higher tiers at higher levels (§3.2).
- **Upkeep quotas** climb the ladder additively as realms develop — a developed realm demands tier-3 goods *and still consumes tier-1 in volume* (Market Vision §4.7).
- **Markets and balancing** can reason about goods by tier (price floors, deficit composition).
- **Proficiency** measures how far below your unlocked tier a recipe sits (§2.3).

### 3.2 Tier unlocks are back-loaded on the XP curve

Tier unlocks map to skill levels, but **not** evenly spaced. Illustrative shape for a five-tier ladder: tiers unlock at levels **1 / 40 / 75 / 90 / 95**.

With an exponential XP curve, the time gaps are far more dramatic than the level numbers read — the climb from 90 to 95 costs more XP than levels 1 through 75 combined. That is the intent:

- **Tier-4/5 producers are genuinely rare.** Top-rung goods stay scarce, which is where the Market Vision wants scarcity and skill to matter. Veteran production is always distinguished.
- **Most of a player's leveling life happens inside tiers 1–2.** This is a feature for the economy (the bulk of the world's supply is low-tier, matching the bulk of its demand) but a hazard for content: **tiers 1 and 2 need front-loaded recipe variety** so the long occupancy doesn't feel like a desert. Content density should be inversely related to tier, even though prestige runs the other way.
- **New players are economically relevant on day one** and remain so forever, per the perpetual-low-tier-demand rule.

Higher skill levels grant two distinct things, and the doc keeps them separate on purpose: **unlocks** (access to higher-tier recipes, stepped at tier boundaries) and **proficiency** (better performance on lower-tier recipes, §2.3). Both derive from the same level, but one gates content and the other tunes throughput.

### 3.3 Regional flavor converges at the refinery

Different realms offer different gathered goods **at the same tier**: the coastal realm has tier-1 palm trees, the inland mountain realm tier-1 pines. Realms may also carry only a subset of gatherable goods at all — that's the specialization rule doing its work.

The settled rule for what happens next: **refining converges variants into shared commodities.** All tier-1 logs — palm or pine — mill into the same planks. Concretely:

- Variant gathered goods share an **input class**, expressed as an item tag (e.g., every regional log variant carries `class.log.t1`), and refining recipes reference the class, not an enumerated variant list. This is a content convention, not an engine change — but the content design document must name and enforce the convention so recipes stay variant-agnostic.
- **Gathering is flavorful and local; refined goods are commodities.** You haul planks across the map, not species of tree. This keeps the goods catalog tractable (variants don't multiply through the whole chain), matches the transport story (commodities are what inter-realm balancing and haulers move), and keeps the trade gradient at the *gathering* layer where realm identity lives.
- **Deferred flair:** a later feature set can add variant-specific refined goods (palm-wood furniture as a luxury line) as *additions* to the converged commodity, never replacements. Convergence-first makes that a pure content expansion.

### 3.4 Facilities: where refining and manufacturing can happen

Gathering happens where the resource is. **Refining and manufacturing require facilities** — a smelter, a mill, a workshop — available either in the realm (communal infrastructure from its development stage) or at the player's estate (a forge-hall estate *is* a facility).

Facilities are expressed through the **existing tag/availability system**, not a new mechanic: a facility is a tag (e.g., `facility.smelter`) emitted by a realm's current development node or by an estate form/upgrade, and refining/manufacturing actions require the tag. This buys, for free:

- **Facility loss is automatic.** A realm regressing along the development graph, or an estate upgrade going dormant from decay, stops emitting the tag — and the dependent actions become unavailable with no special-case code. Infrastructure decay translating directly into lost production capability is exactly the living-world behavior the Market Vision wants.
- **The estate-form identity deepens.** Choosing a forge-hall over a wagon is choosing which parts of the production chain you carry with you versus depend on your realm for — the mobility ↔ depth axis expressed in production terms.
- **Visiting hooks cleanly.** Whether a visitor may use a realm's communal smelter becomes an availability question the visiting design (Market Vision §2.8) can answer in one place.

**Engine caveat (work item, §7):** the current engine resolves *modifiers and caps* from development nodes, estate forms, and upgrades — but realm upgrades cannot yet grant **tags**. Extending tag emission to all availability sources is new engine work and must land before facility-gated content ships.

---

## 4. The other two categories

### 4.1 Exploration — tabled, with a bookmark

Exploration's economic role is settled at the vision level: it produces **access** — discovering resource nodes that open gathering opportunities. The 0.1→0.2 discussions surfaced a design direction worth its own conversation rather than a paragraph here: discoveries as **per-realm, time-limited nodes**, possibly mediated by a **"key"** artifact the discoverer holds — which raises rich questions (realm-wide vs. key-holder access, tradeable keys as the adventurer's sellable product, expiry by time vs. exhaustion) with their own engine implications (expiring realm-scoped availability is a new concept).

All of that is **deferred to a dedicated vision document**. See `exploration-and-keys-vision-TODO.md` for the captured state of the idea. Until then: the sidebar slot stays reserved (design doc §10), and nothing in this document's chain depends on exploration existing.

One property worth recording now because it shapes the eventual design: time-limited discoveries make exploration the **renewable-demand loop for access**, the same way upkeep is the renewable-demand loop for goods — expired nodes mean exploration never saturates.

### 4.2 Combat — the producer-consumer

Combat produces goods and consumes them, and both halves are load-bearing:

- **Every combatant carries a drop table.** Monster drops are gathering-equivalent inputs the industries want — leather, bones, monster parts — making combat economically a gathering skill with risk attached. The action framework already supports this natively (an encounter is an action whose drop table is the monster's loot).
- **Combat runs on consumables.** How long a player can sustain combat skilling is a function of **player stats and consumables (health potions, food) versus the combatant's stats**. Supplies are consumed as the fight cycles; when they run out, the action ends — expressible through the existing input-consumption machinery (consumables as cycle inputs, exhaustion as the stop reason).
- **The economic consequence:** combat is a standing **demand sink** for the agrarian and alchemy industries that scales with how much combat the world's players do. The adventurer buys bread and potions from the settled realms and sells them monster parts back — the archetype feeds the economy in both directions, passing the §6 test twice.

Depth beyond the economic frame — combat stats, encounter design, death rules, equipment — belongs to the planned **Combat vision document**. This document constrains it only thus: whatever combat becomes, it must remain a goods producer with per-combatant drop tables and a goods consumer through supply-based sustain.

---

## 5. How the pieces reinforce each other

- **The chain (gather → refine → manufacture)** creates multi-step dependency → every finished good embodies work from multiple skills, usually multiple realms → the player market stays the connective tissue.
- **Convergent refining** keeps flavor at the gathering layer and commodities at the trade layer → catalogs stay tractable, haulers move standard goods, realm identity lives where the resources are.
- **Back-loaded tiers** make top-rung producers rare → high-tier scarcity is real → veteran distinction without invalidating anyone below.
- **Proficiency** makes veterans the most efficient low-tier producers → perpetual low-tier demand meets willing perpetual supply → the ladder's bottom rungs stay economically alive from both sides.
- **Facilities via tags** tie production capability to infrastructure → realm development and estate investment translate directly into what can be made where → decay costs capability, which upkeep exists to prevent — the loop closes.
- **Combat's consumable sustain** turns fighters into customers → agrarian and alchemy output has a demand sink beyond upkeep → the adventurer participates in the economy going *and* coming.
- **Exploration (future)** will make access itself a renewable good → the frontier loop gets its supply side.

The test for any future skill or good: **name what it eats and name what it feeds.** If either answer is "nothing," it doesn't belong.

---

## 6. The economic-role test

Applied per category (and to be applied to every future skill proposal):

| Category | Eats | Feeds |
|---|---|---|
| Gathering | time (and trivial tools) | refining |
| Refining | gathered goods, facilities | manufacturing |
| Manufacturing | refined goods, facilities | upkeep quotas, combat supply, estate construction, markets |
| Combat | manufactured + farmed consumables | rare/monster inputs back to the industries |
| Exploration (future) | time, travel, supplies | access — new gathering sources |

---

## 7. What this changes in the design doc (work items, not yet decisions)

Roughly in order of when they bite:

- **Tag emission from upgrades and development-node sources.** The engine resolves modifiers and caps from all sources, but availability tags currently do not flow from realm upgrades. Facilities (§3.4) require tags to be emittable by the same closed set of sources that emit modifiers — same resolution pass, same inert/dormant rules. *(Bites before any facility-gated content ships; small, well-defined engine change.)*
- **Item tier as a content property**, with schema validation and the input-class tag convention (§3.3) documented in the content pipeline. *(Bites at content-design time; near-zero engine work.)*
- **Level-derived proficiency as a modifier source.** Threshold table (optional per skill) feeding `cycle_time_pct` from the character's level relative to the recipe's tier. *(New modifier source, existing modifier type — fits the "new sources are content" rule if the engine grows one generic level-vs-tier source hook.)*
- **Per-cycle yield modifier type** — *only if* §8's yield question resolves toward guaranteed extra output. New modifier type = engine change by rule; hence flagged, not assumed.
- **Consumables as combat cycle inputs.** Already expressible; the Combat vision must confirm the shape (inputs per cycle vs. per damage taken) before Phase 6 content.
- **Expiring realm-scoped availability** — exploration's key concept. *Deferred with the feature*; recorded so nobody builds an unlocks table that assumes permanence.

---

## 8. Open questions (to resolve in later visions, design, or content docs)

1. **Proficiency yield.** Does over-tier proficiency grant extra output per cycle in addition to speed, or is speed the whole bonus? (Guaranteed yield needs a new engine modifier type and has stronger economic effects — it deflates low-tier prices faster.)
2. **Proficiency step sizes.** How large is each tier-gap bonus step, and is there a cap? (Content/balance question once the shape is settled.)
3. **Tier count and exact thresholds.** Five tiers at 1/40/75/90/95 is the illustrative shape; the XP Curve vision and content design own the final numbers.
4. **Tier-1/2 content density.** How many recipes per tier per skill keep the long low-tier occupancy interesting? (Content design; the principle — density inverse to tier — is set here.)
5. **Facility granularity.** One tag per facility type (`facility.smelter`) or per facility *tier* (`facility.smelter.t2` for high-tier recipes)? Interacts with realm development stages providing progressively better communal infrastructure.
6. **Visitor facility access.** May a visitor use a realm's communal facilities, at what penalty? (Owned by the visiting design, Market Vision §2.8/§6.3 — flagged here because facilities make it concrete.)
7. **Exploration and keys.** The whole cluster — see `exploration-and-keys-vision-TODO.md`.
8. **Combat depth.** Stats, encounters, death, equipment — owned by the Combat vision, constrained by §4.2's economic frame.
9. **Where tools sit.** Gathering "eats trivial tools" in §6 — are tools durable equipment, consumed inputs, or ignored in v1? (Durable equipment would be a new concept; consumed inputs work today and create another upkeep-like sink.)
