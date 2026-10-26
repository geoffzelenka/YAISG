# Yet Another Idle Skilling Game — Technical Design Document

**Version:** 0.8 — standalone rewrite aligned to `the-vision.md`
**Supersedes:** design v0.7 in full. Earlier vision documents (`realm-vision`, `market-vision`, `skills-and-goods-vision`, `inter-realm-economy-vision`) are no longer authorities; `the-vision.md` is.
**Code baseline:** v0.5 as shipped (Phases 0–4). Nothing from the old Phase 5 onward has been built.
**Scope:** engine mechanics, data model, API and build order. Content (specific goods, actions, realms, numbers) stays with the content designer; every number in this document marked *default* or *illustrative* is a content setting, not a constant.

## 0. How to read this document

Every section carries one of three status marks. The implementation breakdown should treat them differently.

| Mark | Meaning |
|---|---|
| **[SHIPPED]** | Exists in the v0.5 code and stays as it is. Described here so the document stands alone. |
| **[CHANGE]** | Exists in the v0.5 code and must be altered. The section says what changes. |
| **[NEW]** | Not built. |

Rules used to write this version:

- Where `the-vision.md` and v0.7 disagree, the vision wins.
- Where the vision is silent, v0.7 detail is kept. Each such carry-over is listed in §2.2.
- Development data may be wiped. No backfill is designed; migrations may reset state.
- Vision section numbers are cited as **V§n**. The traceability table in §28 maps every vision section to a design section.

---

## 1. Overview and pillars

A multiplayer, web-based idle skilling game. Players train skills in real time through timed action cycles, gather and make goods, and trade. The world is one shared map divided into realms. Each realm has a type, a tier, stores of goods, a gold treasury and a market, and must be kept supplied or it decays. Every player has an estate, mobile or fixed.

**Engineering pillars**

1. **Server-authoritative.** All progression is computed on the server. Client timers are cosmetic.
2. **Content is data.** The engine knows mechanics and never hardcodes content. New *sources* of a bonus, cap or tag are content; new *types* are engine changes.
3. **Offline progress by timestamps.** No per-player background loops. A character's state is resolved lazily when it is read. Realm-scale processes are resolved lazily and idempotently from `last_tick_at`; one scheduled job guarantees they also advance in realms nobody is reading.
4. **Conservation.** Goods come only from skill actions and estate production. Gold comes only from mints. Every transfer is a move between two named holders, and the test suite checks it.
5. **Simple first, swappable later.** SQLite for development, PostgreSQL in CI and production; one monorepo.

---

## 2. Reconciliation with the vision

### 2.1 What the vision changes

| # | Area | v0.7 / shipped | v0.8 | Section |
|---|---|---|---|---|
| R1 | XP curve | Cumulative `floor(100·1.12^(L−2))`, max level 99 | Per-level `floor(A·r^L)`, `r = 2^(1/7)`, 10,000,000 XP total, max level 100 | §5 |
| R2 | Tiers | Not defined | Five tiers at levels 1 / 50 / 75 / 90 / 95, driving proficiency and XP taper | §5.3, §8 |
| R3 | Bonus stacking | Additive within a bonus type across all sources | Additive within a source, multiplied across five sources; XP bonus capped at +45% | §7 |
| R4 | Skill categories | Gathering, refining, crafting | Gathering, refining, manufacturing, combat, exploration, travel | §6.1 |
| R5 | Realm development | Graph nodes, edges that accumulate progress, edge awards | Projects grant tags; a realm upgrade needs a set of tags and a weighted vote | §12 |
| R6 | Projects | Many open at once, contribute from anywhere, tiers with cap bonuses | One active project per realm, kickoff cost, presence required, build phase, idle erosion, failure cooldown | §12.3 |
| R7 | Decay effect | Deferred (`shed()` handler, ledger 13.4a) | Specified: unwind the tag stack, most recent first, then the tier | §14.7 |
| R8 | Remoteness | A per-realm price level `M[realm]` on both sides of the quote | A property of a pair of realms. No distance term at a realm's own market | §15, §16 |
| R9 | Estates | Forms on one mobility axis, relocation paid in gold | Mobile or fixed. Fixed estates never move. Build, buy, surrender. Production goes to realm stores | §13 |
| R10 | Relocation | Endpoint with instant and delayed variants, gold charge | A journey is a Travel skill action, one cycle per map edge, paid in time and supplies | §11 |
| R11 | Presence | Current realm = home realm (interim) | `current_realm` is real; visitors have no malus | §11.2 |
| R12 | Gold creation | None designed; characters started with gold | Mints only. New players arrive with no gold | §14.8, §18 |
| R13 | Combat | Skeleton deferred to a combat vision | Six skills, two XP streams and pools, stance, consumables, stepped offline resolution | §10 |
| R14 | Exploration | Deferred; watch item | Keys as instanced items, a key market, invalidation on realm transition | §19 |
| R15 | Equipment | None | Slots, belt and utility consumables, skilling tools, no durability | §9 |
| R16 | New player | `POST /characters` with a chosen starting realm | Guest account, two isolated tutorial realms, raft, forced registration before leaving | §20 |
| R17 | Realm procurement between realms | Split by deficit weighting | In order of largest draw, cheapest delivered unit, nearer realms preferred | §16 |

### 2.2 v0.7 detail kept where the vision is silent

- **Order expiry** on the global market, and the retention purge of closed orders (§17).
- **The order row is the slot**; inventory caps gate collection, never fills (§17).
- **Shortfall display** (v0.7 "needs"): a realm that wants a good and cannot pay shows the shortage without a tradeable bid (§15.5).
- **Treasury health band** in five buckets with hysteresis; the raw treasury balance is never exposed (§15.5).
- **Per-good bid budgets**, so the first seller of a tick cannot silently empty every other published bid. Kept for the realm's own market only; trade between realms follows the vision's order (§15.4).
- **Treasury gift** endpoint (§15.6).
- **Integrated pricing**: a trade is priced by integrating the curve over its quantity (§15.2).
- All shipped behaviour not touched by §2.1: lazy resolve, offline cap semantics, reward feed, content hashing, auth, error envelope.

### 2.3 Decisions this document makes that the vision does not state

These are the calls made to close gaps. Each is revisable; the breakdown session should treat them as settled unless changed here first.

| # | Decision | Why | Section |
|---|---|---|---|
| D1 | The +45% cap is applied to the combined **XP** bonus. Cycle speed is not capped by the engine; a content lint reports any skill whose best XP × speed stack exceeds the 500-hour anchor. | V§3.3.3 names it an XP bonus cap, and tier proficiency (a speed bonus) "never affects XP". | §7.3 |
| D2 | A speed bonus divides cycle time: `cycle = base / S`. Replaces the shipped percentage subtraction. | Multiplying sources stays well behaved and can never reach zero. | §7.2 |
| D3 | `xp(1)` is 57, not the vision's 58. The vision's four reference points are rounded; exact values are in §5.1. | `floor(A·r)` with the A that makes the total exactly 10,000,000. | §5.1 |
| D4 | Tags persist across a tier-up. A realm regresses when it holds no tag acquired at its current node; tags that survive a regression then count as belonging to the lower node. | Gives the vision's order "tags, most recent first, then the tier" at every tier, not only the top one. | §14.7 |
| D5 | A vote passes when yes-weight is strictly greater than no-weight. No votes cast, or a tie, fails. | V§7.7.2: no quorum, and one vote against with all others abstaining fails. | §12.5 |
| D6 | No vote may be called while a project is active, and no project may be kicked off while a vote is open. | Avoids a project completing into a realm that is already changing. | §12.5 |
| D7 | Tutorial realms are per-player instances, created with the character and deleted on departure. | "One active project per realm" and a persistent tag cannot be shared by every new player. | §20 |
| D8 | Building or buying a fixed estate replaces the player's mobile estate. Its upgrades are lost. | One estate per player for now (V§8); the schema already allows more later. | §13.4 |
| D9 | Upkeep, reserve, cap and price are tracked per **demand line** (an item, or a goods class such as "tier 1 logs"), while stores are held per item. | V§5.1 requires upkeep that accepts any member of a class; the mint needs the same for bullion. | §14.2 |
| D10 | A realm takes part in caravan trade only while it holds a caravan-access tag. | V§7.7: a road is "the first step to connecting a wilderness realm to the rest of the world". | §16.1 |
| D11 | In the Faltering stage facility tags are suspended and bonus tags weakened; access tags (market access, caravan access, mint) keep working. | Suspending the mint would cut a starving realm's only source of gold. | §14.6 |
| D12 | Combat hit, damage and mitigation formulas. | The vision defines the contest and the XP streams, not the arithmetic. | §10.3 |
| D13 | The key market uses the same market-access gate and seller tax as the global market, with its own listing cap. | V§10.5 says only that the seller still pays a tax. | §19.5 |
| D14 | Kickoff gold and upgrade fees go to the realm treasury. Goods paid at kickoff are consumed. | V§9.5.4 implies it: tutorial kickoff gold leaves the game only because the tutorial realm is cut off. | §12.3 |
| D15 | Collecting from an order slot needs market access, as creating an order does. Cancelling does not. | Otherwise goods bought in town can be collected in the wilderness, which removes the cost V§9.2.5 intends. This narrows V§9.2.6. | §17.5 |

### 2.4 One finding about the vision

V§9.5.1 says a mint with scarce bullion "stops creating gold and starts removing it", and V§9.5.3 says a coinage multiple below 1 "runs every mint backwards". Under the stated mechanics neither removes gold from the world. Coining always adds `reference price × multiple` to a treasury, and the gold a realm paid for the bullion went to a player, where it still exists. What a losing mint does is drain its own realm's treasury until that realm can no longer buy bullion, which stops the minting. The throttle works as described; it is a brake, not a sink.

The game therefore has three real gold sinks: tutorial kickoff, abandoned accounts, and the tax burn share that ships at zero. If a stronger sink is wanted, the burn share (§17.4) and the caravan-fee burn (§16.3) are the two levers already wired in.

---

## 3. Technology and architecture [SHIPPED]

| Concern | Choice |
|---|---|
| Services | Two FastAPI services (Python 3.12): **auth** and **game**. Each has its own database and Alembic history. |
| Auth | Argon2 passwords, RS256 access tokens (15 min), JWKS endpoint, rotating opaque refresh tokens stored hashed, reuse revokes all of the user's tokens. |
| Persistence | SQLAlchemy 2.x. SQLite in development, PostgreSQL 16 in CI and production. Both run in the CI matrix. |
| Client | React 18, Vite, TypeScript, TanStack Query, Zustand, Tailwind. REST and JSON; no WebSockets. |
| Jobs | One in-process APScheduler in the game service (§23.2). |
| Layout | Monorepo: `services/auth`, `services/game`, `client`, `content`, `design`, `docs/phase-notes`. A Makefile is the single source of local and CI checks. |

**Engine purity.** `services/game/app/engine/` holds pure functions of the form `(state, content, now, rng) → (new_state, results)`. No database or clock access inside the engine. The HTTP layer loads state under a row lock, calls the engine, and writes the result in one transaction.

**Errors.** Every error uses `{error: {code, message}}` with a stable machine-readable `code`.

---

## 4. Content system

### 4.1 Mechanics [SHIPPED]

Content is a set of JSON packs validated at boot by strict frozen Pydantic schemas with cross-pack referential checks. Packs are hashed canonically (SHA-256); `GET /content/manifest` returns the content version and per-pack hashes, and `GET /content/{pack}` serves each pack with a strong ETag. Content endpoints are unauthenticated.

### 4.2 Packs [CHANGE]

Nine packs are served today. v0.8 reshapes five and adds seven.

| Pack | Status | Holds |
|---|---|---|
| `skills` | CHANGE | Skills with `category`, and their actions (§6.2). `crafting` becomes `manufacturing`. |
| `items` | CHANGE | Goods. Adds `tier`, `classes`, `reference_price`, `bullion`, `spoilage_pct_per_day`, optional `equip` and `consumable` blocks. |
| `tags` | NEW | Tag definitions and their effects (§7.4). |
| `realms` | CHANGE | Realm templates: `{id, name, starting_node_id, isolated}`. The `market_offers` field is removed. |
| `development` | CHANGE | Realm nodes (type and tier), offered projects, upgrade edges with required tags, regression edges (§12.2). Edge progress is removed. |
| `projects` | CHANGE | One tag per project, kickoff cost, total cost, build time, who may kick off (§12.3). Project tiers are removed. |
| `estate_forms` | CHANGE | Adds `mobility`, `tier`, `build_cost`, `travel_profile`, `vote_weight` inputs, active `upkeep` and `production` (§13). |
| `upgrades` | SHIPPED | Estate upgrades. Now emit tags as well as modifiers. |
| `caps` | CHANGE | `market_listings` becomes `order_slots`; adds `key_listings`, `belt_slots`. |
| `map` | CHANGE | Edges gain `terrain`, `supplies`, `min_travel_level`, `base_loss_pct` (§11.1). |
| `combatants` | NEW | Combatant stats, XP pools, drop tables, respawn (§10.2). |
| `exploration` | NEW | Discoverable resource templates and per-realm discovery tables (§19.2). |
| `economy` | NEW | Global settings: tax rate, burn share, price curve defaults, margin, reserve and cap days, tick cadence, gauge thresholds, coinage multiple, caravan settings (§14–§18). |
| `progression` | NEW | Tier thresholds, proficiency and taper tables, bonus cap, stances, tier benefits for Travel and Exploration (§5, §8). |
| `tutorial` | NEW | Tutorial steps and hints (§20). |
| `world_seed` | NEW | Cold start: per realm, starting treasury, starting stores, realm-owned estates (§14.9). Read once when a world is created. Not served. |

The generated XP table (§5.1) is part of the content version hash and is not served as a pack; the profile endpoint reports XP to the next level.

### 4.3 Selectors [NEW]

Wherever content names a good as an input or a need, it may name a single item or a class of items. One shape is used everywhere:

```
selector := {"item": "item.pine_log"}
          | {"class": "log", "tier": 1}        # any item with that class and tier
          | {"class": "bullion"}               # any item with that class, any tier
```

Selectors are used by action inputs (§6.2), travel supplies (§11.4), upkeep and project costs (§12, §13, §14) and equipment requirements. Boot validation rejects a selector that matches no item.

When a selector must be paid from a holding that has several matching items, the cheapest by reference price is taken first, then the lowest item id. The rule is deterministic so that resolves are reproducible.

---

## 5. Progression: XP, levels and tiers

### 5.1 The curve [CHANGE]

XP needed to go from level L to L+1:

```
xp(L) = floor(A · r^L)      L = 1 … 99,   r = 2^(1/7)
A = 52.120034248…           chosen so that Σ xp(L) = 10,000,000 exactly
```

The table is **generated once and checked in** as `content/xp_curve.json` (99 integers). The server does not recompute it from floating point at boot. Boot validation asserts: 99 entries, strictly increasing, sum exactly 10,000,000.

| Level step | XP for the step | Cumulative XP at the lower level |
|---|---|---|
| 1 → 2 | 57 | 0 |
| 50 → 51 | 7,365 | 70,189 |
| 75 → 76 | 87,564 | 840,648 |
| 90 → 91 | 386,714 | 3,714,612 |
| 93 → 94 | 520,478 | 4,999,703 (the halfway point) |
| 95 → 96 | 634,470 | 6,094,836 |
| 99 → 100 | 942,820 | 9,057,180 |

Levels run 1 to 100. A skill starts at level 1 with 0 XP. XP keeps accumulating past 10,000,000 with no further level or effect; `character_skills.xp` is a 64-bit integer.

This replaces the shipped curve. The shipped segmented level-up resolution (§6.4) is unchanged; it reads whichever table is loaded.

### 5.2 Rate targets [NEW]

The three time anchors of V§3.3.2 give the XP per hour an action should pay at its unlock level:

```
target_xp_per_hour(U) = R1 · g^(U − 1)
R1 = 10,000,000 / 2,880 h = 3,472 XP/h      # the level-1 action alone reaches 100 in 2,880 h
g  = 1.015969                               # makes the unbonused optimal path take 720 h
```

| Unlock level | 1 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 75 | 80 | 90 | 95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Target XP/h | 3,472 | 4,004 | 4,692 | 5,497 | 6,441 | 7,547 | 8,842 | 10,360 | 11,214 | 12,139 | 14,223 | 15,395 |

The 720-hour figure assumes a better action unlocks at every level. With one new action every ten levels, actions exactly on the curve give 778 hours, because the player's rate lags between unlocks. A ten-level ladder that lands on 720 hours needs `g = 1.016938`. The content designer chooses which; the lint below reports the result either way.

The third anchor, 500 hours fully bonused, is 720 / 500 = 1.44, which is the +45% cap (§7.3).

**Content lint** (`make content-lint`, also run in CI as a warning-only report). For each non-combat skill it:

1. Computes each action's XP per hour from its XP and base cycle time.
2. Compares it with `target_xp_per_hour(unlock_level)` and lists actions more than a set tolerance off the target (*default* ±15%). An action may carry `"off_curve": "reason"` to silence the warning; that is the vision's "stated choice".
3. Simulates training from 1 to 100 using the best unlocked action at each level, with no bonuses, and reports the hours against 720.
4. Simulates the level-1 action alone and reports the hours against 2,880.
5. For combat, sizes are checked per combatant instead (§10.6).

### 5.3 Tiers [NEW]

`progression.tier_thresholds = [1, 50, 75, 90, 95]`. A character's tier in a skill is the number of thresholds its level has reached, 1 to 5. Tier titles are content.

Every action and every good carries a `tier`. Boot validation checks:

- an action's `tier` equals the tier of its `unlock_level`;
- an action's outputs are of the action's tier (a drop table entry may be flagged `off_tier` to allow by-products);
- an action's inputs are of the action's tier or lower.

**Tier distance** for a character doing an action is `character tier in the action's skill − action tier`, never below zero. It drives proficiency and XP taper (§8).

---

## 6. Skills, actions and the resolve engine

### 6.1 Skills and categories [CHANGE]

A skill has an id, a name and a `category`: `gathering`, `refining`, `manufacturing`, `combat`, `exploration` or `travel`. Categories are content groupings; the engine reads the category for exactly three things: which proficiency row applies (§8), which resolver runs the action (§6.3), and where the client lists it.

The six combat skills are fixed ids the combat resolver refers to: `melee`, `ranged`, `magic`, `accuracy`, `defense`, `vigor`. `travel` and `exploration` are single skills. All other skills are free content.

### 6.2 The action definition [CHANGE]

Every action is the same kind of record:

```
action := {
  id, skill_id, tier, unlock_level,
  base_cycle_ms,
  inputs:  [{selector, quantity}],            # consumed at the start of each cycle
  outputs: [{item_id, quantity_min, quantity_max, chance}],
  xp,                                         # per cycle, before bonuses
  requires: {
    facility:     tag_id | null,              # refining and manufacturing
    realm_tags:   [tag_id],                   # all must be active in the current realm
    skill_levels: {skill_id: level},          # cross-skill gates
    tool_class:   string | null               # a main-hand tool of this class must be equipped
  },
  resolver: "uniform" | "combat" | "travel",  # defaults from the category
  off_curve: string | null
}
```

Changes from the shipped shape: `tier`, selectors in `inputs`, the `requires` block, `resolver`.

**Where an action is available.** A character may start an action when all of these hold:

1. Its level in the skill is at least `unlock_level`.
2. The action is offered in the character's current realm. Gathering, combat and exploration actions are listed by the realm's node (`node.actions`), which is how a desert has no fishing. Refining and manufacturing actions are offered anywhere their facility is present. Travel is offered everywhere.
3. `requires.facility`, if set, is an active facility tag of the current realm **or** of the character's own estate when that estate is in the current realm (§7.4).
4. `requires.realm_tags`, `skill_levels` and `tool_class` are met.
5. Or: the action is supplied by a key the character holds (§19.4), in which case rules 2–3 are replaced by the key's own checks.

`GET /actions/available` returns every action of the character's skills with a per-action list of unmet requirements, so the client can explain why something is locked.

A running action is re-checked at each resolve. If its requirements stop holding (a facility tag is lost to decay, the realm changes node), the action ends at that moment with reason `REQUIREMENT_LOST`.

### 6.3 Resolvers [CHANGE]

The shipped engine assumes every cycle of an action is identical and resolves a batch in closed form behind a `CycleRewardStrategy`. Combat and travel do not fit: cycles differ in length and outcome. The seam widens from a reward strategy to a **resolver**:

```
class ActionResolver(Protocol):
    def resolve(self, state, action, ctx, budget_ms, rng) -> ResolveResult
```

`ctx` carries resolved bonuses, caps and content. `budget_ms` is the time to consume, already clipped by the offline cap. `ResolveResult` carries the new action state, XP by skill, items gained and lost, elapsed time actually consumed, a stop reason if the action ended, and a resolver-specific `details` object for the summary.

| Resolver | Used by | Method |
|---|---|---|
| `uniform` | Gathering, refining, manufacturing, exploration, key gathering | The shipped closed-form batch, segmented at level-ups. **[SHIPPED]** with the changes in §6.4. |
| `combat` | Combat actions | Simulates cycle by cycle (§10.5). **[NEW]** |
| `travel` | Journeys | One step per map edge (§11.3). **[NEW]** |

Stepped resolvers keep their in-progress state in `active_actions.meta` (shipped JSON column).

### 6.4 The uniform resolver [SHIPPED, with changes]

Unchanged behaviour:

- **Lazy.** Nothing runs between requests. A resolve computes how many whole cycles fit between `last_resolved_at` and now, and keeps the partial cycle.
- **Segmented at level-ups.** Effective values are recomputed when a level changes inside the batch.
- **Offline cap.** At most `offline_hours` (a cap, §7.5) of an absence is granted. The action ends after the in-budget cycles; if no whole cycle fits, it stays pending.
- **Stops.** Inputs exhausted, inventory full (overflow takes precedence over input exhaustion in the same cycle), or requirements lost.
- **RNG.** Seeded from a CSPRNG per resolve.
- **Clock.** A backwards clock correction is a no-op.
- **Reward feed.** `reward_log` rows are claimed in the transaction that builds the poll response (at most once).

Changes:

- Inputs are selectors (§4.3).
- Effective cycle time, XP and drop chance come from the new combination rules (§7.2).
- XP is multiplied by the taper factor for the action's tier distance (§8.2).
- A tier change inside a batch is a segment boundary, like a level-up, because proficiency and taper change with it.
- For key gathering, the cycle count is also clipped by the key's remaining uses (§19.4).

One character has at most one active action. Starting an action stops the current one with its final rewards.

---

## 7. Bonuses, caps and tags

### 7.1 Sources [CHANGE]

The shipped engine resolves modifiers, caps and availability from three places: the realm's node, the estate form, and installed estate upgrades. v0.8 has five **source groups**, matching V§4.6:

| Group | Made of | Applies when |
|---|---|---|
| **G** gear | Every equipped item (§9.2) | Always |
| **E** estate | The estate form and its non-inert, non-suspended upgrades | The estate is in the character's current realm |
| **R** realm | The current realm's node and its active tags | Always (the realm the character is in) |
| **C** consumables | Active timed buffs and the per-cycle utility item | While active |
| **P** proficiency | The tier-distance table (§8.1) | Cycle speed only |

A visiting player's estate is somewhere else, so group E contributes nothing to them (V§11.5.2). This falls out of the "applies when" column; there is no visitor rule.

### 7.2 Combining [CHANGE]

For one bonus type on one action:

```
factor(group) = max(min_factor, 1 + Σ(percentages from that group) / 100)
total         = factor(G) × factor(E) × factor(R) × factor(C) × factor(P)
```

A group with no bonus has factor 1. Maluses are negative percentages inside a group. `min_factor` (*default* 0.25) stops a group of maluses from driving a factor to zero.

Bonus types and how the total is applied:

| Type | Scope | Applied as |
|---|---|---|
| `cycle_speed_pct` | A skill, a skill category, or all | `cycle_ms = max(min_cycle_ms, floor(base_cycle_ms / total))` |
| `xp_pct` | A skill, a category, or all | `xp = floor(base_xp × min(total, xp_cap) × taper)` |
| `extra_drop_chance_pct` | A skill or category | `chance = clamp(base_chance × total, 0, 1)` |
| Combat stat types (§10.3) | Combat | Multiplies the named stat |
| Travel types (§11.4) | Travel | Multiplies journey time or supply quantity |

Types never combine with each other. Proficiency feeds only `cycle_speed_pct`.

Worked example from the vision: two gear bonuses of +5%, one estate bonus of +10%, one realm bonus of +20% of the same type give `1.10 × 1.10 × 1.20 = 1.452`. This is a unit test.

The shipped modifier type `cycle_time_pct` (a percentage subtracted from cycle time) is replaced by `cycle_speed_pct` (D2). The shipped placeholder content is converted.

### 7.3 The XP cap [NEW]

`progression.xp_bonus_cap_pct = 45`. The combined `xp_pct` total for any action is clamped to 1.45 (D1). The profile and action responses report both the uncapped and the capped figure, so a player can see when a bonus is wasted.

The lint (§5.2) additionally computes, per skill, the largest `xp_pct × cycle_speed_pct` total obtainable from content outside proficiency and warns when it exceeds 1.45, since that is what would breach the 500-hour anchor.

### 7.4 Tags [NEW]

A tag is a string id with a definition in the `tags` pack. Tags are emitted by sources and resolved in the same pass as bonuses and caps.

```
tag := {
  id, name, kind: "facility" | "bonus" | "malus" | "access",
  modifiers:  [{type, scope, pct}],
  cap_bonuses: {cap_id: amount},
  upkeep:     [{selector, per_day}],          # added to the holder's upkeep
  effects: {
    market_access:  bool,                     # §17.5
    caravan_access: bool,                     # §16.1
    mint: {value_per_day} | null,             # §14.8
    edge_loss_reduction_pct: number,          # §16.3
    reserve_days_delta: number                # §14.3
  }
}
```

Who emits tags:

- **Realm nodes** emit inherent tags. They are part of the realm's identity and cannot decay.
- **Completed realm projects** add one tag each to the realm's tag stack (§12.4). These can decay.
- **Estate forms and estate upgrades** emit tags for their owner. A facility tag from an estate serves only its owner.

A tag is **active** unless its holder is Faltering or worse and the tag's kind is `facility` (§14.6), or the upgrade that emits it is inert.

**Inert upgrades [SHIPPED].** An estate upgrade may declare `requires_realm_tags`. If the estate's realm lacks them, the upgrade is inert: it stays installed, contributes nothing, and comes back if the realm regains the tag. Inert status is derived on every resolve and never stored. Estate forms gain the same optional field; this is how a wharf does little in a desert.

### 7.5 Caps [CHANGE]

Caps are per-character limits resolved by adding bonuses from every applicable source to a base. They are additive across all sources (caps are amounts, not percentages) and are exposed as `{base, effective}` on the profile.

| Cap | Enforced at |
|---|---|
| `offline_hours` | Resolve budget |
| `inventory_slots` | Item gain, order collection, key purchase |
| `order_slots` | Order creation (renamed from `market_listings`) |
| `key_listings` | Key listing creation |
| `estate_upgrade_slots` | Upgrade install |
| `belt_slots` | Belt consumable assignment |

Caps travel with the player. A cap bonus that comes from the estate still follows the "applies when" rule of group E. If a cap falls below current usage (a visitor leaves their estate behind), nothing is taken away; the player simply cannot add more until usage is back under the cap.

---

## 8. Proficiency and XP taper [NEW]

Both tables live in the `progression` pack, keyed by skill category and tier distance (§5.3).

### 8.1 Proficiency (cycle speed)

| Category | Distance 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Gathering | +5% | +10% | +15% | +20% |
| Refining | 0 | +5% | +10% | +20% |
| Manufacturing | 0 | +10% | +20% | +30% |
| Combat | none; see §10.4 | | | |
| Travel, exploration | none; see §8.3 | | | |

The looked-up percentage is group P in §7.2. It is a speed bonus only; there is no yield bonus.

### 8.2 XP taper

| Category | Distance 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Gathering | 1 | 1 | 1 | 1 | 1 |
| Refining | 1 | 1 | *0.5* | 0 | 0 |
| Manufacturing | 1 | *0.5* | 0 | 0 | 0 |
| Travel, exploration | 1 | 1 | 1 | 1 | 1 |
| Combat, offensive stream | 1 | *0.75* | *0.5* | *0.25* | *0* |

Italic values are defaults the vision leaves to balance. The taper multiplies XP after the cap (§7.2). It never affects outputs or drop tables. The combat row applies to the offensive stream only (§10.4).

### 8.3 Tier benefits for Travel and Exploration

These skills have no below-tier activity. They get a benefit on reaching each tier, as rows in `progression.tier_benefits`:

| Skill | Benefit per tier | Applied as |
|---|---|---|
| Travel | `journey_speed_pct`, `supply_reduction_pct` | Group P of the travel types (§11.4) |
| Exploration | `cycle_speed_pct`, `keys_per_discovery_bonus`, `rarity_weight_shift` | §19.3 |

---

## 9. The player: inventory, equipment, consumables

### 9.1 Inventory [SHIPPED, with one addition]

One inventory per character, carried everywhere. Stackable goods occupy one slot per item id, subject to the item's `stack_limit`. The slot count is the `inventory_slots` cap. There is no estate storage and no bank.

Addition: instanced items (keys, §19) occupy one slot each and never stack. Slot usage is `distinct stackable items + instances held`.

### 9.2 Equipment [NEW]

Slots:

| Group | Slots |
|---|---|
| Armour | `head`, `chest`, `gloves`, `legs`, `feet` |
| Jewellery | `neck`, `left_arm`, `right_arm`, `left_ring`, `right_ring` |
| Other | `belt`, `cape` |
| Hands | `right_hand`, `left_hand` |
| Combat utility | `utility` (a stack) |

An equippable item has:

```
equip := {
  slot,                         # or "ring" / "arm": either side
  two_handed: bool,             # occupies right_hand, blocks left_hand
  requires: {skill_id: level},
  modifiers: [{type, scope, pct}],          # group G
  cap_bonuses: {cap_id: amount},
  weapon: {style, attack_interval_ms, power, accuracy, damage_type} | null,
  armour: {armour, max_hp} | null,
  tool_class: string | null,                # e.g. "pickaxe"
  belt_slots: int | null                    # belts only
}
```

Rules:

- Equipping moves the item from inventory to the slot; unequipping needs a free inventory slot.
- Equipping a two-handed item unequips the left hand. Equipping a left-hand item while a two-handed item is held is rejected.
- Equipment may not be changed while a combat action is running. Other actions allow it; the next resolve picks up the new bonuses from that moment (the resolve is run first, then the change applied).
- A skilling tool goes in `right_hand` and satisfies `requires.tool_class`. It usually also carries a `cycle_speed_pct` for its skill.
- Capes carry `xp_pct` only. This is a content rule the validator enforces: `xp_pct` on gear is allowed only in the `cape` slot.
- Gear has no durability. Nothing in the engine consumes or degrades an equipped item.

### 9.3 Consumables [NEW]

Two kinds, both set up before an action starts.

**Utility stack.** One item stack in the `utility` slot. One unit is consumed at the start of each combat cycle. Its effect lasts for that cycle. The item's `consumable.utility_for` names the attack style it serves.

**Belt slots.** The equipped belt provides `belt_slots` positions (plus the `belt_slots` cap). Each holds an item stack and a trigger:

```
belt_slot := {item_id, quantity, trigger}
trigger   := {"hp_below_pct": n}            # healing food and potions
           | {"buff_missing": true}         # timed buffs: re-apply when the buff runs out
```

A consumable item defines `heal` (hit points restored) or `buff` (`modifiers`, `duration_ms`). Belt consumables are used by the combat resolver (§10.5) and by exploration, where a buff-style consumable shapes the discovery table (§19.3). At most one belt item is consumed per cycle.

### 9.4 Hit points [NEW]

`max_hp` comes from Vigor level and armour (§10.3). Current hit points are stored with a timestamp and regenerate lazily:

```
hp(now) = min(max_hp, hp_stored + regen_per_min × minutes since hp_updated_at)
```

`regen_per_min` is *default* 1% of `max_hp`. Regeneration runs at all times, including during combat, where the resolver adds it per cycle. A character needs at least `min_engage_hp_pct` (*default* 25%) of maximum hit points to start a combat action.

---

## 10. Combat [NEW]

### 10.1 Shape

A combat action is `fight combatant X at location Y`. Locations are flavour and grouping: the realm node lists combat actions, each naming its combatant and a location label. The action runs through the `combat` resolver. One cycle is one of the player's attacks.

### 10.2 The combatant

```
combatant := {
  id, name, tier, style,
  max_hp, accuracy, power, defense, armour,
  attack_interval_ms, respawn_ms,
  weak_to: [damage_type], resistant_to: [damage_type],
  xp_pool_offense, xp_pool_defense,
  defense_xp_per_damage,
  drops: [{item_id, quantity_min, quantity_max, chance}]
}
```

Drop tables may contain bullion goods. Boot validation rejects any drop table, on a combatant or anywhere else, that would grant gold (V§9.5.2); gold is not an item, so this is enforced simply by there being no gold field.

### 10.3 Stats and the hit (D12)

Effective skill level, for Melee, Ranged, Magic, Accuracy and Defense:

```
eff(skill) = level × (1 + 0.05 × (tier − 1))        # the uniform tier multiplier, V§3.7
```

Vigor has no tier multiplier.

Player stats (each then multiplied by its bonus total from §7.2):

| Stat | Formula | Bonus type |
|---|---|---|
| Attack rating | `eff(accuracy) + weapon.accuracy` | `combat_accuracy_pct` |
| Max hit | `combat.base_hit + eff(style skill) × combat.hit_per_level + weapon.power` | `combat_power_pct` |
| Defense rating | `eff(defense)` | `combat_defense_pct` |
| Armour | `Σ armour of equipped items` | `combat_armour_pct` |
| Max hit points | `combat.base_hp + vigor level × combat.hp_per_level + Σ armour.max_hp` | `combat_hp_pct` |
| Cycle time | `weapon.attack_interval_ms` | `cycle_speed_pct` scoped to combat |

Unarmed uses a content-defined default weapon. The style in use is the equipped weapon's style.

An attack, in either direction:

```
p_hit   = clamp(attack / (attack + defense), 0.05, 0.95)
rolled  = uniform integer in [1, max_hit]
rolled  = rolled × 1.25 if weak_to, × 0.75 if resistant_to     (floor)
if miss:   dealt = 0,   mitigated = rolled
if hit:    blocked = floor(rolled × armour / (armour + combat.armour_k))
           dealt = rolled − blocked,   mitigated = blocked
```

The damage roll is made whether or not the attack lands, so that a dodged blow still counts as damage mitigated for the defensive stream. All `combat.*` constants are settings in the `progression` pack.

### 10.4 Tier distance in combat

Against a combatant below the player's tier (distance from the attack style's skill tier):

- **Effectiveness.** `progression.combat_effectiveness[distance]` (*default* +10% per tier) is group P for `combat_accuracy_pct`, `combat_power_pct` and `combat_defense_pct`. Vigor-derived hit points are excluded. Cycle time is unaffected.
- **Offensive taper.** The combat row of §8.2 multiplies offensive-stream XP. XP removed by the taper is still drained from the pool.
- The defensive stream is not tapered. Drop tables are never reduced.

### 10.5 The cycle and the encounter

State kept in `active_actions.meta`: combatant hit points, remaining offensive and defensive pool, the combatant's attack-time carry, respawn time left, active buffs with expiry, and running totals for the summary.

Each cycle, in order:

1. **Utility.** Consume one unit from the utility stack if it matches the style. Ranged with no ammunition: the action ends, reason `OUT_OF_AMMO`. Melee and magic without it continue without its bonus.
2. **Player attacks.** Resolve the hit. Damage is clipped to the combatant's remaining hit points.
3. **Combatant attacks.** Add the cycle length to the carry; the combatant attacks once per whole `attack_interval_ms` in the carry. Each attack is resolved against the player.
4. **Offensive XP.** `damage dealt × xp_pool_offense / max_hp`, clipped to the remaining pool, times the taper. Split between the style skill and Accuracy by the player's **stance**.
5. **Defensive XP.** `(damage taken + damage mitigated) × defense_xp_per_damage`, clipped to the remaining pool. The part from damage taken goes to Vigor, less `combat.taken_to_defense_pct` (*default* 20%) which goes to Defense; the part from damage mitigated goes to Defense.
6. **Regeneration** for the cycle's duration (§9.4).
7. **Belt.** Evaluate triggers in slot order; consume at most one item.
8. **Terminal checks.**
   - Combatant at 0 hit points: roll the drop table into inventory (the normal overflow rule applies), discard what is left in both pools, start the respawn wait. When it ends, a new encounter begins with full hit points and full pools.
   - Player at 0 hit points: the action ends, reason `DEFEATED`. The player becomes idle and regenerates. There is no other penalty.

If both reach zero in the same cycle the kill counts first, then the defeat.

**Stance** is a standing setting on the character: one of `progression.stances`, *default* `aggressive` 75/25, `balanced` 50/50, `precise` 25/75 (style / Accuracy). It can be changed at any time; the change applies from the next resolve.

**Pools.** Each pool is per encounter and refills only on respawn. A player who never kills a combatant drains its defensive pool once and then earns nothing more from that stream.

**Offline.** The combat resolver simulates cycle by cycle over the offline budget; there is no closed form. Respawn waits consume budget without cycles. Cost is bounded: twelve hours of two-second cycles is about 22,000 iterations of integer arithmetic. `combat.max_cycles_per_resolve` (*default* 50,000) is a hard ceiling; reaching it ends the action with reason `OFFLINE_CAP`.

**Summary.** The resolver's `details` object holds kills, defeats, damage dealt and taken, XP by skill, consumables used by item, loot by item, and the stop reason. The welcome-back modal renders it.

### 10.6 Sizing pools (content lint)

For each combatant the lint estimates, for a player at the combatant's unlock level in standard gear, the expected time to kill plus `respawn_ms`, and checks that `xp_pool_offense × stance share` and the defensive split each give roughly `target_xp_per_hour` (§5.2) for the skill receiving them. Four skills train at once, each at the pace of any other skill, not faster.

---

## 11. The world: map, presence and travel

### 11.1 The map [CHANGE]

The `map` pack is a graph of realm templates joined by edges. The shipped pure function `path_cost` stays, with a new cost model.

```
edge := {
  id, a, b, one_way: bool,
  terrain: "land" | "water",
  base_time_s,
  supplies: [{selector, quantity}],
  min_travel_level,                 # 1 = open to all; higher = a shortcut or a hard road
  base_loss_pct                     # caravan loss, §16.3
}
```

`GET /map` (unauthenticated) returns the graph plus, per realm: node, tier, decay stage, treasury health band, and whether a transition is pending. Tutorial realms are never on the map.

### 11.2 Presence [CHANGE]

Each character has a `current_realm_id`. The shipped `characters.realm_id` column is renamed to it. A character's **home** is the realm of its estate.

- **Resident** of a realm: owns an estate located there. A mobile estate counts.
- **Visitor**: `current_realm_id` differs from the estate's realm.

Everything that needs presence reads `current_realm_id`: actions offered, realm-market trading, project contributions, the market-access gate, the realm credited with the seller tax. There is no visitor malus. A visitor lacks estate bonuses only because the estate is elsewhere (§7.1).

There is no state between realms. During a journey step the character is in the realm the step started from; when the step completes it is in the next one.

### 11.3 Journeys [NEW]

A journey is an action of the `travel` skill, run by the `travel` resolver.

```
POST /travel/start {destination_realm_id, mode: "visit" | "relocate"}
```

- `relocate` requires a mobile estate that is in the character's current realm. The estate moves with the character, step by step.
- `visit` leaves the estate where it is. Owners of fixed estates can only visit. Owners of mobile estates may do either.
- The route is the cheapest path from the current realm to the destination, by total time, over the edges this traveller may use: the edge's `terrain` is in the traveller's profile, and Travel level ≥ `min_travel_level`. Ties break by fewest edges, then edge ids. No route: `NO_ROUTE`.
- `GET /travel/preview` returns the route, time and supplies per edge without starting.

The route is fixed in `active_actions.meta` at start. Each edge is one step:

1. **At step start**, the edge's supplies (after reductions) are taken from inventory. If they are missing the journey ends in the current realm, reason `OUT_OF_SUPPLIES`.
2. The step lasts the edge's effective time.
3. **At step end**, `current_realm_id` moves to the far end of the edge; in `relocate` mode the estate's `realm_id` moves too; Travel XP is granted.

Stopping a journey leaves the character in the realm of the last completed step. The partial step is lost, including its supplies. A new journey can be started from there.

Journeys continue offline within the offline cap. The summary lists edges completed, supplies used, XP gained and where the character now is.

If the estate arrives in a realm mid-transition or one whose node changed, nothing special happens; inert rules (§7.4) apply on the next resolve.

### 11.4 Cost of a step

```
time     = edge.base_time_s × profile.time_mult     / total(journey_speed_pct)
supplies = ceil(edge.quantity × profile.supply_mult / total(supply_reduction_pct))   per supply line
xp       = floor(edge.base_time_s × progression.travel_xp_per_second)
```

`total(...)` is the §7.2 combination: gear, estate (when relocating, the estate is by definition present), realm, consumables, and the Travel tier benefit as group P. XP depends on the edge's base time, not the time actually taken, so getting faster never lowers XP per edge.

**Profiles.** The traveller owns the profile:

- `visit` uses `progression.visit_profile`: light supplies, fairly quick, terrains `[land, water]`.
- `relocate` uses the estate form's `travel_profile := {time_mult, supply_mult, terrains}`. A boat lists only `water`; a wagon only `land`.

Mobile estate tiers improve their profile and may produce travel supplies (§13.6). The same edge costs apply to caravans (§16).

---

## 12. Realms: nodes, projects, tags and upgrades

### 12.1 Realm records [CHANGE]

`realm_state` gains instance fields so that tutorial realms can exist per player (§20):

```
realm_state (id PK, template_id, isolated, owner_character_id NULL,
             current_node_id, treasury, pending_transition JSON NULL,
             last_tick_at, gauge, decay_stage, shed_progress,
             vote_cooldown_until NULL, treasury_band)
```

For world realms `id = template_id`. `isolated` realms have no upkeep, no decay, no market, no caravans, pay no tax to anyone, and are excluded from every list and map.

### 12.2 The development graph [CHANGE]

A node is a realm type at a tier.

```
node := {
  id, realm_type, tier,
  inherent_tags: [tag_id],
  modifiers, cap_bonuses,                 # realm-tier bonuses, group R
  actions: [action_id],                   # gathering, combat and exploration offered here
  upkeep: [{selector, per_day}],          # the node's own upkeep; empty for a barren realm
  projects: [project_id],                 # what may be built here
  carried_tags: [tag_id],                 # tags from elsewhere that remain valid here
  upgrades: [{id, to_node, kind: "tier_up" | "morph", required_tags: [tag_id], fee_gold}],
  regression: {to_node} | null,           # null only for the barren root
  reserve_days, cap_days, margin_pct      # optional overrides of the economy defaults
}
```

Removed from the shipped shape: edge progress, edge awards, and the `award_edge_progress` engine function. The shipped lazy, idempotent `finalize_realm` is kept and becomes the transition-completion step (§12.6).

Content rules the validator enforces: every `required_tags` entry is the tag of a project offered at that node or in `carried_tags`; morph edges exist only where the content designer allows (the vision's "easier at low tiers, not at all once highly specialised" is expressed by simply not authoring them at high tiers); the graph of regression edges reaches the barren root from every node.

### 12.3 Projects [CHANGE]

```
project := {
  id, name, grants_tag,
  kickoff: {gold, goods: [{selector, quantity}], who: "residents" | "anyone"},
  cost: [{selector, quantity}],
  build_seconds,
  realm_completion_days,              # §14.4
  requires_tags: [tag_id],            # prerequisites, e.g. mint tier 2 needs mint tier 1
  repeatable: false
}
```

A project whose tag the realm already holds is not offered. Tiered facilities (a deeper mine, a larger mint) are separate projects chained by `requires_tags`, each granting its own tag.

**A project run** is one attempt:

```
realm_project_runs (id, realm_id, project_id, status,
                    kicked_off_by, kicked_off_at,
                    required JSON, contributed JSON,
                    last_contribution_at, build_completes_at NULL,
                    failed_at NULL)
status: funding → building → complete        or        funding → failed
```

**Kickoff.** `POST /realms/{id}/projects/{project_id}/kickoff`. Conditions, each with its own error code:

| Condition | Code |
|---|---|
| The character is in the realm | `NOT_PRESENT` |
| `who` allows them (resident, or anyone) | `RESIDENTS_ONLY` |
| The node offers the project, prerequisites held, tag not held | `PROJECT_NOT_OFFERED` |
| No run is in `funding` or `building` in this realm | `PROJECT_ACTIVE` |
| No vote is open and no transition pending | `REALM_VOTING`, `REALM_TRANSITIONING` |
| The project is not in its failure cooldown | `PROJECT_COOLDOWN` |
| The character has not kicked off any project anywhere in the last 24 hours | `KICKOFF_LIMIT` |
| The character can pay the kickoff cost | `MISSING_INPUTS` |

Kickoff gold goes to the realm treasury; kickoff goods are consumed (D14). `characters.last_kickoff_at` enforces the daily limit.

**Contributing.** `POST /realms/{id}/project/contribute {item_id, quantity}`. The character must be in the realm; residence is not required. The quantity is clamped to what the matching cost line still needs (shipped behaviour); goods are consumed and never refunded. Each contribution writes a `realm_contributions` row with the run id. The realm itself contributes each tick (§14.4), recorded with a null character.

**Idle erosion.** Measured from `last_contribution_at` (a realm contribution counts):

| Idle for | Effect |
|---|---|
| Up to `project.idle_grace_days` (*default* 2) | None. Shown publicly as "stalled". |
| Beyond that | Each tick, every cost line's contributed amount falls by `project.erosion_pct_per_day` (*default* 20) of its **required** amount, pro rata. |
| Contributed amounts all reach zero | The run fails. The project cannot be kicked off again in this realm for `project.fail_cooldown_hours` (*default* 36). |

Any contribution resets the idle clock. Erosion is processed in the realm tick.

**Building.** When every cost line is met the run moves to `building` and `build_completes_at` is set. Erosion no longer applies. At completion (processed lazily by `resolve_realm`), the tag is pushed onto the realm's stack.

### 12.4 The tag stack [NEW]

```
realm_tags (realm_id, tag_id, seq, node_id, acquired_at, project_run_id)   PK (realm_id, tag_id)
```

`seq` is a per-realm increasing number; the highest is the most recent. `node_id` is the node the tag counts as belonging to (D4). `project_run_id` links the tag to its kickoff and contribution log, which `GET /realms/{id}/tags/{tag_id}` returns as the credits: who kicked it off, and total contributions per character.

A realm's active tags are its node's inherent tags plus its stack, subject to §7.4.

### 12.5 Realm upgrades and the vote [NEW]

**Calling.** `POST /realms/{id}/upgrades/{upgrade_id}/call`. The caller must be a resident, present or not; the realm must hold every required tag; no project run may be active (D6); no vote open; no transition pending; `vote_cooldown_until` passed. The caller pays `fee_gold`, which goes to the treasury at once and is never returned.

**Eligibility** is snapshotted at the call: every character who is a resident at that moment, with a weight from their estate.

| Estate | Weight |
|---|---|
| Mobile, any tier | 1 |
| Fixed, tier *t* | 9 + *t* (tier 1 = 10, tier 2 = 11, …) |

```
realm_votes   (id, realm_id, upgrade_id, called_by, called_at, closes_at,
               status, yes_weight, no_weight, eligible_weight, fee_gold)
realm_vote_eligibility (vote_id, character_id, weight, voted_at NULL)
```

**Secret ballot.** A cast vote adds the voter's weight to `yes_weight` or `no_weight` and sets `voted_at`. The choice itself is not stored against the character anywhere. Participation (who has voted) is public; running totals are not shown until the vote closes.

**Rules.** One vote per eligible character, no changes. Not voting is abstaining. The vote lasts `vote.duration_hours` (*default* 72) and closes early once every eligible character has voted. It passes when `yes_weight > no_weight` (D5). The caller gets no automatic vote.

**Failing** sets `vote_cooldown_until = now + vote.fail_cooldown_hours` (*default* 72).

**Passing** starts a transition.

Closing a vote is processed lazily by `resolve_realm`, like every other realm-timed event.

### 12.6 Transitions [CHANGE]

A transition is the shipped `pending_transition` with a wider role. It is started by a passed vote or by a decay regression (§14.7).

```
pending_transition := {to_node, cause: "upgrade" | "regression", started_at, completes_at}
```

It lasts `transition.duration_days` (*default* 7). While pending:

- No project may be kicked off and no vote called.
- The realm's reserve for every demand line rises by `transition.duration_days` (§14.3).
- Every key discovered in the realm is marked deprecated (§19.6).
- Decay does not shed tags; the gauge keeps moving.

At completion (`finalize_realm`, lazy and idempotent):

1. `current_node_id` becomes `to_node`.
2. Tags not offered or carried by the new node are dropped.
3. On an upgrade, surviving tags keep their `node_id`. On a regression, surviving tags are restamped with the new node's id.
4. On a regression, the gauge is reset to zero and `shed_progress` cleared.
5. Keys of the realm are invalidated and any action using one stops.
6. Actions that are no longer offered end at the next resolve (§6.2).

---

## 13. Estates

### 13.1 Records [SHIPPED, with changes]

```
estates (id, owner_character_id NULL, realm_id, form_id, status,
         gauge, decay_stage, shed_progress, data JSON)
estate_upgrades (estate_id, slot_index, upgrade_id, purchased_at)
estate_larder   (estate_id, item_id, quantity)
estate_ownership_history (estate_id, character_id NULL, from_at, to_at NULL)
```

Ownership is already decoupled from identity. `owner_character_id IS NULL` means the realm owns the estate. `characters.home_estate_id` points at the character's one estate. The columns `relocating_to_realm_id` and `relocation_completes_at`, and the `level` and `upgrade_slots` columns that forms now determine, are dropped. Nothing may assume one estate per character forever; the limit is enforced in the endpoints, not the schema.

### 13.2 Forms [CHANGE]

```
form := {
  id, name, mobility: "mobile" | "fixed", tier,
  build_cost: {gold, goods: [{selector, quantity}]},     # to build this form from nothing (tier 1) or from its predecessor
  requires_realm_tags: [tag_id],                         # needed to build or transform into the form; inert rule otherwise
  modifiers, cap_bonuses, tags,                          # group E
  upgrade_slots,
  upkeep:     [{selector, per_day}],
  production: [{item_id, per_day}],
  travel_profile: {time_mult, supply_mult, terrains} | null,     # mobile only
  transforms_to: [form_id],                              # the estate upgrade graph
  regresses_to: form_id | null
}
```

The estate upgrade graph is the graph of `transforms_to` edges between forms, plus the upgrades installed in a form's slots. Tier 1 fixed forms are generalists; specialisation is authored into higher forms.

The vision's "estate upgrade" covers both a transform to a higher form and an installed upgrade.

### 13.3 Upgrades and transforms [SHIPPED]

- `POST /estates/me/upgrades/{upgrade_id}`: install into a free slot. Errors `UNKNOWN_UPGRADE`, `NO_FREE_SLOT`, `ALREADY_INSTALLED`, `MISSING_INPUTS`. The last free slot is taken under a row lock.
- `POST /estates/me/transform {form_id}`: move along a `transforms_to` edge, paying the destination's `build_cost`. Errors `INVALID_TRANSFORMATION`, `MISSING_INPUTS`, `ESTATE_BUSY` (now: a journey in `relocate` mode is running), `WOULD_ORPHAN_UPGRADES` (the destination's own slots, excluding installed-upgrade bonuses, cannot hold what is installed).

Changes: a transform never changes mobility, both actions require the owner to be in the estate's realm, and costs may use selectors.

### 13.4 Getting and giving up an estate [NEW]

A character in the world always has exactly one estate.

| Action | Endpoint | Effect |
|---|---|---|
| **Build** a tier 1 fixed estate | `POST /estates/build {form_id}` | Character must be in the realm with a mobile estate that is also there. Pays `build_cost`. A new fixed estate is created in the current realm; the mobile estate and its upgrades are destroyed (D8). The client must confirm. |
| **Buy** a realm-owned estate | `POST /estates/{id}/buy` | Same preconditions. Pays the sale price in gold to the realm treasury. Ownership transfers; the mobile estate is destroyed. |
| **Surrender** a fixed estate | `POST /estates/me/surrender {donate: bool}` | Owner must be in the estate's realm. The realm pays `min(value, treasury)`, or nothing if `donate`. Ownership passes to the realm. The character receives a free `progression.basic_mobile_form` estate in the current realm. |

A mobile estate cannot be sold or surrendered. An owner of a fixed estate who wants a different one surrenders first, then builds or buys.

**Value** of an estate is the cost to rebuild it as it stands: the `build_cost` of every form on the path from tier 1 to its current form, plus the cost of each installed upgrade. Gold counts at face value. Each good counts at

```
min(reference_price, realm's current unit ask for that good)      # reference_price if the realm is not selling it
```

For a selector, the cheapest matching item is used.

**Sale price** is `ceil(value × (1 + estate.sale_markup_pct / 100))` (*default* 15). Because the realm pays at most the value and charges the value plus the markup, buying and reselling to the realm always loses.

`GET /realms/{id}/estates` lists estates in a realm: owner or "realm-owned", form, decay stage, and for realm-owned estates the current sale price.

### 13.5 Residency effects

Owning an estate in a realm makes the character a resident, which matters in exactly three places: who may kick off resident-only projects (§12.3), who may call and vote on upgrades (§12.5), and the vote weight.

### 13.6 Production, upkeep and the larder [NEW]

Estates are processed in their realm's tick (§14.5). The owner takes no action and need not be online.

- **Production** is credited to the **realm's stores**, never to the owner. This is V§8.8.2 and it is deliberate: an estate's return to its owner is its bonuses, facilities and vote, not goods.
- **Upkeep** is taken from the estate's larder first, then from the realm's stores above the reserve.
- **The larder** is deposit-only: `POST /estates/me/larder {item_id, quantity}`, owner present in the realm. Only items matching one of the estate's upkeep selectors are accepted. Nothing ever comes back out. Spoilage applies (§14.5).
- **Estates hold no gold.**
- A mobile estate's production may include travel supplies. They still go to the stores of the realm it is in.

Realm-owned estates behave the same with an empty larder: they produce into the stores and eat from them. This is how a fresh realm has an economy before players arrive (§14.9).

An estate whose form has no upkeep and no production (the basic raft, the starter camp) is skipped by the tick entirely.

### 13.7 Estate gauge and decay [NEW]

An estate has its own deficit gauge with the same arithmetic and stages as a realm (§14.6), computed from its own upkeep.

| Stage | Effect on an estate |
|---|---|
| Fed, Strained | None. Strained is shown to the owner and on the realm's estate list. |
| Faltering | Estate bonuses and production are scaled by `decay.faltering_factor`; facility tags are suspended. |
| Failing | Installed upgrades are removed, most recently purchased first, at the shed rate. |
| Regressed | With no upgrades left, the form drops to `regresses_to`, its gauge reset. If the form has no `regresses_to`, the estate is destroyed. A player-owned estate that is destroyed is replaced by a free basic mobile estate in the owner's **current** realm. |

There is no inactivity rule. An estate lasts as long as its upkeep is met, whoever owns it and whether or not they ever log in.

---

## 14. The realm economy [NEW]

Nothing in this section exists in code except the dormant `realm_state.treasury` column and the estate form profiles.

### 14.1 Stores

```
realm_stores (realm_id, item_id, quantity_milli)
```

Stores and larders are held in thousandths of a unit so that an hourly tick can take a twenty-fourth of a daily amount without drift. Player inventories and every trade are in whole units.

The amount due for a daily rate `d` (in milli-units) at tick index `n` of `T` ticks per day is

```
due(n) = floor(d × (n + 1) / T) − floor(d × n / T)
```

which sums to exactly `d` over a day and needs no stored remainder.

### 14.2 Demand lines (D9)

A realm's appetite is a set of **demand lines**. A line is one selector (§4.3) with a daily draw. Lines are derived, never authored directly; at each tick the realm's lines are the sum, grouped by selector, of:

| Source | Contributes |
|---|---|
| The node | `node.upkeep` |
| Active tags, inherent and stack | each tag's `upkeep` |
| The mint | one line `{class: bullion}`, value-measured (§14.8) |
| Estates in the realm | each estate's `upkeep`, in full, whether or not its larder covers it |
| The active project | the overlay of §14.4 |

A line is measured in **line units**. An item contributes `w` line units per unit: `w = 1` for ordinary lines, and `w = reference_price` for a value-measured line. Boot validation requires all items matched by an ordinary class selector to share one reference price, so that a line's members are interchangeable.

An item belongs to the most specific line that matches it (item, then class with tier, then class). Content lint warns when two selectors used as upkeep overlap.

```
realm_lines (realm_id, line_key, selector JSON, draw_per_day, reserve, cap,
             stock, in_transit, budget_gold)
```

`realm_lines` is a derived table, rewritten at the end of every tick and adjusted on every trade. It is what the read endpoints serve.

### 14.3 Draw, reserve and cap

```
draw    = Σ daily rates on the line                       (line units per day)
reserve = draw × (reserve_days + Σ tag reserve_days_delta + transition days if a transition is pending)
cap     = draw × cap_days
```

`reserve_days` (*default* 3) and `cap_days` (*default* 10) are economy settings a node may override. `cap_days` must exceed the largest reserve the realm can reach.

**Goods with no line.** Reserve is zero, so all of it may be sold. The cap is a hard cap: `economy.warehouse_value_cap / reference_price` units (an item may override it). The realm does not bid for these goods.

### 14.4 The project overlay

While a run is in `funding`, each of its cost lines adds to the realm's draw:

```
extra draw = remaining requirement / project.realm_completion_days
```

so that with no player help the realm would finish the project in that many days. As players contribute, the remainder shrinks and so does the extra draw. Each tick the realm contributes up to the tick's share of that extra draw, taking only stock above the reserve.

### 14.5 The tick

`resolve_realm(realm, now)` is lazy and idempotent. It reads `last_tick_at`, works out how many whole ticks have elapsed, and applies them one after another. Every read or write of a realm's market, stores, projects or votes calls it first, under the realm's row lock. The scheduled job (§23.2) calls it for every non-isolated realm each tick, which is what guarantees decay advances in a realm nobody visits. Catch-up is capped at `tick.max_catchup` (*default* 72) ticks per call; a longer gap is worked off over successive calls.

The cadence is `tick.per_day` (*default* 24). Upkeep is authored per day.

Three timed events are not tied to tick boundaries. `resolve_realm` finalises them at their exact due time whenever it runs, before applying ticks: a vote past `closes_at`, a build past `build_completes_at`, and a transition past `completes_at`.

Each tick, in this order:

| Step | What happens |
|---|---|
| 0 | Caravan shipments due by this tick arrive in the stores (§16). |
| 1 | Each estate's production is added to the stores, scaled by the estate's decay stage; inert forms produce nothing. |
| 2 | Each estate takes its upkeep from its own larder. |
| 3 | Estates still short take the rest from the stores, but only stock above each line's reserve. If several estates compete for too little, it is shared pro rata to what each is owed. |
| 4 | The realm takes its own upkeep (node, tags, mint) from the stores, and may go below the reserve. The mint coins what it consumed (§14.8). |
| 5 | The realm contributes to its active project from stock above the reserve. Project idle erosion is applied (§12.3). |
| 6 | Spoilage: each item with `spoilage_pct_per_day` loses that share, pro rata to the tick, from stores and from larders. |
| 7 | Anything above a cap is lost. For a line, the excess is removed from its most plentiful item first. |
| 8 | The realm's gauge and each estate's gauge are updated (§14.6). |
| 9 | Decay advances or recovers for the realm and for each estate (§14.7, §13.7). |
| 10 | `realm_lines`, bid budgets (§15.4) and the treasury band (§15.5) are recomputed. |

The rule in short: above the reserve, estates eat first; below it, the realm eats first.

All of it is integer arithmetic with no randomness. Steps 1–3 are set-based: production is one upsert per item, and estates are loaded in one query per realm.

### 14.6 The deficit gauge and stages

The gauge is in **days**. For the realm's own upkeep (not its estates'), each tick:

```
unmet_share = Σ (unmet line units × unit reference value) / Σ (due line units × unit reference value)

if unmet_share > 0:  gauge = min(gauge.max, gauge + unmet_share / T)
else:                gauge = max(0, gauge − gauge.recovery_per_day / T)
```

Weighting by reference value means a missing expensive good counts for more than a missing cheap one. A realm short of one input out of many rises slowly. The gauge reads as "this realm has been short the equivalent of *n* days". Which lines are short is reported separately on the realm page.

| Stage | Gauge (*defaults*, days) | Effect |
|---|---|---|
| **Fed** | 0 | None. |
| **Strained** | > 0.5 | **None.** Shown on the map and the realm page. A test asserts that no engine value differs between Fed and Strained. |
| **Faltering** | > 2 | Bonus and malus tags are scaled by `decay.faltering_factor` (*default* 0.5); facility tags are suspended; access tags keep working (D11). Nothing is lost. |
| **Failing** | > 4 | Tags are shed (§14.7). |
| **Regressed** | No tag of the current node left | A regression transition starts (§12.6). |

`gauge.max` is *default* 10 days and `gauge.recovery_per_day` *default* 1: a day fully fed cancels a day of hunger.

### 14.7 Shedding and regression (D4)

While Failing and with no transition pending, each tick:

```
shed_progress += (shed.base_per_day + shed.per_gauge_day × (gauge − failing_threshold)) / T
```

When `shed_progress ≥ 1`, one is subtracted and the realm loses its most recent tag: the highest `seq` among tags whose `node_id` is the current node. The tag row is deleted; its credits are kept in `realm_contributions` and the run. *Defaults:* one tag per two days at the threshold, faster as the gauge climbs.

When the realm is Failing and holds no tag of its current node, it is Regressed: a transition to `node.regression.to_node` starts. A node with no regression edge (the barren root) simply stays Failing with nothing more to lose.

When the gauge is below the Failing threshold, `shed_progress` drains at `shed.recovery_per_day`. A rescued realm therefore climbs back from where it fell to. Lost tags do not return; they are rebuilt through projects.

### 14.8 The mint

A tag with `effects.mint = {value_per_day}` gives its realm a value-measured demand line on `{class: bullion}`. If several mint tags are active, the largest `value_per_day` applies; mint tiers are separate chained projects.

The line behaves like any other: it has a reserve and a cap, the realm bids for bullion at its market, buys it by caravan, and its unmet share feeds the gauge.

At step 4 of each tick the mint consumes up to the tick's share of `value_per_day` in bullion from the stores, and

```
treasury += floor(reference value consumed × economy.coinage_multiple)
```

`coinage_multiple` is one global setting (*illustrative* 1.2). This is the only code path that creates gold. It credits a treasury and never a player. A property test asserts that the total gold in the world changes only by this amount and by the named sinks (§18).

### 14.9 Cold start

A world is created from `world_seed`: for each realm, a starting treasury, starting stores, and a list of realm-owned estates (`owner_character_id` null). A wild realm with nothing but a couple of realm-owned camps has something to sell and something to eat on day one.

`make seed-check` runs the tick over a seeded, player-less world for a simulated thirty days and reports each realm's gauge, treasury and stores. A seed in which realms starve with no players in the world fails the check. The realms a new player can arrive at (§20) must show funded bids for tier 1 goods throughout.

---

## 15. Realm markets [NEW]

### 15.1 What a realm market does

A realm buys goods it has a demand line for, into its stores, up to the cap. It sells goods from its stores that are above the reserve. Trading requires `current_realm_id` to be that realm. There is no distance term in any price at a realm's own market.

### 15.2 The price curve

For a line with stock `s` and cap `C` (line units), the bid multiplier is

```
bid_mult(s) = f + (c − f) × (1 − s/C)^k
```

*Illustrative defaults:* `f = 0.33`, `c = 2.1`, `k = 3`, giving 2.10× the reference price when empty, 1.08× at a quarter full, 0.55× at half, and 0.33× when full. The three parameters are economy settings.

Trades are priced by integrating over the quantity, never at the spot price. For a move of the line's stock from `a` to `b`:

```
F(a, b) = f × (b − a) + (c − f) × C / (k + 1) × [ (1 − a/C)^(k+1) − (1 − b/C)^(k+1) ]
```

| Trade | Gold |
|---|---|
| Player sells `q` units of an item with weight `w` | `floor( (reference_price / w) × F(s, s + q·w) )` paid by the realm |
| Player buys `q` units | `ceil( (1 + m) × (reference_price / w) × F(s − q·w, s) )` paid to the realm |

`m` is the margin (*default* 25%, node override allowed). The ask is always the bid times `1 + m` over the same stretch of the curve, so buying from a realm and selling straight back loses exactly the margin on any quantity, and rounding always favours the realm. The engine has no way to express a crossed quote.

Example with the defaults, reference price 10, cap 1,000, stock 100: selling 500 units pays 4,439 gold. At the spot price it would have been 8,101.

`quote(ctx, item, side, quantity)` is a pure function over an explicit context `(reference_price, w, stock, cap, reserve, f, c, k, m, budget, treasury)`. It is computed with decimal arithmetic at fixed precision so both databases and all platforms agree.

### 15.3 Limits on a trade

Selling to the realm:

- The item must belong to a line with draw above zero, else `NO_DEMAND`.
- The quantity may not take the line above its cap: `STORES_FULL`.
- The gold may not exceed the line's budget or the treasury: `UNFUNDED_DEMAND`. The response carries the largest fundable quantity.

Buying from the realm:

- Only stock above the reserve is for sale, and only what exists of that item: `NOT_FOR_SALE`.
- The buyer needs the gold and the inventory room: `INSUFFICIENT_GOLD`, `INVENTORY_FULL`.

Every trade is all-or-nothing and carries a `limit_gold` (the least the seller accepts, or the most the buyer will pay). A quote that has moved past it fails with `PRICE_MOVED` and changes nothing.

### 15.4 Budgets

One treasury, many hungers. At step 10 of each tick the treasury is divided across the lines:

```
weight(line) = (cap − stock) × unit reference value × (2 if stock < reserve else 1)
budget(line) = floor(treasury × weight / Σ weights)
```

A sale to the realm reduces both the treasury and that line's budget. Gold that arrives during a tick is allocated at the next one. The **funded quantity** of a line is the largest quantity the realm can buy within its budget and cap, found by bisection on the integral; it is what the market endpoint publishes. A realm with an empty treasury publishes no bids.

### 15.5 What is visible

Everything, from anywhere, to any logged-in player:

`GET /realms/{id}/market` returns, per line: selector, member items, stock, reserve, cap, draw, days of cover, spot bid, funded quantity and its total price; per item for sale: quantity above the reserve and spot ask; **shortfalls** (lines below the reserve that the realm cannot fund, with the amount missing); the decay stage and gauge in days; and the **treasury band**.

The treasury band has five buckets, by how many days of the realm's upkeep the treasury could buy at reference prices (*defaults:* under 1, 1–3, 3–7, 7–14, over 14), with 10% hysteresis so it does not flicker. The raw balance is never returned by any endpoint.

`GET /realms/{id}/market/quote?item_id=&side=&quantity=` returns the exact gold for that trade and the largest quantity currently tradable.

### 15.6 Endpoints that move things

- `POST /realms/{id}/market/trade {item_id, side, quantity, limit_gold}`: presence required.
- `POST /realms/{id}/treasury/gift {gold}`: presence required. A plain transfer from a player to a treasury.

---

## 16. Trade between realms [NEW]

### 16.1 Who takes part (D10)

A realm buys or sells by caravan only while it holds an active tag with `effects.caravan_access`. Isolated realms never do. A frontier realm without a road depends entirely on players.

### 16.2 Remoteness

`remoteness(a, b)` is the total `base_time_s` of the cheapest path between two realms over edges with `min_travel_level = 1`, expressed in hours. It is a property of the pair. The map is content, so the all-pairs table is computed once at boot. Realms with no such path cannot trade.

### 16.3 The pass

A balancing pass runs every `caravan.pass_every_ticks` ticks (*default* 6), driven by the scheduled job and recorded in `world_state.last_caravan_pass` so it is never run twice. Missed passes are not replayed.

Buyers are taken hungriest first (highest gauge, then realm id). For each buyer, its lines below the reserve are taken in order of largest draw by reference value. For a line:

```
need = reserve − stock − in_transit              # what is already on the way is not bought twice
```

For each realm that has caravan access, a route, and stock of a matching item above its own reserve, the buyer works out a candidate shipment of `q` units:

| Term | Value |
|---|---|
| Goods cost | The seller's ask for `q`, by the integral of §15.2 |
| Caravan fee | `ceil(reference value of q × caravan.fee_pct_per_hour × remoteness / 100)`, paid to the seller's treasury |
| Loss | `1 − Π over route edges (1 − edge loss)`, where `edge loss = base_loss_pct × (1 − reduction)` and `reduction` is the summed `edge_loss_reduction_pct` of the active tags of the two realms the edge joins, capped at 100% |
| Delivered | `floor(q × (1 − loss))` |
| Delivered unit cost | `(goods cost + fee) / delivered` |

`q` is the largest quantity that satisfies all of: delivered ≤ need; `q` ≤ the seller's excess; goods cost + fee ≤ the buyer's treasury; goods cost + fee ≤ what the buyer would itself bid for the delivered quantity (its own integral, §15.2); and the buyer's and seller's remaining `caravan.capacity_value_per_pass`.

The buyer takes the candidate with the lowest delivered unit cost. Ties go to the smaller remoteness. If no candidate has `q ≥ 1`, the line is skipped.

On dispatch, in one transaction with both realms locked in id order: gold moves from the buyer's treasury to the seller's; `q` leaves the seller's stores; a shipment row is written. Loss is applied as its expected value, with no dice.

```
realm_shipments (id, from_realm_id, to_realm_id, item_id, quantity_sent, quantity_arriving,
                 goods_gold, fee_gold, dispatched_at, arrives_at, status)
```

`arrives_at = dispatched_at + remoteness × caravan.time_mult`. The goods are added to the buyer's stores at step 0 of the first tick at or after `arrives_at`. Until then they count in the buyer's `in_transit`.

A caravan always costs the buyer more per delivered unit than the seller's ask, takes time, and loses goods. A player who carries the same goods pays none of the three, which is the hauler's margin.

`caravan.fee_burn_pct` (ships at 0) destroys that share of the fee instead of crediting the seller.

---

## 17. The global player market [NEW]

Designed in v0.6–v0.7 and never built. Restated here in full with the vision's adjustments.

### 17.1 Model

One order book per good for the whole world. Matches move goods and gold instantly. Instanced items are not traded here (§19.5).

- **Buy order** `{item_id, quantity, unit_price}`: the full gold is escrowed at creation.
- **Sell order** `{item_id, quantity, unit_price}`: the goods are escrowed at creation.
- **Matching** is continuous with price-time priority. A new order sweeps crossing resting orders best price first, oldest first within a price, trading at the resting order's price. Any remainder rests at its own price. A buyer who crosses at a better price gets the difference back into the slot.
- One insert is one transaction, with row locks on the swept orders taken in price-time order.

### 17.2 Slots

```
market_orders (id, character_id, side, item_id, unit_price,
               quantity, quantity_remaining,
               escrow_gold_remaining, fill_items, fill_gold,
               status, realm_id, created_at, expires_at, closed_at NULL)
market_matches (id, maker_order_id, taker_order_id, buyer_character_id, seller_character_id,
                item_id, quantity, unit_price, tax_gold, burned_gold, tax_realm_id, matched_at)
```

The order row is the slot. `status` walks `open → collectable → closed`:

1. **open**: on the book. Escrow flows out as it fills; fills accumulate in `fill_items` or `fill_gold`.
2. **collectable**: fully filled, cancelled or expired. Off the book. The slot is still occupied by whatever is waiting.
3. **closed**: collected and empty. The slot is free.

Slots in use are the character's orders that are not `closed`, checked against the `order_slots` cap inside the insert transaction. Fills on an open order may be collected early without closing it.

Nothing enters an inventory or wallet except through collection. Inventory caps therefore gate collection and never a fill; a collect that does not fit moves what fits and leaves the rest in the slot.

Orders expire after `market.order_days` (*default* 14). The scheduled job moves expired orders to `collectable` and purges `closed` orders past a retention window. `market_matches` is the durable history, which is why it carries both character ids.

### 17.3 Endpoints

- `GET /market/book/{item_id}?depth=`: aggregated price levels, both sides. Available from anywhere.
- `GET /market/orders/me`, `GET /market/history/me`.
- `POST /market/orders {side, item_id, quantity, unit_price}`: reports immediate fills.
- `POST /market/orders/{id}/cancel`
- `POST /market/orders/{id}/collect`

### 17.4 Seller tax

Each match takes `market.tax_pct` (flat, global) from the seller's proceeds, rounded up. It is credited to the treasury of `market_orders.realm_id` of the **sell** order: the realm the seller was in when the order was created. `market.tax_burn_pct` (ships at 0) destroys that share of the tax instead.

There is no per-realm tax modifier.

### 17.5 Access

| Operation | Needs the current realm to have market access |
|---|---|
| Viewing books, own orders, history | No |
| Creating an order | Yes: `NO_MARKET_ACCESS` |
| Cancelling | No |
| Collecting | **Yes (D15, see below)** |

V§9.2.6 says the tag "only gates creating orders". Read literally, a player could place a buy order in town, walk into the wilderness and collect the goods there, which removes the cost of leaving the road that V§9.2.5 says the gate exists to create. This design gates collection as well. Cancelling stays free so that a stranded player can always pull an order; the remainder waits in the slot.

Market access is the `market_access` effect of an active tag of the realm. It is an access tag, so it survives Faltering and is lost only when the tag is shed.

### 17.6 Invariant

Every unit of gold is at all times in exactly one of: a wallet, buy-order escrow, a slot's uncollected proceeds, or a realm treasury. Every unit of a good is in exactly one of: an inventory, an equipment or belt slot, sell-order escrow, a slot's uncollected fills, a realm's stores, an estate larder, or a caravan. Property tests run random sequences of operations and check the totals; concurrency tests race two takers for one resting order on both databases.

---

## 18. Gold [NEW]

New characters have zero gold. The shipped starting grant is removed.

| | Path | Section |
|---|---|---|
| **Created** | Mint coinage, to a treasury | §14.8 |
| **Created** | World seed treasuries, once | §14.9 |
| **Created** | Tutorial seed gold, to a guest character in an isolated realm | §20 |
| **Destroyed** | Deleting a tutorial realm and its treasury | §20 |
| **Destroyed** | Tax burn share and caravan-fee burn share (both ship at 0) | §17.4, §16.3 |
| **Idle** | Gold held by players who stop playing | — |

Treasury inflows: seller tax, sales to players, caravan sales and fees, project kickoff gold, upgrade vote fees, estate sales, gifts, coinage. Treasury outflows: purchases from players, caravan purchases and fees, estate buy-backs on surrender.

A `gold_ledger` table records every creation and destruction with its cause. `GET /admin/economy` (operator-only) reports world gold by holder type and the ledger totals; the conservation test compares the two.

---

## 19. Exploration and keys [NEW]

### 19.1 Instanced items

Goods are fungible rows of `(character, item, quantity)`. A key is not: each one has its own rolled contents.

```
item_instances (id, kind, template_id, holder_character_id,
                discovered_by_character_id, discovered_by_name,
                realm_id, payload JSON, uses_total, uses_remaining,
                state, bound_at NULL, created_at)
state: active | deprecated | invalid | depleted
```

`kind` is `key` for now; the table is general so that other one-of-a-kind items (estate blueprints, V§8.4) can use it later. `discovered_by_name` is copied at discovery so the name survives renames and deletions. Each instance takes one inventory slot.

### 19.2 Content

```
discovery_template := {
  id, name, flavour, rarity,
  kind: "gather" | "combat",
  gather: {skill_id, tier, unlock_level, base_cycle_ms, outputs, xp, tool_class}    # an inline action
        | null,
  combat: {combatant_id} | null,
  uses:  {min, max},                 # gathering cycles, or combatant spawns
  keys:  {min, max},                 # keys per discovery
  requires_realm_tags: [tag_id]
}

exploration action := an ordinary action (§6.2) of the exploration skill, plus
  discovery_chance,                              # per cycle, small
  table: [{template_id, weight}],
  consumable_effects: [{item_id, chance_pct | weight_shift}]
```

Exploration actions are listed in `node.actions` like gathering spots, so content decides where exploring is possible. Their `requires.skill_levels` carry the cross-skill gates (a gathering minimum to recognise the find, a combat minimum to survive). Cycles are long and `discovery_chance` low by content, so that a night's exploring yields a key or two.

### 19.3 A discovery

Exploration runs on the uniform resolver. Each cycle grants XP; with probability `discovery_chance` (after any consumable effect) it also makes a discovery:

1. Pick a template from the table. Weights are shifted toward rarer templates by the Exploration tier benefit (§8.3) and by the character's tier in the template's gating skills.
2. Roll the number of keys in `keys`, plus the tier benefit's `keys_per_discovery_bonus`.
3. For each key, roll its own `uses` and any ranged output values independently, and create an `item_instances` row held by the explorer, with `realm_id` the current realm.

Keys from one discovery share a template and nothing else. If the inventory is full the key is lost, by the normal overflow rule, and the summary says so.

### 19.4 Using a key

`POST /actions/start {key_id}` starts the key's action. Requirements:

- The character holds the key, its state is `active` or `deprecated`, and `uses_remaining > 0`.
- The character is in the key's realm.
- The character meets the inline action's `unlock_level` and `tool_class` (gather) or the combat engagement rule (combat).

The first use sets `bound_at`; a bound key can never be listed or transferred.

- **Gather keys** run on the uniform resolver with the cycle count clipped to `uses_remaining`; each cycle uses one.
- **Combat keys** run on the combat resolver; each spawn of the combatant uses one, counted when the encounter begins.

At zero uses the state becomes `depleted` and the action ends with reason `KEY_DEPLETED`. A depleted key stays in the inventory as a trophy until `DELETE /keys/{id}`, which the holder may call on any key they hold.

Access is private: the key's action exists only for its holder, and nothing about it is added to the realm.

### 19.5 The key market (D13)

```
key_listings (id, instance_id UNIQUE, seller_character_id, price_gold, realm_id,
              status, created_at, sold_at NULL, buyer_character_id NULL)
```

- Fixed price, buy-out only. No bids, no partial fills.
- Only unbound keys in state `active` may be listed. A listed key leaves the seller's inventory.
- Listing and buying require market access in the current realm, as for the global market. Viewing does not.
- Listings count against the `key_listings` cap, not order slots.
- On purchase the buyer pays the price; the seller receives it less the same seller tax, credited to the treasury of the realm the seller was in when listing. The key goes straight to the buyer's inventory, so the buyer needs a free slot.
- `GET /keys/market?realm_id=&class=&item_id=&kind=` browses by realm, by goods class or exact good (matched against the template's outputs or the combatant's drop table), with the key's uses and rolled values shown.
- Cancelling returns the key if the seller has a free slot.

### 19.6 Realm transitions

When a transition starts (§12.6), every key with that `realm_id` in state `active` becomes `deprecated`. It still works; the client marks it. Listed deprecated keys stay listed and are flagged.

When the transition completes, every such key becomes `invalid`. Running actions on them end with reason `KEY_INVALIDATED`. Open listings are cancelled and the keys returned. Invalid keys remain as trophies.

---

## 20. New players and Tutorial Island [NEW]

### 20.1 Guest accounts [CHANGE to the auth service]

- `POST /auth/guest` creates a user with no email and no password, flagged `kind = guest`, and returns the usual access and refresh tokens. The access token carries the `kind` claim.
- `POST /auth/upgrade {email, password}` turns the same user into a full account. The user id does not change, so the character carries over.
- Guest users with no activity for `auth.guest_ttl_days` (*default* 14) are purged, along with their characters and tutorial realms.
- Guest creation is rate-limited per IP by the existing limiter.

### 20.2 The island

`POST /characters {name}` no longer takes a starting realm. It creates, in one transaction:

- the character, with zero gold and `tutorial_step` set to the first step;
- two isolated realm instances owned by that character, from the templates `tutorial.realm_1` and `tutorial.realm_2` (D7);
- a starter estate of form `progression.tutorial_camp_form`: mobile, no bonuses, no upkeep.

The character starts in the first tutorial realm. The map pack holds one edge between the two tutorial templates and none from either to the world; on the island, an edge between templates is resolved to the character's own instances. Departure (below) is the only way off. Both realms run the ordinary engine: actions, combat, travel between the two, projects and tags. Because they are isolated they have no market, no upkeep, no decay and no caravans, and their owner is the only character who can ever be in them.

The intended run, all of it content:

1. **Realm 1.** Gather; make clothes and a club; fight; make food. Travel the one edge to realm 2.
2. **Realm 2.** On arrival the tutorial grants seed gold equal to the kickoff cost of the raft-site project. The player kicks off the project, contributes its goods, and waits out a short build. The site's facility tag unlocks the raft action. Building the raft is a transform of the starter estate into the raft form, the first real mobile estate.
3. **Leaving.** `POST /tutorial/depart {destination_realm_id}` requires the raft, a full account (`ACCOUNT_REQUIRED` for a guest), and a destination from `tutorial.arrival_realms`. It sets the character's gold to zero, moves the character and estate to the destination, deletes both tutorial realms and their treasuries, and clears `tutorial_step`.

The seed gold is created in an isolated realm, spent into that realm's treasury, and destroyed with it. No gold reaches the world. Zeroing the wallet at departure is a guard, not the mechanism.

### 20.3 Steps and hints

```
tutorial.steps := [{id, hint, done_when}]
done_when := {has_item | skill_level | equipped | in_realm | tag_present | estate_form | project_kicked_off}
```

`tutorial_step` advances lazily whenever the profile is resolved and the current step's condition holds. The client shows the current hint. Steps are sized by content to finish in a few cycles each. Nothing prevents a player from doing other things on the island; the steps only guide.

---

## 21. Data model (consolidated)

Auth database: `users` gains `kind` (`guest` | `full`) and nullable credentials; otherwise as shipped.

Game database. Development data is wiped; migrations may be destructive.

| Table | Status | Notes |
|---|---|---|
| `players` | SHIPPED | |
| `characters` | CHANGE | `realm_id` → `current_realm_id`; add `stance`, `hp`, `hp_updated_at`, `tutorial_step`, `last_kickoff_at` |
| `character_skills` | CHANGE | `xp` to 64-bit; levels to 100 |
| `active_actions` | CHANGE | add `key_instance_id NULL`; `meta` now carries resolver state |
| `inventories` | SHIPPED | |
| `currency` | CHANGE | starting gold 0; `premium` stays dormant |
| `reward_log` | SHIPPED | `details` carries resolver summaries |
| `character_equipment` | NEW | `(character_id, slot, item_id, quantity)`; quantity used by `utility` |
| `character_belt` | NEW | `(character_id, slot_index, item_id, quantity, trigger JSON)` |
| `character_buffs` | NEW | `(character_id, item_id, expires_at)` for buffs outside combat |
| `item_instances` | NEW | §19.1 |
| `key_listings` | NEW | §19.5 |
| `estates` | CHANGE | §13.1 |
| `estate_upgrades`, `estate_ownership_history` | SHIPPED | |
| `estate_larder` | NEW | `(estate_id, item_id, quantity_milli)` |
| `realm_state` | CHANGE | §12.1 |
| `realm_edges` | **DROP** | progress model removed |
| `realm_projects` | **DROP** | replaced by runs |
| `realm_project_runs` | NEW | §12.3 |
| `realm_contributions` | CHANGE | add `run_id`; `character_id` nullable (the realm) |
| `realm_tags` | NEW | §12.4 |
| `realm_votes`, `realm_vote_eligibility` | NEW | §12.5 |
| `realm_stores` | NEW | §14.1 |
| `realm_lines` | NEW | derived, §14.2 |
| `realm_shipments` | NEW | §16.3 |
| `market_orders`, `market_matches` | NEW | §17.2 |
| `gold_ledger` | NEW | `(id, cause, amount, realm_id NULL, character_id NULL, at)` |
| `world_state` | NEW | single row: `seeded_at`, `last_caravan_pass`, content version at seed |

Database rules [SHIPPED]: no engine-specific SQL outside a thin dialect layer; row locks by `SELECT … FOR UPDATE` on PostgreSQL and an immediate writer transaction on SQLite; any operation touching two realms locks them in id order.

---

## 22. API (consolidated)

All game endpoints need a valid access token except where marked public. Every read of a character runs `resolve_character` first; every read or write of a realm runs `resolve_realm` first.

| Area | Endpoint | Status |
|---|---|---|
| Content | `GET /content/manifest`, `GET /content/{pack}` (public) | SHIPPED; pack list per §4.2 |
| Map | `GET /map` (public) | CHANGE |
| Auth | `POST /auth/guest`, `POST /auth/upgrade` | NEW |
| Character | `POST /characters {name}` | CHANGE |
| | `GET /characters/me`, `GET /characters/me/inventory` | CHANGE: adds hit points, stance, equipment, belt, tiers, capped and uncapped bonus totals, tutorial step |
| | `PUT /characters/me/stance` | NEW |
| Equipment | `POST /equipment/equip`, `POST /equipment/unequip`, `PUT /equipment/utility`, `PUT /equipment/belt/{slot}` | NEW |
| Actions | `GET /actions/available`, `POST /actions/start`, `GET /actions/poll`, `POST /actions/stop` | CHANGE: requirements report, `key_id`, combat |
| Travel | `GET /travel/preview`, `POST /travel/start` | NEW |
| | `GET /characters/me/relocate/preview`, `POST /characters/me/relocate` | **REMOVE** |
| Estates | `GET /estates/me`, `POST /estates/me/upgrades/{id}`, `POST /estates/me/transform` | SHIPPED, with §13.3 changes |
| | `POST /estates/build`, `POST /estates/{id}/buy`, `POST /estates/me/surrender`, `POST /estates/me/larder` | NEW |
| Realms | `GET /realms`, `GET /realms/{id}` | CHANGE: node, tags, stage, gauge, lines short, active run, open vote, transition |
| | `GET /realms/{id}/estates`, `GET /realms/{id}/tags/{tag_id}` | NEW |
| Projects | `POST /realms/{id}/projects/{project_id}/kickoff`, `POST /realms/{id}/project/contribute` | CHANGE (was `/contribute`) |
| Votes | `POST /realms/{id}/upgrades/{upgrade_id}/call`, `GET /realms/{id}/vote`, `POST /realms/{id}/vote {choice}` | NEW |
| Realm market | `GET /realms/{id}/market`, `GET /realms/{id}/market/quote`, `POST /realms/{id}/market/trade`, `POST /realms/{id}/treasury/gift` | NEW |
| Global market | §17.3 | NEW |
| Keys | `GET /keys/me`, `DELETE /keys/{id}`, `GET /keys/market`, `POST /keys/market`, `POST /keys/market/{id}/buy`, `POST /keys/market/{id}/cancel` | NEW |
| Tutorial | `POST /tutorial/depart` | NEW |
| Operator | `GET /admin/economy` | NEW |

---

## 23. Cross-cutting concerns

### 23.1 Transactions and locking [SHIPPED, extended]

One request, one transaction. A character-scoped mutation locks the character row. A realm-scoped mutation locks the realm row; if it also touches a character, the character is locked first, then the realm. Two realms are locked in id order. An order insert locks the swept orders in price-time order. Estate purchase, surrender and build lock the character, then the realm, then the estate.

### 23.2 The scheduled job [NEW]

One APScheduler instance in the game service. Jobs, all idempotent:

| Job | Cadence | Does |
|---|---|---|
| Realm tick | every tick | `resolve_realm` for each non-isolated realm |
| Caravan pass | every `pass_every_ticks` ticks | §16.3 |
| Order expiry and purge | every few minutes | §17.2 |
| Guest purge | daily | §20.1 |

The job is a liveness driver. It is never the only thing that advances a realm; any request that reads a realm resolves it first, so a late or crashed job cannot make a quoted price stale. With more than one game-service process, the job runs under a database advisory lock so only one instance fires.

### 23.3 Scale notes

- Combat offline resolution is the only per-character loop; it is bounded (§10.5).
- The realm tick touches every estate with a tick profile in the realm. Basic mobile estates have none and are skipped. This is the one place where work grows with players; it is set-based and hourly. If it becomes heavy, the tick can be split per realm across the hour without changing semantics.
- The all-pairs remoteness table and the shortest-path cache are computed at boot from content.

### 23.4 Testing [SHIPPED, extended]

Existing: Hypothesis property tests for resolve associativity and recipe conservation, seeded drop statistics, two-session lock contention, both databases in CI.

To add, by section:

- §5: the XP table sums to 10,000,000; level 93 is the halfway level; tier thresholds.
- §7: the vision's 1.452 example; group multiplication; the XP cap; negative groups.
- §8: every cell of both tables; a tier-up inside a batch.
- §10: hit probability bounds; pools drain once and refill only on respawn; pool remainder lost on kill; ranged stops without ammunition; defeat ends the action; offline equals online for the same seed.
- §11: no between-realms state; a stopped journey leaves the character in a realm; boat cannot relocate over land.
- §12: one active run per realm; kickoff daily limit; erosion and failure; vote secrecy (no per-character choice stored); weights; early close; fail on tie and on no votes.
- §14: tick idempotence (`resolve_realm` twice equals once); catch-up equals step-by-step; tick order; Strained has no effect; shed order; regression restamps tags; mint is the only gold creator.
- §15: `ask = bid × (1 + m)` for every quantity; round trip never profits (property test over random stores and quantities); integral equals the summed unit prices within rounding; budgets never exceed the treasury.
- §16: nothing bought twice while in transit; nearer seller preferred at equal ask; caravan never cheaper than the seller's ask.
- §17: conservation invariant; price-time priority; maker price; two takers racing.
- §19: keys never stack; binding; invalidation stops actions.
- §20: no gold leaves the island.

### 23.5 Security [SHIPPED]

Server-side validation of everything; JWT middleware; per-IP rate limiting on auth. Rate limiting of game mutations is still to do and belongs with hardening.

### 23.6 Observability [SHIPPED, extended]

Structured JSON request logs with request ids. Add counters: ticks run and their duration, gold minted, gold by holder type, matches and tax, realm trades, caravan shipments and losses, tags shed, regressions, keys discovered.

---

## 24. Client [CHANGE]

The shipped shell stays: sidebar, a global action strip driven by one 4 Hz clock, boundary-aligned polling with jitter, welcome-back modal, reward toasts, inventory grid, Estate, Realm and Map routes.

| Panel | Work |
|---|---|
| Skills | Tier badge, proficiency and taper shown per action, locked-reason list, capped XP bonus display. Crafting renamed Manufacturing. |
| Combat | Location and combatant picker, stance, hit points, belt and utility set-up, encounter log, offline summary. |
| Equipment | Slot doll, equip and unequip, requirement display. |
| Map | Decay stage and treasury band per realm, route preview with time and supplies, journey progress. |
| Realm | Node and tags with credits, gauge and short lines, active project with contribution form, upgrade list with required tags, vote panel with participation list, transition countdown, estate list with sale prices. |
| Realm market | Lines with stock, reserve and cap, bids with funded quantity, items for sale, shortfalls, quote-then-confirm trade form, presence state. Viewable for any realm. |
| Global market | Book view, order form, slots with collect, history, access state. |
| Estate | Form and upgrade graph, larder with days of cover, gauge, build, buy and surrender flows with confirmation. |
| Keys | Held keys with rolled values and state, key market browser. |
| Tutorial | Hint banner, guest-to-account upgrade prompt at departure. |

---

## 25. Not in this design

- WebSockets or server push.
- More than one character per account; deletion or rename.
- More than one estate per character. The schema allows it; no endpoint does.
- Player-to-player estate sales, inheritance, or direct trade between players outside the two markets.
- Guilds, chat, friends.
- Premium currency mechanics.
- Mutable map state (blocked roads, events). Edge loss reduction comes only from realm tags.
- Admin tooling beyond the economy report.
- Real content and balance. Placeholder content is extended only as far as tests need.

---

## 26. Build order

Workstreams, not prompts. Each row can be broken into PR-sized steps in the next session. "Needs" lists what must exist first.

| # | Workstream | Contents | Needs |
|---|---|---|---|
| A | **Foundation reset** | Destructive migration baseline; new XP table and level 100; `progression` and `economy` packs; tiers on actions and items; selectors; `crafting` → `manufacturing`; zero starting gold | — |
| B | **Bonus model** | Source groups, multiply across groups, `cycle_speed_pct`, XP cap, proficiency and taper, tier as a segment boundary, content lint | A |
| C | **Tags and requirements** | `tags` pack, emission from nodes, forms and upgrades, facility requirement on actions, availability report | A |
| D | **Presence and travel** | `current_realm_id`, map edge shape, resolver interface, travel resolver, visit and relocate, removal of the relocation endpoints | B, C |
| E | **Realm development** | Node shape, project runs, kickoff, presence-gated contribution, build phase, tag stack, credits; removal of edge progress | C, D |
| F | **Estates** | Mobility, build, buy, surrender, valuation, larder, realm-owned estates, vote weight | D, E |
| G | **Realm economy** | Stores, demand lines, tick, gauge, stages, shedding, regression, project overlay and erosion, spoilage, `world_seed`, scheduled job | E, F |
| H | **Realm market** | Curve and integral, quote, trade, budgets, visibility, treasury band, gift | G |
| I | **Global market** | Order book, slots, tax, expiry, access gate, conservation tests | C, D |
| J | **Mint and gold** | Bullion class, mint line, coinage, `gold_ledger`, economy report | G, H |
| K | **Votes and transitions** | Call, eligibility snapshot, secret ballot, close, transition, reserve rise | E, F, G |
| L | **Caravans** | Remoteness table, pass, shipments, loss, caravan access | G, H |
| M | **Equipment** | Slots, gear as group G, tools, belt, utility | B |
| N | **Combat** | `combatants` pack, stats, combat resolver, streams and pools, stance, hit points, offline summary | M, D |
| O | **Exploration and keys** | Instanced items, discovery, key actions, key market, transition invalidation | N, I, K |
| P | **Tutorial and guests** | Guest auth, realm instances, isolated flag, steps, departure | E, F, M, N |
| Q | **Client** | Runs alongside each workstream; panels per §24 | each |
| R | **Hardening** | Mutation rate limits, load sanity, counters, seed-check in CI | all |

A through C are prerequisites for nearly everything and should go first, in that order. After D, three lines can proceed in parallel: E → F → G → H → J/K/L (the world), I (the player market), and M → N (combat). O and P come last because they sit on top of the rest.

The smallest slice that shows the economy working end to end is A–H plus J: a seeded world in which players gather, sell to realms, and realms eat, mint and decay.

---

## 27. Decision log

Carried forward and still in force:

- The offline cap ends the action after granting only in-budget cycles.
- The reward feed is at-most-once.
- Drop rates are exposed in content.
- Inventory overflow takes precedence over input exhaustion in the same cycle.
- Content endpoints are unauthenticated.
- Reuse of a refresh token revokes all of that user's tokens.
- Level-ups are resolved in segments.
- A backwards clock is a no-op.
- #20: `WOULD_ORPHAN_UPGRADES` excludes installed-upgrade bonuses from the destination's capacity.
- #24: the player market is a global order book with price-time priority at the maker's price.
- #27: `market_listings` becomes `order_slots`.
- #28: inventory caps gate collection, never fills.
- #29: the order row is the slot.

Superseded by this version (v0.7 log numbers):

- Project tiers declaring cap bonuses: projects have no tiers; tags carry cap bonuses.
- Additive stacking within a type across all sources: §7.2.
- #18, nine served packs: §4.2.
- #19 and #22, relocation columns and origin identity during relocation: relocation is a journey.
- #21, no edge awards during a transition: edge awards no longer exist. The rule that nothing starts during a transition is kept in §12.6.
- #23, contributions are not residence-restricted: still true, but presence is now required.
- #25, interim residents-only presence at the realm market: §11.2.
- From v0.7: `M[realm]`, deficit-weighted procurement between realms, `map_edge_state`, the `shed()` placeholder.

Still retired: #26, `market_tax_pct` as a modifier type.

New in v0.8: D1–D15 in §2.3.

---

## 28. Vision traceability

| Vision | Subject | Design |
|---|---|---|
| V§3.1–3.3 | Levels, curve, time budget, XP cap | §5.1, §5.2, §7.3 |
| V§3.2, 3.4, 4.4 | Tiers, proficiency, taper | §5.3, §8 |
| V§3.5, 3.6 | Unlock cadence, access | §5.2 (lint), §6.2 |
| V§3.7, 4.5 | Combat levelling, streams and pools | §10.3–10.6 |
| V§3.8 | Travel and Exploration tier benefits | §8.3 |
| V§4.1–4.3 | Skill categories, facilities | §6 |
| V§4.6 | How bonuses combine | §7.1–7.2 |
| V§5 | Goods, tiers, classes, reference price | §4.2, §4.3, §5.3 |
| V§6 | Combat loop, offline, regeneration | §9.4, §10 |
| V§7.1–7.2 | Realms, types, tiers | §12.1–12.2 |
| V§7.3, 7.6 | Upkeep, goods pyramid | §14.2 (content authors the pyramid through node and tag upkeep) |
| V§7.4, 7.7.1 | Projects | §12.3–12.4, §14.4 |
| V§7.7.2 | Upgrades and votes | §12.5–12.6 |
| V§7.5, 7.7.3, 9.4.11–12 | Decay | §14.6–14.7 |
| V§8.1–8.5 | Estates, mobile and fixed, upgrade graph | §13.1–13.3 |
| V§8.6, 8.8 | Estate production, upkeep, larder, decay | §13.6–13.7, §14.5 |
| V§8.7 | Estate sales | §13.4 |
| V§9.2 | Global market | §17 |
| V§9.3, 9.4.8 | Realm market and prices | §15 |
| V§9.3.3 | Cold start | §14.9 |
| V§9.4.1–9.4.7 | Stores, reserve, cap, trade between realms | §14.1–14.4, §16 |
| V§9.4.9–9.4.10 | Tick order, spoilage | §14.5 |
| V§9.5 | Currency, mint, sinks, bootstrapping | §14.8, §18, §2.4 |
| V§9.6 | Archetypes | Supported by §11, §15, §16; no engine feature of their own |
| V§10 | Exploration and keys | §19 |
| V§11 | Travel and visiting | §11 |
| V§12.1–12.2 | New player, Tutorial Island | §20 |
| V§12.3 | Equipment | §9.2–9.3 |
