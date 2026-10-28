## Built

- Added Play now on the auth entry screen, creating the normal guest session and
  routing through the existing auth and character guards. New sessions clear
  prior account query data; upgrading preserves the current character identity.
  Character creation retains Prompt 34's name-only request and no realm picker.
- Load and cache the public tutorial pack. The shell displays the hint selected
  by the server's tutorial_step, clears guidance after departure, and supplies
  island travel controls using pack template destinations. Island journeys default
  to relocating the camp so it is present for raft transformation. Realm APIs continue
  using the profile's actual instance address. The realm inspector includes the
  current private island alongside ordinary world inspection choices.
- Departure offers only configured arrival realms and sends
  destination_realm_id. ACCOUNT_REQUIRED displays an in-place account upgrade
  form and disables departure. Upgrade installs the new token and awaits
  /players/me before unlocking departure. A failed game confirmation can be
  retried without resubmitting already-saved credentials. Success refreshes
  profile, estate, action and other affected queries.
- Projects with empty contribution costs explicitly say they are fully paid at
  kickoff. Existing project controls display the whole kickoff payment and short
  build countdown, without a contribution form during construction. This follows
  Prompt 34's human ruling rather than adding a tutorial-specific project rule.
- Added Keys navigation and held-key cards with discoverer name, resource realm,
  stored name/flavour, rolled outputs, requirements, uses, lifecycle, bound and
  deprecated markers. Start sends key_id; destroy requires confirmation. Server
  errors remain visible, including depletion and invalidation errors.
- Added the separate fixed-price key market browser and listing form, with
  discovery-realm, goods-class, exact-good and resource-kind filters. Cursor
  navigation preserves filters; purchases pin the displayed server price.
  Cancellation, capacity errors and retryable market failures retain server
  authority. Commodity pickers remain unchanged.
- Enabled Exploration navigation and merged its separately served definitions
  into recipe presentation. Existing resolver summaries retain discovery counts.
  Key holdings refresh after action polls and mutations. Combat encounter identity
  and equipment/belt/utility locks recognize active.meta.key_action and key_id
  even when no public action has that template id.
- Added Vitest tests:
  `routes Play now to character creation through an authenticated guest session`;
  `updates the hint from the current server step and hides it after departure`;
  `blocks guest departure, upgrades in place, confirms game promotion, then departs`;
  `retries game confirmation after credentials were saved without repeating upgrade`;
  `shows %s key state and retained provenance` (four lifecycle states);
  `starts keys by instance, lists at a fixed price, retains filters on cursor pages, and pins buy price`;
  `recognizes private combat key identity without a public action definition`;
  `locks equipment, belt and utility for a private combat key template`.
  `can default island travel to relocating the camp`.
  Existing content-fetch fixtures now include the tutorial pack.
- Validation: repository-virtualenv make ci passes on SQLite: auth 35 with one
  dialect-specific skip, game 832 with 30 dialect-specific skips, client 113.
  Ruff, formatting, strict types, ESLint, Prettier, production build, script
  checks and warning-only content lint pass. Disposable SQLite make db-reset
  and subsequent game/auth upgrades to head pass. git diff --check is clean.

## Removed

- Removed the Exploration coming-soon placeholder. No tests or server APIs removed.

## Design ambiguities resolved

- §24 / §20.2: expose island journey controls in the tutorial banner because the
  public world map intentionally omits tutorial edges. Destinations come from
  the tutorial pack; the server resolves the character's private instance.
- §24 / §20.1: show the upgrade form on ACCOUNT_REQUIRED and retain explicit
  departure confirmation after successful registration. Never infer full account
  status from credentials being accepted before game identity is synchronized.
- §24 / §19.5: market cancellation is submitted as an ownership-checked intent;
  public browse responses intentionally contain no seller identity. The server
  decides whether the selected listing belongs to the current character.

## Deviations

None.

## Ratification needed

None introduced. Existing combat and commodity self-matching questions are
unchanged; no new gameplay rule depends on resolving them here.

## Hand-offs

- 36-hardening: preserve the upgrade-to-/players/me ordering, token installation,
  confirmation retry, key-action metadata identity and query refresh behavior.
  Market failures are surfaced for an explicit fresh request, with no automatic
  purchase resubmission. Existing server-side concurrency and conservation tests
  remain unchanged.

## New error codes

- No new server codes. Client-only UPGRADE_CONFIRMATION_FAILED means credentials
  were saved but game identity confirmation must be retried. AUTH_FAILED and
  REQUEST_FAILED are transport fallbacks when no structured server code exists.
- No dependencies added.

## Orchestrator verification and review hand-offs

- Verified at 60ba7bb: SQLite make ci (auth 35, game 832 / 30 skipped, client 113); PostgreSQL game 861 / 1 skipped, auth 36; alembic check clean; boot 200.
- Review round 1: APPROVE, no blocking findings. Non-blocking hand-offs for 36-hardening:
  - `client/src/api/http.ts`: the upgrade call never refreshes an expired guest access token; on 401 refresh once and retry, as `gameRequest` does.
  - `KeysPanel.tsx`: "Cancel my listing" appears on other players' listings (browse has no seller identity); track own listing ids or label it.
  - `KeysPanel.tsx`: key actions share one error slot; show errors next to the key or listing that caused them.
  - `KeysPanel.tsx`: show the realm name from content and a friendly state label instead of raw ids.
  - `KeysPanel.test.tsx`: add an unbound-key case, a destroy (confirm then DELETE) assertion and the "Fully paid at kickoff" text.
  - `http.ts`: split `guestSession(credentials?)` into `createGuest` and `upgradeAccount`.
