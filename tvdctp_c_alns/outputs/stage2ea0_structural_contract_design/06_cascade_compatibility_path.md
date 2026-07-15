# Cascade Removal 兼容路径

## Native evidence 优先

当 `source_destroy_operator == "cascade_aware_removal"` 且 capability/版本/fingerprint 全部通过时，adapter 必须优先、原样把 producer evidence 转换为现有 `CascadeBundleSnapshot`：

- final removal closure：现有 `removal`（`operators.py:589-599`）；
- bundle partition：sortie 顺序 bundle + sorted remaining singletons（601–615）；
- dependency order：当前 `customer_ids` 原样写入（`operators.py:559-568`）；
- snapshot contents / affected scope：`_capture_cascade_bundle_snapshot` 当前全部字段（358–578）；
- bundle 顺序、IDs、source/destroyed fingerprints：现有 contract（617–657）。

Stage 2E-A.1 可把这些内容作为 optional producer evidence 放进 raw context，但不得重算、重排或用普通 Union-Find 合并/拆分。adapter 仅做 lossless mapping 和一致性验证；Stage 2D legacy-equivalence test（`tests/test_stage2d0_cascade_contract.py:161-199,244-267`）继续作为 oracle。

## 论文/实现边界

公式（93）规定 removal-set closure，不直接规定 bundle partition 与 dependency order。现有 partition/order 是 Stage 2D 已关闭实现契约（`state.py:100-125`，validator `operators.py:2941-3097`），不是新的论文声明。

> 本阶段保持当前 Cascade implementation 不变；其 bundle partition 与 dependency order 的论文语义校准留到 Stage 2F。

Stage 2E-A 不执行 Stage 2F 校准，也不把普通规则反向应用到 Cascade source。

