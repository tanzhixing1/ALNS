# Stage 2F.0 Gate Decision

| Gate | Result | Evidence |
|---|---|---|
| Baseline HEAD correct | PASS | Exact `760e3bc445b04fd2673c81774c90d30422f890df`. |
| Tracked diff clean | PASS | `git diff --name-status` empty. |
| Staged diff clean | PASS | `git diff --cached --name-status` empty. |
| Primary PDF inspected | PASS | Direct primary file read; pages rendered from that file. |
| PDF pages recorded | PASS | PDF/printed pages 16, 17, 18 retained and cited. |
| Formula/Algorithm evidence recorded | PASS | Formula (93), formula (95), Algorithm 1 steps 1–8. |
| Seed selection classified | PASS | PARTIAL. |
| Dependency relation classified | PASS | PARTIAL paper definition; implementation gap confirmed. |
| Recursive propagation classified | PASS | EXPLICIT; current control ALIGNED. |
| Closure termination classified | PASS | EXPLICIT; current control ALIGNED. |
| Final `R*` classified | PASS | EXPLICIT paper rule; current result PARTIALLY ALIGNED due incomplete `D_i`. |
| Related route/sub-route classified | PASS | PARTIAL; route discovery NOT IMPLEMENTED, same-sub-route PARTIALLY ALIGNED. |
| Bundle partition classified | PASS | PARTIAL paper rule; production PARTIALLY ALIGNED. |
| Dependency order classified | PASS | PAPER UNSPECIFIED / engineering interpretation. |
| Native Cascade path traced | PASS | Solver entry through removal, closure, snapshot, removal, context, and repair boundary. |
| Ordinary adapter separated | PASS | Source allowlist plus Native bypass focused test. |
| Engineering infrastructure separated | PASS | Context, snapshots, lifecycle, adapter, and registry separately classified. |
| RNG semantics mapped | PASS | Native zero/one-call contract, global-stream position, count effect, adapter/context isolation. |
| Current behavior snapshot recorded | PASS | Four reliable cases × two runs in Markdown/CSV/raw JSON. |
| Determinism checked | PASS | All required compared fields equal in every pair. |
| Paper–implementation gaps classified | PASS | Required categories used in matrix. |
| Stage 2F.1 contract defined | PASS | Conditional contract with six MEDs, exact scope, tests, and invariants. |
| Stage 2F.2 regression plan defined | PASS | Semantic, deterministic, boundary, lifecycle, 16-pair, repair-isolation, small-run gates. |
| Production untouched | PASS | No tracked diff. |
| Tests untouched | PASS | No tracked diff; tests only executed. |
| Existing outputs untouched | PASS | All Stage 2F writes confined to the new output directory. |

## Decision

```text
CASCADE REMOVAL PAPER CONTRACT PARTIAL
MINIMAL ENGINEERING DECISIONS REQUIRED
CASCADE REMOVAL PAPER GAP CONFIRMED
STAGE 2F.0 COMPLETE
STAGE 2F.1 CONDITIONALLY READY — NATIVE REMOVAL CORRECTION REQUIRED
STAGE 2F.2 HELD
STAGE 2G HELD
```

The primary confirmed gap is not the fixed-point loop: it is the incomplete Native dependency predicate and the non-general, potentially overlapping per-sortie bundle construction. The paper does not fully specify the replacement graph/partition/order, so the decisions in `06_stage2f1_implementation_contract.md` must remain visibly labeled as engineering decisions.

This decision does **not** claim that Cascade-aware Removal is already correct, that Stage 2F is complete, that the C-ALNS baseline is frozen, or that performance is solved.

