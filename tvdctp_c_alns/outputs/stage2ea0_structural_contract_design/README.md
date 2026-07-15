# Stage 2E-A.0 — Universal Destroy-to-Repair Structural Contract

只读设计、调用链审计与实施可行性 Gate。Baseline/HEAD：`b886431084f1e2b8cc1db59d13f03f5798d8fa30`。

## 目录

- `00_paper_interface_boundary.md`：论文明确/未明确/implementation choice
- `01_destroy_execution_audit.md`：四 destroy 调用链、RNG、selection/deletion/mutation
- `02_capture_feasibility.md`：入口 projection 与增量方案比较
- `03_removal_structural_context_schema.md`：repair-agnostic raw schema
- `04_mutation_footprint.md`：实际 pre/post footprint
- `05_bundle_adapter_semantics.md`：ordinary atomic-edge Union-Find
- `06_cascade_compatibility_path.md`：native Cascade lossless path
- `07_dependency_order_design.md`：precedence/topological order/cycle policy
- `08_external_boundary_semantics.md`：业务不变量 projection
- `09_fingerprint_and_context_id.md`：canonical business fingerprint/deterministic ID
- `10_context_lifecycle_architecture.md`：ephemeral metadata lifecycle
- `11_producer_capability_validation.md`：trusted producer validation
- `12_regression_contract.md`：Cascade strict、existing 12、新 3 pairs
- `13_implementation_plan.md`：A.1/A.2 文件/函数级计划
- `14_gate_decision.md`：总 Gate

## 关键结论

- raw facts 与 repair-specific bundle 解释严格分层；四 destroy 不各自复制 Cascade 逻辑。
- recommended capture：pre immutable structural projection + 最小顺序观察 + authoritative post diff。
- ordinary bundles 只由直接原子结构边形成；不使用 same-route broad coupling；无边客户 singleton。
- Cascade current closure/partition/order/snapshot原样直通，Stage 2F语义校准未执行。
- active context推荐临时 State metadata，但必须在所有 public repair边界 exactly-once消费，并在 persistent current/best 前双重断言清除。
- Final：`STAGE 2E-A.0 COMPLETE` / `STAGE 2E-A.1 READY`。

本目录仅含审计报告；无 production/test/config/registry patch，无 commit。

## 验证记录（2026-07-15）

- destroy-focused：`test_stage2d0_cascade_contract.py`，`18 passed in 6.91s`。
- Stage 2D contract：D0 + D1 + multidrone，`58 passed in 22.07s`。
- collect-only：`160 tests collected in 4.88s`，与可信基线规模一致。
- full `pytest -q tests`：分别在 180 秒与 900 秒执行上限被工具终止，均无 assertion failure traceback；不得据此声称 full suite 本轮通过或失败。可信 baseline 仍为用户提供的 `160 passed, 5 warnings`。
- 固定 coordinated fixture 通过公开 destroy API做 pre/post diff；输入 State fingerprint 均不变，诊断未写入 production/test/config。
