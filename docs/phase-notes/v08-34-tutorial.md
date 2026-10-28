## Built

- POST /characters now accepts only {name}. Its transaction creates a zero-gold
  character, first tutorial_step, two isolated RealmState instances with
  owner_character_id, and the progression.tutorial_camp_form estate in island 1.
  Concurrent and duplicate creation retain the existing identity/name errors.
- Added a strict public tutorial pack: two templates, arrival realms, raft-site
  project, raft form and ordered hints with all seven §20.3 condition kinds.
  Loader validates references, unique steps, camp properties and island/world
  edge separation. Profile resolution advances satisfied hints from persisted
  state; skill milestones derive levels from XP rather than trusting the cache.
- Instance addresses combine the template and owner UUID. Pure realm lookup and
  routing understand these addresses without database access or mutable global
  content aliases. Template destinations resolve to the traveller's own instances.
  World/tutorial crossings and foreign-instance travel are rejected. First-touch
  realm loading still never instantiates an isolated template.
- Private realm detail, estate and tag-credit reads require ownership. World
  lists/map retain their isolation filters. Realm markets, quotes, gifts and
  trades are excluded; global commodity/key market access explicitly excludes
  isolated instances even if content accidentally supplies an access tag.
  Scheduler/caravan filters and ordinary isolated project resolution remain intact.
- Arrival in island 2 atomically grants the raft-site kickoff cost once, with a
  tutorial_seed ledger row. Character.tutorial_seeded persists that one-time
  fact across repeat visits, independently of how quickly hints are completed.
- POST /tutorial/depart validates the raft, full account and configured arrival.
  Under character, sorted realm and estate locks it audits wallet/treasury/order
  gold as tutorial_destroy, settles listing custody and local discoveries,
  removes action references, audits stores/shipments and obsolete estate holdings,
  removes projects (including funded totals), contributions, tags, lines and
  votes, moves the character and raft, deletes both instances and clears progress.
  Shared cleanup helpers keep guest purge and departure consistent. Durable gold
  and goods audits have no foreign keys to deleted holders. Already-consumed
  project contributions are historical totals, not physical goods destroyed twice.
- Placeholder content teaches gathering, clothes/club crafting and equipping,
  a winnable dummy fight, making food from its drop, travel, project kickoff and
  funding, short construction, raft transformation and departure. The dummy's
  short fight does not depend on the unresolved zero-HP regeneration ruling.
- Activated arrival-realm funded tier-one bids at every simulated seed-check tick.
  The synthetic arrival workshop balances production/upkeep and starts below
  storage cap so funded bids persist through the thirty-day player-less run.
- Updated unrelated world fixtures to place characters directly in the world
  after API identity creation; their original mechanic assertions remain intact.
  Extended generated world accounting with tutorial_creation/tutorial_departure
  in OPERATIONS and the independent required set, preserving the gold-minus-ledger
  oracle and independently expected tutorial goods sinks.
- Added tests in test_tutorial.py:
  test_guest_completes_island_upgrades_and_departs_with_zero_gold_and_raft;
  test_island_visibility_and_travel_ownership;
  test_postgres_two_private_project_kickoffs_succeed;
  test_departure_audits_wallet_orders_stores_keys_and_rolls_back;
  test_seed_check_validates_arrival_bids_at_every_tick;
  test_each_tutorial_condition_advances_lazily (seven condition kinds).
  Updated test_concurrent_first_characters_create_independent_islands and added
  client test "creates a character with a name and no starting realm".

- SQLite make ci passes: auth 35, game 828, client 101, with dialect-specific
  skips. Formatting, lint, strict types, client build, script checks and content
  lint pass. Disposable SQLite db-reset, subsequent head upgrade, Alembic schema
  comparison, application lifespan/manifest smoke test and thirty-day seed-check
  pass. git diff --check is clean.

- Pre-review fix: the PostgreSQL realm-list locking regression now selects the
  two lowest non-isolated world ids, initializes only world rows, and expects
  only world response ids. Its observed lock wait and higher-id NOWAIT probe
  remain unchanged. The late-realm market regression now matches the enumeration
  SELECT with its isolation WHERE clause and explicitly creates a non-isolated
  late realm. The failure was a stale exact-SQL test hook, not a production
  enumeration/locking regression; retry and subsequent settlement assertions
  remain unchanged.

## Removed

- Starting-realm request field and client picker. Starting-realm validity tests
  now reject the obsolete field with INVALID_REQUEST; the concurrent shared-world
  initialization test now verifies independent private instances. The old missing
  realm parameter case is covered by strict-field rejection. No tests deleted.

## Design ambiguities resolved

- §12.1 / §20.2: use template:owner-UUID addresses for ephemeral instances. This
  preserves immutable content and pure routing while database ownership gates
  remain authoritative. Bare templates never create shared state.
- §20.3: conditions use {kind, id, quantity?}, with quantity defaulting to one.
  The final departure hint stays visible until departure explicitly clears it.
  Hints are guidance; departure checks the raft/account/destination, not hint order.
- §20.2 / §18: tutorial_seeded is a durable once-only marker independent of the
  current hint. It prevents revisiting island 2 from creating additional gold.
- §20.2 / §19: local discoveries and their listings disappear with their resource
  realms, with signed goods audits. Unrelated world keys remain held; a listing
  tied to a deleted realm is explicitly settled before deletion. Inconsistent
  foreign custody or action references abort atomically rather than orphaning it.

## Deviations

None.

## Ratification needed

None introduced. The earlier combat regeneration and commodity self-matching
questions remain unchanged.

## Hand-offs

- 35-client-keys-tutorial: load /content/tutorial, show the hint selected by
  profile.character.tutorial_step, and use the server's current_realm_id for realm
  APIs. Island travel accepts either the destination template from the tutorial
  pack or the owner's instance address; responses carry actual instance ids.
  World /map intentionally contains no tutorial edge. POST /characters is {name}.
  POST /tutorial/depart is {destination_realm_id}; refresh profile/estate/action
  queries after success. Handle ACCOUNT_REQUIRED with the guest-upgrade flow and
  observe the full token through /players/me as handed off by 33.
- 35-client-keys-tutorial: this prompt changes only the creation request/picker
  in the client. Island guidance, departure/upgrade controls and key UI remain
  yours; consume pack ids rather than hardcoding the synthetic tutorial content.
- 36-hardening: preserve owned-instance checks, once-only seed serialization,
  durable cleanup audits, the two-session kickoff regression and both generated
  operation coverage sets. Travel still conservatively locks world candidates
  and the caller's own instances, as earlier phases did for world candidates.

## New error codes

- ACCOUNT_REQUIRED (403): a guest attempts departure with a raft.
- RAFT_REQUIRED (409): departure requires the configured raft estate form.
- NOT_IN_TUTORIAL (409): departure was requested after leaving the island.
- INVALID_ARRIVAL_REALM (422): destination is outside tutorial.arrival_realms.
- Reused UNKNOWN_REALM, NO_ROUTE, NO_MARKET_ACCESS and INVALID_REQUEST for
  isolation and obsolete starting-realm requests. No new dependencies.
