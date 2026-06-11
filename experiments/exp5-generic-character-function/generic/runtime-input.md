# Runtime Input Schema

## Scene frame

```yaml
scene_frame:
  time:
  place:
  prior_context:
  public_visibility: private | semi-public | public
  global_stakes: low | medium | high
  physical_danger: none | present | acute
  irreversible_loss_risk: low | medium | high
  immediate_event:
```

## Participants

```yaml
participants:
  - id:
    role_in_scene:
    present: true
```

## Relationship edges

```yaml
relationship_edges:
  - from: playable
    to:
    role: companion | lover | rival | stranger | authority | dependent | other
    trust: low | medium | high
    relational_tension: low | medium | high
    intimacy: none | latent | active | established
    obligation: none | debt | promise | duty | protection
    conflict_residue: none | fresh | unresolved | repaired
    power_balance: equal | other_up | self_up | unstable
    play_affordance: none | mild | live
    rupture_risk: low | medium | high
```

## Local affordances

```yaml
local_affordances:
  - target:
    kind: vulnerability | contradiction | care_signal | overreach | concealment | invitation | threat
    strength: weak | medium | strong
    evidence:
```
