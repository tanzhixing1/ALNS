# RNG Semantics Audit

## Current Native Cascade RNG calls

Within `operators.cascade_aware_removal`, the only random call is at `operators.py:722`:

`rng.choice(served, size=count, replace=False)`

It occurs after State copy, stale-metadata cleanup, pre-destroy projection/fingerprint capture, served-list construction, and requested-count calculation, but before dependency discovery. When `served` is empty, no Native random call occurs.

The closure loop, dependency helper, dependency trace, bundle construction, snapshot capture, customer removal, duplicate cleanup, contract fingerprints, and structural-context construction make no RNG calls.

`cascade_repair` explicitly leaves its RNG unused (`operators.py:3786–3787`). The ordinary adapter has no RNG parameter and contains no RNG call.

## Solver-level stream position

The same NumPy `Generator` is shared by the ALNS loop. Before a Native destroy call, `run_c_alns` normally consumes RNG for destroy selection and repair selection. Later SA acceptance may consume `rng.random()` depending on candidate cost. Therefore:

- the local Native contract is “zero or one choice call”;
- the exact sampled customers also depend on all earlier global-stream consumption;
- Stage 2F.1 must not add closure/partition/context RNG, because that would shift repair/acceptance and future iterations.

## Dependency on expansion and removal quantity

- RNG call count does **not** depend on the dependency expansion result: it is one call when served customers exist.
- Expansion size does not trigger further random calls.
- Requested removal quantity changes the `size` argument and therefore the sample and potentially the generator state after the call, even though the Python-visible call count remains one.
- An empty served set changes the call count from one to zero.

## Determinism evidence

Four reliable fixture cases, including requested counts 1 and 2, were repeated twice. Each pair had identical RNG call arguments, initial selections, expansion traces, final customer sets, bundle partitions, dependency orders, and destroyed fingerprints. The current baseline is deterministic for those cases.

The closure and removal iterate Python sets. Integer hashing is stable in the audited runtime, but set traversal is not an appropriate cross-runtime semantic contract. A future implementation should use an explicit ordered worklist while preserving the same customer set and number of RNG calls.

## Native versus ordinary adapter

- Native source `cascade_aware_removal`: Cascade repair bypasses `adapt_removal_context_to_cascade_bundles`.
- Random/Greedy/Related source: Cascade repair invokes the adapter after the ordinary destroy has completed.
- Adapter validation, edge construction, component partition, topological ordering, snapshot construction, and contract installation consume no RNG.
- Context capture/finalization/attach/detach/discard consume no RNG.

Thus the adapter and context infrastructure do not alter Native Cascade RNG semantics.

## Paper classification

- EXPLICIT/PARTIAL evidence: random removal is random; related-removal seed is uniformly random; Cascade recursively expands an initial set.
- PAPER UNSPECIFIED: standalone Native Cascade’s exact initial-set generator, multi-customer sampling API, NumPy generator type, exact call count, global stream position, closure traversal order, bundle order, and tie behavior.

Conclusion: preserve the current single-call behavior as a **MINIMAL ENGINEERING DECISION**, not as a paper requirement. Any Stage 2F.1 change to seed eligibility or quantity must record the intentional sampled-set/fingerprint delta while proving that no additional RNG call is introduced.

