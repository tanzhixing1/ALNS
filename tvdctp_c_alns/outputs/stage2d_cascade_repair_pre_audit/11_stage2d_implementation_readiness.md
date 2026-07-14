# Stage 2D implementation readiness

## Confirmed paper semantics

- Cascade Removal creates a dependency closure `R*`.
- `R*` is partitioned into customer bundles based on structural dependency.
- Cascade repair processes each bundle through joint feasible strategies `Omega(B)`.
- Candidate selection minimizes the full candidate objective.
- Associated truck/van/drone routes, sub-routes, and coordination relationships are reconstructed together.
- Independent per-customer insertion is not the intended Multi-node Cascade Repair semantics.

## Confirmed current mismatches

- Bundle candidates are globally completed over every unassigned customer.
- Bundle-external unassigned customers are actively repaired.
- Candidate feasibility/objective is evaluated only after global completion, conflating bundle and external failure.
- Candidate strategies are a small mixture of sequential and size-limited patterns, not a documented joint `Omega(B)` implementation.
- Missing metadata falls back to all unassigned.
- Stale metadata is accepted.
- Final global sortie consolidation can actively rewrite unrelated served structures.

## Blocking removal/input findings

- Dependency closure covers only direct current-sortie relations.
- Bundle metadata contains customer IDs only.
- Removed route segments, prior sortie structures, launch/recovery/carrier relations, truck/warehouse relations, and dependency ordering are absent.
- Non-cascade destroy paths do not create or clear a valid Cascade bundle contract.
- ALNS can pair Cascade repair with any destroy, so required inputs are not guaranteed.

## Recommended controlled sequence

1. User confirms the six paper-unspecified alignment choices.
2. Stage 2F or a separately approved interface stage defines the immutable removal result: generation ID, `R*`, ordered dependency bundles, and associated structural context.
3. Stage 2D implements strict input validation, bundle-only scope, joint candidate generation/selection, association-scoped structural reconstruction, atomic failure behavior, and passive downstream propagation.
4. Add focused tests for bundle-external unassigned exclusion, stale/missing metadata rejection, bundle atomicity, associated-versus-unrelated served effects, and deterministic ordering.
5. Do not modify Global, Local, Regret, objective, checker, or unrelated registries as part of the repair implementation unless separately authorized.

## Decision

**STAGE 2D BLOCKED BY REMOVAL INPUT**

The paper semantics are sufficiently clear to reject the current global-completion behavior, but the current removal output does not carry enough structural information to implement the paper's coordinated reconstruction. Proceeding directly would force Stage 2D either to guess dependencies from an already-destroyed State or to preserve a simplified heuristic not supported by the paper.

No implementation was performed in this audit.
