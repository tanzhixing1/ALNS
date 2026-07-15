# Producer Capability 验证

## Trusted descriptor

不能只判断 `source_operator in {...}`。定义受信 producer descriptor registry，绑定 registered callable identity、`structural_context_version`、支持的 schema versions 与 capabilities，例如：

```text
produces_structural_context
captures_pre_projection
reports_selection_order
reports_deletion_order
reports_mutation_diff
provides_cascade_native_evidence   # Cascade only
```

context 中声明的 `producer_capabilities` 必须是 trusted descriptor 的子集并与 callable/source一致；字符串仅作为审计标签，不能自行授予能力。

## Adapter validation 顺序

1. source callable 是当前注册的受信 producer；
2. schema/context version 支持，必填 capability 全；
3. canonical serialization 与 `context_id` digest 重算一致；
4. embedded pre projection digest == pre fingerprint；当前 destroyed business projection digest == post fingerprint；
5. `actually_unassigned == post.unassigned - pre.unassigned`，并全部在 destroyed State 为 unassigned；selected、selection/deletion/unassignment order集合关系合法；
6. mutation footprint == 权威 pre/post structural diff；event attribution 不得少报；
7. external boundary 与 R 不相交，projection references 均来自 pre-state；
8. Cascade source：native closure/partition/order/snapshot fingerprints 与 current Stage 2D evidence逐项相等；
9. ordinary source：atomic edge references均存在于 pre projection；
10. adapter 后 `union(bundles)==R`、bundles pairwise disjoint、非空、无 external membership；
11. dependency order 是各 bundle 的精确排列并满足所有 precedence；cycle fail closed；
12. affected scope 与 footprint/boundary一致，snapshot reference 全来自 pre-state。

任一失败返回 typed contract error；不得 fallback、补 metadata、扩大 R 或进入 `Ω(B)`。

现有 Cascade validator在 `operators.py:139-168,2941-3097` 已覆盖 schema/source/fingerprint/bundle overlap/union/scope的一部分；A.2 应把它提升为通用 capability validation，同时保持 native path现有严格条件。

