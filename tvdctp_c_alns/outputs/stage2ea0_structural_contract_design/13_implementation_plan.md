# Stage 2E-A.1 / A.2 实施计划（不编码）

## Stage 2E-A.1 — 所有 destroy 生产 raw context

| Step | 预计文件/函数 | 实施内容 | Gate test |
| --- | --- | --- | --- |
| 1 schema | 新 `removal_structural_context.py`（或等价独立模块）；`state.py` 仅在需要类型导出时引用 | frozen raw fact/projection/footprint/context types；无 repair bundle 字段 | canonical round-trip、immutability |
| 2 pre projection | 新模块 `capture_structural_state` / `business_state_projection` | allowlisted immutable State 投影与 stable IDs；不调 objective/cache/RNG | metadata exclusion、cross-process digest |
| 3 footprint diff | 新模块 `diff_structural_projection` | route edit spans、sortie/link/carrier/coordination semantic diff、boundary | collateral sortie、anchor position counterexample |
| 4 common execution trace | `operators.py:_remove_customers` 及四个目标 destroy入口/选择点 | append-only observation of existing selection/deletion/unassignment order；不物化/重排 Cascade set | before/after RNG + business + order exact equality |
| 5 producer capture | `operators.py:random_customer_removal`, `greedy_removal`, `related_customer_removal`, `cascade_aware_removal` | working-copy入口 capture；结束 build context；Cascade native evidence原样附加 | per-destroy raw completeness |
| 6 lifecycle | `operators.py` 五个 public repair boundary、`_finalize_repair`, `_finish_cascade_result`; `alns_solver.py:run_c_alns` | attach/consume/clear；nested repair exactly once；persistent guards | success/failure/direct-call/current/best context-free |
| 7 fingerprints | 新模块 + `operators.py:_state_business_fingerprint`兼容入口 | canonical business fingerprint；legacy Stage 2D identity保持或版本桥接 | metadata/objective/cache equivalence |
| 8 tests | 新 `tests/test_stage2ea1_structural_context.py`；增强 Stage 2D strict oracle | 四 destroy、copy/cache/RNG/marginal/relatedness/closure equivalence | focused + full 160 baseline |

A.1 不改变 Cascade repair accepted producer范围，不解锁三对，不修改普通 bundle语义；完成后重新跑 Stage 2D 全契约。

## Stage 2E-A.2 — Adapter 与 Cascade 通用消费

| Step | 预计文件/函数 | 实施内容 | Gate test |
| --- | --- | --- | --- |
| 1 adapter | 新模块 `normalize_for_cascade_repair` | capability validation + typed result/failure | tamper/fail-closed |
| 2 native path | adapter + `operators.py:_validated_cascade_bundles` | Cascade evidence lossless mapping，禁止普通 normalize | strict snapshot/sequence equality |
| 3 ordinary grouping | adapter atomic extractor/Union-Find | contiguous block、sortie、coordination、carrier direct edges；singleton | no same-route broad edge |
| 4 order | precedence graph/stable topo | structural order、tie-break、cycle failure | route/sortie/multi-structure/cycle |
| 5 boundary | projection validator + `operators.py:_candidate_changes_only_affected_scope` | scope内 business invariants、scope外 exact | rewrite allowed + invariant preserved |
| 6 producer validation | trusted descriptor registry，邻近 `DESTROY_OPERATORS` registration | callable/version/capabilities/set/fingerprint/diff/snapshot checks | spoofed string rejected |
| 7 Cascade consumer | `operators.py:cascade_repair` entry 与 validator | 接受四个合法 producer；仍无 fallback | new 3 pairs enter `Ω(B)` |
| 8 tests | 新 `tests/test_stage2ea2_bundle_adapter.py`、`test_stage2ea2_pair_matrix.py` | 16-pair contract matrix、3 new pairs、12 old pairs、Cascade strict | full regression |
| 9 audit rerun | `diagnose_calns.py` 只读 API/既有 Stage 2E.0 audit workflow | 重新生成 compatibility matrix | 16/16 contract-compatible |

预计无需修改 `objective.py`、`feasibility.py` 或 config；若测试证明 business projection遗漏，不得用 metadata豁免绕过 checker/cache，而应回到 A.1 schema gate。operator registry只增加受信 descriptor/包装，不改变 paper/default mode与action space（Stage 2E.1仍另行执行）。

## 可实施性

- **Stage 2E-A.1：READY**，所有捕获点和生命周期边界已定位。
- **Stage 2E-A.2：READY AFTER A.1**，普通原子边、order、boundary与validation均已有 fail-closed规则。

