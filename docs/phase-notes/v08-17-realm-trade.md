## Built

- Added POST /realms/{realm_id}/market/trade and
  POST /realms/{realm_id}/treasury/gift. Both resolve the character and realm
  under the shared character → sorted realms → estate lock order, then require
  current presence. Visitors have the same rules as residents.
- Trades validate the complete requested quantity before transferring wallet /
  treasury gold and inventory / store goods. Integrated totals retain the
  existing realm-favouring rounding. Whole inventory units move as exactly
  1,000 store milli-units; cap and reserve checks use line weights.
- Sales decrement both treasury and the selected line budget. Derived lines
  refresh after every trade, preserving spent budgets. Gifts and purchases do
  not replenish line budgets before the next tick. Neither response exposes
  raw treasury balances. No tick-loop work or queries were introduced.
- The character-state loader now accepts explicit content for inventory-cap
  checks, retaining its existing default for callers.
- Added test_trade_errors_are_atomic (both price-limit directions, cap and
  reserve), test_trade_funding_inventory_and_presence_errors,
  test_random_trades_and_gifts_conserve_holdings (Hypothesis),
  test_trade_and_gift_routes, test_postgres_sellers_cannot_overspend_line,
  test_funding_maximum_and_gift_preserves_spent_budget,
  test_buy_requires_slot_and_only_requested_item_stock,
  test_price_moved_route_rolls_back_all_state, and
  test_fractional_cap_and_reserve_never_leak_a_whole_unit,
  test_sale_missing_inputs_and_empty_stack_removal, and
  test_weighted_line_moves_item_milli_without_rounding_gap.
  The PostgreSQL race uses separate sellers/sessions and verifies actual lock
  blocking with pg_blocking_pids before releasing the first seller.

## Removed

None. No existing tests, routes, content or schema fields were removed.

## Design ambiguities resolved

- §15.3: UNFUNDED_DEMAND supplies error.max_quantity, matching the quote
  endpoint's existing whole-item maximum name. Missing player goods reuse
  MISSING_INPUTS. Physical limits precede funding checks; PRICE_MOVED precedes
  buyer affordability / capacity checks once the requested stock is available.
- §15.6: gifts require strictly positive integral gold. Trade quantities are
  strictly positive integers, and limit_gold is a nonnegative integer.
  Successful trades return gold and max_quantity equal to the executed quantity;
  gifts return 204 with no balance disclosure.
- §15.3: failed requests roll back their entire transaction, including lazy
  character/realm resolution and derived-line refreshes. The next successful
  request can resolve the same elapsed interval normally.

## Deviations

None.

## Ratification needed

None.

## Hand-offs

- 18-mint-gold: include player wallets and realm treasuries in world gold
  accounting. Trades and gifts are transfers, so require no creation/destruction
  ledger entries. Preserve spent budgets. The earlier player gold INTEGER
  versus realm treasury BIGINT question remains owned by Prompt 18.
- 22-client-realm-market: trade responses carry integrated gold and executed
  max_quantity; UNFUNDED_DEMAND carries error.max_quantity. PRICE_MOVED rejects
  the complete request. Gift success is 204; no treasury balance is returned.
- 34-tutorial: apply the isolated-instance market exclusion when introducing
  owned tutorial realms and their endpoint access policy.

## New error codes

- STORES_FULL, UNFUNDED_DEMAND (with error.max_quantity), INSUFFICIENT_GOLD,
  INVENTORY_FULL and PRICE_MOVED implement §15.3.
- Reused NO_DEMAND, NOT_FOR_SALE, MISSING_INPUTS, NOT_PRESENT, UNKNOWN_ITEM,
  UNKNOWN_REALM and the shared boundary-validation envelope.
- No dependencies added.
