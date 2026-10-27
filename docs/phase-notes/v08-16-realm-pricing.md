## Built

- Added strict economy.market curve settings f/c/k/m, content-authored treasury
  band boundaries and hysteresis; existing node margin_pct overrides the global
  margin. m is a fraction, while margin_pct is a percentage.
- Added pure Decimal pricing with a local 50-digit context, the scarcity
  integral, realm-favouring floor/ceil totals, physical limits and bisection of
  funded whole-item quantities. The specification example pays 4,439 gold.
- Step 10 allocates floor-rounded budgets by unmet reference value, doubles
  below-reserve weights, and updates the stored five-bucket band. Cached line
  reference values are reused; the tick steps issue no database queries.
- Market and quote GET endpoints resolve/lock the realm and publish demand,
  alternative member quotes, sales, shortfalls, stage, gauge days and band.
  Any authenticated player can inspect any world realm without presence.
  Reads retain spent budgets. Initial world creation funds its first lines;
  subsequent gold is allocated by step 10.
- Wired persisted estate valuation to the realm's current rounded spot unit ask,
  retaining reference-price fallback when no whole unit can be sold.
- Map band scaffolding now receives calculated values, including at world seed.
  Seed-check reports that arrival bid verification is skipped because the
  tutorial pack and arrival_realms do not yet exist.
- Added curve/example, margin/round-trip/integral, budget/bisection, hysteresis,
  weighted/physical-limit, step-10, API/privacy, schema privacy, spent-budget,
  estate-provider and PostgreSQL realm-lock tests in test_market.py.
  Updated the old null-band assertion and supplied explicit treasury state to
  the existing pure Fed/Strained equivalence test.
- Validation: SQLite make ci passes all lint, formatting, strict typing, tests,
  client build and content lint checks (auth 15; game 433 with 12 skips; client
  41). Disposable SQLite make db-reset, a subsequent alembic upgrade head and
  world creation pass. Focused market tests pass (14 with one database-specific
  skip); git diff --check is clean.

- Round 1: fixed above-cap/zero-cap integrals and empty-treasury bands; made
  published spot bids and band arithmetic deterministic at fixed precision;
  selected line figures by best funded capacity with stable ties; added typed
  market responses and reused one market snapshot per estate listing. Added
  regression coverage for these cases and all three requested funding mutants.
  SQLite make ci passes (auth 15; game 443 with 12 skips; client 41).

## Removed

None. No tests or routes removed.

## Design ambiguities resolved

- §15.2 / §15.5: an oversized physical quote is priced through the physical
  limit and returns max_quantity separately. Funding does not clamp its gold:
  callers can compare the requested physically possible total with capacity.
  No trade or balance mutation is implemented.
- §15.5: bands are stored as strings "0" through "4", ordered from poorest to
  richest. Upward transitions require 110% of a boundary, downward transitions
  require less than 90%; initial placement uses the unadjusted boundaries.
  Zero treasury always has band "0". With positive treasury and no realm
  upkeep, treasury cover is infinite and the band is "4".
  Band upkeep counts the node and live tag upkeep, not estate/project appetite.
- §15.5: line amounts and shortfalls remain milli-line-units, matching Prompt
  13. Member quotes use whole item quantities. Per-line funded quantity is in
  milli-line-units; member bids are alternatives sharing one budget, not
  independently funded promises. Shortfalls use the best member's capacity.
- §13.4: spot unit asks round upward to integral gold for the existing UnitAsk
  provider contract. Selling requires at least one whole available item.

- §15.2 / §15.5: stock may remain above a newly reduced cap until the next
  step 7. The integral charges the floor f on the part above cap, including
  when cap <= 0 (all nonnegative stock is then above cap). This extends the
  existing clamped spot curve continuously and preserves the bid/ask margin.
- §15.1 / §15.2: a stored good without a demand line is offered with reserve 0
  and cap max(stock, warehouse_cap). This uses the same scarcity pricing for
  warehouse surplus while allowing no funded demand for that good.
- §15.5: line figures use the member with greatest funded milli-line capacity;
  ties choose lowest reference price, then item id. Its spot bid and funded
  total accompany that capacity, and shortfalls use the same best capacity.
  Member bids are alternatives, so they are never summed as independent bids.
  Spot bid strings have eight decimal places, computed at 50-digit precision.
- §15.5 / V§9.4.8: funded totals and visible budget weights inherently allow
  players to estimate treasury closely. This is a known inference disclosure
  for human assessment; the required fields remain published and the raw
  balance remains absent. Behaviour follows the explicit design fields.
- §15.5: the design does not settle zero treasury divided by zero upkeep.
  Zero treasury is assigned band 0 because it cannot buy any upkeep; positive
  treasury with zero upkeep retains infinite cover. Hysteresis cannot retain
  a richer band when treasury is empty.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 17-realm-trade: use QuoteContext/quote/total under the existing character →
  realm → estate transaction order. Validate demand, physical quantity,
  funding, inventory, gold and limit_gold before moving holdings; quotes do not
  implement trade errors or player affordability. Decrement both line budget
  and treasury on a sale. Recompute derived stock preserving spent budgets;
  newly added demand receives funding at the next step 10.
- 18-mint-gold: supply value-measured mint demand to the existing line machinery
  and include mint reference upkeep in treasury coverage when adding mint
  upkeep. Weighted quote support already uses reference_price as item weight.
- 22-client-realm-market: render band 0–4 and market member alternatives; raw
  treasury and per-line budgets remain private. Spot bids are decimal strings;
  total prices and spot asks are integer gold.
- 34-tutorial: replace the explicit arrival-bid skip in seed-check with checks
  at every simulated tick for tutorial.arrival_realms and tier-one funded bids.

## New error codes

- NO_DEMAND for quoting a sale of a good without a demand line.
- UNKNOWN_ITEM for an unknown quoted good; UNKNOWN_REALM is reused.
- Invalid query fields retain the shared validation envelope.
