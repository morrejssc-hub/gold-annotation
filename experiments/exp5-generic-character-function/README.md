# exp5 generic character function

This experiment reorganizes the runtime around a generic character function instead of a Holo-specific prompt bible.

## Core design moves

1. Relationship is a first-class runtime object.
2. Scene pressure is split into relationship tension and global stakes.
3. Purpose is a hidden candidate variable, not a stored axis.
4. Purpose must be corrected by legality gates so literary continuation does not masquerade as role-faithful intent.
5. Canon names, body-feature nouns, examples, and old card labels stay out of the generic runtime.

## Directory map

- `CONTRACT.md`: generic architecture contract
- `runtime.generic.md`: minimal runtime prompt for evaluation/production
- `generic/`: reusable runtime pieces
- `instances/holo/`: Holo-specific kernel, substrate, and voice
- `probes/`: new evaluation matrix for relation routing, grounding, and crisis overrides
- `MIGRATION.md`: mapping from exp4 lessons into exp5 structure
