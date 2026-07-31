"Design doc" = ./design/design.md. Section references (§) point into it.
Definition of done for every prompt: code compiles/lints clean (ruff + mypy for Python, tsc + eslint for TS), all new and existing tests pass, docker-compose up yields a working stack, and a short docs/phase-notes/<prompt-id>.md summarizes what was built and any deviations.
The agent must not build anything listed in §10 (non-goals) and must not invent game content beyond the placeholder pack.

