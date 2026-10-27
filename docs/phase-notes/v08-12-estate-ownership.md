## Built

- Pure rebuild valuation includes every form on the cheapest tier-one path and
  installed upgrade costs. Selectors use their cheapest matching good. A unit-ask
  provider defaults to not selling; values use reference prices until Prompt 16.
  Valuation returns the selected path on the fly without persisting it. Sale prices
  use exact integer ceiling and economy.estate's content-defined 15 percent markup.
- Added build, buy, surrender and deposit-only larder endpoints. Builds transfer
  gold to the realm treasury and consume selector goods, following Prompt 11.
  Purchases transfer gold to the treasury; surrender transfers at most its balance
  back to the owner, or zero on donation. Builds and purchases destroy the mobile
  estate and its upgrades. Fixed estates retain upgrades and larder on surrender.
  Acquisitions write ownership history; surrender closes the ownership interval.
  Destroyed mobile dependants follow the existing cascading-history schema.
- All flows use the shared character resolver and its character, sorted realm,
  estate lock order. Buyers lock and recheck the target after locking the realm.
  Realm estate listings expose sale prices for realm-owned fixed estates without
  treasury balances, estate locks or valuation writes. Presence and mobile journey
  guards preserve the existing bonus and lifecycle contracts.
- Added EstateLarder and migration v08_0007_larder with positive milli-quantities,
  plus a minimal fake fixed workshop for build/upkeep coverage. Inventory deposits
  accept positive whole units, matching the existing inventory representation.
  Extended client economy content types and fixtures; ownership UI remains 21's.
- Tests added: test_valuation_goods_selector_gold_and_provider,
  test_valuation_records_cheapest_tier_one_path,
  test_buy_surrender_always_loses_gold (Hypothesis),
  test_build_buy_surrender_and_larder (donate and paid cases),
  test_postgres_two_buyers_one_estate, test_ownership_flow_preconditions.
  Updated the public listing assertion for sale_price. Existing reset/migration
  tests cover schema parity, downgrade and rebuild. No tests removed or weakened.

- Validation: `PATH=$PWD/.venv/bin:$PATH make ci` passes on SQLite: auth 15,
  game 333 with eight database-specific skips, client 41. Formatting, lint, strict
  typing, client build, scripts and warning-only content lint pass. Existing
  migration/reset tests rebuild both services and check game schema parity and
  downgrade. `git diff --check` passes. No dependencies added.

- Round 1: replaced the arithmetic-only property with deterministic, deadline-free
  Hypothesis coverage of real buy/surrender endpoints using generated costs and
  treasury balances and the content markup. Assertions cover both purchase gold
  deltas, payouts capped at value when treasury exceeds it, total gold and strict
  player loss. The property also checks closed ownership intervals and fresh
  acquisition rows. Added invalid-target and read-only listing regressions;
  mobile sale prices are null. Removed valuation_path persistence and public
  estate row locks, retained the on-the-fly cheapest-path rule, added lifecycle
  audit events, used indexed item lookup and removed the unused helper argument.
  Recorded the history-retention decision for 15-decay. Both reviewer mutations
  fail the endpoint property at the expected gold-delta assertions. Final SQLite
  `PATH=$PWD/.venv/bin:$PATH make ci` passes: auth 15, game 337 with eight
  database-specific skips, client 41; all lint, formatting, type and build checks
  pass. No dependencies added.

## Removed

None.

## Design ambiguities resolved

- §13.4: multiple tier-one paths are compared using current rebuild prices;
  equal costs break ties lexicographically by the complete form-id path. Cycles
  cannot revisit a form within a path. The chosen path is returned with valuation,
  without writing estate.data.
- §13.4 / Prompt 11 hand-off: build gold credits the estate realm's treasury,
  following the explicitly supplied payment rule and conservation requirement.
- §13.6: surrender retains prepaid larder goods with the fixed estate; ownership
  transfer does not refund deposits. Destroying a mobile estate deletes its larder
  along with its other dependent records.
- §13.2 / 04 hand-off: existing form-aware exhaustive lint bounds already cover
  the new fixed form and its slots; no separate valuation bonus source is added.

## Deviations

None.

## Ratification needed

- §13.4: should zero-valued fixed forms be forbidden by content validation?
  The stated formula gives zero buy and surrender prices, so strict gold loss
  cannot hold for that case. Implemented the formula as written, with no invented
  minimum charge; property coverage asserts strict loss for positive values.
  The fake fixed form has a positive valuation.

## Hand-offs

- 18-mint-gold: currency.gold is a 32-bit INTEGER while realm treasury is
  BigInteger. Decide whether player gold needs 64 bits. The endpoint property
  bounds generated costs and treasuries at 10**8 to keep all written balances
  within the current column range, with max_examples retained at 25.

- 14-realm-tick: consume/spoil EstateLarder.quantity_milli in batched tick context;
  deposits currently only transfer goods. Preserve 10a's bounded-query hand-off.
- 15-decay: lifecycle replacement may reuse the basic mobile acquisition/history
  pattern; upkeep and decay are deliberately absent here. Destroying a mobile
  estate currently deletes EstateOwnershipHistory rows through the FK cascade
  (and explicit SQLite cleanup). §13.1 suggests history should outlive estates;
  decide how to retain it when implementing estate destruction in decay.
- 16-realm-pricing: wire a real unit-ask provider into persisted_estate_value;
  estate_value already accepts a pure (realm_id, item_id) provider returning an
  integer ask or None for not selling.
- 21-client-realm-estate: implement ownership confirmations and larder controls;
  GET realm estates includes sale_price (null on player-owned and mobile estates).

## New error codes

- INVALID_BUILD_FORM: unknown, mobile or non-tier-one build destination.
- MOBILE_ESTATE_REQUIRED: build/buy requires a present mobile estate.
- NOT_FOR_SALE: target is missing, owned, mobile or outside the current realm.
- CANNOT_SURRENDER_MOBILE: surrender requires a fixed estate.
- NOT_UPKEEP_ITEM: larder good matches no upkeep selector.
- Reused NOT_PRESENT, NOT_ESTATE_OWNER, ESTATE_BUSY, MISSING_REALM_TAGS and
  MISSING_INPUTS. Boundary validation retains the shared validation error envelope.
