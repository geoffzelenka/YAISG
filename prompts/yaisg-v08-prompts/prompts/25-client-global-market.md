## Prompt 25 — Client: global market

**ID:** `25-client-global-market` · **Workstream:** Q · **Needs:** 24 · **Design:** §24 (Global market)

### Build

Book view with depth; order form (side, quantity, unit price) with access state; slots list with status and collect, partial-collect messaging; cancel; history. Disabled order creation and collection outside market-access realms, with the reason.

### Tests (vitest)

Access-gated controls; slot state rendering; immediate-fill report.

