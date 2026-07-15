# External Boundary 语义

## 定义

external boundary 是与本次实际 mutation footprint 有直接结构关系、但没有进入 `actually_unassigned_customer_ids` 的客户或资源。它保护业务身份和不变量，不要求底层 route/sortie dict 逐字段冻结。

## `external_boundary_projection`

按 stable business IDs 捕获：

- external customer：pre service count=1、service mode、resource membership、container/warehouse assignment；
- affected route：去掉 R 后的 external node subsequence、直接 boundary predecessor/successor、home/endpoints；
- affected sortie：ordered external customers、launch/recovery node与van、drone ID、carrier before/after、coordination precedence；
- resource：affected van/drone/container IDs、home/initial carrier、scope membership；
- scope 外：完整 business structural projection digest。

repair 后验证：

1. external customer 仍且仅被服务一次，且不进入 unassigned；
2. service mode 保持，除非 Stage 2D 当前某一显式策略已经允许并由 snapshot scope 声明；默认不允许；
3. resource ownership、carrier continuity、launch/recovery 可达性与既有 checker constraints 成立；
4. external nodes 的既定相对顺序及直接 coordination invariants 保持；
5. declared affected scope 外的结构 projection 完全相等；
6. scope 内可为恢复 R 重写承载 external entity 的 route/sortie 对象，但上述业务投影必须等价。

因此不能简单断言 `before sortie == after sortie`。固定 fixture 已证明 route position 的语义变化可在 sortie dict 相等时发生；反方向上，合法 repair 也可能更新时间/位置字段而仍保持 external 业务不变量。

现有 `_external_structure_projection`（`operators.py:3100-3139`）提供 Stage 2D 基础，但它把 outside modes/routes/sorties/assignments整体冻结；A.2 需要将其扩展为“scope 外 exact + scope 内 invariant projection”，并继续服从 `_candidate_changes_only_affected_scope` 的限制（3142–3168）。

## Gate

**EXTERNAL BOUNDARY PASS**

