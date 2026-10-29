## Prompt 08 — Safe transition-history retention

**ID:** `08-key-history-retention` · **Needs:** 07 · **Source:** F4 (v0.8 31, 32 and 36 hand-offs) · **Design:** §19.3–19.6

### Goal

Let `transition_history` be pruned without changing any key's validity or any historical earnings.

### Build

1. Define a safe watermark: the earliest timestamp still needed by any unresolved action, discovery or key. Prune only history entirely older than it.
2. Cache parsed history only where the first-cutoff-wins rule and exact historical earnings are preserved.
3. Run pruning in the scheduled job, in bounded batches, with the same lock discipline as Prompt 07.
4. Never truncate history an unresolved action could still need. If no safe watermark exists for some state, keep the history and record why.

### Tests

- Pruning at the watermark leaves every key's state, every resolve result and every discovery identical to no pruning. Use a Hypothesis scenario with transitions, discoveries and long-idle actions.
- First-cutoff-wins holds across a prune.
- A long-idle action resolving after a prune earns exactly what it would have earned without the prune.
- Concurrency on PostgreSQL: pruning racing a resolve.

### Out of scope

Changing key rules.

### Review focus

The watermark is provably safe. No path reads pruned history.
