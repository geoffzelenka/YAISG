# Yet Another Idle Skilling Game — Skills and Goods Vision Document

**Version:** 0.3 (aligned to the XP Curve vision v0.1)
**Scope:** The production side of the world economy — skill categories, the goods tier ladder, proficiency, facilities, and how combat and exploration participate as economic actors. This is a sibling of the **Market Vision** document (`market-vision.md`), which owns the demand side (upkeep, markets, treasury); this document owns supply. The **XP Curve** vision (`xp-curve-vision.md`) now owns the numbers this document only shaped — the curve, tier thresholds, proficiency tables, and the xp taper; the **Combat** vision owns combat depth within §4.2's economic frame.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't yet support, that is a design-doc work item (§7), not a license to improvise. The future content design document turns this vision into concrete skills, recipes, items, and numbers.

**Changes from 0.1:** Convergent refining (§3.3) settled; facilities-via-tags settled with an engine work item for tag emission from upgrades (§5, §7); proficiency settled as threshold-based and optional per skill (§2.3); tier thresholds settled as back-loaded on the XP curve (§3.2); combat's economic role defined (§4.2); exploration's per-realm, time-limited "key" concept **tabled** to its own future vision document (§4.1); added the economic-role test (§6) and engine work items (§7).

**Changes from 0.2 (alignment with `xp-curve-vision.md` v0.1):** Tier thresholds finalized at **1/50/75/90/95** (§3.2), superseding the illustrative 1/40/75/90/95. The "most of a player's leveling life happens inside tiers 1–2" claim amended per the XP vision's cross-doc patch — true of activities, unlocks, and level count, not time (§3.2). Proficiency settled as **cycle-time only, no yield** (XP §4.1 resolves open question #1); the asymmetric per-family speed tables and the 4-below cap live in XP §4.2 (resolving question #2's shape and cap). Proficiency's pairing with the **xp taper** (XP §5) and the estate-passive-production rationale (realm-vision §3.4) recorded in §2.3. Proficiency optionality **resolved here** (answering XP question #4): family tables are defaults; the per-skill block is an override/opt-out (§2.3). Content-density guidance updated for the top-tier time occupancy (§3.2, per XP §6). Conditional yield-modifier work item struck; proficiency work item folded into the generic level-vs-tier hook (§7). Tier achievement-gates (XP §9) recorded as a watch item where this document assumes tier = f(level) (§3.2, §8). Exploration references updated to the now-existing `exploration-and-keys-vision.md` (§4.1). Two further questions closed in this pass: **visitor facility access resolved by citation** — visitors use communal facilities at full rate, no malus (visiting-vision §5.1; §3.4, §8 #6) — and **tools resolved out of v1** — gathering eats time alone; the demand sink tools would have created is served instead by estates consuming generic, purpose-made manufactured upkeep goods (§2.1, §6, §8 #9).

---

## 1. The elevator pitch

Skills turn **time into goods**, and goods climb a **ladder of tiers** that the whole economy — upkeep, markets, realm development — reads from. Every skill category has a defined economic role: what it eats and what it feeds. Nothing produces into a void, and nothing consumes from nowhere. A skill that doesn't participate in the economy's loops is a design mistake by definition.

The production chain is the spine: **gathering → refining → manufacturing**, with combat as a risk-flavored producer-consumer alongside it and exploration as the future supplier of *access itself*.

---

## 2. Skills

### 2.1 Categories

Skills belong to categories with defined positions in the production chain:

- **Gathering** — turns time into basic goods. Mining yields ore; lumberjacking yields logs; farming yields grain. Inputs: **none — gathering eats time alone** (tools are resolved out of v1, §8 #9). Gathering is where realm flavor lives (§3.3).
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

- **Threshold-based, stepping at tier boundaries.** The bonus applies in steps at tier distances, not a continuous per-level curve. The step tables are now owned by the XP Curve vision (§4.2 there): **asymmetric per family** — gathering ramps smoothly from one tier below (+5/10/15/20%); refining and manufacturing start later and ramp harder (manufacturing reaching +30% at four below). Four-below is the implicit cap — with five tiers it is the maximum possible distance. One threshold scheme serves both tier unlocks and proficiency.
- **Family tables as defaults; per-skill block as override.** *(This resolves XP Curve open question #4, which was queued for this review.)* The family tables in XP §4.2 apply to every skill in the family by default. The per-skill proficiency block from v0.2 survives as an **override**: a skill may declare its own step values, or declare the block empty to opt out entirely where speed-scaling low-tier work would distort its economics. This keeps the v0.2 content-designer knob without forcing every skill definition to restate the family shape.
- **Speed is the whole bonus — settled, no yield.** The XP Curve vision (§4.1) resolves v0.2's open question #1: proficiency is **cycle-time only**, expressible entirely through the existing `cycle_time_pct` machinery as a level-derived source. No per-cycle yield bonus, no new modifier type; design.md 13.3's exclusion of yield stands as confirmed. More logs per hour comes from more cycles per hour, never more logs per cycle.
- **Paired with the xp taper.** Proficiency coexists with the XP vision's diminishing returns (XP §5): xp per cycle tapers on recipes far below a character's tier (per family — gathering never, manufacturing hardest), while proficiency speed persists even at zero xp. The two ride the same level-vs-tier hook and are tuned as a pair — inside the taper band, speed partially recovers the lost xp/hour; past the zero step, it converts cleanly into production throughput.

**Why proficiency matters economically:** the Market Vision promises that low-tier demand is perpetual, so early-game production never becomes worthless. Proficiency is the supply-side half of that promise — it gives *veterans* a standing reason to produce tier-1 goods, because they are the world's most efficient producers of them. A max-level smith cranking out cheap tools for a realm's upkeep is playing correctly, not slumming — the taper removes the progress-payment for that work, and proficiency is the compensation. The XP vision adds a second rationale worth restating here: the veteran's **estate already passively produces low-tier goods** (realm-vision §3.4), so active low-tier work must out-compete the player's own passive stream to be worth doing — proficiency is what makes the grandmaster personally felling logs better than watching their estate do it.

---

## 3. Tiers and goods

### 3.1 Tier is a property of goods, read by everything

Goods carry a **tier** as a formal content property (settling the Market Vision's open question §6.8 in the direction it leaned). Tier is the shared vocabulary between systems:

- **Skills** unlock the production of higher tiers at higher levels (§3.2).
- **Upkeep quotas** climb the ladder additively as realms develop — a developed realm demands tier-3 goods *and still consumes tier-1 in volume* (Market Vision §4.7).
- **Markets and balancing** can reason about goods by tier (price floors, deficit composition).
- **Proficiency** measures how far below your unlocked tier a recipe sits (§2.3).

### 3.2 Tier unlocks are back-loaded on the XP curve

Tier unlocks map to skill levels, but **not** evenly spaced. The thresholds are now settled by the XP Curve vision (§2.2 there): five tiers unlocking at levels **1 / 50 / 75 / 90 / 95**, on a curve whose XP cost doubles every seven levels and whose XP midpoint is **level 93**.

The time gaps are far more dramatic than the level numbers read — on the settled curve, the climb from 90 to 95 costs roughly **three times** levels 1 through 75 combined, and tiers 4–5 together hold ~63% of a skill's total XP. That is the intent:

- **Tier-4/5 producers are genuinely rare.** Top-rung goods stay scarce, which is where the Market Vision wants scarcity and skill to matter. Veteran production is always distinguished.
- **Most of a player's leveling life — measured in activities, unlocks, and level count — happens inside tiers 1–2.** *(Amended per XP §3.1's cross-doc patch: it is not true of time — tiers 1–2 are ~8% of a skill's XP, roughly 60 optimal hours.)* The economic claim this supported — the bulk of the world's supply is low-tier, matching the bulk of its demand — survives, but it is delivered by **proficiency** (veterans efficiently producing below their tier, §2.3), not by players lingering at low levels.
- **Content density is needed at both ends of the ladder, for different reasons.** Tiers 1–2 still need **front-loaded recipe variety**: they hold 74 of the 100 levels and nearly all of a skill's unlocks, so the leveling *cadence* lives there (a new activity roughly every 10 levels, XP §6). Tiers 4–5 span only ten levels but the **majority of a veteran's hours**, so they need horizontal breadth — more recipes at the tier — added as content allows, per XP §6's opened cadence. The v0.2 rule "density inverse to tier" is superseded by this two-ended shape.
- **New players are economically relevant on day one** and remain so forever, per the perpetual-low-tier-demand rule.

Higher skill levels grant three distinct things, and the doc keeps them separate on purpose: **unlocks** (access to higher-tier recipes, stepped at tier boundaries), **proficiency** (faster work on lower-tier recipes, §2.3), and — running the other way — the **xp taper** (progress-payment fades on recipes far below your edge, XP §5). All derive from the same level; one gates content, one tunes throughput, one directs the curve's payment toward your edge.

**Watch item — tier achievement-gates.** The XP vision records (its §9, unratified) a direction where refining and manufacturing tiers additionally require completing a content-defined recipe set, breaking the tier = f(level) assumption this section and its readers currently make. Nothing here may be built in a way that hard-codes tier-from-level outside the single derivation function; nothing is built for the gates until ratified.

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
- **Visiting hooks cleanly — and the answer is in.** The visiting design answered the question in one place, as hoped: availability while visiting is the current realm's node tags, so a visitor **may use a realm's communal facilities at full rate, with no visitor penalty** (visiting-vision §5.1). The cost of acting away from home is the absence of your own estate's bonuses, not a malus — which is exactly what makes the facility tag the whole answer.

**Engine caveat (work item, §7):** the current engine resolves *modifiers and caps* from development nodes, estate forms, and upgrades — but realm upgrades cannot yet grant **tags**. Extending tag emission to all availability sources is new engine work and must land before facility-gated content ships.

---

## 4. The other two categories

### 4.1 Exploration — tabled, with a bookmark

Exploration's economic role is settled at the vision level: it produces **access** — discovering resource nodes that open gathering opportunities. The 0.1→0.2 discussions surfaced a design direction worth its own conversation rather than a paragraph here: discoveries as **per-realm, time-limited nodes**, possibly mediated by a **"key"** artifact the discoverer holds — which raises rich questions (realm-wide vs. key-holder access, tradeable keys as the adventurer's sellable product, expiry by time vs. exhaustion) with their own engine implications (expiring realm-scoped availability is a new concept).

All of that now lives in its own vision document: **`exploration-and-keys-vision.md`**, which owns the key concept, discovery mechanics, and exploration's leveling pace (on a scaled-down baseline of the shared curve, XP §7). Nothing in this document's chain depends on exploration existing.

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
- **The xp taper and proficiency are a matched pair** (XP §5) → the curve stops paying *progress* for old work exactly where speed starts paying *production* → veterans work low tiers for the economy's sake, not the curve's, and the xp/hour spine can't be gamed from below.
- **Facilities via tags** tie production capability to infrastructure → realm development and estate investment translate directly into what can be made where → decay costs capability, which upkeep exists to prevent — the loop closes.
- **Combat's consumable sustain** turns fighters into customers → agrarian and alchemy output has a demand sink beyond upkeep → the adventurer participates in the economy going *and* coming.
- **Exploration (future)** will make access itself a renewable good → the frontier loop gets its supply side.

The test for any future skill or good: **name what it eats and name what it feeds.** If either answer is "nothing," it doesn't belong.

---

## 6. The economic-role test

Applied per category (and to be applied to every future skill proposal):

| Category | Eats | Feeds |
|---|---|---|
| Gathering | time | refining |
| Refining | gathered goods, facilities | manufacturing |
| Manufacturing | refined goods, facilities | upkeep quotas (realm *and* estate), combat supply, estate construction, markets |
| Combat | manufactured + farmed consumables | rare/monster inputs back to the industries |
| Exploration (future) | time, travel, supplies | access — new gathering sources |

Tools are deliberately absent from the "eats" column: v1 has no durable equipment and no per-cycle tool inputs for gathering (§8 #9). The standing consumption that tools would have modeled lives at the **estate** instead — estates eat **generic manufactured goods authored specifically to feed the economy** (upkeep goods), settled through the existing store/solvency machinery (realm-vision §3.6, market-vision §3.2). This keeps the sink where the accounting already is, and keeps gathering the chain's pure time-to-goods entry point.

---

## 7. What this changes in the design doc (work items, not yet decisions)

Roughly in order of when they bite:

- **Tag emission from upgrades and development-node sources.** The engine resolves modifiers and caps from all sources, but availability tags currently do not flow from realm upgrades. Facilities (§3.4) require tags to be emittable by the same closed set of sources that emit modifiers — same resolution pass, same inert/dormant rules. *(Bites before any facility-gated content ships; small, well-defined engine change.)*
- **Item tier as a content property**, with schema validation and the input-class tag convention (§3.3) documented in the content pipeline. *(Bites at content-design time; near-zero engine work.)*
- **Generic level-vs-tier source hook.** One hook feeding both proficiency speed (`cycle_time_pct`, family defaults + per-skill overrides, §2.3) and the xp taper (negative `xp_pct`, XP §5) from the character's level relative to the recipe's tier. Existing modifier types only — fits the "new sources are content" rule. *(Now specified as XP Curve work item #1; recorded here because both emissions serve this document's economics.)*
- ~~**Per-cycle yield modifier type**~~ — **struck.** XP §4.1 resolves the yield question toward no: proficiency is cycle-time only. No new modifier type is needed.
- **Consumables as combat cycle inputs.** Already expressible; the Combat vision must confirm the shape (inputs per cycle vs. per damage taken) before Phase 6 content.
- **Expiring realm-scoped availability** — exploration's key concept. *Deferred with the feature*; recorded so nobody builds an unlocks table that assumes permanence.

---

## 8. Open questions (to resolve in later visions, design, or content docs)

1. ~~**Proficiency yield.**~~ **Resolved by XP §4.1: no yield — speed is the whole bonus.** The new-modifier-type cost is deleted with it.
2. ~~**Proficiency step shape and cap.**~~ **Shape and cap resolved:** asymmetric per-family tables (XP §4.2) with 4-below as the implicit cap. **Exact step values remain content/balance** (XP question #3), tuned against low-tier price deflation from a +20–30% veteran throughput edge and against the taper-counterweight pairing.
3. ~~**Tier count and exact thresholds.**~~ **Resolved: five tiers at 1/50/75/90/95** (XP §2.2).
4. **Content density at both ends.** How many recipes per tier per skill keep tier-1/2 leveling varied *and* tier-4/5 time-occupancy interesting? (Content design; the two-ended principle is set in §3.2, superseding v0.2's density-inverse-to-tier rule.)
5. **Facility granularity.** One tag per facility type (`facility.smelter`) or per facility *tier* (`facility.smelter.t2` for high-tier recipes)? Interacts with realm development stages providing progressively better communal infrastructure.
6. ~~**Visitor facility access.**~~ **Resolved by the visiting design (visiting-vision §5.1):** visitors may use any communal facility at full rate — availability is the current realm's node tags, and there is no visitor malus. See §3.4.
7. **Exploration and keys.** The whole cluster — now owned by `exploration-and-keys-vision.md`.
8. **Combat depth.** Stats, encounters, death, equipment — owned by the Combat vision, constrained by §4.2's economic frame.
9. ~~**Where tools sit.**~~ **Resolved: tools are out of v1.** Gathering eats time alone — no durable equipment (which would be a new concept) and no per-cycle tool inputs. The demand sink tools were reaching for is carried by **estates consuming generic, purpose-made manufactured upkeep goods** through existing store/solvency accounting (§6). Durable tools remain possible as a later feature but nothing depends on them.
10. **Tier achievement-gates.** Ratify or reject the XP vision's recorded direction (its §9): refining/manufacturing tiers requiring a completed recipe set in addition to level, with gathering exempt. Breaks tier = f(level); see the watch item in §3.2. Owned jointly with the XP vision (its question #2).
