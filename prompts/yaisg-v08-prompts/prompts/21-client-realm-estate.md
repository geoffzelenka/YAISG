## Prompt 21 — Client: realm, projects, votes, estate

**ID:** `21-client-realm-estate` · **Workstream:** Q · **Needs:** 20 · **Design:** §24 (Realm, Estate)

### Goal

Expose realm development and estates to players.

### Build

1. **Realm panel**: node, type, tier, tags with credits; stage and gauge in days with short lines; active project with progress, stalled marker, kickoff form (costs, who may kick off, the reason it is unavailable) and contribution form; upgrades with required tags held or missing; vote panel with participation list, choice buttons and countdown; transition countdown; estate list with realm-owned sale prices.
2. **Estate panel**: form, mobility, tier, transforms graph, installed upgrades, larder with days of cover, gauge and stage; build, buy and surrender flows with an explicit confirmation that names what will be lost (D8, and the surrender payout or donation).
3. Presence state shown wherever an action needs it, with the travel shortcut to get there.

### Tests (vitest)

- Kickoff unavailable reasons; vote panel hides totals while open; build confirmation lists the mobile estate's upgrades; larder days of cover.

### Out of scope

Markets.

### Review focus

Every irreversible action is behind a confirmation; no treasury number appears.

