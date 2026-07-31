Prompt 2.2 — Character creation and profile

Implement §5.2 (minus inventory display polish) on top of the content system.

Server requirements:

Migrations for characters, character_skills, currency (gold + premium columns, premium untouched), estates, inventories per §6.2 — including the estate-table shape with its own UUID PK and upgrade_slots.
POST /characters {name, realm_id}:
Validate: player has no character (v1 one-character rule, §6.2), name 3–20 chars alphanumeric + spaces, globally unique (case-insensitive), realm exists in content.
Create character, one character_skills row per content skill at level 1 / 0 XP, currency row (starting gold from a config constant), and an estate in the chosen realm at level 1 with base estate_upgrade_slots from caps config.
Error codes: CHARACTER_EXISTS, NAME_TAKEN, INVALID_NAME, UNKNOWN_REALM.
GET /characters/me — profile: character, skills (xp, level, xp-to-next from the curve), gold, realm summary (id, name, tags, active modifiers), estate summary (level, slots, installed upgrades — empty for now). Returns 404 NO_CHARACTER if none, which the client uses to route to creation.
GET /characters/me/inventory — item stacks with quantities (empty for now).
Level derivation: single engine function level_for_xp(xp, curve); character_skills.level is a cached value always written through this function. Property test: monotonic, consistent with the table.

Client requirements:

Post-login routing: no character → character creation screen (name field + realm picker rendering realm names, tags, and modifiers from content); has character → main shell.
Profile panel (first real sidebar section, §9.1): character name, realm info, gold, and a skill list with level + XP progress bars computed from server-provided xp-to-next.
Sidebar: sections from §9.1 with dividers; Profile is live; all others remain "coming soon"; Exploration rendered disabled.

Tests: creation happy path; each error code; one-character enforcement under concurrent double-submit (two simultaneous requests → exactly one character); profile math for xp-to-next.
