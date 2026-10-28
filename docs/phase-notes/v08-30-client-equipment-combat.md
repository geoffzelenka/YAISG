## Built

- Added Equipment and Combat sidebar routes. The equipment doll displays all
  fourteen permanent slots, inventory choices, authored skill/tool requirements,
  concrete ring/arm sides, equip and unequip controls. Two-handed right-hand
  equipment blocks the left hand and explains displacement before equipping.
- Added shared belt and utility setup to both panels. Stack forms submit total
  quantities, healing HP thresholds or buff-missing triggers, and return stacks.
  Belt capacity combines the resolved cap with the equipped belt's positions;
  existing holders beyond a reduced capacity remain visible and returnable.
- Added location/combatant selection from content and server availability,
  persisted stance selection with authored XP shares, authoritative player HP,
  server cycle times and current opponent HP, pools and respawn wait. Encounter
  logs retain the last thirty poll summaries while the panel is mounted.
- Added combat summary headings alongside the existing recursive resolver-detail
  renderer. Ordered resolutions retain kills, defeats, damage, XP, consumed
  goods and loot in the encounter log, global rewards and welcome-back modal.
  OUT_OF_AMMO, DEFEATED and OFFLINE_CAP remain supported stop reasons, including
  DEFEATED with the current server's disputed regeneration behavior.
- Extended client content/profile types for equipment, consumables, belt,
  HP/timestamps, stance and combat progression settings. Setup and stance use
  the shared ApiError and refresh character/profile, inventory, availability and
  the shared action poll after success. Polls refresh authoritative HP even
  while idle; active polls also refresh consumable holdings and availability.
- Permanent equipment, belt and utility controls wait for action status and
  disable during combat with a reason. Stance remains changeable during combat.
  The server continues validating requirements, capacity and every transfer.
- Added Vitest cases:
  - `blocks the left hand for a two-handed item and permits removing the right hand`
  - `equips a two-handed item using the concrete right-hand slot and refreshes views`
  - `disables permanent gear, utility and belt controls during combat with a reason`
  - `submits healing thresholds and buff-missing belt triggers and clears stacks`
  - `assigns utility through its PUT endpoint and refreshes character holders`
  - `adds belt positions to the resolved cap and allows returning an unavailable position`
  - `uses server encounter availability, HP and stance and retains poll log entries`
  - `renders offline combat summary and %s` (all three combat stop reasons).

- Validation: repository-virtualenv `make ci` passes on SQLite: auth 15,
  game 750 with 22 dialect-specific skips, client 100. Formatting, lint,
  strict typing, production build, scripts and content lint pass. Existing
  migration/reset tests rebuild both services and check schema parity.
  `git diff --check` passes.

## Removed

- Replaced the Combat coming-soon sidebar entry. No tests, server behavior,
  content, schema fields or dependencies removed.

## Design ambiguities resolved

- §24 / §9.3: show belt positions as one-based labels and send zero-based API
  positions. An unavailable existing position supports return only, preserving
  the capacity-loss contract established by Prompt 27.
- §24 / §10.5: the encounter log is a bounded history of server poll summaries,
  rather than invented individual hit events. Pool numerator/denominator pairs
  are formatted for display only; no combat or HP simulation runs in the client.
- §24: share consumable setup between Equipment and Combat. Preserve the existing
  welcome-back threshold of more than five completed cycles and the ordered
  resolutions wrapper, including unknown nested resolver fields.

## Deviations

None.

## Ratification needed

No new questions. Prompt 29's zero-HP regeneration and combat XP multiplier/cap
questions remain unchanged. This client renders the server's DEFEATED outcome
without introducing a new defeat or XP rule.

## Hand-offs

- 35-client-keys-tutorial: combat-key actions may not have an ordinary content
  action id. Extend encounter identity and equipment combat-lock presentation
  for the key action projection when building the key UI. Current guards identify
  combat through the ordinary public action definitions.
- 36-hardening: preserve authoritative HP/holder refresh and setup locking when
  optimizing polling. Encounter history is local to the mounted panel; the
  existing global rewards drawer retains the shared session feed.

## New error codes

No new server codes. The new request hook retains server ApiError codes/messages;
EQUIPMENT_REQUEST_FAILED is its client fallback for an unstructured failure.
No dependencies added.
