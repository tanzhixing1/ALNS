# Stage 2D.0 paper joint-repair clarification

## Controlling semantic correction

This section is the controlling interpretation for Stage 2D.0 and is placed before all earlier Prompt interpretations. It overrides any conflicting claim that the paper defines a complete per-customer Cartesian-product candidate space, that candidate complexity is the product of independent customer move counts, or that a bundle contract needs only customer IDs.

The paper establishes a final cascade set `R*`, partitions it by structural dependency into customer bundles `B`, and processes `for each bundle B`. For each bundle it constructs `Ω(B)`, selects `π*(B)` with the full objective, and jointly reconstructs associated vehicle routes, drone sub-routes, and coordination relationships. It expressly says that customers are not inserted independently. Therefore the default Stage 2D.1 candidate unit is a `BundleReconstructionStrategy` over affected route/sub-route/coordination structures, not a direct product of ordinary single-customer `InsertionMove` sets.

The paper does not define how `Ω(B)` is generated, whether it is exhaustively enumerated, the internal customer order, tie-breaks, empty-candidate behavior, fallback, pruning, branch-and-bound, or bundle-size distribution. Every such point is **Paper unspecified**. A future per-customer Cartesian implementation must be named **extended customer-compositional mode** and must not be represented as the paper-defined Cascade repair.

## Evidence table

| Question | Paper evidence | Conclusion | Confidence |
|---|---|---|---|
| Full Cartesian required | Section 5.1.3 says the bundle is jointly inserted and customers are not inserted independently; neither Eq. (95) nor Algorithm 1 defines `Ω(B)` as `Ω(i1) × … × Ω(ik)` | NO — no such requirement; generation is Paper unspecified | HIGH |
| Dependency-order reconstruction | Algorithm 1 processes bundles sequentially but gives no order within a bundle and no bundle-order rule | UNSPECIFIED | HIGH |
| Affected-route restriction | Section 5.1.2 and Algorithm 1 steps 7 and 14 name associated vehicle route segments, drone sub-routes, and coordination structures; exact exclusivity/boundaries are not defined | UNSPECIFIED — association-scoped wording is clear, exact limits are not | MEDIUM |
| Full objective selection | Eq. (95) and Algorithm 1 line 13 select `arg min` of `f(S ⊕π B)` | YES | HIGH |
| Candidate pruning | No branch-and-bound, pruning, top-K, beam, candidate cap, or lossy approximation is specified | UNSPECIFIED | HIGH |
| Bundle size evidence | Sections 5.1 and 6 report instance sizes and runtimes, not typical/max bundle size or cascade depth | NO explicit bundle-size evidence was found | HIGH |

## Narrow questions answered

1. Of choices A–E, **E** is correct for the enumeration algorithm: the evidence is insufficient to identify a specific generator. Choice C is the closest description of the named structural scope, but the paper does not prove an exclusive original-route-only restriction.
2. Exhaustive bundle strategy enumeration, dependency order, global route access, global launch/recovery access, pruning, and fallback are all **Paper unspecified**. Full-objective selection for each defined `Ω(B)` is explicit.
3. Section 6 supplies instance sizes, fleet parameters, and C-ALNS CPU times. It does not supply bundle sizes, cascade removal counts, cascade depth, or strategy counts.
4. Table 4 CPU time is performance background only. It cannot identify the implementation of `Ω(B)` or justify pruning.

## Equation (95) notation audit

**Likely notation inconsistency:** the right side of Eq. (95) prints `f(S ⊕π i)`, while its left side, surrounding definition, and Algorithm 1 line 13 all operate on bundle `B`. The implementation interpretation is `f(S ⊕π B)`. The paper file was not changed.
