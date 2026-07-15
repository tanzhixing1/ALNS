# 普通 Destroy 的 Bundle Adapter 语义

## 输入与集合不变量

仅 `normalize_for_cascade_repair(context)` 执行 repair-specific 解释；Random、Greedy、Related 不直接构造 `CascadeBundleSnapshot`。

```text
R = set(context.actually_unassigned_customer_ids)
E = external boundary customer IDs
Union(B_i) = R
B_i ∩ B_j = ∅, i != j
R ∩ E = ∅
```

adapter 不得扩大 R；pre-existing unassigned 不自动进入 R；任何 external customer/resource 不进入 bundle。空 R 是受控 contract failure，而不是伪造空/单例 bundle。

## 当前 State 中可证明的原子结构

1. **连续 removed van block**：在同一 pre-state `van_routes[van_id]`（`state.py:180,376-382`）中，R 内客户占据连续 customer positions，中间没有 external customer。只连接同一 block 的 R 节点；同 route 的不连续 block 不连。
2. **同一 removed drone sortie**：pre-state `drone_sorties` 的 ordered `customers`（`state.py:184,366-374`；sortie 结构见 README）中属于 R 的节点两两连边。公共 helper 删除整条 sortie，所以 collateral members 也应已在 R；否则 validation failure。
3. **不可分割 launch/recovery coordination unit**：同一 sortie 的 `(launch_van_id, launch node/position, ordered customers, recovery node/position, recovery_van_id)` 是一个直接协调单元。只连接该单元里同时属于 R 的 customer nodes；未移除 anchor 留作 boundary。
4. **carrier-transfer atomic unit**：同一 sortie 的 drone ID、initial carrier、launch carrier、recovery carrier 构成直接 transfer relation。它可连接该 sortie/anchor unit 中的 R customers，但绝不连接相关 vans 上所有客户。
5. **明确 coordination edge**：当前模型没有独立 edge collection；直接 edge 由 sortie 的 launch/recovery/carrier 字段与 route occurrence 共同表达（现有 snapshot 在 `operators.py:538-557` 生成对应 IDs）。只使用这些可定位直接边。
6. **Cascade native evidence**：仅 Cascade source 使用，见 `06_cascade_compatibility_path.md`，不与普通规则混用。

warehouse、container、service mode、几何距离与 customer ID 不构成结构边。特别禁止“同一整条 van route”宽泛耦合。

## Union-Find 算法

```text
make-set(customer) for customer in R
for each objectively captured atomic structure in pre-state:
    members = ordered customers of that structure intersect R
    if len(members) >= 2:
        union adjacent members and retain edge evidence
components = connected components over exactly R
singleton for every node with no union edge
```

每条 union edge 必须携带 `atomic_kind`、stable structure ID、pre-state positions 与 source fact references，以便 producer validation 和 precedence graph 使用。components 输出顺序由其最早 structural ordinal、再由 actual-unassignment order确定；不得依赖 set/dict/hash 偶然顺序。

## 边界处理

- 同 sortie external launch/recovery anchor：记录为 boundary customer/route occurrence，不加入 component。
- route block 前后 external nodes：记录相邻 boundary，验证 relative order/service，不与远处同 route customers 连接。
- external van/drone/container resources：保留 resource boundary 与业务约束，不作为 customer bundle 成员。
- 若 diff 显示 external customer 被实际 unassigned，它必须进入 R；若 `external_boundary_entities` 仍把它标为 E，validation failure。

## Gate

**BUNDLE SEMANTICS PASS**

普通 destroy 已有足够 pre-state 原子关系形成保守、互斥、覆盖 R 的 components；没有直接关系的客户明确形成 singleton，不需要猜测距离/仓库/整 route 关系。

