# Mutation Footprint 审计与计算方法

## 为什么 selected IDs 不足够

公共删除 helper 会删除整条 sortie 并 collateral-unassign 全部 sortie customers（`operators.py:200-211`）。固定 fixture 证明 selected anchor `5` 可得到 actual `[5,7]`；一条 `[7,9]` multi-customer sortie 中仅 selected `7` 会实际 unassign `[7,9]`。删除一个 van 节点还会改变相邻节点的 route adjacency/position，即使相关 sortie dict 没有逐字段变化。

## Footprint schema

```text
mutation_footprint = {
  mutated_van_route_ids,
  mutated_contiguous_route_segments(before range, after range, boundary nodes),
  removed_sortie_ids,
  rewritten_sortie_ids,
  mutated_launch_recovery_link_ids,
  mutated_carrier_relation_ids,
  mutated_coordination_edge_ids,
  service_mode_transitions,
  unassigned_transitions,
  protected_external_customer_ids,
  protected_external_resource_ids
}
```

Route segment 用最小 edit span 加一层直接 predecessor/successor boundary；只把实际变化和验证所需邻界纳入 scope，不把整条 route 上所有客户耦合。sortie ID 基于 pre-state stable structural key 加 occurrence ordinal，不使用对象地址；删除后 list index 位移不得误报其余 sorties rewritten。若 stable matching 歧义，controlled construction failure。

## 每个 destroy 的真实 fixture 结果

| Destroy/case | selected | actually unassigned | business structures changed | external entities touched |
| --- | --- | --- | --- | --- |
| Random seed29 | `[12]` | `[12]` | `van_0` 最小删除 segment | 前后 route 邻界节点 |
| Greedy seed29 | `[7]` | `[7]` | `sortie:0`、其 launch/recovery/carrier/coordination 关系 | anchor `5`、`van_0`、`drone_0` |
| Related seed29 | `[12]` | `[12]` | 同 Random | 同 Random |
| Cascade seed29 | closure `[12]` | `[12]` | 同 Random；native bundle 保留 | native affected scope |
| Random/Related selected anchor `5` | `[5]` | `[5,7]` | `van_0` + `sortie:0` + coordination | route 邻点、van/drone resources；`7` 属于 R 而非 external |
| Cascade initial anchor `5` | closure `[5,7]` | `[5,7]` | 同上 | 同上；closure/partition 不改 |
| Random one customer in `[7,9]` sortie | `[7]` | `[7,9]` | 整条 multi-customer sortie | launch/recovery anchors/resources |
| Random van-before-anchor | `[9]` | `[9]` | route position/adjacency 改；sortie对象相等 | external anchor `5` 的真实位置与 coordination invariant |

四个目标 destroy 不直接改变 carrier maps 或 assignments，但删除 sortie 意味着 active carrier/coordination relation 被移除；footprint 必须记录关系层变化，而不能以 map equality 判定“carrier 未触碰”。

## A/B/C 比较

- A 显式 mutation events：适合记录 selection、deletion attempt、actual-unassignment 顺序与 mutation attribution；单独使用会漏共享/派生关系。
- B pre/post structural projection diff：能检测代码实际改了什么，包括意外 collateral mutation；单独使用不能恢复执行顺序，且需语义 matching。
- C 两者结合：**推荐**。B 是 footprint 权威真相，A 是顺序与归因交叉校验；二者不一致时 contract construction failure，不以理论预测覆盖实际 diff。

projection 必须在 destroy 前捕获，并在 destroy 后再次规范化；禁止用 `before sortie == after sortie` 代替 route-position、carrier 或 coordination 语义检查。

