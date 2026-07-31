Prompt 3.3 — Client: skill panels and the global action strip

Implement the skilling UI per §9. Server from Prompt 3.2 is complete.

Requirements:

Skill sections (Gathering, Refining, Crafting) become live routes. Each lists its actions from GET /characters/me/actions/available + content: name, level requirement, inputs, outputs (drop items + rates — exposed per design), effective cycle time. Locked actions render with their blocked_by reason. A Start button per startable action.
Global active-action strip (§9.1) visible on every route: current action name + icon placeholder, an animated progress bar, and a stop button. Progress animates client-side from started_at and effective cycle_ms (single 4-times-per-second interval store — zustand — driving all timers; no per-component intervals).
Polling: TanStack Query refetches GET /characters/me/action aligned to cycle boundaries with ±10% jitter, plus on window refocus and on network reconnect. On response: merge rewards into a reward feed (toast stack + a scrollback list in the strip's expandable drawer), and invalidate profile/inventory queries only when the response shows changes.
Offline catch-up UX: when a response's since_last spans many cycles (threshold: > 5), show a "Welcome back" summary modal (cycles, xp per skill, items, and stop_reason if capped) instead of toast spam.
Inventory panel: add a simple inventory grid to the Profile section (item name, quantity) fed by the inventory endpoint; shows stack count vs inventory_slots cap.
Stop reasons: when the server reports the action ended (inputs_exhausted, offline_cap, inventory_full), clear the strip and surface the reason in the feed.
Keep §9.2's rules: no client-computed rewards displayed as authoritative; the progress bar is explicitly cosmetic (if a poll reveals the server has less/more progress, snap to server truth).

Tests (vitest + testing-library): action list renders locked/unlocked states from fixture data; strip progress math from started_at; welcome-back modal triggers on large since_last; poll scheduling honors cycle boundaries (fake timers).

Acceptance criteria (manual, in browser): create character → start a gathering action → watch two cycles complete with reward toasts → start a refining action that consumes the gathered items → stop it → close the tab for a few minutes → reopen → welcome-back summary shows offline gains; profile XP bars and inventory reflect everything.
