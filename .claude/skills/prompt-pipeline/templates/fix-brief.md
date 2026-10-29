<!-- Fix message for `codex exec resume <thread> --json "$(cat fix.md)"`. Include only
findings you ruled valid. Quote human rulings verbatim. -->
Review round <N> for <id> came back <verdict>. Fix every blocking finding, then the listed nits.

B1. <one-line defect> (<file:line>).
- Why it matters: <concrete failure scenario, with the reviewer's reproduction if any>.
- Fix: <the requested change>.
- Test: <the test to add, and the mutation it must fail under>.

<B2 ...>

Nits:
- N1, <file:line>: <change>.

<HUMAN RULING (verbatim): "...">
<What to implement for the ruling, and that it goes under Design ambiguities resolved in the phase note, attributed to the human.>

Keep following every earlier instruction. Never touch design/.the-vision.md.swp. Add no dependencies. When you're done, run make ci with PATH=$PWD/.venv/bin:$PATH and update docs/phase-notes/<V>-<id>.md.
