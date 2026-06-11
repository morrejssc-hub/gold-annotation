# exp5 generic character function

This orphan branch is the clean starting point for the next architecture pass.

## Goal

Build a relation-first character runtime instead of another character-specific bible.

The runtime is split into:

- generic contract: invariant architecture with no proper nouns, canon examples, or trigger-card labels
- character instance: roots, posture, lie/masking behavior, substrate, and voice for one character
- scene binding: runtime inputs for scene frame, relationship edges, and local affordances
- legality gates: purpose correction against root ownership and method constraints
- renderer: final action + line, with hidden reasoning

## Branch contents

New architecture docs live under `experiments/exp5-generic-character-function/`.

Retained from `exp4` for evaluation only:

- `experiments/exp4-core-function/probes/probes.frozen.md`
- `experiments/exp4-core-function/probes/round2.frozen.md`
- `experiments/exp4-core-function/probes/runs/round1.md`
- `experiments/exp4-core-function/probes/runs/round1-regression.md`
- `experiments/exp4-core-function/probes/runs/round1-bareR.md`

Everything else from the old project tree was intentionally dropped on this branch so the new runtime architecture can be built without inherited prompt/card baggage.
