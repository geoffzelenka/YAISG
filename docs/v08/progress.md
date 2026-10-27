# v0.8 pipeline progress

Prompt 00 is ready for review on its branch; merge commits are populated by the
orchestrator after approval/merge. “Ready for review” does not assert a merge or
an independent PostgreSQL green run inside the restricted coding sandbox.

| # | Prompt | Title | Status | Branch | Merge commit | Summary |
|---|---|---|---|---|---|---|
| 00 | `00-preflight` | Baseline alignment audit | done | v08/00-preflight | 6069863 | Baseline audited (94 OK / 6 DRIFT / 1 MISSING / 1 PARTIAL, no BLOCKER); FIX-HERE: GET /realms now locks realms in id order, PostgreSQL regression test; codebase map written. |
| 01 | `01-foundation` | Schema reset, XP curve, levels to 100, tiers, zero gold | done | v08/01-foundation | 2693109 | Single v08_0000_baseline migration; make db-reset; checked-in XP curve (sum 10,000,000) to level 100 with cached thresholds; progression pack with tiers; zero starting gold. |
| 02 | `02-content-model` | Goods, actions, selectors, categories, caps | done | v08/02-content-model | 48680db | Skill categories and fixed §6.1 skills; item tier/classes/reference_price; three-shape Selector with pure engine pay_selector; §6.2 action record with §5.3 tier validation; caps renamed to order_slots, key_listings, belt_slots added. |
| 03 | `03-bonus-model` | Source groups, multiplication, XP cap, proficiency, taper | done | v08/03-bonus-model | e70c574 | Five source groups multiplied with per-group floor; XP bonus cap 45% then taper; proficiency by tier distance feeds cycle speed only; §8 tables in progression pack; cycle_time_pct and market_tax_pct removed. |
| 04 | `04-content-lint` | XP-rate content lint | done | v08/04-content-lint | 46f38fb | Warning-only make content-lint (text + JSON): per-action rate vs target curve ±15%, exact-Fraction training ladders, §7.3 stack bound; lint settings in progression pack; non-fatal CI step. |
| 05 | `05-tags` | Tags, action requirements, availability report | done | v08/05-tags | b75ded2 | Tags and economy packs; pure active_tags with D11 stage effects; all-of realm tags; one unmet_requirements for start/resolve/availability incl. REQUIREMENT_LOST; profile shares the state loader. |
| 06 | `06-resolver-presence` | Resolver seam, current_realm_id, presence | done | v08/06-resolver-presence | 4d41518 | ActionResolver protocol + registry with UniformResolver (golden-verified against pre-refactor engine); current_realm_id; presence helpers; character-row lock on every resolve; /actions/poll and /actions/stop. |
| 07 | `07-travel` | Map edges, journeys, the Travel skill | done | v08/07-travel | b6a2192 | Map edges with terrain/level/one-way; Dijkstra routing with exact tie-breaks; step-wise journeys (TravelResolver) with supplies via pay_selector and flat Travel XP; relocation removed; offline equals online. |
| 08 | `08-client-skills-travel` | Client: skills, tiers, travel | done | v08/08-client-skills-travel | 87f63a7 | Skill panels with server tier/title, effective values and locked reasons; travel preview/start form with relocate mode; journey progress from server meta; resolver details in the reward feed without empty-journey toasts. |
| 09 | `09-development-graph` | Nodes, tag stack, transitions | done | v08/09-development-graph | defeb6e | Development nodes, realm tag stack with persistent seq, timed transitions; old edges/projects/contributions removed |
| 10 | `10-project-runs` | Project runs and resolve_realm | done | v08/10-project-runs | ddc37f1 | Project runs (kickoff/contribute/build/erosion/failure), realm_contributions with run id, resolve_realm bounded catch-up; main PG flake fixed by 10a |
| 10a | `10a-tick-batching` | Realm tick catch-up batching | done | v08/10a-tick-batching | 3805505 | Tick catch-up preloads RealmTickContext and flushes once (4 statements for 72 ticks); deadline=None on DB Hypothesis tests |
| 11 | `11-estate-forms` | Estate forms, transforms, realm-owned estates | done | v08/11-estate-forms | b63b9ac | Strict estate form graph, selector-paid transforms to realm treasury, realm-owned estates, vote weights; global slot base removed |
| 12 | `12-estate-ownership` | Build, buy, surrender, valuation, larder | done | v08/12-estate-ownership | 719ec0b | Valuation (cheapest tier-1 path, provider-priced goods), build/buy/surrender with treasury flows, deposit-only larder |
| 13 | `13-stores-lines` | Stores, demand lines, world seed | done | v08/13-stores-lines | 8099216 | Store due math, demand lines with most-specific membership, reserve/cap, private versioned world seed created once at boot |
| 14 | `14-realm-tick` | The realm tick and the scheduled job | ready for review | `v08/14-realm-tick` | — | Batched estate/store ticks and advisory-locked scheduler; overlay timing needs ratification. |
| 15 | `15-decay` | Gauges, stages, shedding, regression, seed-check | pending | — | — | — |
| 16 | `16-realm-pricing` | Realm market pricing and visibility | pending | — | — | — |
| 17 | `17-realm-trade` | Realm trade and treasury gift | pending | — | — | — |
| 18 | `18-mint-gold` | Mint and the gold ledger | pending | — | — | — |
| 19 | `19-votes` | Realm upgrade votes and transitions | pending | — | — | — |
| 20 | `20-caravans` | Trade between realms | pending | — | — | — |
| 21 | `21-client-realm-estate` | Client: realm, projects, votes, estate | pending | — | — | — |
| 22 | `22-client-realm-market` | Client: realm market and world health | pending | — | — | — |
| 23 | `23-global-market` | Global order book, slots, tax, access | pending | — | — | — |
| 24 | `24-market-lifecycle` | Order expiry, purge, world conservation suite | pending | — | — | — |
| 25 | `25-client-global-market` | Client: global market | pending | — | — | — |
| 26 | `26-equipment` | Equipment slots and gear bonuses | pending | — | — | — |
| 27 | `27-consumables-hp` | Belt, utility, buffs, hit points | pending | — | — | — |
| 28 | `28-combat-model` | Combatants, stats, the hit, stance, combat lint | pending | — | — | — |
| 29 | `29-combat-resolver` | The combat resolver | pending | — | — | — |
| 30 | `30-client-equipment-combat` | Client: equipment and combat | pending | — | — | — |
| 31 | `31-keys` | Instanced items, exploration, key actions | pending | — | — | — |
| 32 | `32-key-market` | The key market | pending | — | — | — |
| 33 | `33-guest-auth` | Guest accounts | pending | — | — | — |
| 34 | `34-tutorial` | Tutorial Island | pending | — | — | — |
| 35 | `35-client-keys-tutorial` | Client: keys, tutorial, guest upgrade | pending | — | — | — |
| 36 | `36-hardening` | Rate limits, counters, load, seed-check in CI | pending | — | — | — |
| 37 | `37-conformance` | Final design conformance audit | pending | — | — | — |
