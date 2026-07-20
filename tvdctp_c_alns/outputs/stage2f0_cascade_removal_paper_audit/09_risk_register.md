# Stage 2F Risk Register

| ID | Risk | Likelihood / impact | Evidence | Mitigation / gate |
|---|---|---|---|---|
| R1 | Paper dependency predicate is under-specified. | High / High | p.17 names structural relationships but gives no complete graph. | Use only MED-2 explicit structural facts; label decisions; one test per edge kind. |
| R2 | Standalone Native seed semantics are ambiguous. | Medium / High | `R^(0)` comes from “any above” strategy, while production registers Cascade independently. | Retain current one-call seed generator as MED-1; freeze eligibility and RNG trace. |
| R3 | Over-expanding every same-route/warehouse customer collapses neighborhoods toward global removal. | Medium / High | Paper says associated decisions, not all co-located customers. | Conservative customer edges; keep non-customer route structures in snapshot scope; unrelated exclusion tests. |
| R4 | Under-expansion misses truck/van/linked-sortie effects. | High / High | Current helper only sees a matching sortie. | Add accepted coordination edge kinds from pre-projection; document remaining evidence gaps. |
| R5 | Per-sortie bundle construction can overlap. | Medium / High | Current loop does not subtract `assigned` before appending later sortie intersections. | Build weak connected components; assert disjoint union equals `R*` before snapshots/removal. |
| R6 | Direction or cycles create order-dependent closure. | Medium / High | Paper examples imply direction but do not formalize it. | Explicit edge semantics; monotone visited worklist; cycle and multi-source tests. |
| R7 | Python set iteration changes removal trace/fingerprints across runtimes. | Medium / Medium | Current closure/removal traverse sets; only same-runtime determinism was proven. | Ordered worklist and explicit deletion order; multi-process/cross-runtime probe. |
| R8 | Extra RNG calls shift the entire ALNS stream. | Medium / High | One shared generator controls operator selection, destroy, repair, and SA. | Preserve zero/one Native call contract; RecordingRng tests across all ordinary and Native paths. |
| R9 | Corrected Native logic accidentally enters ordinary adapter or expands ordinary actual-R. | Low / High | Both paths share Cascade repair and snapshot type. | Native adapter-bypass canary; three ordinary adapter call-count/union tests. |
| R10 | Repair semantics drift while changing bundle inputs. | Medium / High | `dependency_order` and bundle grouping are consumed by `Ω(B)`. | Freeze repair source/hash; keep ascending-ID order as MED-5; repair-isolation tests. |
| R11 | Context or contract metadata leaks into current/best. | Low / High | Context is deliberately carried on destroyed candidates. | Success/failure/exception lifecycle tests and solver assertions. |
| R12 | Snapshot is captured after mutation and loses structural evidence. | Low / High | Current code correctly captures first; refactor could reorder it. | Pre-removal snapshot assertions and exact source/destroyed fingerprints. |
| R13 | A malformed dependency graph triggers silent fallback/truncation. | Medium / High | Paper gives no failure policy; fallback is prohibited. | Fail fast before business mutation; no reroll/fallback; explicit malformed-graph test. |
| R14 | Existing reliable fixtures do not cover truck-level decision changes or two-source/one-new-target provenance. | High / Medium | Current audit marked evidence gaps. | Add canonical small fixtures in Stage 2F.2; do not fabricate current results. |
| R15 | Action IDs or default mode drift through unrelated refactoring. | Low / High | Paper mode identity is a frozen external contract. | Registry fingerprint, all 16 IDs, default/extended mode tests. |
| R16 | Stage 2F expands into deferred performance work. | Medium / Medium | Regret bottleneck is known but explicitly deferred. | Scope diff gate bans cache/incremental evaluation/State changes; no benchmark target. |

## Highest-priority blockers

R1, R4, and R5 are the semantic blockers for Stage 2F.1. R2 is deliberately contained by retaining the current seed generator as a transparent engineering decision. R8–R11 are non-regression gates that protect the already completed Stage 2 work.

