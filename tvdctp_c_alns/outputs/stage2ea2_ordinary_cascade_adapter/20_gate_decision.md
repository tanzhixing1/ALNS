# Stage 2E-A.2 gate decision

| Gate | Result | Evidence |
| --- | --- | --- |
| Starting baseline correct | PASS | Production/test tree equals `901ee48`; actual HEAD `8331bb8` only adds the user's out-of-scope PDF |
| Tracked worktree clean | PASS | Clean at start; only the two requested root text exports were untracked |
| Representability passed | PASS | `00_representability_gate.md` and pre-edit dynamic fixtures |
| R equals actual-unassigned transition | PASS | Context/post/current transition recomputed and tested |
| No removal expansion | PASS | Adapter is read-only and union equals exact actual-R |
| Atomic edges factual | PASS | Direct route/sortie/anchor/transfer/coordination tests |
| No broad same-route edge | PASS | Non-contiguous `{9,11}` remains separate |
| No same-drone-only edge | PASS | Same-drone no-transfer sorties remain separate |
| Bundle union complete | PASS | Construction assertion and tests |
| Bundles disjoint | PASS | Construction assertion, validator and tests |
| External boundaries excluded/protected | PASS | Overlap rejection and normalized projection test |
| Dependency order structural | PASS | Reverse-ID route fixture yields `(10,9)` |
| No customer-ID fallback | PASS | Structural first-occurrence Kahn tie-break |
| Cycles controlled | PASS | Explicit two-edge cycle raises controlled error |
| Context available before Cascade adapter | PASS | Source-aware public Cascade boundary |
| Context cleaned after success/failure | PASS | Success, stale, malformed, empty and rollback paths |
| Native Cascade bypasses adapter | PASS | Monkeypatch call count zero |
| Native Cascade strict equivalence | PASS | Old IDs/counts/sequence/objective/fingerprint exact |
| Existing Ω(B) unchanged | PASS | Ω(B) function body has no diff; existing tests pass |
| Random + Cascade compatible | PASS | Real Ω(B), 6/5/4, feasible success |
| Greedy + Cascade compatible | PASS | Real Ω(B), 11/11/10, feasible success |
| Related + Cascade compatible | PASS | Real Ω(B), 6/5/4, feasible success |
| All16 A/B | PASS | A=10, B=6 |
| C=0 | PASS | Matrix test |
| D=0 | PASS | Matrix/lifecycle test |
| No fallback | PASS | All other repair entry points monkeypatched forbidden |
| Existing13 unchanged | PASS | Exact A.1 matrix and trace digests |
| Adapter lazy | PASS | Exactly the three new pair invocations |
| Unrelated candidate counts unchanged | PASS | Direct-body/public-boundary differential and A.1 baselines |
| Unrelated objective/checker calls unchanged | PASS | Instrumented count differential |
| Performance measurements reported | PASS | 13-pair A.1/A.2 medians and 16×3 A.2 CSV |
| Deterministic | PASS | Three runs per new pair, exact context/bundle/candidate/result/RNG |
| Baseline-relative regression passed | PASS | 220 pass; sole A.1 medium hang reproduced separately |
| Scope clean | PASS | `19_scope_diff_review.md` |
| Git diff check passed | PASS | Final worktree/cached checks performed before commit |

The one-shot full suite did not complete, so this gate does not claim a full
suite pass. The accepted result is the explicitly permitted baseline-relative
grouped regression classification.

## Final decision

OPERATOR PAIR CONTRACT PASS

STAGE 2E-A.2 COMPLETE

STAGE 2E.1 READY
