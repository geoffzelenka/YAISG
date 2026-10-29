## Prompt 04 — NO_DEMAND status; no self-matching

**ID:** `04-market-rulings` · **Needs:** 03 · **Source:** Q6, Q7 · **Design:** §15.3, §17.1, §17.3, §22

### Rulings

- **Q6:** "Yes, align NO_DEMAND statuses"
- **Q7:** "Yes, Prohibit a user matching an order they themselves posted. If a self-match would occur, it should notify the user."

### Build

1. **Q6:** `NO_DEMAND` returns **409** everywhere (realm market quote and trade), matching the other state-conflict market errors. Update the client to rely on the code alone.
2. **Q7 (the orchestrator's reading):**
   - An incoming order on the global book that would cross any of the same character's resting orders, at a price it would actually reach while sweeping, is rejected whole before any match, with **409 `SELF_MATCH`**.
   - Nothing is matched, escrowed or charged, and the order book is unchanged.
   - The error message names the conflicting resting order, so the client can tell the player, which is the ruling's "notify the user".
   - Orders that don't reach the player's own resting order trade normally.
   - Record the reading, and the alternatives you rejected (skipping own orders, or cancelling the resting order), under Design ambiguities.
3. Same-account or same-character only, whichever identity the book stores as the order's owner. Use the character, and record that.
4. **Client:** the market order form shows the `SELF_MATCH` message, with a link to the player's conflicting order.
5. Remove the self-match allowance from the world conservation scenario, which used distinct owners anyway, and add a self-match attempt to its generated operations as a rejected operation.

### Tests

- A crossing self-order gets 409 `SELF_MATCH` with no state change, for buy-into-own-sell and sell-into-own-buy.
- A sweep that would reach other players first, then the player's own order, is rejected whole.
- An order that crosses only other players' orders matches as before.
- A non-crossing order from the same player rests normally.
- Concurrency on PostgreSQL: a player's two simultaneous crossing orders can't match each other.
- The quote and trade `NO_DEMAND` responses are both 409.
- The client shows the self-match message.

### Out of scope

The key market (fixed-price listings, §19.5); realm trades.

### Review focus

The check happens under the same locks and in the same price-time order as matching (§17.1, §23.1). No escrow leaks on rejection.
