# Yet Another Idle Skilling Game — Combat Vision Document

**Version:** 0.2 (key-system patch: §7.2 rewritten to the ratified Exploration & Keys model)
**Scope:** The combat system — the encounter loop, combat skills and the tier multiplier, player equipment (a new modifier source spanning combat *and* skilling), hit points and sustain, combat locations and access keys, and the player-attached automation behaviors combat requires. This document deepens the economic frame that **Skills and Goods** §4.2 established and is constrained by it: whatever combat becomes, it remains a goods producer with per-combatant drop tables and a goods consumer through supply-based sustain.
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't yet support, that is a design-doc work item (§9), not a license to improvise. Siblings: **Skills and Goods** (supply side; owns the constraint this document inherits), **Market Vision** (demand/trade side), **Realm & World Vision** (the map combat locations live on). The **Exploration & Keys** vision (v0.1, now extant) owns the key system outright — §7.2 here is the combat-side application of its ratified model — and the planned **XP Curve** vision owns final tier thresholds and multiplier numbers. A future **Player QoL / Automation** vision (not yet scheduled) owns the automation-behavior surface this document only reserves (§6).

**Changes from the rough draft:** Forever-gear ratified with the market consequence named and the enchanting chase recorded as the long-term sink (§4.5); the §13.6 consumable-shape question answered as a hybrid (§5.1); ammunition exhaustion redefined as a fallback to unarmed melee rather than near-zero ranged damage (§5.2); tier multiplier defined (+5% per tier to associated total skill) and tier-gated equipment ratified (§3.3); HP regeneration set at ~20%/hour with manual re-engagement (§5.3); respawn timers settled as content-defined (§7.1); estate-attached auto-consume behaviors relocated to player-attached QoL upgrades, deferred to their own vision (§6); tools split — player tools are durable equipment, estate-worker tools remain consumed upkeep goods (§4.4, patching Skills and Goods §8.9); offline combat resolution defined as a stateful summary with a terminal state and idle-time display (§2.3).

**Changes from 0.1:** The anticipated Exploration & Keys patch (the "if the two conflict, Exploration & Keys wins" clause of §7.2) has landed. §7.2 is rewritten to that vision's ratified model: **permanent combat keys are walked back — no key is permanent**; combat keys are instanced items in the shared key family (provenance/discoverer tag, tradeable-until-bound, one-way binding on first use); expiry is **session-scoped** with drop rates as the severity-tuning knob; the interim safe subset changes from "permanent keys only" to **no keys until the instanced-item system lands**. §9.8 and §10.9 updated accordingly. No other section is touched.

---

## 1. The elevator pitch

Combat turns **time and consumables into combat xp and monster drops**, feeding the economy in both directions. Each encounter is a contest of the player's stats, equipment, and bonuses against a combatant's stats, resolved cycle by cycle: hits land or miss, damage wears down hit points, consumables burn, and when one side's hit points are exhausted the encounter ends — in loot and a respawn, or in the player retiring from the field to heal.

Combat is economically a gathering skill with risk attached: monster drop tables produce the leather, bones, and monster parts the industries want, while the fight itself consumes the food, potions, and ammunition the agrarian and alchemy industries produce. The adventurer buys bread and potions from the settled realms and sells them monster parts back — feeding the economy going *and* coming, passing the economic-role test twice.

---

## 2. The combat loop

### 2.1 Engagement

The player engages combat at a **combat location** within a realm (an inn's basement, a hunting ground, a deep cave, a bandit hideout — §7), then chooses a **combatant** to fight. The encounter is an action under the existing cycle framework: combat is the `CycleRewardStrategy` the engine's per-cycle reward seam was built for, not a parallel system.

### 2.2 The cycle

Cycle length derives from **weapon speed** plus applicable modifiers (the existing `cycle_time_pct` machinery; equipment joins the modifier sources per §4). Each cycle resolves:

1. **Hit resolution** — who hit whom, and for how much damage (§3.2's formula frame).
2. **XP award** — the player earns combat xp proportional to damage dealt, drawn against the combatant's total xp value. Damage is the xp meter; a fight the player dominates pays out quickly, a slugfest pays out over more cycles.
3. **Consumable resolution** —
   - The **utility-slot item** (ammunition, weapon oil, magic components) is consumed **per cycle**, via the existing input-consumption machinery (§5.1).
   - **Reactive consumables** (health potions, combat-buff consumables) are consumed **in response to player state** — health dropping below a threshold, a buff expiring — either by standing player instruction or by an automation behavior (§6).
4. **Terminal checks** —
   - **Combatant HP exhausted:** award loot from the combatant's drop table; wait out the respawn timer (§7.1); engage the next combatant automatically. The action continues.
   - **Player HP exhausted:** the player **retires to idle**. The action ends. Death costs nothing further — no item loss, no xp loss, no corpse run (§5.3). Failure's price is the consumables already burned and the time now spent idle instead of fighting.

### 2.3 Offline resolution and the return summary

Combat resolves lazily like every other action, but it is a **state machine, not uniform cycles**: hit points, consumable stocks, kill/respawn alternation, and possible mid-absence failure all evolve across the resolved span. When a player returns, the welcome-back summary reports:

- encounters completed and combatants defeated,
- xp earned per combat skill,
- consumables consumed (by kind),
- loot gained,
- and the **terminal state**: still fighting, or *failed out at time T* — with the elapsed idle time displayed, so the player sees exactly what their consumable budget bought and what the absence cost.

The player is returned to the combat UI regardless of terminal state. This summary is the honest ledger of combat's risk: the downside of a fight going badly overnight is visible, bounded, and never destroys anything the player didn't knowingly commit (the consumables they equipped and carried).

---

## 3. Combat skills

### 3.1 The six skills

**Melee, Ranged, Magic, Accuracy, Defense, Vigor.**

- **Accuracy + attack skill** (Melee, Ranged, or Magic) determines whether the player's hits land.
- **The attack skill** determines how much damage a successful hit inflicts.
- **Defense + attack skill** determines whether the opponent lands a hit.
- **Defense** also mitigates the damage of hits that land.
- **Vigor** determines the player's maximum hit points.

Three attack styles, three supporting skills; every fight exercises the active attack style plus Accuracy, Defense, and Vigor. Encounter design and the concrete formulas are content/design-doc work — this vision fixes only the roles above.

### 3.2 The tier multiplier

Combat skills follow the shared tier system (Skills and Goods §3), and tiers grant a **combat-effectiveness multiplier**: each tier level adds on the order of **+5% to the associated total skill contribution** in the combat formulas. Because the multiplier applies to the absolute skill value, the gap between a tier-1 and a tier-4 fighter is *super-linear*: a tier-4 magician at level 90 versus a tier-1 magician at level 15, in identical equipment, differ by both the raw skill spread and the compounding tier bonus on top of it. Tier is not just an unlock gate in combat — it is power.

The exact percentage, and whether it is uniform across all six skills, belongs to the XP Curve vision and content balance. The shape ratified here: **per-tier multiplicative bonus on the skill's contribution, compounding with the underlying level difference.**

### 3.3 Tier unlocks gate equipment

Reaching a tier threshold also unlocks the **use of higher-tier goods**: tier-3 armor requires the appropriate tier-3 skill to wear, tier-4 weapons require tier-4 in their attack style. This is the combat expression of the tier ladder's demand side — every tier climb creates a re-equipping moment, which is a primary demand driver for manufactured gear under the forever-gear rule (§4.5).

Which skill gates which slot (Defense for armor, the attack skill for weapons, Vigor for anything?) is a content-design question; the principle — **tier thresholds gate gear eligibility** — is settled here.

---

## 4. Equipment

### 4.1 Slots

- **Standard equipment:** head, chest, gloves, legs, feet.
- **Jewelry:** neck, left and right arm (bracers/bands), left and right ring.
- **Belt** — carries consumable slots; may also grant skill benefits.
- **Cape** — the specialized xp-bonus slot.
- **Weapons:** left and right hand; two-handed weapons occupy both.
- **Combat utility slot:** the per-cycle consumable — ammunition (ranged), weapon oils (melee), magic components (magic).

### 4.2 Weapons

Three types matching the three attack styles:

1. **Melee** — one-handed weapon + shield, or two-handed weapons. Damage flavors: piercing (knives, spears, rapiers), bludgeoning (maces, hammers, clubs), slashing (swords, axes). Whether damage flavor is cosmetic or interacts with combatant resistances is a content question.
2. **Ranged** — two-handed (bow, crossbow). Requires ammunition in the utility slot; exhaustion behavior per §5.2.
3. **Magic** — one-handed wand + focus, or two-handed staff.

Weapons modify their associated attack skill. **Two-handed weapons grant larger bonuses at the cost of the off-hand slot (defense) and slower attack speed** — the offense/defense/tempo triangle, expressed entirely through existing modifier arithmetic.

### 4.3 The other slots

- **Standard equipment** grants Defense (and Vigor). Lower-tier armor is general-purpose; higher-tier armor specializes toward one attack style — a tier gradient from generalist to build-defining.
- **Jewelry** may modify **any skill, including non-combat skills** — the slot family that makes equipment a global system rather than a combat subsystem.
- **Belt** holds consumable slots and may carry minor skill benefits.
- **Cape** is the dedicated xp-bonus slot.
- **Utility slot** consumables grant style-appropriate bonuses: ammunition a **large** bonus for ranged (it is nearly the style's damage), components a **modest** bonus for magic, oils a **small** bonus for melee.

### 4.4 Main-hand tools: equipment reaches skilling

The weapon slot family extends to **skilling tools**: a main-hand pickaxe, axe, or hammer that improves the speed (and potentially other properties) of the associated non-combat skill. Equipment is therefore a **modifier source for the whole game**, not a combat special case — one new source category, resolved in the same pass as development node, estate form, and upgrades (§9).

**Cross-doc clarification (patches Skills and Goods §8.9):** the "where tools sit" question splits in two. **Player tools are durable equipment** under this document's forever-gear rule. **Estate-worker tools remain consumed goods** inside the estate upkeep profile (Realm Vision §3.4) — the recurring tool *sink* lives in upkeep, not in player gear. Both halves of the original question get an answer; they were two different objects.

### 4.5 Forever-gear: the ratified durability decision

**Weapons, standard equipment, jewelry, belts, capes, and tools have no durability and last forever.** Only utility-slot items and reactive consumables are consumed.

This is a deliberate economic trade-off, made with the consequence named: **gear demand comes from population growth, tier climbs (§3.3), build diversification, and — eventually — the perfect-roll chase, not from replacement.** Manufacturing's recurring demand from combat flows through consumables (which feed agrarian/alchemy) and through the upkeep and construction sinks the other visions own; the smithing chain's combat demand is event-driven (re-equipping at tier thresholds) rather than perpetual.

The long-term answer that keeps gear demand alive is recorded now as intended direction, not a v1 feature: a later **crafting/enchanting system in which item stats roll within ranges**, making a perfectly rolled item incredibly rare and giving veterans a standing reason to craft, buy, and chase gear forever. Under that future, forever-gear stops being a saturating market and becomes an open-ended one — each item permanent, but the *pursuit* unbounded. Nothing in v1 may preclude per-item-instance stats (a watch item, §9).

---

## 5. Sustain: consumables, exhaustion, and hit points

### 5.1 The hybrid consumption model (answers design.md §13.6)

The design doc's open question — consumables per cycle vs. per damage taken — is answered as a **hybrid**:

- **Utility-slot items are per-cycle inputs**, consumed through the existing input-consumption machinery exactly like a refining recipe's inputs. This half needs no new engine concept.
- **Health and buff consumables are reactive** — consumed when player state calls for them (HP below a threshold, buff expired), under standing player configuration or automation behaviors (§6). This half is conditional per-cycle logic the current machinery does not do, and is the combat resolver's genuinely new engine surface (§9).

### 5.2 Exhaustion ends things honestly — with one graceful fallback

Sustain exhaustion follows the engine's honest-stop philosophy rather than degraded limbo, with one ratified exception:

- **Ammunition exhausted (ranged):** the player **falls back to unarmed melee** — the fight continues, resolved with the Melee skill, bare-handed effectiveness. This keeps the action alive (idle-friendly) while making the consequence real and legible: the archer who forgot arrows is now a brawler, and the return summary will show it. Unarmed melee is the universal floor every character can always express.
- **Health consumables exhausted:** nothing special happens at the moment of exhaustion — the player simply fights on without a safety net until HP resolves the encounter one way or the other.
- **Player HP exhausted:** the action ends; the player is idle (§2.2, §5.3).

The rough draft's "ammo runs out but combat continues at near-zero ranged damage" is superseded: seven offline hours of accomplishing nothing reads as punishment; seven hours of accidental fisticuffs reads as a story.

### 5.3 Hit points, death, and regeneration

- **Max HP derives from Vigor** (plus equipment).
- **Death costs nothing beyond the fight**: no item, gold, or xp loss. The price of failure is the consumables burned and the idle time that follows — visible in the return summary (§2.3). This is combat's expression of the world's tuning philosophy: failure is a *slow, visible, recoverable* setback, not a cliff.
- **Out of combat, HP regenerates** at a content-tuned slow rate — on the order of **20% of max HP per hour**. A defeated player is fully restored in a few hours and can re-engage.
- **Re-engagement is manual in v1.** Regeneration happens passively (it is timestamp math, like everything else), but resuming combat is a player action. Auto-resume-on-full-health is a natural future **automation behavior** (§6) — deliberately not a base rule, both to keep v1 simple and because "the character decides to fight again" is exactly the kind of QoL the automation surface exists to sell.

---

## 6. Automation behaviors: reserved surface, deferred vision

Combat requires a small amount of **conditional automation**: auto-consuming a health potion below an HP threshold, auto-triggering a buff. The rough draft attached these to estate upgrades; that is superseded — estates change, relocate, and go inert, and a player's combat reflexes should not flicker with their real-estate situation. **Automation behaviors attach to the player.**

This creates a new progression surface — **player QoL upgrades** — with its own questions (acquisition paths, slot or cap structure, presentation) that are **deferred to a dedicated future vision document**. This document reserves only what combat needs:

1. The engine concept is a **behavior/automation source** — distinct from modifiers, caps, and tags — whose grants are *rules the resolve loop executes*, not numbers it adds.
2. The concept should be **source-agnostic** in the engine even though v1 behaviors are player-attached, leaving room for estate-flavored automations later (a "field hospital" that auto-heals residents is too good a flavor to foreclose).
3. Combat v1 ships with, at minimum, threshold-based auto-consumption of health consumables as the proving behavior — whether as a default capability or the first purchasable QoL upgrade is the future vision's call.

---

## 7. Combat locations and access

### 7.1 Permanent locations

Combat locations are **content on realm types** — part of a development node's identity, expressed through the existing tag/availability machinery. The forest realm's hunting grounds (turkeys, stags, bears), the wasteland's orc encampment, the populated realm's inn basement (rats and spiders) — all realm flavor, all lost or transformed when the realm's node changes, with no special-case code.

**Respawn timers are content-defined per combatant:** fodder respawns in a second or two (flavor-scale, negligible throughput impact); area bosses may carry meaningfully long timers (a deliberate throughput and scarcity knob). The content designer owns the number; the engine owns making the wait exact in offline math.

### 7.2 Keyed locations — the Exploration & Keys model applied (patched in 0.2)

Some combat locations are **locked behind keys**. The key system is owned end to end by the **Exploration & Keys vision** (v0.1); this section states its combat-side application, which supersedes the 0.1 text in full:

- **Combat keys are the shared key item family** — instanced items with denormalized provenance (the discoverer's name travels on the key forever), tradeable on the unique-item market until first use, **bound and untradeable from the moment a key-gated action starts**, and persisting as inventory trophies after depletion. A key dropped by a monster and a key found by an explorer are the same object; the character whose kill dropped a loot-table key is its "discoverer."
- **No key is permanent.** The 0.1 "permanent or limited-use" rule is walked back: every key expires. Combat keys use **session-scoped expiry** — a key persists while its holder's combat session at the keyed location runs and depletes when that session ends, for any reason. (Gathering keys use exhaustion-based expiry — a cycle budget; wall-clock expiry is used by neither, by design: key life is a function of *use*, which lazy resolution handles natively.)
- **Session expiry is severe by design; drop rates are the tuning knob.** A rarer key granting one full overnight session is a legible, tunable prize — the expiry rule stays fixed and content tunes value through scarcity.
- A key is **specific to the realm** it opens content in. **If the realm's development node changes, its keys are marked depleted** — with one grace: a key whose holder has an active action running against it survives until that action stops. Access remains realm-state-scoped, never a permanent per-character unlock, in continued compliance with design.md §10.

**Interim rule (changed from 0.1):** the previous safe subset — shipping permanent keys ahead of the shared model — no longer exists, because permanent keys no longer exist. **Combat content ships no keys until the instanced-item system lands** (Exploration & Keys work items #1–#3). Combat locations are unaffected: they ship unkeyed under the ordinary tag machinery of §7.1, and keyed variants arrive with the key system.

---

## 8. The economic-role test

| | Eats | Feeds |
|---|---|---|
| **Combat** | reactive consumables (food, potions — agrarian/alchemy demand), per-cycle utility items (ammunition, oils, components — manufacturing demand), gear at tier thresholds (event-driven manufacturing demand, §4.5) | monster parts, leather, bones back to the industries; keys to further combat/gathering access; combat xp |

Both halves are load-bearing, and both are now concrete:

- **The consumable sink scales with activity**: how much combat the world's players do directly drives agrarian and alchemy demand. Ammunition makes ranged the most industry-coupled style — an archer is a standing customer of the fletcher.
- **The drop tables are gathering-equivalent supply**: every combatant is a walking resource node whose loot the industries want.
- **The gear demand is event-driven, not perpetual** — named honestly per §4.5, with the enchanting chase as the recorded long-term answer.

---

## 9. What this changes in the design doc (work items, not yet decisions)

Roughly in order of when they bite — all targeting the Phase 6 window unless noted:

1. **Combat resolver as a stateful `CycleRewardStrategy`.** The seam exists (Phase 3); the resolver is the largest single piece: HP for both sides, hit/damage formulas, kill → loot → respawn-wait → re-engage alternation, consumable triggers, and mid-absence failure — all resolved lazily and segmented, with `active_actions.meta` carrying encounter state. The offline story of §2.3 (summary + terminal state + idle time) is the acceptance criterion.
2. **Player combat state**: six new skills (content, mostly free), plus **persistent current-HP** with timestamp-based regeneration (~20%/hour) — a new piece of character state resolved like everything else.
3. **Equipment as a modifier source** — the new source *category*: equipped-item tables, slot rules (two-handed exclusion, style-appropriate utility items), tier-gating on equip (§3.3), and equipment joining the modifier/caps resolution pass. Global scope (tools, jewelry affecting non-combat skills), so the resolution work serves skilling too.
4. **Tier multiplier hook** in the combat formulas (+~5%/tier on associated skill contribution) — numbers owned by the XP Curve vision.
5. **Reactive consumable machinery** — conditional per-cycle consumption driven by player state; the genuinely new half of the hybrid model (§5.1).
6. **Behavior/automation source concept** — source-agnostic engine shape, v1 player-attached, minimum viable behavior = threshold auto-heal (§6). Full surface owned by the future QoL vision.
7. **Ranged→unarmed fallback** — a style-switch rule inside the resolver (§5.2); small but novel (an action changing its own effective skill mid-resolve).
8. **Keyed-location availability** — key-gated actions per the ratified Exploration & Keys model (§7.2): held-instance availability checks, binding on action start, session-scoped depletion for combat keys, realm-transition sweep with the active-action grace rule. **Sequencing changed:** depends on the instanced-item system (Exploration & Keys work items #1–#3), so keyed combat content ships after that lands — Phase 6 ships locations unkeyed. Ledger item 13.8 is superseded by the concrete shapes in that document's §9.
9. **Watch item — per-item-instance stats.** Nothing in v1 may assume items are fully fungible per item-id forever; the future enchanting/rolled-stats system (§4.5) will need item instances. (Inventory today is `(character_id, item_id, quantity)` — the future split is flagged, not built.)
10. **Cross-doc patch — Skills and Goods §8.9**: tools split into durable player equipment (this doc) and consumed estate-upkeep goods (realm vision); the economic-role table's "gathering eats trivial tools" becomes a one-time equipment purchase plus the estate-side recurring sink.

---

## 10. Open questions

1. **Concrete combat formulas.** Hit chance, damage, mitigation — the exact functions of (Accuracy, attack skill, Defense, equipment, tier multiplier). Design-doc/content work; this vision fixes only the roles (§3.1) and the tier-multiplier shape (§3.2).
2. **Tier multiplier scope.** Uniform +5% across all six skills, or differentiated? Do Accuracy/Defense/Vigor tier at all, or only attack styles? Owned by the XP Curve vision with content balance.
3. **Slot-gating map.** Which skill's tier gates which equipment slot (§3.3). Content design.
4. **Damage flavors.** Do piercing/bludgeoning/slashing interact with combatant resistances, or are they cosmetic in v1? Content design.
5. **Encounter and combatant design.** Stat blocks, drop-table composition, xp values, location curation per realm archetype. Content design, constrained by the economic-role test.
6. **Buff consumables.** What the combat-modifying consumable family does (damage buffs? accuracy? regen-in-combat?) and its reactive triggers. Content design over the §5.1 machinery.
7. **Multi-combatant encounters.** v1 assumes one combatant at a time. Packs/waves would be a resolver extension — deliberately out of v1 scope, noted so the resolver isn't built in a way that makes it impossible.
8. **Auto-resume after regen.** Deferred to the QoL/automation vision as a candidate behavior (§5.3).
9. **Key expiry alignment.** **Settled in 0.2:** the Exploration & Keys vision (v0.1) ratified the model and §7.2 is patched to it — session-scoped expiry for combat keys, no permanent keys, shared instanced-item family. Residuals (combat-key drop rates as the severity knob) are content/balance, tracked in that document's open question #5.
10. **PvP.** Entirely out of scope for this vision and for v1; nothing here is designed for or against it.
