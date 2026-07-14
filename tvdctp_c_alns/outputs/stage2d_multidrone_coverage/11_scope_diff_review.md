# Scope and diff review

## Production scope

- `operators.py`: added one deterministic candidate-drone helper and replaced
  first-only selection in the two existing shared drone candidate loops.
- The existing per-sortie hard-feasibility call remains authoritative.
- Candidate keys and resulting strategy identities retain concrete `drone_id`.

## Test and evidence scope

- Added seven real-model multi-drone tests covering symmetry, unavailable first
  drone, existing task, current-carrier transfer, cross-van recovery, Stage 2C,
  and Stage 2D whole-bundle use.
- Added this Stage 2D final audit report directory.

## Explicitly unchanged

Objective; canonical feasibility semantics; timing rules; capacity/energy rules;
Cascade removal selection; dependency closure; bundle partition; Global/Local
repair; Regret-2 ordering; Cascade candidate families; operator registry; SA;
ALNS main loop; initial solution; Stage 2E; Stage 2F; Stage 3.

No old test was deleted, skipped, xfailed, or relaxed. No lossy pruning was
introduced.
