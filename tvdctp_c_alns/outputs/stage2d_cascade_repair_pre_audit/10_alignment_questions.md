# Alignment questions

Only matters not determined by the paper and current code are listed.

### Alignment question 1

Paper evidence: Equation (95) defines the best strategy in `Omega(B)` but does not define `Omega(B)=empty` behavior.

Current code: Falls back to independent `_all_moves`, continues globally, and may return a partially repaired State.

Why this matters: Skip, atomic failure, and generic fallback produce different neighborhoods and failure rates.

Available options: Fail the whole Cascade candidate atomically; leave only that bundle unassigned and let the full checker reject; invoke an explicitly named fallback.

Recommended option: Fail the whole Cascade candidate atomically and return a clearly invalid/unchanged candidate result for ALNS rejection; do not invoke another repair implicitly.

Risk of each option: Atomic failure can increase rejected candidates; partial continuation creates hard-to-interpret mixed semantics; generic fallback collapses Cascade into ordinary repair.

### Alignment question 2

Paper evidence: Algorithm 1 says “for each bundle” but gives no bundle order or tie-break.

Current code: Uses metadata order and sorts customers high-floor first then ID, although intended paper insertion is joint.

Why this matters: Earlier bundles alter feasibility and objective context for later bundles.

Available options: Preserve removal-provided order; deterministic dependency/topological order; evaluate bundle orders as part of the candidate strategy.

Recommended option: Require removal to provide a deterministic dependency/topological order and preserve it in repair.

Risk of each option: Raw metadata order may be accidental; topological order requires richer Stage 2F data; order enumeration may be computationally expensive.

### Alignment question 3

Paper evidence: The paper requires joint `Omega(B)` but does not define an exhaustive enumeration algorithm.

Current code: Tries a small fixed family and only enumerates mixed subsets for bundle sizes 2-3.

Why this matters: Exact exhaustive search may be intractable; a restricted heuristic changes what “optimal in Omega(B)” means.

Available options: Exhaustive feasible joint enumeration; bounded deterministic beam/search with disclosed limits; a formally specified heuristic strategy family.

Recommended option: Define a deterministic, auditable joint strategy family with no silent size-based semantic switch; if bounded, expose the bound as an implementation choice and report candidate coverage.

Risk of each option: Exhaustive search may be too slow; bounded search may miss the paper-level optimum; fixed families may underrepresent coordination.

### Alignment question 4

Paper evidence: The normal flow gives Cascade repair `R*` bundles and says nothing about unrelated pre-existing unserved customers or arbitrary destroy/repair pairing.

Current code: ALNS independently pairs any destroy with Cascade repair; missing bundle metadata becomes one all-unassigned bundle.

Why this matters: A strict Cascade repair cannot reconstruct dependency structures that were never supplied.

Available options: Allow Cascade repair only with destroy outputs carrying the required contract; make every destroy produce valid dependency bundles; retain all-unassigned inference.

Recommended option: Require a validated bundle contract for Cascade repair and constrain eligibility/pairing accordingly; do not infer one bundle from all unassigned.

Risk of each option: Pair constraints reduce action-space combinations; enriching all destroys expands Stage 2F; inference is semantically unsupported and may use stale data.

### Alignment question 5

Paper evidence: Associated launch and receiving van routes may be adjusted simultaneously, but exact limits on served anchor nodes are not defined.

Current code: Uses served nodes as anchors and can globally consolidate unrelated sorties.

Why this matters: Allowing arbitrary served-node movement greatly enlarges the neighborhood and can alter assignments outside the removed set.

Available options: Only passive timing propagation outside `B`; allow structural changes only to explicitly associated route segments supplied by removal; allow unrestricted route-wide reconstruction.

Recommended option: Permit active changes only within explicitly associated route segments/coordination objects supplied in the bundle context; elsewhere allow passive timing/load propagation only.

Risk of each option: Passive-only may be too restrictive for flexible docking; association-scoped changes require richer metadata; unrestricted reconstruction obscures Cascade scope.

### Alignment question 6

Paper evidence: No lifecycle rule is given for engineering metadata.

Current code: Cascade metadata survives successful repair and can become stale across later non-cascade destroys.

Why this matters: A later Cascade repair can consume an old bundle as if it described the current removal.

Available options: Consume-and-clear metadata; attach iteration/generation IDs and validate; recompute when missing.

Recommended option: Use generation-tagged immutable removal output consumed by exactly one repair call, then discard it.

Risk of each option: Clearing alone offers weak diagnostics; generation IDs require an interface change; recomputation inside repair violates the Stage 2D/2F boundary.
