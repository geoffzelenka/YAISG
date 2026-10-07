## 1. Overview

This document contains the vision for YAISG (Yet Another Idle Skilling Game). It describes how the game and its mechanics work, while leaving the implementation details to design.md. YAISG is a multiplayer, web-based idle skilling game (similar to Melvor Idle, Idle Clans, Ironwood RPG, etc). Players train skills in real time via timed action cycles to accumulate experience points (XP) and resources. The main differentiator for YAISG is the existence of a World Map that is divided into Realms. The player also develops and maintains their own estate. The estate may be mobile (a small camp or caravan) or fixed in a chosen realm.

### 1.1 Terms used in this document

These terms are used with one meaning throughout.

| Term | Meaning |
|---|---|
| Realm | A region of the single shared world map, with its own type, tier, market, stores and treasury. |
| Realm project | A communal build inside a realm. On completion it grants the realm a tag. |
| Tag | What a completed realm project (or an estate) provides: a facility, a bonus, a malus, or access (for example market access, or a mint). |
| Realm upgrade | A change of the realm itself: a tier-up, or a morph to another realm type. It requires a set of tags and a vote of the residents. |
| Estate upgrade | An improvement a player makes to their own estate. Unrelated to realm upgrades. |
| Resident | A player who owns an estate in the realm. |
| Visitor | A player who is in a realm without owning an estate there. |
| Stores | A realm's stock of goods. Realms have stores; they do not have a larder. |
| Larder | An estate's prepaid upkeep buffer. Estates have a larder; realms do not. |
| Treasury | A realm's gold. |
| Reference price | The content-defined price of a good. Realm prices and estate values are calculated from it. |
| Draw | How much of a good a realm consumes per day. |
| Reserve | The level of a good's stores a realm keeps for itself and will not sell below. |
| Cap | The most of a good a realm's stores can hold. |
| Remoteness | How far one realm is from another. It is a property of a pair of realms, not of a single realm. |
| Bullion | Goods a mint can turn into gold (gold ore, coin purses, jewels, etc). |
| Combatant | The opponent in a combat encounter. |
| Key | An instanced item that gives its holder access to a discovered resource. |


## 2. Overarching Features and Mechanics

1. XP Curve and Tiers
   a. 1 curve shared among all skills; time to max out a skill depends on access and cycle time
   b. 5 tiers of skill and goods values, unlocked by achieving a set level in the skill
2. Skills
   a. Skills turn time (and optionally input goods) into goods.
   b. The current vision contains 6 categories of skills:
      i. Gathering - strictly time into raw material
      ii. Refining - time + raw material into materials that feed manufacturing
      iii. Manufacturing - time + goods into finished goods
      iv. Combat - Melee, Ranged, Magic, Accuracy, Defense, Vigor for performing Player vs Environment combat encounters
      v. Exploration - turns time into keys
      vi. Travel - lowers the time it takes to move between realms, gates certain routes and can open shortcuts
3. Goods
   a. Goods are also divided into tiers and drive the economy
   b. Gathered goods can have regional flavor; refined goods converge back into shared commodities
   c. Refining and Manufacturing require facilities from realms or estates
4. Combat
   a. Turns time and optional consumables into combat skill XP and loot drops.
   b. Combat is a contest between the player's and the combatant's skills that resolves cycle by cycle: hits land or miss, wearing down hit points; consumables are consumed; and the contest ends when one side's hit points reach 0. Then the combatant respawns or the player retires from the field to heal.
   c. Economically, combat is similar to a gathering skill
5. Realms
   a. One world divided into many realms that contain player estates.
   b. Realms have a type and are distinct from each other.
   c. Once a realm has been settled it requires upkeep; this is the engine that keeps goods flowing through the economy
   d. Realms have a gold treasury and stores of goods. A realm cannot create goods from thin air. It can create gold only through a mint.
      i. Mint - a realm project that lets the realm turn bullion (gold ore, monster-dropped coin purses, jewels, etc) into gold
   e. Realms follow a graph and can tier up or morph through realm projects and voted realm upgrades; a realm that cannot maintain its upkeep will decay and can eventually drop a tier
   f. Available gathering and combat spots are content defined.
   g. Available refining and manufacturing facilities depend on the player's estate and the realm's completed projects
6. Estates
   a. Every player always has an estate, either mobile or fixed
   b. Mobile estates move with the player; fixed estates stay in their realm and give deeper bonuses and a heavier vote
   c. Estates follow their own upgrade graph, produce goods into their realm's stores, and require upkeep
   d. Players may build new estates, buy available estates from the realm, or surrender an estate to the realm
7. Market and Economy
   a. Goods are only produced via player skill actions and estate production
   b. Gold is only created by realms with a mint that turns bullion into gold
   c. There are 2 markets, the global player market and the local realm markets
   d. Global player market:
      i. Only players may use the player market, and the realm the player is in must have the market-access tag (access roads/waterways and some sort of town)
      ii. Players get order slots that are used for buying and selling on the player market; they provide a sane limit to orders and a place to hold the goods and gold for (partial) fills
   e. Realm market:
      i. Serves to churn the world goods market - it buys goods needed for realm upkeep and sells excess goods from its stores
   f. The goods design pass assigns a reference price to each good. The de facto price is determined by the global and realm markets; players may arbitrage by buying on the global market and selling to a starving realm market, so long as that realm has a treasury
   g. Goods flow across realms via player activity and trade between realms
   h. All market state is viewable from anywhere; trading is what is gated
8. Exploration and Keys
   a. An advanced skill that turns time into keys
   b. Cycles are much longer than other skills and leveling is deliberately slow
   c. Keys carry the name of their discoverer and create instances of a new finite resource
9. Realm travel and visitation
   a. Visitation - leave your estate's realm and visit a realm to do activities somewhere else
   b. Relocation - move your mobile estate to a different realm
      i. Fixed estates cannot move; they must be surrendered to the realm if the player wishes to relocate
   c. Travel itself is a skill that gains XP when the player moves between realms
10. The player
    a. New players start on Tutorial Island and arrive in the world with a raft and no gold
    b. Player equipment is permanent gear in slots, plus per-cycle consumables


## 3. XP Curve, Levels, and Tiers
### 3.0 Summary
Skills go from Level 1 (0 XP) to 100 (10,000,000 XP) spanning 5 tiers along an exponential curve with ratio 2^(1/7).

One curve, shared across all skills, that turns time spent skilling into levels and levels into tiers. The curve doubles in cost every 7 levels, meaning level 93 is the halfway point to level 100.

### 3.1 Levels
- Characters start every skill at level 1 with 0 XP accumulated
- The maximum level at release will be 100. XP will still accumulate after level 100, but there is no new level or other game-mechanic reward

### 3.2 Tiers and thresholds
- At launch there will be 5 tiers that represent skill aptitude with thresholds of:
    Tier 1 / 2 / 3 / 4 / 5 unlock at levels 1 / 50 / 75 / 90 / 95
- Tier titles are content defined

### 3.3 The XP Curve
#### 3.3.1 The function
XP required to advance from L to L+1:
**xp(L) = floor(A · r^L)**, for L = 1 … 99, with **r = 2^(1/7) ≈ 1.10409** and **A chosen so that total XP to level 100 = 10,000,000** (A ≈ 52)

Reference points along the curve: Level 1-2 = 58 XP; 50-51 = 7,200 XP; 90-91 = 370k XP; 99-100 = 940k XP.

#### 3.3.2 Time Budget
Three anchors for how the skill curve should *feel*:
- Using only the level 1 skill action - 2,880 hours (4 months) to level 100
- Optimal skill advancement and no resource constraints - ~720 hours
- Fully-bonused and optimal play - ~500 hours - which fixes a cap of +45% bonus to a skill

The XP per hour that a skill action should give at its unlock level is derived from these anchors. The content designer checks each action against that derived rate; an action that is deliberately off it should be a stated choice.

#### 3.3.3 Skilling XP bonus cap
The total from all sources - estate upgrades, realm modifiers, realm-tier bonuses, equipment bonuses, consumables - should cap out at +45%. Section 4.6 describes how bonuses from different sources combine; the cap applies to the combined total.

### 3.4 Tier Proficiency
#### 3.4.1 What and why
A veteran in a skill should be able to finish the skill cycle faster than the neophyte; however, alongside that cycle speed bonus there may be a taper in XP earned per cycle.

Proficiency speeds up the skill cycle in steps, by how many tiers the activity is below the character's tier, per skill category:

| Category | 1 below | 2 below | 3 below | 4 below |
|---|---|---|---|---|
| Gathering | +5% | +10% | +15% | +20% |
| Refining | — | +5% | +10% | +20% |
| Manufacturing | — | +10% | +20% | +30% |
| Combat | No cycle speed bonus. Instead, a combat-effectiveness bonus against lower-tier combatants (excluding Vigor). Cycle time stays weapon speed. See section 4.5. | | | |
| Travel / Exploration | No below-tier proficiency. Instead, benefits granted on reaching each tier. See section 3.8. | | | |

Diminishing returns kick in as follows:
- Gathering: no diminishing returns at any distance.
- Refining: XP tapers from 2 tiers below the character's tier; 3 tiers below and beyond, XP is zero.
- Manufacturing: XP tapers at 1 tier below; 2 tiers below and beyond, XP is zero.
- Exploration and Travel: no diminishing returns.
- Combat: the offensive XP stream tapers by tier distance against lower-tier combatants (distances and steps are content/balance); the defensive stream fades naturally (weak combatants deal little damage) and needs no taper; drop tables never diminish.

Tapering of Refining and Manufacturing is to encourage veteran players to continue to produce goods at the top of their skill level and to work on improving the realms to accept those goods to create markets. Since Gathering has no resource inputs, gathering low-level goods would be to feed an economic need at the expense of XP efficiency.

### 3.5 Unlock cadence and content density
- Activity definitions are the content designer's responsibility
- Gathering, Refining, and Manufacturing aim for a new activity every 10 levels in tiers 1-3
- Gathering, Refining, and Manufacturing at tiers 4 and 5 should have new activities unlock quicker and offer more horizontal choices

### 3.6 Skill category baselines and access
- Section 3.3.2 defines the skill baselines (2,880 hours, 720 hours, 500 hours); however, the "feel" of each skill category can be tuned through its XP per hour and cycle times via content definition, or through assumptions about player cycle bonuses.
- Access is a large block to achieving truly optimal skilling: realms that contain high-tier gathering spots, and facilities from realms or estates to refine and manufacture

### 3.7 Combat leveling
- Tier multiplier - for Melee, Ranged, Magic, Accuracy, and Defense, a uniform +5% per tier bonus to each skill. Vigor gets no tier multiplier.
- Combat XP is earned through two streams drawn from two pools. This is described with the skills in section 4.5.

### 3.8 Travel and Exploration
- Travel tier-ups grant faster journey time and a reduction to the per-edge supply costs.
- Travel level may gate access to certain map edges; more experienced travellers know where the shortcuts are, or can brave a more treacherous route.
- Exploration tier-ups grant faster expedition cycles and more keys per discovery, and higher tiers skew the exploration drop table toward rarer keys


## 4. Skills
### 4.1 Skills summary
Skills turn time into goods, and goods and skills climb a ladder of tiers that the whole economy is based on. Each skill category has a defined economic role: what it consumes and what it supplies. Nothing produces into the void and nothing consumes from nowhere. A skill that doesn't participate in the economy loop is a design mistake.

The production spine is Gathering -> Refining -> Manufacturing. Combat is a risk-flavored producer-consumer and Exploration is a supplier of access through keys.

Refining and Manufacturing also require facilities - these are made available through the realm the player is currently in or from the player's estate.

### 4.2 Skill Categories
- Gathering - turns time into basic goods. Mining yields ore; lumberjacking yields logs; farming produces grains, vegetables, etc. Gathering is where realm flavor may live
- Refining - turns gathered goods plus time into intermediate goods. Smelting turns ore to ingots, milling turns logs into planks. Refining converges locally flavored goods into commodities
- Manufacturing - turns refined goods and monster drops into finished goods. Alchemy takes herbs and monster parts to make potions, weaponsmithing takes ingots and planks to make swords, etc. Manufacturing also produces the generic tools and generic goods that are required for estate and realm upkeep.
- Combat - producer-consumer hybrid - consumes consumables like potions and food and produces items from a combatant's drop table (eg leather, coin purses, spider fangs, etc)
- Exploration - turns time spent into access: discovers resource nodes, monster dens, etc in the form of keys that can be sold to other players
- Travel - time spent travelling that opens up access to frontier realms, and faster and cheaper travel

### 4.3 Category Rules
- Every skill requires an economic role; a skill's outputs must be an input to something
- Production chains cross realms by design. A realm will rarely have enough inputs to do a complete chain, especially of higher-tier goods
- Categories are content groupings. Every skill action is the same kind of thing: a cycle time, inputs, outputs, and conditions for when it is available. Categories exist for content design and UI groupings

### 4.4 Proficiency: mastery of fundamentals
Players with higher skill levels can work faster - a level 80 blacksmith can make a level 10 item faster than a level 10 blacksmith.

- Threshold based, stepping at tier boundaries. The bonus is a step function of tier distance, not a continuous curve. Different skill categories have different proficiency rules (section 3.4).
- Speed is the only tier-based bonus; there is no additional yield
- Tier distance also determines the XP taper, where it applies to that skill category

### 4.5 Combat XP: two streams, two pools
Each combat skill earns XP from the thing that exercises it.

- **Offensive stream.** XP from damage dealt. It goes to the attack style in use (Melee, Ranged or Magic) and to Accuracy. The player's stance, a standing combat setting, decides how it is split between the two. This stream tapers against combatants below the player's tier.
- **Defensive stream.** XP from damage taken and damage mitigated. Vigor earns from damage taken; Defense earns mainly from damage mitigated. It needs no taper, because a weak combatant deals little damage.

Every combatant carries two content-defined XP pools, one for each stream. A pool is the most XP its stream can pay out in one encounter.

- A pool is per encounter. It refills when the combatant respawns, not over time. A player who stands in front of a combatant they never defeat drains the defensive pool once and then earns nothing more from it.
- Whatever is left in a pool when the combatant is defeated is lost.
- The size of each pool is a content lever. A tough combatant that hits softly trains offense; a fragile one that hits hard trains defense.

In any one fight four skills earn at once: the attack style, Accuracy, Defense and Vigor. Each of them progresses at the same pace as any other skill would; combat trains several skills side by side, not any one of them faster. Pools are sized against the time budget in section 3.3.2, using the expected time to defeat the combatant plus its respawn time.

### 4.6 How bonuses combine
Bonuses come from five sources: gear, the player's estate, the realm the player is in, consumables, and tier proficiency (section 3.4).

- Bonuses from the same source add together.
- The totals from different sources multiply.

**total bonus = (G1 + G2 + ...) × (E1 + E2 + ...) × (R1 + R2 + ...) × (C1 + C2 + ...) × (P)**

The G terms are gear bonuses, the E terms estate bonuses, the R terms realm bonuses, the C terms consumable bonuses and P the tier proficiency bonus. Each source's sum is applied as a multiplier, and a source with no bonuses counts as ×1.

Only bonuses of the same type combine with each other, and the formula is applied separately for each type. A mining cycle speed bonus does not combine with a cape's XP bonus, for example. Tier proficiency is a cycle speed bonus, so it combines with other cycle speed bonuses for that skill and never affects XP.

For example, for a single bonus type, two gear bonuses of +5% each, one estate bonus of +10% and one realm bonus of +20% combine as 1.10 × 1.10 × 1.20 = 1.452, a total bonus of about +45%.


## 5. Goods
### 5.1 Goods Summary
- Goods are items generated from skills.
- All goods can be generated via some skill's action
- Goods are all designed by the content designer
- All goods are assigned a tier, and that tier should come from the skill activity that generated it (eg a tier 3 activity should create a tier 3 good, but may use inputs that are tier 1, 2, or 3). Generally higher-tier skill cycles are longer than lower-tier cycles.
- Goods have tags that help categorize their use. A pine log and a palm log may both be tier 1 and tagged as logs, so that a tier 1 lumber milling activity can turn either of them into a tier 1 wooden plank, and a lumber-mill-themed estate that requires tier 1 logs for upkeep would accept either.
- Gathered goods may have realm-specific flavor, but once they have been refined the refined good is a commodity.
- Every good has a content-defined reference price.


## 6. Combat
### 6.1 Combat Summary
Combat turns time and consumables into combat skill XP and loot drops. Each encounter is a contest between the player's stats, equipment and bonuses and a combatant's stats, resolved cycle by cycle: hits land or miss; damage wears down hit points; consumables are used; and when one side's hit points are exhausted the encounter ends - in loot and a respawn, or in the player retiring from the field to heal.

Combat is economically a gathering skill with risk attached: combatants have drop tables for goods used by other skills.

### 6.2 Combat Loop
#### 6.2.1 Engagement
The player engages in combat by choosing a combat location within the realm (an inn's basement, a hunting ground, a deep cave, or a bandit hideout) and a combatant to fight. The encounter then runs as a repeating skill action like any other, each cycle being one round of combat.

#### 6.2.2 The Combat Cycle
Combat cycle length derives from weapon speed plus applicable modifiers, and each cycle resolves as follows:
1. Hit resolution - who hit whom, and for how much damage
2. XP award - offensive XP for damage dealt and defensive XP for damage taken and mitigated, each drawn from the combatant's matching XP pool (section 4.5)
3. Consumable resolution:
   - Utility slot items (ammunition, weapon oil, magic components) are consumed per cycle
     - A ranged attacker who runs out of ammunition leaves the field. The combat action ends, since they can no longer train Ranged.
     - Melee and Magic may keep fighting without their utility slot consumables, but are less effective
   - Reactive consumables (potions, food) are consumed in response to player state, eg low health or a buff expiring
4. Terminal checks:
   - The combatant's HP is exhausted: award loot from the combatant's drop table; wait for a respawn timer; then begin combat cycles again
   - The player's HP is exhausted: the player retires to being idle. The action ends. Death costs nothing more than the player becoming idle.

#### 6.2.3 Offline resolution
Combat resolves while the player is offline like every other action, but it has to account for more than uniform cycles: hit points, consumable stacks, kill/respawn alternation, and the player losing and going idle. The player should receive a summary report when returning from being offline.

### 6.3 Idle health regeneration
Players that are missing health slowly regenerate it.


## 7. Realms
### 7.1 Realms summary
Realms are not parallel servers, but different regions on a single shared map. The map helps players realize they're part of an interconnected world and gives them a sense of place. The map makes travel feel real and not an arbitrary time-gate, and gives players a way to view the evolution of the world. Each realm has its own market that can only be traded at in person, its own stores and treasury whose differences from other realms move goods around the world, and its own realm flavor.

### 7.2 Realm types and tiers
Each realm has its own economic identity based on its content-defined geography and how far along its tier web it has evolved. The realm type gives availability and bonuses to some skills, possibly a malus to others, and certain skills may not be available at all (eg fishing in a desert realm). Some example realm types:

- Agrarian realm - farming, cooking and other food skills and resources
- Mountain realm - mining, smelting, metal crafting bonuses
- Forest realm - lumberjacking, plank milling, and carpentry - an end-to-end timber economy, with hunting-flavored combat encounters
- Desert realm - mining and glass industry
- Industrial realm - trees have been felled, fields paved over - but trade and industry flourish here
- Barren / Wilderness realm - a frontier realm, or a realm that has regressed and decayed - few economic bonuses, but dangerous fauna to hunt, resources to prospect, and room to build or recover what once was

Realms become more specialized as they move up the tiers through realm projects and realm upgrades. Realms can morph horizontally more easily at low tiers, and not at all once highly specialized.

No realm can do everything itself. Tier 1 realms may be self-sustaining, but once a realm heads down the road of specialization it depends more and more on other realm types to feed its goods needs.

### 7.3 Upkeep
Developed realms have an upkeep: goods that are needed to maintain the realm. As realms complete projects and have estates built, they develop upkeep costs. This is the goods sink that keeps goods circulating and gives all the stuff created by players and their estates somewhere to go.

As a realm specializes further, it requires more goods from other industries to maintain that specialization.

### 7.4 Realm evolution
A realm's identity is earned by the players that populate it. Realms have a set of projects that work like public quests to steer the identity and bonuses/maluses of the realm. Once enough projects are complete, a vote may be called among the residents to morph or tier up the realm along an edge of its development graph. An example would be a forested realm's populace constructing sawmills and moving toward an industrial realm, versus clear-cutting forests and planting fields to move toward an agrarian realm.

### 7.5 Decay and regression
If a realm misses its upkeep and its stores run dry, the realm starts to decay. First, its most recent project tags stop functioning and are lost; ultimately the realm regresses to a lower tier until it can meet equilibrium again, or collapses entirely into a barren realm.

Decay is a way to self-correct realms that advance too quickly, or that become stale when the population moves on to other areas of the map. It allows a frontier to re-establish.

Decay is a slow process that should be easily seen by players. The stages are in section 9.4.12.

### 7.6 Realm tiers and the goods pyramid
As a realm tiers up, the goods it requires form a pyramid. New tiers of goods are added to the top, and the previous tiers of goods are expanded upon. The base needs to get larger to support the taller pyramid. This way tier 1 goods stay relevant forever. And, as the realm becomes more specialized, it requires a broader set of lower-tier goods as well.

### 7.7 Realm projects and realm upgrades
A realm project is a discrete community activity that a player may start and that any player inside the realm may then contribute to. The realm may also contribute to its own projects if it has excess goods in its stores. Example projects:
- Construct a road - the first step to connecting a wilderness realm to the rest of the world
- Establish trade routes - grants the market-access tag, letting players in the realm trade on the global player market
- Build a lumber mill - creates the facility that allows milling logs into planks
- Construct city walls - a step toward tiering up the realm
- Dig the mine deeper - a step toward upgrading the realm along a mining tier
- Build a mint - lets the realm turn bullion into gold

Upon completion of a project the realm gains a tag that grants access, bonuses, and/or maluses. The tag lasts until it is lost to decay.

A realm upgrade is how a realm changes itself, either tiering up or morphing horizontally into a different type. The realm development graph defines the tags a realm must hold before an upgrade can happen. Since an upgrade is a major change, a realm-wide vote is held before it can occur.

#### 7.7.1 Project lifecycle
The content designer creates projects for each realm type in the realm development graph. Each realm type can therefore only offer the projects designed for it, which move it along the edges of its graph node. A player in the realm can kick off a project by paying its kickoff cost in gold and goods. Each project is flagged as to whether only residents may kick it off, or residents and visitors.

Once a project has been kicked off, its total cost must be met. Players in the realm may contribute as much as they like. A project also adds to the realm's draw for the goods it needs, so that a realm may be able to complete projects passively through its own market.

A project that has not been contributed to for a while starts to lose its contributions and ultimately fails, using the same mechanic as realm decay. A failed project enters a significant cooldown (a day or two) before it can be begun again. Goods used by projects are consumed, just like realm upkeep; no goods are refunded.

Once a project's cost has been met, it moves to a build phase: an amount of time before the tag is added to the realm.

A player may only kick off 1 project a day, across the whole world.

A realm may only have one active project at a time.

There should be a log of who kicked off a project and who contributed. It is attached to the tag when it is added to the realm, so that players can have some meta-game bragging rights about project contributions.

#### 7.7.2 Realm upgrade lifecycle
Once the realm holds the tags required for a realm upgrade, a resident of the realm may request that the upgrade begin. The player must pay a significant fee to start the process. Since realm upgrades can have major ramifications, the residents of the realm vote on whether the upgrade will happen. A player's type of estate gives weight to their vote as follows:

| Estate | Weight |
| --- | --- |
| Mobile estate (tent, wagon, boat, etc) | 1 |
| Fixed estate, tier 1 | 10 |
| Fixed estate above tier 1 | +1 per tier (10% of base) - tier 2 = 11, tier 3 = 12, ... |

A player may only vote once. The ballot is secret, but participation in the vote is public. A player is only eligible to vote if they were a resident of the realm when the vote was called. The default position is to abstain and there is no minimum quorum, so 1 vote against with the rest of the residents abstaining means the vote fails. A vote lasts a few days; if every eligible resident has cast a vote, the vote may end early.

If a vote fails, there is a cooldown before another realm upgrade vote may be called. The fee goes to the realm's treasury regardless of the outcome.

If the vote succeeds, the realm starts its transition. For a week the realm is in a transitory state, during which no projects or upgrade votes may be started. Keys for that realm are handled as described in section 10.3.3.

#### 7.7.3 Realm decay
If a realm decays, it unwinds its stack of project tags, most recent first, and then its tier. When a project decays, its tag is removed from the realm. If the realm decays enough to drop a tier, it enters a transitory period like the one for a realm upgrade.


## 8. Estates
Estates are how a player specializes themselves. The player chooses between a mobile estate and a fixed one, and then how they will specialize as they move up the estate upgrade graph.

A player always has an estate. A player who ends up without one (for example after surrendering a fixed estate) is given a free basic mobile estate.

Owning more than one estate at the same time should be technically possible, but there is not yet a way to do it in the game.

### 8.1 Mobile Estates
Mobile estates represent things like a humble tent, a trader's caravan, or a boat. They let the player bring their estate bonuses with them by relocating with the player. These estates suit the traveller, adventurer, trader, or developer playstyles.

### 8.2 Fixed Estates
Fixed estates become a set piece of a realm's economy. They give the player significant bonuses and create goods for the realm's economy. Fixed estates represent things like a farmstead, a forge-hall, a lumber mill, a workshop, or even a keep. A fixed estate cannot be moved. The trade-off for choosing a fixed estate is deeper bonuses and a heavier vote in the realm, against mobility.

### 8.3 Estates and Realms
Estates interact with realms. Both have upkeep needs: the realm feeds its upkeep from its stores, and the estate from its larder. Estates also generate goods that go directly into the realm's stores. Estate bonuses work best when paired with a similar realm type, such as a forge-hall in an ore-rich mountain realm. Similarly, a fishmonger's wharf should not work very well in a desert realm bereft of water. Estate bonuses multiply with bonuses from other sources, such as the realm and gear (section 4.6). Tier 1 realms should be able to have their needs met by a few tier 1 estates.

### 8.4 Creating an estate and the upgrade graph
The specific kinds of estates and their upgrade graph are under the purview of the content designer. Realms could have local flavor in the estates available. Estate-style blueprints could be an interesting drop type. Players can build a valid tier 1 fixed estate in a realm at a hefty cost, one that means the player has graduated from the early game to the mid-game. A tier 1 fixed estate should be a generalist within what its realm offers; as it upgrades it should begin to specialize. Building and upgrading an estate requires goods of the tier it belongs to, as well as some lower-tier goods.

### 8.5 Estate tiers
Estates get better the more they are invested in. Mobile estates travel better, need fewer travel supplies, and produce some of their own travel supplies or goods along the way. Fixed estates get better at producing their specific manufactured or refined goods and give better bonuses.

### 8.6 Estate production and upkeep
Estates also have an upkeep: they need input materials as well as general goods to maintain the estate and its followers, workers, wagons, etc. The player may load the estate's larder, and the estate will draw from the realm's stores when the larder runs out. The same decay mechanism that exists for realms applies to estates.

### 8.7 Estate sales
Realms must be bootstrapped with NPC estates to get production going. Players may buy NPC estates from the realm.

Players that no longer want their estate may surrender it to the realm. The realm pays as much as it can for the estate, up to the estate's value; the player may also choose to donate the estate for no charge.

The value of an estate is the cost to rebuild it as it currently stands. Each good in that cost is counted at the lesser of its reference price and the price the realm is currently selling that good for. If the realm is not currently selling the good, its reference price is used.

The realm sells estates at the estate's value plus a defined percentage on top, so that players cannot make money buying from and reselling to the realm. However, a developer-archetype player could build up estates, sell them to a realm and buy back, to jump-start a wilderness realm's development.

An estate whose owner no longer does anything with it simply persists for as long as its upkeep is met. There is no inactivity rule. It is subject to the same decay as any other estate, and if it falls apart completely, it is gone.

### 8.8 Estate market mechanics
#### 8.8.1 Estates tick with the realm
Estate passive production is processed when the realm is processed; the player needs to take no action.

#### 8.8.2 Estates transact in goods
Estates hold no gold, just goods. An estate credits its production to the realm's stores, and takes its upkeep goods from its own larder first and then from the realm's stores.

#### 8.8.3 Estate deficit gauge
Estates have a deficit gauge that works like the realm's (section 9.4.11).

#### 8.8.4 Estate larder
A prepaid upkeep buffer, not goods storage. It lets a player prepay if they know they will be absent, or just not worry about the estate decaying. The player can only deposit; no goods can come back out.

#### 8.8.5 Estate decay
Estate decay works the same as realm decay (section 9.4.12), losing estate upgrades most recent first.


## 9. Market and Economy
### 9.1 Summary
There are two kinds of market: the global player market and the realm markets. The global player market is a world-wide order book for players to trade gold for goods instantly. It seeks to maximize liquidity and price discovery. The realm markets are the economic engine that drives supply and demand for all the generated goods. A realm market buys what the realm needs and sells what the realm has in excess, from the realm's own stores, at prices that rise with scarcity, and only with gold its own economy has earned.

Players trade on the global market to move goods between players, while realm markets trade to sustain the world itself.

### 9.2 The Global Player Market
#### 9.2.1 One book, whole world
There is a single global order book per good. Goods and gold match instantly, with no transport time. The goal is to maximize liquidity and price discovery that scales with the world population. It is expected that players can arbitrage between the global market and the realm markets.

#### 9.2.2 Full order book, buy and sell orders
- Buy orders: the player names a good, a quantity, and a unit price. The gold required to fill the order is placed in that order's slot when the order is created.
- Sell orders: the player names a good, a quantity, and a unit price. The goods are moved into that order's slot when the order is created.
- Cancellation: the remaining escrow and any partial fills stay in the order slot for the player to collect.
- Fulfillment: the seller is paid the order's value less the global market tax (section 9.2.4). The buyer receives the goods into their order slot.

#### 9.2.3 Order slots
Players have a set number of order slots. A slot holds the escrowed gold or goods when an order is created, and serves as a basket to hold (partial) fills. Players then collect from the slot.

The order lifecycle is:
1) Create an order in an empty slot
2) Escrow flows out as the order is filled
3) The slot enters collection mode when the order is completed or cancelled
4) The player collects goods and/or gold to empty the slot
5) The slot is ready for a new order

Order slots are a capped resource, primarily as an anti-manipulation measure, and also as a valuable resource that could be made available through late-game estate upgrades or as a premium upgrade.

#### 9.2.4 Global market seller tax
Every order match pays a flat, content-defined global tax rate out of the seller's proceeds, credited to the treasury of the realm the seller was in when the sell order was created.

The rate is flat and global to prevent realms racing to the bottom on tax rates. It applies only to the seller's side, since that is where the money ends up. The tax goes to the realm where the seller was present, since that realm facilitated the trade. This tax is one of the few ways for realms to fill their treasuries.

#### 9.2.5 Global market access is earned, and losable
Players can only trade on the global market from a realm that has the market-access tag. That tag comes from one of the early realm projects, and as such can be lost if the realm decays far enough.

This serves a gameplay purpose, as it creates an economic cost to venturing out into the wilderness.

#### 9.2.6 Visibility
The global market's full order book is visible to all players anywhere. The market-access tag only gates creating orders.

### 9.3 Realm Markets
#### 9.3.1 Market function: sink and engine
Each realm operates a market that:
1) Buys the goods required to fill its stores, in order to feed its upkeep and its active project
2) Sells goods from its stores that it has in excess, which come from its hosted estates' production and from what players have sold it

Realm markets cannot create goods from thin air; goods must be produced by players and estates.

#### 9.3.2 Prices
Realm market pricing has three layers:
1. Reference price - the content-defined price of the good.
2. Scarcity - what a realm offers for a good depends on the reference price and how full its stores of that good are. When the stores are full, the price is near the floor; it climbs as the stores empty out. Section 9.4.8 describes how this behaves.
3. Treasury - the first two layers are what a realm is willing to pay; however, a realm cannot create gold out of thin air to pay. The realm's treasury caps what it can pay for a good. A realm cannot bid an amount that it cannot pay.

A player selling to the realm they are standing in pays no distance cost. Distance only enters when realms trade with each other (section 9.4.7).

#### 9.3.3 Cold start
A fresh world needs goods and gold in circulation, otherwise realms deadlock and fade away before players can begin. The content designer must seed a world that has some semblance of balance and sustainability.

#### 9.3.4 Presence
Trading with a realm's market requires the player to be in that realm, either by living there or by visiting.

#### 9.3.5 Visibility
Every realm market is viewable from anywhere: its store levels, its prices, and how healthy the realm is. Only trading requires presence. This is what lets haulers and developers see where the world is hungry.

### 9.4 Realm stores, upkeep, and trade between realms
#### 9.4.1 Summary
Periodically, realms balance unmet needs among each other, treasury to treasury, through NPC caravans.

This realm-to-realm trade is a secondary choice. Realms can only ship a limited amount of goods at a time between each other. The caravans cost gold, take time, and lose some goods on the way, so they are always a worse way to supply a realm than a player hauler.

#### 9.4.2 Concepts for this mechanic
1) Draw - how much of a good a realm consumes per day. It comes from the realm's estates and tags. The draw is the realm's goods appetite; an active realm project adds a small temporary increase to it.

2) Reserve - a number of days of draw that the realm keeps for itself. Goods at or below the reserve are not for sale at any price, not available to private estates, and not available for projects. The reserve is the line between what a realm has and what it can spare.

3) Cap - the most of a good a realm's stores can hold, also expressed as a number of days of draw (more days than the reserve).

4) Remoteness - how far one realm is from another, measured along the map edges between them. It is a property of a pair of realms, not a fixed value of one realm. It only matters when two realms trade with each other.

#### 9.4.3 Only sell excess
A realm offers a good for sale only when it holds more than its reserve, and never sells below its reserve. A realm will not starve itself to serve a buyer, and "buying a realm dry" won't be a thing.

The reserve has a configured default number of days, which realm modifiers can change.

A pending realm transition raises the reserve by the number of days required for the transition.

#### 9.4.4 Only buy what you need and can afford
If a realm has no draw for a good, it does not bid for that good.

A realm with no treasury makes no bids.

At its own market, a realm buys from players all the way up to its cap, at a price that falls as the stores fill.

From other realms, a realm only buys when it is below its reserve, and only enough to get back to it. It shops for its goods in order of largest draw, for as long as it has funds.

#### 9.4.5 Goods a realm does not consume
For a good the realm has no draw for, the reserve is zero, so all of it may be sold. However, there must be a hard cap: the warehouse has a roof.

Any production above the hard cap is lost.

#### 9.4.6 Project contributions
The realm is a slow contributor of last resort to its own project. An active project adds to the draw for each good the project still requires. The size of that addition is set so that, with no help from players, the realm would finish the project on its own in a content-defined number of days. As players contribute, the remaining requirement shrinks and so does the extra draw.

The realm only contributes goods to the project that are above its reserve.

#### 9.4.7 Trade between realms
A realm that is below its reserve for a good looks for it at other realms that hold that good in excess. The lower its stores, the more it is willing to pay, up to the limits of its treasury. Likewise, a realm with goods in excess of its reserve sets an asking price that falls as its stores approach the cap.

Trade between realms must take remoteness into account and must prefer nearer realms. Three costs do this, and all three grow with the remoteness between the two realms:
- **The caravan fee.** The buying realm pays gold for the NPC caravan, on top of the selling realm's asking price. The fee goes to the selling realm's treasury.
- **Travel time.** Gold changes hands immediately, but the goods take time to arrive.
- **Loss on the road.** As a risk of travelling across less developed realms, some of the goods are lost to banditry or bad luck. Realm projects along the route (roads, a militia) can reduce this.

The buying realm compares sellers by what a delivered unit will really cost it, counting the asking price, the caravan fee and the expected losses, and picks the cheapest.

#### 9.4.8 How realm prices behave
Rules for the price a realm quotes at its own market:

- **The bid follows scarcity.** With full stores a realm pays well under the reference price; the price stays low across most of the range and climbs steeply only as the stores run empty. As an illustration: about a third of the reference price when full, a little over double when empty, treasury permitting.
- **The asking price is the realm's own bid plus a fixed margin** (as an illustration, 25%). Because the two always move together, a player can never profit by buying from a realm and selling straight back to it. A realm whose stores are draining also stops being a cheap source at the moment it starts getting hungry.
- **The margin is a content setting** with a global default. A trade-hub realm could run a tighter margin.
- **Large trades move the price as they go.** Selling 500 grain to a starving realm does not pay the empty-stores price for all 500 units. The price falls as the stores fill, the same way a large order works through an order book. Buying from a realm works the same way in the other direction.
- **The treasury limits the trade.** A realm buys only as much as it can pay for.

#### 9.4.9 Upkeep
The cadence of upkeep is configurable, but should start as hourly. The content designer defines upkeep per day, and each tick takes the matching fraction.

Because goods bought from other realms take time to arrive, a realm needs to know what it already has on the way, so that it does not buy the same shortfall twice.

Each tick, in this order:
1. Estates add their production to the realm's stores.
2. Each estate takes its upkeep from its own larder first.
3. An estate whose larder is short takes the rest from the realm's stores, but only down to the realm's reserve.
4. The realm takes its own upkeep from its stores, and may go below the reserve. The reserve limits what a realm will spare, never what it will eat.
5. The realm contributes to its active project, only from stores above the reserve.
6. Spoilage is applied.
7. Anything above a cap is lost.
8. The deficit gauges of the realm and of each estate are updated.
9. Decay advances or recovers.

The rule in short: above the reserve, estates eat first; below it, the realm eats first.

#### 9.4.10 Spoilage
Certain goods have a content-defined spoilage rate, which defaults to zero. Spoilage applies only to goods in realm stores and estate larders. It is separate from the goods lost on the road in trade between realms.

#### 9.4.11 Deficit gauge
A realm's health is measured by a running total of unmet upkeep, not by how its stores look at one moment.

- Each tick in which the realm cannot fully feed its upkeep, the gauge rises by the share that went unmet. Goods are weighted by reference price, so missing an expensive good counts for more than missing a cheap one.
- Each tick in which upkeep is fully met, the gauge falls back at a set recovery rate.

The gauge therefore reads as "how long this realm has been going hungry", which can be shown to players: "this realm has been short the equivalent of three days."

Using a running total gives a grace period for free, since the gauge has to build before anything happens, and it settles the question of one missing good versus many: a realm short of a single input slides slowly and does not collapse at once.

Which good is short is shown separately, because that is what a hauler needs to know.

#### 9.4.12 The realm decay stages
| Stage | When | Effect |
|---|---|---|
| **Fed** | Gauge is zero | Normal operation. |
| **Strained** | Gauge passes the first threshold | **Signal only - no mechanical effect.** Publicly visible on the map and the realm's page. |
| **Faltering** | Gauge passes the second threshold | The realm's bonuses weaken and its facilities are suspended. Fully reversible; nothing is lost. |
| **Failing** | Gauge passes the third threshold | The realm starts losing project tags, most recent first, faster the higher the gauge. Dropping a tier is the last resort. |
| **Regressed** | Nothing left to lose at this tier | The realm drops to a lower tier or type through a realm transition. |

**Strained must stay purely cosmetic.** It is the recruitment stage: the window in which haulers and the community notice, before anything is taken away. A realm that suffers the moment it dips is a realm whose players learn to hoard, not trade.

Recovery walks back down. If a failing realm is rescued, its progress toward losing the next tag drains away gradually, so the realm climbs back from where it fell to. Once something has been lost, the way back is the ordinary route: rebuild it through realm projects.

### 9.5 Currency
Where does gold come from?
- Realms are bootstrapped with some treasury as part of the initial content definition
- Mints

New players are given a little seed gold on Tutorial Island, but it is spent there and never reaches the world (section 9.5.4).

#### 9.5.1 The mint
A mint is a tag from a realm project. It gives the realm a draw for bullion: precious metals and other goods flagged as bullion. The realm then acquires bullion the same way it acquires any other good it has a draw for, at its market and from other realms.

Each tick the mint consumes bullion from the realm's stores and adds new gold to the realm's treasury. The gold created is the reference price of the bullion consumed, times a global coinage multiple (as an illustration, about 1.2). This is the only place in the game where gold comes into existence, and it goes to the realm's treasury, never directly to a player.

The mint throttles itself:
- **Bullion abundant** - the realm's bullion stores are full, so it pays little for bullion and coins far more gold than it spent. The mint creates gold freely.
- **Bullion scarce** - the stores are nearly empty, so the realm bids high for bullion and can pay more than the gold it coins. The mint stops creating gold and starts removing it.

The amount of gold in the world therefore follows how much bullion the world actually produces, with nothing to tune by hand.

Rules for the mint:
- The coinage multiple is defined as a multiple of the reference price, never as a separate price of its own.
- Bullion is treated like every other good. It counts toward the deficit gauge, and a realm that cannot feed its mint decays for it.
- A mint can be built in tiers. A higher-tier mint consumes more bullion per day; it does not coin more gold per unit. The coinage multiple is one global setting.

#### 9.5.2 Combat does not drop coin
Combat must not have gold in its drop tables, but it may drop bullion items (a bandit's coin purse, a dragon's hoard of gold bars, a guardian's silver plate, etc).

#### 9.5.3 Currency sinks
- If the gold supply runs too hot, setting the coinage multiple below 1 runs every mint backwards.
- Player churn effectively neutralizes a chunk of gold.
- A share of the global market tax could be destroyed instead of credited to the realm. This setting ships at zero.

Otherwise, gold just flows through the realms and players. The caravan fee in trade between realms (section 9.4.7) goes to the selling realm for now; destroying some of it is a possible future sink.

#### 9.5.4 Bootstrapping the player
A new player is given a little seed gold on Tutorial Island so that they can kick off the realm project there (section 12.2). Paying the kickoff cost removes that gold from the game, because the tutorial realms are cut off from the world.

Players therefore arrive in the world with no gold. Their first gold comes from selling what they gather or make, to the realm market or on the global player market. The realms a new player can arrive at must be seeded so that they can buy low-tier goods.

### 9.6 Players and the Realm Economy
#### 9.6.1 Haulers
The player hauler has a niche to fill: transporting goods from a realm with full stores to sell to desperate ones. The hauler can also arbitrage between the global player market and a needy realm. Arbitrage can still be severely limited by realm treasury levels.

Frontier realms without market access also require supply runs by players to bootstrap their development.

#### 9.6.2 Other archetypes
- The producer - generates lots of a specific type of good and invests their skills and estate heavily into it. They then sell on the global market.
- The trader - works the global market's order book
- The adventurer - buys consumables, heads into the wilderness to secure rare goods and brings them back
- The developer - purposefully works to develop realms and build estates


## 10. Exploration and Keys
### 10.1 Summary
Exploration turns time and long activity cycles into access: keys to resources that otherwise wouldn't be available. A discovery conjures a new lode, a hidden grove, or a monster-infested cave that is embodied in the key itself, an instanced item that carries the discoverer's name forever and a finite number of uses. A key may be sold on a dedicated market before its first use; afterwards it is bound to the user until the user chooses to destroy it.

Exploration is a "prestige" skill: it has far longer cycles and discoveries are rare. Leveling is deliberately slow.

### 10.2 The Exploration Skill
#### 10.2.1 The action loop
Exploration is a repeating skill action like any other: repeated search cycles with a discovery drop table. Three properties, all content settings, distinguish it:
- Cycles are much longer; exploration is measured in expeditions, not swings of a pickaxe.
- Discoveries are rare - most cycles yield only XP, and a discovery is a low chance - maybe one or two keys after a night-long skilling session.
- Optional consumables (like the optional consumables for Melee and Magic) can give a small targeted boost or shape the drop table (supplies, lures, charts, etc)

#### 10.2.2 Availability and gating
- Exploration can happen in any realm where the content defines it as possible; no residence is required, just presence.
- Exploration has cross-skill gates: gathering and combat skill minimums (you must be able to survive the expedition, and to recognize what you find).
- Higher tiers in those gathering and combat skills can shape the drop table

#### 10.2.3 Discoverable resources
Discoveries are content-defined with some random parameters. The content designer authors discoverable resource templates. A template defines what a key may contain: resource kind, yield range, key-count range, eligible realm tags, flavor. On a successful discovery, keys are generated from the template with rolled values.

The number of keys generated per discovery is rolled from the template's parameters.

### 10.3 Keys
#### 10.3.1 Summary
A key grants its holder access to actions on a discovered resource that may not otherwise exist in the realm: gathering a rare resource, combat in a newly discovered monster camp, etc. This access is private to the holder of the key.

#### 10.3.2 The key is the node
The key is the node that the actions are performed against. Each key is self-contained: it holds the resource definition and its remaining uses.

- Multiple keys from one discovery are all unique and independent - they share flavor, but carry their own yield. A discovery of 3 keys of 500 resources has put 1,500 resource units into the world.
- The resource type and remaining uses are readable from the key item itself
- A gathering key holds a number of gathering cycles. Each cycle uses one.
- A combat key holds a number of monster spawns. Each spawn of the combatant uses one.
- Once a key's uses run out, it no longer functions as a node.
- A depleted key remains in the holder's inventory until the player chooses to destroy it, and may be kept as a trophy

#### 10.3.3 Realm transitions invalidate keys
Keys are scoped to the realm in which they were discovered.

- When a realm transition begins (a passed realm upgrade vote, or a decay regression), the realm's keys are marked deprecated. They still work; the mark is the hint to use them before the transition completes.
- When the transition completes, all of the realm's keys are invalidated, and any action using one stops.

### 10.4 Instanced items
Keys are not interchangeable with one another, so they work differently from commodity goods. Even keys from the same discovery may roll different values. As such, keys do not stack, each one takes up its own inventory slot, and they need their own market.

### 10.5 Trading keys
Keys are sold through a separate market for instanced items:

- Fixed-price, buyout only
- The seller still pays a tax
- A way to browse keys by realm and by either goods category or exact good
- Only unbound, unused keys may be listed


## 11. Realm Travel and Visitation
### 11.1 Summary
Acting where you don't live. The world is a map of realms, and a character may travel to a realm they do not call home, in order to sell to a starving realm, hunt its dangerous fauna, or develop a frontier realm.

Travel itself is a skill. Journeys cost time and supplies; active travellers get faster and more efficient.

### 11.2 Moving
A character's movement mode is determined by the form of their estate.

- A player with a fixed estate may visit another realm. The estate stays where it is.
  - A fixed estate cannot relocate. A player who wants to move for good surrenders the estate to the realm (section 8.7), receives a free basic mobile estate, and relocates with that.
- A player with a mobile estate relocates: the estate moves with the player, and so the player's home realm moves along too.
  - A player with a mobile estate will generally not want to visit, and should want to relocate.
  - A player with a boat should not be able to relocate over land-based map edges

### 11.3 Travel is a Skill
#### 11.3.1 Journey as an action
A journey is a skill action like any other, made of cycles.
- The player picks a destination realm
- The route is the cheapest path over the map
- Each edge of the route takes one action cycle

The player is always in a realm; there is no limbo, between-realms state.

Travel continues while the player is offline, like every other action. The welcome-back summary should mention how far along the journey the player has gone and any supplies consumed.

#### 11.3.2 Travel leveling
Travel earns XP per edge travelled, scaled by the edge's base time cost. A longer road gives more XP than a shorter one. Higher Travel tiers reduce journey time.

### 11.4 Travel costs
Map edges own the cost of travel: time, supply costs, and any Travel level gates. These costs also apply to the NPC caravans that carry trade between realms.

The traveller owns the movement profile:
- A visiting traveller uses a base travel profile - light rations and fairly quick
- A relocating mobile estate travels according to its estate type

### 11.5 Being Away From Home
#### 11.5.1 What visitors can do
There is no visitor malus. Visitors may do any skill that is available in the realm. Visitors may contribute to the project underway in the realm. And of course, trade at the realm market.

#### 11.5.2 Bonuses and caps
Estate bonuses stay with the estate. A mobile estate that relocates with the player keeps providing its bonuses. A player who visits a realm without their estate does not receive any estate bonuses there.

Caps (limits such as inventory size and order slots) apply to the player, and travel with them everywhere.

#### 11.5.3 Inventory
There is one player inventory that the player carries everywhere, plus the market order slots. There is no estate storage, and no goods can be kept anywhere other than the player's inventory.


## 12. The Player
### 12.1 The new player
The new player should get an easy introduction to the game's mechanics. A new player should be able to join without friction, as an anonymous person with a temporary account. The new player "awakens" on Tutorial Island.

### 12.2 Tutorial Island
Two ephemeral realms, cordoned off from the rest of the game world, that teach the player to use the different skills to bootstrap themselves.
- Realm 1 - The player gathers items to create a set of clothes and a club. Then the player performs some combat to create some food. Then the player travels to Realm 2.
- Realm 2 - Intro to realm projects. The player is given a little seed gold and uses it to kick off a realm project: a raft-making site. With the site built, the player builds a raft, which is their first mobile estate, and can then travel to at least 1 realm in the actual game world.
- The seed gold is spent on the project's kickoff cost. Because the tutorial realms are cut off from the world, that gold leaves the game; the player arrives in the world with no gold (section 9.5.4).
- Before actually leaving Tutorial Island, the player is required to create an actual account
- The player should be hinted at how to do each step and should be able to complete each step in just a few action cycles

### 12.3 Player equipment
#### 12.3.1 Slots
- Standard equipment: head, chest, gloves, legs, feet
- Jewelry: neck, left arm, right arm, left ring, right ring
- Belt: carries consumable slots; may grant skill benefits
- Cape: specialized XP-bonus slot
- Weapons: left hand, right hand; a two-handed item goes into the right hand slot and disables the left hand slot
- Combat utility slot: per-cycle consumable - ammunition (Ranged), weapon oils (Melee), magic components (Magic)

#### 12.3.2 Weapons
- Melee - a one-handed weapon + shield, or two one-handed weapons, or a two-handed weapon. Can have damage flavors: piercing, bludgeoning, slashing. Optional utility slot items provide a small benefit
- Ranged - two-handed; requires ammunition in the utility slot
- Magic - a one-handed wand + focus, or a two-handed staff. Optional utility slot items have a moderate effect

Weapons modify their associated attack skill. Two-handed weapons grant larger bonuses at the cost of the off-hand slot and slower attack speed.

#### 12.3.3 Non-weapon equipment slots
1. Standard equipment - grants Defense and Vigor. Lower-tier armor is general purpose; higher-tier armor specializes toward one attack style and requires that skill's tier to wear
2. Jewelry - may modify any skill
3. Belt - holds consumable item slots and may carry minor skill benefits
4. Cape - dedicated slot for XP-bonus items
5. Utility slot - per-combat-cycle consumable for the appropriate attack style

#### 12.3.4 Main-hand tools for skilling
The weapon slot family extends to skilling tools: a main-hand axe, hammer or pickaxe that improves skill cycle speed.

#### 12.3.5 Gear durability
Gear has no durability and as such lasts forever. Acquiring gear is a milestone for the player, not an industry.
For producers, there are other items that serve as fungible trade goods required by realms.
