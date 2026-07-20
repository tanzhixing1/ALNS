# Optimization Opportunity Classification

## Class 1 — low-risk mechanical

- Candidate-scoped immutable timing/physical-route/structural context shared by
  exact objective and checker.
- Reuse immutable stage-1 cost constants and avoid repeated complete signature
  construction inside one candidate evaluation.
- Preserve all calls at the logical API/oracle boundary even if internal derived
  traversal is shared.

Measured basis: 35,496 timing requests for
17,743 unique candidate States and
45.258740 s exclusive timing work.

## Class 2 — medium-risk representation

- Move descriptor, local overlay, route/sortie copy-on-write, delayed full
  materialization and copying audit-only metadata only for the selected move.
- Basis: 23.877473 s and 0/17,743
  scored candidate copies retained.

## Class 3 — high-risk exact incremental evaluation

- Local timing, incremental objective, localized checker and selective remaining
  customer recomputation. Requires zero-false-negative dependency proof and a
  full-State oracle for every candidate.

## Class 4 — approximation

Top-K, sampling, beam, candidate truncation, restricted drone combinations and
heuristic pruning are **extended_mode only** and prohibited in `paper_mode`.
