# Stage 2F.1 Conditional Implementation Contract

## Readiness

Stage 2F.1 is **conditionally ready**. Formula (93), fixed-point termination, final `R*`, simultaneous removal, and dependency-based bundle partition are strong enough to constrain the algorithm. The exact dependency graph, standalone seed generator, partition rule, and customer order are not fully specified and therefore require the explicit minimal engineering decisions below.

## Frozen prerequisites

Stage 2F.1 must reuse without semantic redesign:

- `RemovalStructuralContext` and pre/post structural projections;
- pre-removal `CascadeBundleSnapshot` capture;
- ordinary destroy → Cascade adapter, which remains ordinary-only;
- bundle-scoped Cascade Repair `Ω(B)` and its atomic failure behavior;
- context attach/consume/cleanup lifecycle;
- paper-mode 16-action registry and action IDs;
- current objective, canonical checker, State business representation, `State.copy`, timing, SA, adaptive weights, and all Global/Local/Regret behavior.

## Minimal engineering decisions

### MED-1 — standalone Native `R^(0)`

Retain the current one-call, without-replacement sample and removal-count rule for the standalone Native Cascade action. Preserve sorted served input and record the returned list as seed order. Rationale: the paper permits an initial removal set but does not choose one generator for a separately registered fourth action; retaining it avoids action-identity and RNG drift. This is not claimed as an explicit paper rule.

Risk: the paper wording around van-served versus all served customer eligibility is ambiguous. A focused test must freeze the chosen eligible domain and report it as engineering policy.

### MED-2 — conservative customer dependency graph

Build a read-only dependency graph from the **pre-destroy** structural projection. Customer dependency edges may be created only from explicit, already represented coordination facts:

1. all customer nodes within the same drone sub-route, including launch/recovery only when they are customer nodes;
2. explicit customer-to-customer launch/recovery coordination relations;
3. explicit carrier-transfer/linked-sortie relations where both endpoints are customer nodes;
4. other customer-to-customer coordination edges already present in the structural projection and directly attributable to the affected route/sub-route.

Do not infer that every customer sharing a van, warehouse, container, or truck route is dependent; that would risk global over-expansion unsupported by the paper. Truck/van route segments and non-customer coordination structures remain affected **snapshot scope** even when they do not add customer nodes to `R*`.

Risk: this conservative interpretation may still omit a paper-intended downstream dependency not represented by current structural facts. Stage 2F.2 needs an explicit fixture for each accepted edge kind and an evidence-gap test for unsupported truck-level changes.

### MED-3 — direction and closure traversal

Treat same-sub-route co-removal as symmetric customer dependency. Preserve direction for explicit impact/coordination edges. Compute the monotone closure with an ordered worklist initialized by Native seed order; append newly discovered customers in stable structural rank and customer-ID tie order. Maintain a set only for membership, never for visitation/removal order.

No depth cap, probability, feasibility cutoff, reroll, or fallback is permitted. Cycles terminate through membership tracking.

### MED-4 — bundle partition

Partition the induced dependency graph on `R*` into weakly connected components. This is a minimal deterministic interpretation of Algorithm 1 step 8 (“according to structural dependency relationships”). Every `R*` member occurs in exactly one component; isolated nodes become singleton bundles. Bundle order follows first appearance in closure discovery order.

This replaces per-sortie intersections that can miss cross-structure links or overlap. It does not change ordinary-adapter partitioning.

### MED-5 — `dependency_order`

The paper does not define an internal customer order. To minimize repair-side change, retain stable ascending customer-ID order within each Native component as `dependency_order`, with the existing “Paper unspecified” label. Do not introduce a topological requirement or repair fallback in Stage 2F.1.

### MED-6 — RNG and removal execution

Dependency graph construction, closure, partition, snapshot capture, context evidence, and removal must consume zero RNG. The only Native RNG call remains MED-1. Actual removal follows the explicit closure discovery order; business membership must equal `R*` regardless of sortie side effects.

## Allowed production changes

| Location | Paper evidence | Before | Target | RNG impact | `R*` impact | Bundle impact | Order impact | Required focused test |
|---|---|---|---|---|---|---|---|---|
| `operators.py:_cascade_dependencies` or narrowly scoped replacement helpers | p.17 `D_i`; Algorithm 1 step 3 | Same matching sortie plus non-warehouse anchors only | Read-only MED-2 dependency graph/query | none | may expand to newly represented structural dependencies | supplies graph edges | supplies stable rank/provenance | one fixture per edge kind and explicit unrelated-route exclusion |
| `operators.py:cascade_aware_removal` seed block | p.17 `R^(0)` partial | one random sample | retain MED-1 and expose exact seed provenance | no call-count change | seed set unchanged at first implementation | none | seed order frozen | exact RecordingRng call and eligibility-domain test |
| `operators.py:cascade_aware_removal` closure loop | formula (93); Algorithm 1 steps 2–6 | repeated Python-set iteration | ordered worklist exact closure | none | fixed point over corrected graph | supplies complete membership | explicit discovery/removal order | chain cycle multi-source duplicate and fixed-point tests |
| `operators.py:cascade_aware_removal` bundle block | p.17 bundle text; Algorithm 1 step 8 | per-sortie intersections plus singletons | MED-4 weak components with disjoint union checks | none | none after closure | corrected complete partition | stable component order | cross-sortie component multiple components overlap prevention |
| `operators.py:_capture_cascade_bundle_snapshot` call inputs | Algorithm 1 steps 7–8 | current bundle list; sorted customer IDs | corrected component membership; MED-5 order | none | none | snapshot matches component | ascending ID within bundle | snapshot/contract fingerprint determinism and pre-removal capture |
| Native context evidence assembly | engineering infrastructure | records current trace/partition/order | records exact seed-to-closure provenance and corrected partition/order | none | none | evidence only | evidence only | context equals Native contract and does not alter business State |

New helpers may be added only in `operators.py` unless a pre-existing immutable projection accessor in `removal_structural_context.py` is insufficient. Any proposed change outside these locations requires a new scope review before implementation.

## Prohibited changes

No changes to Cascade repair strategy enumeration/scoring, Global/Local/Regret repair, candidate generation, objective, canonical checker, `compute_timing`, State fields/business signature, `State.copy`, SA acceptance, weights, action IDs, default paper mode, extended-mode rules, top-K/beam/sampling/approximation/cache/incremental Regret/copy-on-write, performance engineering, PPO, or Stage 3.

## Expected unchanged behavior

- Paper mode remains default with the same 16 IDs and Native Cascade + Cascade at ID 15.
- Ordinary Random/Greedy/Related destroy semantics and RNG remain exact.
- Ordinary adapter still receives only ordinary contexts and never expands `actually_unassigned`.
- Cascade repair consumes the same snapshot type and keeps `Ω(B)` unchanged.
- No active context survives into current/best or a returned candidate.
- No fallback, reroll, masking, or approximate evaluation is introduced.

## Stage 2F.1 exit condition

Implementation is acceptable only if focused semantic/determinism/boundary tests pass and the diff is limited to the allowed Native-removal scope. Long performance benchmarks are neither required nor authorized.

