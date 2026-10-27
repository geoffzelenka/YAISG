## Built

- Skill panels display server levels, tier badges/titles and XP to next, including
  maximum level. Added the Travel sidebar entry and map link. Travel uses the
  route preview rather than the placeholder uniform action figures (07 hand-off).
- Action cards display effective cycle time, XP per cycle, formatted proficiency,
  taper and capped/uncapped XP percentages with a visible capped marker. All
  requirement codes have readable explanations, with a fallback for future codes.
- Map destination/mode form previews server time and selector supplies per edge,
  then starts the selected journey. Relocate requires a mobile estate in the
  current realm. Changing destination/mode clears the preview; pending requests
  disable changes. Map lists tier, decay stage, available treasury band and
  pending transitions without exposing treasury balances.
- Active summaries now expose persisted meta. Journey step/count/current edge
  come from that snapshot. The existing 4 Hz clock animates only the current
  paid edge, clamps at completion, and snaps to the next server snapshot. Boundary
  polling uses the current edge's remaining time instead of journey start time.
- Welcome-back modal, reward drawer and toasts render ordered resolver details
  recursively, preserving unfamiliar nested payloads. Travel adds completed-edge
  count and current realm; consumed supplies appear alongside ordinary rewards.
  Journey starts deliver their immediate claimed rewards to the same feed.
- Tests added: `previews server edge times and supplies then starts the selected
  journey`; `disables relocate for an estate that is %s` (fixed/away);
  `renders journey progress from server meta`; `shows welcome-back travel summary
  and supplies, preserving unknown details`; `renders generic reward details in
  resolution order`; `shows server tier at level %i` (ten boundary fixtures);
  `clamps at the current edge and snaps to a new server snapshot`.
- Extended `renders startable and locked actions from server fixtures` to assert
  all requirement reasons, server effective figures and the capped marker.
  Extended `test_travel_preview_start_stop_and_removed_routes` to verify poll
  metadata with a half-completed paid edge; its existing fixture supports both
  database dialects. Updated the map test fixture for the estate eligibility read.

- Validation: full `PATH=$PWD/.venv/bin:$PATH make ci` passes on SQLite:
  auth 15, game 257 with four database-specific skips, client 38. Formatting,
  lint, strict typing and production build pass. Disposable SQLite `make
  db-reset` rebuilt both services; subsequent game `alembic upgrade head`
  succeeded. `git diff --check` is clean. No dependencies added.

## Removed

- No remaining legacy relocation controls/hooks were present after 07. Searches
  find only the new journey's relocate mode and its tests. No tests removed.

## Design ambiguities resolved

- §24 / §11.3: the Travel skill entry shows progression and links to the map;
  it does not display the travel action's placeholder uniform rates. Per-edge
  server preview supplies the meaningful timing and costs, as 07 directs.
- §6.3 / §24: unfamiliar resolver details render as nested labelled data in
  resolution order. Travel supplies remain visible even for a paid partial edge
  with zero completed cycles. Existing welcome-back eligibility is preserved.
- §24: added meta to the active action response because it was persisted by 07
  but omitted by its response serializer. No resolver or persistence rules change.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 30-client-equipment-combat: recursive resolver details already preserve nested
  encounter payloads; add combat-specific presentation alongside the travel summary.
- 21-client-realm-estate / 22-client-realm-market: map renders treasury bands when
  supplied; no balance or local health calculation is introduced here.

## New error codes

None. Existing server errors display their messages.
