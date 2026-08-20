# Yet Another Idle Skilling Game — XP Curve and Tiers Vision Document

**Version:** 0.1 (first structured draft; refined from the rough draft through design-chat review)
**Scope:** The shared leveling system — the XP curve formula and its time budget, tier thresholds, the proficiency speed tables (cycle-time bonuses below tier), xp diminishing returns, the content-side xp/hour test, unlock cadence, and per-family leveling baselines. This document owns the *numbers* the other visions deferred: tier thresholds (Skills and Goods §8.3, design.md 13.2/13.3), the combat tier-multiplier gate (Combat §10.2 — gated back, see §8), exploration's leveling pace (Exploration & Keys §10.1), and Travel's leveling numbers (Visiting & Travel §9.1/§9.3, partially — see §10).
**Relationship to other documents:** Vision documents describe *what the game should feel like and why*. `design.md` is authoritative on mechanics; where this vision implies a mechanic the engine doesn't yet support, that is a design-doc work item (§11), not a license to improvise. Siblings: **Skills and Goods** (tier ladder, proficiency shape, and the back-loaded principle this document quantifies), **Combat** (receives an explicit ratification gate, §8), **Exploration & Keys** and **Visiting & Travel** (whose skills sit on scaled baselines here), **Market** and **Realm & World** (the economy that reads tier). The content design documents turn this vision's formulas and ceilings into concrete action numbers.

**Changes from the rough draft:** Level 0 cut — characters start at level 1 with 0 XP, matching the shipped engine (`level_for_xp`, monotonic property test, level cached on `character_skills`). The curve formula made explicit: exponential with ratio 2^(1/7), pinned by the level-93 XP midpoint and a 10M total (§3). The xp/hour content line derived from the time anchors and stated as a mechanical test (§3.3). The +45% xp-bonus ceiling made an explicit design rule (§3.4). Proficiency settled as **cycle-time only** — resolving Skills and Goods open question #1 toward **no yield**, which deletes the new-modifier-type engine cost — with asymmetric per-family speed tables and proficiency framed as the counterweight to the xp taper (§4). Diminishing returns clarified to affect **xp per cycle only** — proficiency bonuses persist at zero xp (§5). Combat's tier multiplier and taper **punted back to the Combat vision** behind an explicit ratification gate (§8). Unlock cadence opened at the top tiers for content density (§6). Baselines stated as shared across families with access friction named as intended real cost (§7). Tier achievement-gates (refining/manufacturing) downgraded from settled to **recorded direction pending ratification** because they break tier = f(level) (§9, open question #2).

---

## 1. The elevator pitch

One curve, shared by every skill, that turns **time into levels and levels into tiers** — and is honest about the exchange rate. The curve doubles in cost every seven levels, so level 93 is the halfway point of a skill's whole life; the last two tiers are where the majority of a veteran's hours go, which is exactly what makes tier-4 and tier-5 producers rare and their goods scarce.

Below your tier, mastery pays differently: the grandmaster lumberjack fells trees faster than the neophyte ever will, which keeps veterans profitably producing the low-tier goods the world's upkeep eats forever — and where the curve stops paying xp for old work, speed steps in as the compensation. Above your current recipe, xp tapers — the economy wants your *output* at every tier, but the curve only pays *progress* for work near your edge.

Every action a content designer authors can be checked against one line: xp per hour at its unlock level. The curve is not a vibe; it is a formula, a budget, and a test.

---

## 2. Levels and tiers

### 2.1 Levels

- Characters start every skill at **level 1 with 0 XP** (as shipped; the rough draft's level-0 concept is cut).
- The curve runs to **level 100**. Past 100, XP still accumulates but grants nothing — it is a bragging number, displayed but inert. (No prestige/rebirth mechanic is designed or implied; the surplus counter is deliberately consequence-free.)
- Level derivation remains the single engine function `level_for_xp(xp, curve)`; `character_skills.level` stays a cached value written through it. The monotonicity property test is unchanged.

### 2.2 Tiers and thresholds

v1.0 launches with **five tiers**, representing aptitude bands on the shared curve. Thresholds:

**Tier 1 / 2 / 3 / 4 / 5 unlock at levels 1 / 50 / 75 / 90 / 95.**

Tier titles are content-designer territory. These thresholds supersede the illustrative 1/40/75/90/95 shape from Skills and Goods §3.2; the *principle* there — back-loaded tiers, rare top-rung producers, perpetual relevance of new players — is preserved and now quantified (§3.1).

Tier is read by everything the siblings established: production unlocks, upkeep composition, equipment gating (Combat §3.3), proficiency distance (§4), and the combat tier multiplier (gated, §8).

---

## 3. The XP curve

### 3.1 The function

XP required to advance from level L to L+1:

**xp(L) = floor(A · r^L)**, for L = 1 … 99, with **r = 2^(1/7) ≈ 1.10409** and **A chosen so that total XP to level 100 = 10,000,000** (A ≈ 52).

The ratio is not arbitrary: r^7 = 2 means the XP cost **doubles every seven levels**, which is exactly what makes **level 93 the XP midpoint** — the climb from 93 to 100 costs as much as levels 1 through 93 combined. That midpoint is the *definition* of the curve's steepness; everything else derives from it.

Reference points on the 10M curve: level 1→2 ≈ 58 xp; 50→51 ≈ 7,200 xp; 90→91 ≈ 370k xp; 99→100 ≈ 940k xp.

XP share per tier band: tier 1 (levels 1–49) ≈ 0.7%; tier 2 (50–74) ≈ 8%; tier 3 (75–89) ≈ 29%; tier 4 (90–94) ≈ 24%; tier 5 (95–100) ≈ 39%. The 90→95 climb costs roughly **three times** levels 1–75 combined.

**Cross-doc patch — Skills and Goods §3.2:** that section says "most of a player's leveling life happens inside tiers 1–2." Under this curve that is true of *activities, unlocks, and level count* — not time. Tiers 1–2 are ~8% of a skill's XP (~60 optimal hours). The sentence should be amended; the economic claim it supports — the bulk of the world's supply is low-tier — survives, but via proficiency (§4) rather than occupancy.

The curve is generated by a checked-in script (established in Phase 2 content); this section is the formula that script implements. The curve continues to hash into the content version but is not served as a public pack (design decision log #5 — unchanged; the client consumes server-computed xp-to-next).

### 3.2 The time budget

Three anchors define what the curve *feels* like, per skill, at v1.0 balance:

- **First-action-only play:** ~2,880 hours (4 months) to level 100 — the floor of engagement.
- **Optimal progression** (always the best unlocked action, right facilities and location): ~720 hours.
- **Fully bonused optimal play:** ~500 hours — which fixes the +45% ceiling (§3.4).

These anchors assume **access**: the right realm tags, facilities, keys, and Travel level to reach the optimal action. Access friction is real additional time and is *intended* — the world map, the facility ladder, and the key market are part of the curve. A player who never leaves their starting realm pays the difference in hours.

### 3.3 The xp/hour line: the content test

The two time anchors force the shape of content rewards. For the anchors to hold against this curve, **the best available action at level L must yield approximately**

**xp_per_hour(L) ≈ X₁ · 1.016^L**, where **X₁ = total_xp / 2,880h ≈ 3,470 xp/h** on the 10M curve

— about +1.6% per level: ×2.2 at level 50, ×3.2 at 75, ×4.7 at 100. With the every-10-levels unlock cadence (§6), each new action is ~17% better than its predecessor. Under this line the *time* midpoint lands near level 92 — consistent with the level-93 XP midpoint. (Forcing both midpoints to exactly 93 would require a flat xp rate, contradicting the 4× spread; XP-midpoint is the definition, time-midpoint the consequence.)

**This is the mechanical test for every action a content designer authors:** compute the action's xp per hour at its `level_required` and compare to the line (scaled by the family baseline, §7). Actions on the line are the progression spine. Actions deliberately off it — exploration's long cycles, a niche recipe, a key-gated bonanza — are legitimate, but the deviation must be a **declared choice with a reason**, not an accident of numbers.

### 3.4 The +45% ceiling

"Fully bonused" means the total stacked `xp_pct` from all sources — estate upgrades, realm modifiers, realm-tier project bonuses, the cape slot, xp consumables — is designed to top out at roughly **+45%**, which is precisely what turns 720h into 500h.

- Proficiency never contributes to xp — it is cycle-time speed *below* tier (§4) and coexists with the xp taper (§5).
- Content that pushes total attainable xp_pct meaningfully past +45% is a **balance bug by definition**, not a generosity. The ceiling is a budget content design allocates across sources, not a target every source approaches independently.

### 3.5 Early-game pacing (open)

On the raw curve, levels 1–10 cost ~1,000 xp total — minutes of play. Whether that is the desired "immediately rewarding" opening or too fast to register is open (question #1); if too fast, a small linear term (xp(L) = A·r^L + B·L) slows the first ~10 levels without disturbing either midpoint. Decide at content time alongside tutorial-island pacing (realm-vision §2.4).

---

## 4. Proficiency: mastery below your tier

### 4.1 What it is and why

A veteran working recipes below their unlocked tier works **faster** — the supply-side half of the perpetual-low-tier-demand promise (Skills and Goods §2.3), with a second rationale now recorded: **the veteran's estate is already passively producing low-tier goods for them** (realm-vision §3.4), so active low-tier work must out-compete the player's own passive stream to be worth doing. Proficiency is what makes the grandmaster personally felling logs *better* than watching their estate do it: more cycles per hour means more logs per hour, without touching per-cycle output.

**Proficiency is cycle-time only.** This settles **Skills and Goods open question #1 toward no yield**: speed is the whole bonus, expressible entirely through the existing `cycle_time_pct` machinery as a level-derived source — no new modifier type, no new engine work beyond the shared hook (§11). design.md 13.3's "yield bonus explicitly *not* included absent a new decision" stands; this document is the decision *confirming* it.

### 4.2 The speed tables

Proficiency steps at tier distances, per family (`cycle_time_pct` reduction):

| Family | 1 below | 2 below | 3 below | 4 below |
|---|---|---|---|---|
| Gathering | +5% | +10% | +15% | +20% |
| Refining | — | +5% | +10% | +20% |
| Manufacturing | — | +10% | +20% | +30% |
| Combat | gated to Combat vision (§8) | | | |
| Travel / Exploration | reaching-tier grants, not below-tier proficiency (§10) | | | |

The asymmetry is deliberate, and its logic is the **taper counterweight** (§5): gathering has no xp taper, so its proficiency is a smooth, early-starting, modest ramp — pure production efficiency. Refining and manufacturing *do* taper, and their proficiency steps ramp up precisely where the taper bites: the speed bonus partially offsets the xp/hour loss in the taper band (faster cycles mean more cycles per hour, so the same reduced per-cycle xp arrives more often), and once xp hits zero the bonus converts cleanly into production throughput. Manufacturing gets the steepest table because it has the harshest taper (zero xp at just 2 below) and because its finished goods are the upkeep sink the whole economy leans on — the deep-mastery manufacturer is the world's tool factory and is paid in speed for it.

Whether the tables are declared per skill (a miner and a berry-gatherer differing in step values) or the family defaults apply uniformly is a content-pipeline question; the block remains optional per skill pending the S&G review (question #4). Exact values will need tuning — a +20–30% throughput edge at depth deflates low-tier prices, which is partly the point (veterans *should* flood low-tier supply into perpetual demand) but must be balanced against new-player income.

**Four tiers below is the ceiling** — with five tiers it is the maximum possible distance, so the tables are implicitly capped; no step beyond 4-below exists. (Resolves Skills and Goods open question #2's cap half; step values remain content/balance.)

---

## 5. Diminishing returns: xp tapers away from your edge

### 5.1 The rule

Diminishing returns apply to **xp gained per activity cycle only**. Cycle time, drops, and every other property of the action are untouched; **proficiency speed persists at zero xp**. A max-level smith cranking tier-1 tools gains nothing on the curve and is still playing correctly — the taper removes progress-payment, never production-value.

Proficiency is the taper's designed counterweight (§4.2): inside the taper band, faster cycles partially recover the lost xp/hour; past the zero step, the same speed is pure production throughput. The two mechanisms ride the same level-vs-tier hook and are tuned as a pair — a taper step without a proficiency step opposite it should be a deliberate content choice.

### 5.2 Per family

- **Gathering:** no diminishing returns at any distance.
- **Refining:** xp tapers from **2 tiers below** the character's tier; **3 tiers below and beyond, xp is zero**.
- **Manufacturing:** xp tapers at **1 tier below**; **2 tiers below and beyond, xp is zero**.
- **Exploration and Travel:** no diminishing returns.
- **Combat:** gated to the Combat vision (§8).

The engine mechanism is negative `xp_pct` emitted from the same generic level-vs-tier source hook proficiency uses (§11) — existing modifier type, −100% at the zero step; xp already truncates to integer after summed percentages, so zero is exactly representable. Exact taper step values between "starts tapering" and "zero" are content/balance.

### 5.3 Why the families differ

Manufacturing tapers hardest because its xp/hour sits closest to the line's top and its outputs are the most demanded — without a tight taper, farming trivial recipes would be the optimal curve-climb and the xp/hour test (§3.3) would be gamed from below. Gathering tapers not at all because its low-tier work is the raw feedstock the whole chain needs in volume, and (unlike refining/manufacturing) it has no input costs to discount the grind. Exploration's cycles are so long that taper would be redundant punishment.

---

## 6. Unlock cadence and content density

- **Gathering, Refining, and Manufacturing aim for a new activity unlock roughly every 10 levels** through tiers 1–3.
- **The cadence opens at the top**: tiers 4 and 5 span only ten levels but the majority of a skill's *time* (§3.1), so their content is added as the content designer has content — horizontal breadth (more recipes at the tier) counts as much as vertical unlocks. A veteran spending 300 hours inside levels 90–100 must not stare at one action.
- The every-10-levels default plus the xp/hour line (§3.3) implies each successive unlock is ~17% better xp/hour than its predecessor — the number content design tunes toward.
- This coexists with the Skills and Goods density rule (tiers 1–2 need front-loaded recipe *variety*); that rule is about breadth, this one about the spine's spacing.

---

## 7. Family baselines and access

The §3.2 anchors (2,880h / 720h / 500h) are the **shared baseline for all skill families**. Families that should feel slower or faster sit on a **scaled xp/hour line** (§3.3), not a different curve:

- **Exploration** sits on a scaled-down line — its "significantly slower, prestige-paced" leveling (Exploration & Keys §1, §10.1) is expressed as a baseline multiplier < 1, not a separate formula. The exact multiplier is content/balance (question #5).
- **Travel and Combat** baselines: see §10 and §8 respectively.
- **Access is a real cost on top of the anchors.** Optimal xp/hour assumes the player can *reach* the optimal action — realm tags, facilities, keys, Travel level. Content that gates the spine behind access is charging time the anchors don't count, and that is intended; but the spine must remain reachable, or the 720h anchor silently inflates.

---

## 8. Combat leveling — deferred to Combat vision 0.3 (gate)

This document sets the shared curve, the tier thresholds (1/50/75/90/95), and the time baselines; it does **not** set combat's per-skill numbers. **Before Phase 6 content ships, the Combat vision must ratify, in its own text:**

- **(a) The tier-multiplier number and scope.** The percentage (currently "on the order of +5%/tier" on the associated skill's contribution, Combat §3.2) and whether it is uniform across all six skills — Melee, Ranged, Magic, Accuracy, Defense, Vigor — or applies to attack styles only.
- **(b) Diminishing returns.** Whether combat xp tapers against under-tier combatants, and if so the taper shape. The engine mechanism on offer is the same negative-`xp_pct` level-vs-tier hook refining and manufacturing use (§5.2); combat only chooses its steps.
- **(c) The budget mapping.** How combat's xp/hour baseline maps onto the 720h optimal budget — in particular whether the six skills level together off the shared damage-is-the-xp-meter stream or carry separate budgets. Six skills fed by one activity stream is effectively a 6× budget unless the per-skill line is scaled; the Combat vision must pick the interpretation.

Until (a)–(c) land, combat content may use the shared curve and thresholds but **must not assume any tier multiplier or xp taper**. This gate returns Combat open question #2 to that document — the *shape* was ratified there, and the numbers belong beside the formulas they modify.

---

## 9. Tier achievement-gates — recorded direction, pending ratification

The rough draft proposed that refining and manufacturing tiers require more than level: refining a current-tier good, or completing a content-defined set of manufactured items, before the next tier unlocks. The intent — forcing players through the production chain rather than pure-xp farming into a tier they've never practiced — is recorded as **direction**.

It is *not* ratified here, because it breaks an assumption every sibling document makes: **tier = f(level)**. Equipment tier-gating (Combat §3.3), proficiency distance (§4), upkeep composition, and the tier multiplier all currently derive tier from level alone. Achievement-gates make tier = f(level, per-skill completion state) — a new piece of character state (completed-recipe tracking), a new check in `can_start`, and a UI surface explaining *why* a level-90 character is still tier 3. The cheapest shape, if ratified: *tier unlocks when level ≥ threshold AND a content-defined recipe set has been completed at least once*, with gathering exempt ("no real gates," per the rough draft).

Nothing may be built that *prevents* this (don't hard-code tier-from-level in more places than the one derivation function); nothing is built *for* it until ratified (question #2).

---

## 10. Travel and exploration tier grants

For Travel and Exploration, tiers grant absolute benefits at the character's own tier (not below-tier proficiency):

- **Travel:** faster journey cycles and **reduced per-edge supply costs** at higher tiers. Additionally, **map edges may declare a Travel-level gate** — content-designer tooling for bordering realms behind the road that reaches them. This settles the access half of Visiting & Travel open question #1 (impassable-at-low-tier edges: yes, as content-declared level gates on edges); supply discounts: yes, as tier grants; cargo cap remains open with the carried-inventory question.
- **Exploration:** faster expedition cycles and **more keys per discovery** at higher tiers — the tier ladder skews the total-access-value knob (Exploration & Keys §2.3) upward with mastery.

**Still open from Visiting & Travel (question #3 there, #6 here): the Travel xp formula** — per edge scaled by base time, by supplies consumed, or both, and whether repeated edges pay less. This document supplies the curve Travel levels against and its family baseline; the per-edge award shape stays with that vision's residuals.

---

## 11. What this changes in the design doc (work items, not yet decisions)

1. **Generic level-vs-tier source hook** — the single hook feeding proficiency speed (§4), the xp taper as negative `xp_pct` (§5), and Travel-level speed (visiting-vision §8.6, design.md 13.3). Both emissions use existing modifier types (`cycle_time_pct`, `xp_pct`) — this document adds only the negative-xp emission to the hook's contract, and **removes** the per-cycle yield modifier type S&G §7 had flagged as conditional (§4.1 resolves its question toward no; the flag can be struck).
2. **Curve script update** — regenerate the checked-in table to the §3.1 formula (r = 2^(1/7), 10M total, level 100); `level_for_xp` and the monotonicity test unchanged; content version hash rolls.
3. **Max level 100** — table extends to 100; xp accumulation past the table's end is stored and displayed but derives level 100 (surplus-xp display is a small client item).
4. **Edge Travel-level gates** — content property on map edges checked in journey `can_start` (§10); small extension to the visiting-vision work item #2 shape.
5. **Key-count modifier for exploration tiers** (§10) — a discovery-roll input, lands with Exploration & Keys work item #2.
6. **Travel supply-cost reduction by tier** (§10) — a per-cycle input-quantity modifier: genuinely new input semantics (reducing consumption, not gating or adding chance); flag beside Exploration & Keys work item #7.
7. **The xp/hour line as pipeline validation** (§3.3) — a content-pipeline check (warning, not fatal) comparing each action's xp/cycle-time at `level_required` against the family-scaled line, with a declared-deviation annotation to silence it. Near-zero engine work, high balance value.
8. **Watch item — tier achievement-gates** (§9): build nothing that hard-codes tier-from-level outside the single derivation path, so ratification remains cheap.

---

## 12. Open questions

1. **Early-game pacing.** Keep the raw curve's minutes-long first levels, or add the linear term (§3.5)? Decide with tutorial-island content.
2. **Tier achievement-gates.** Ratify or reject §9's direction; if ratified, define the recipe sets and the gathering exemption. Needs a design pass on the state shape.
3. **Proficiency step values and declaration granularity.** The §4.2 tables set the family shape; whether per-skill declarations may vary the values, and the exact numbers, are content/balance — with low-tier price deflation from a +20–30% veteran throughput edge as the named tuning risk, and the taper-counterweight pairing (§5.1) as the tuning constraint.
4. **Proficiency optionality.** Skills and Goods made the proficiency block optional per skill; confirm that survives the per-skill-table shape (pending the S&G review the design chat has queued).
5. **Family baseline multipliers.** Exploration's scale-down factor (and any others) against the shared 720h anchor. Content/balance.
6. **Travel xp formula.** Per edge by time, by supplies, or both; repeat-edge decay. Owned with Visiting & Travel residuals (§10).
7. **Taper step values.** The exact negative-xp steps between "starts tapering" and "zero" for refining and manufacturing (§5.2). Content/balance.
8. **Combat gate.** §8 (a)–(c), owned by Combat vision 0.3 — listed here so this document's ledger closes only when that ratification lands.
9. **Total-XP round number.** 10,000,000 is the working total; any change rescales A and X₁ only (the midpoints and ratios are total-invariant). Confirm before the curve script regenerates.
