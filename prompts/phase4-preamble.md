Conventions (unchanged from the Phase 0–3 prompt file):

"Design doc" = design.md v0.5. Section references (§) point into it.
Definition of done for every prompt: code compiles/lints clean (ruff + mypy for Python, tsc + eslint for TS), all new and existing tests pass on both CI database engines, docker-compose up yields a working stack, and a short docs/phase-notes/<prompt-id>.md summarizes what was built and any deviations.
The agent must not build anything listed in §10 (non-goals). In Phase 4 this especially means: no upkeep, decay, solvency, production, regression traversal, transfer/escheat, or inter-realm balancing mechanics — several schemas and content fields for these exist and must be created, but nothing reads them except validation.
The agent must not invent game content beyond the placeholder pack changes each prompt specifies.

Phase-4-wide notes:

The flat-tier realm model from earlier phases is superseded (§7.4, log #15). Migrate, don't parallel-build: the old realm_state.tier/project_id/contribution_totals columns and any tier-based content go away in 4.1.
Prompt 3.1's "engine is frozen" rule is relaxed for this phase in one specific way: the engine's modifier/cap source resolution is extended per §7 (development node + estate form as sources). Resolution math, the resolve loop, and all existing engine tests must not change behavior; every engine edit must keep the existing suite green untouched (except where a test hardcodes the old source model — those may be updated, listed in phase notes).
