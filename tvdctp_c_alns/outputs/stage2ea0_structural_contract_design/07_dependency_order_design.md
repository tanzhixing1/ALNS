# Dependency Order 设计

## 普通 destroy 的 precedence graph

对每个 ordinary component 构造有向图；节点恰为 bundle customers，边只来自 pre-state 直接结构：

- 连续 van block：按原 route position 添加相邻 precedence edges；
- drone sortie：按原 `customers` 顺序添加相邻 edges；
- launch/service/recovery：仅当 launch/recovery 本身是 R 内 customer 时，添加 `launch → first service → ... → recovery`；external anchor 只作为边界约束，不成为节点；
- carrier/coordination：只添加当前模型能明确推出的时间/承载先后边，不因同 carrier/van 任意连边；
- 多原子结构连接后保留全部真实 precedence，执行稳定 Kahn topological sort。

单一连续 block 由 route order 决定；单一 sortie 由 sortie customer order 决定。禁止 `sorted(customer_ids)` 作为结构顺序。

## 稳定 tie-break

只在多个当前 indegree=0、彼此无 precedence 时使用：

1. earliest pre-state structural ordinal（规范 traversal 中的 van route occurrence 或 sortie occurrence）；
2. earliest incident atomic structure stable ID；
3. `actual_unassignment_order`，再到 `deletion_attempt_order`。

每个 R customer 必有实际 unassignment ordinal，所以无需 customer ID、set/dict order 或 Python hash。stable structure ID 来自 canonical pre projection，不含对象地址。真实 precedence 永远优先于 tie-break。

## 环与冲突

选择 **A：controlled contract construction failure**。若 route、sortie、launch/recovery 或 carrier edges 形成环/互相矛盾：

- adapter 返回 typed failure，列出 cycle nodes 与 edge evidence；
- Cascade repair 不构造 `Ω(B)`、不 fallback、不得删除 edge、不得按 customer ID 强拆；
- destroyed candidate 与 context 一起丢弃。

不选择自动拆 component，因为 component 的 union edges已经声明直接不可分割结构；在没有额外论文/模型证据时拆分会破坏原子语义。

Cascade native source 不走此拓扑排序，完全保留当前 native dependency order。

## Gate

**DEPENDENCY ORDER PASS**

