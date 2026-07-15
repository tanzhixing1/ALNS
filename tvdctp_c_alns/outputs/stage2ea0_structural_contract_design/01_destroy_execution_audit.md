# 四个 destroy 执行模式与调用链审计

## 公共签名与调用入口

四者签名均为 `(state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig) -> TVDState`（`operators.py:230-232,242-244,264-266,581-583`），匹配 `DestroyOperator`（`operators.py:50`）。solver 先复制 current，再调用 destroy，随后原样把 destroyed State 交给 repair（`alns_solver.py:145-148`）。各 destroy 内部又执行 `state.copy()`。

公共变更链为 `_remove_customers` → 逐项 `_remove_customer`（`operators.py:192-217`）。`_remove_customer`：

- 从所有 `van_routes` 删除该节点并同步 `van_route`（192–198）；
- 若客户是 sortie customer、launch 或 recovery，则删除整条 sortie，并收集该 sortie 的全部 drone customers（200–208）；
- 对全部 collateral drone customers 与当前客户调用 `mark_unassigned`，后者追加 `unassigned` 并把 `service_mode` 改为 `unassigned`（210–211；`state.py:384-387`）。

它不直接改写 `order_assignment`、`container_assignment`、`drone_initial_carrier`、`van_home` 或 truck/container routes；但删除 sortie 会消灭该 sortie 内承载的 launch/recovery、carrier-transfer 与 coordination 关系。

## 真实调用链

### Random

`random_customer_removal` → `state.copy` → `_clear_stale_cascade_metadata` → `_served_customers` → `_removal_count` → **一次** `rng.choice(..., size=count, replace=False)` → diagnostics → `_remove_customers`（`operators.py:230-239`）。完整 selected list 在 line 237 已确定，然后按 NumPy 返回顺序统一删除；无删除后重算。

### Greedy

`greedy_removal` → copy/clear → `objective(destroyed.copy())` 计算一次 base → 对每个 pre-state served customer 创建独立 trial、删除该单客户、从 trial 清掉该客户的 unassigned penalty、计算 trial objective → 排序全部 score → 统一删除（`operators.py:242-261`）。

每个 marginal 都基于同一未实际破坏的 `destroyed`，不是逐删逐算；实际删除期间不重算 objective、route state 或 marginal。`rng` 完全未使用。tuple 反向排序使贡献优先，平分时当前实现隐含 customer ID 降序（258–259）；这是现状，不是拟议 dependency order。

### Related

`related_customer_removal` → copy/clear → sorted served → **一次** scalar `rng.choice(served)` 选 seed → 按 `ground_distance_matrix[seed, customer]` 排序取前 count → 统一删除（`operators.py:264-279`）。relatedness 只计算这一轮 pre-state 距离键，删除后不重算；距离相同时 Python stable sort 保留 sorted served 顺序。

### Cascade

`cascade_aware_removal` → copy/clear → pre fingerprint → sorted served → **一次** vector `rng.choice` 选 initial → 在未删除的 State 上反复调用 `_cascade_dependencies` 做 set closure → 按 sortie 顺序构造 native bundles、余者 singleton → 在删除前生成 snapshot/contract → `_remove_customers(removal_set)` → 去重 unassigned → 写 native metadata（`operators.py:581-658`）。

`_cascade_dependencies` 把命中的 sortie customers 及非 endpoint 的 customer launch/recovery 加入 closure（`operators.py:316-326`）。closure 期间 State 不变；删除顺序是当前 Python `set` 的实际迭代顺序，不是 initial RNG 顺序，也不是 sorted order。Stage 2E-A.1 必须观察并记录该真实迭代次序，不能为了“稳定”而重排。

## 执行表

| Destroy | Selection style | Incremental deletion | RNG calls | Recalculation after each deletion | Final removed set known when |
| --- | --- | --- | --- | --- | --- |
| Random | 一次无放回抽样 | No；完整 list 后统一删 | 1× `choice` | None | `operators.py:237` |
| Greedy | 对所有 pre-state 单删 trial 一次性排名 | No | 0 | None；所有 marginal 在实际删除前完成 | `operators.py:259` |
| Related | 一次 seed + 静态距离排序 | No | 1× scalar `choice` | None | `operators.py:275-277` |
| Cascade | 一次 initial 抽样 + pre-state dependency closure | No | 1× `choice` | closure 迭代重查 dependency，但不删除、不重算 objective | closure 终止于 `operators.py:599` |

删除顺序不会影响四者的**后续客户选择**，因为选择/closure 均先完成；但会影响 `unassigned` 的列表次序，且第一次命中共享 sortie 时会先 collateral-unassign 全部 sortie customers。

## 选择与实际变更表

| Destroy | Selected IDs | Actually unassigned | Routes mutated | Sorties mutated | Carrier/coordination mutated |
| --- | --- | --- | --- | --- | --- |
| Random | RNG 返回 list | post-pre 新增 unassigned，可能严格超集 | 含 selected van/anchor 的 routes | 命中 member/launch/recovery 的整条 sortie 删除 | sortie 关系随之消失；carrier map 本身不改 |
| Greedy | score top-k | 同上，可能严格超集 | 同上 | 同上 | 同上 |
| Related | distance top-k | 同上，可能严格超集 | 同上 | 同上 | 同上 |
| Cascade | final closure `R*` | 通常等于 closure；仍须 diff 验证 | 同上 | closure 相关整条 sortie | native snapshot 保存关系；map 本身不改 |

## 固定 fixture 只读诊断

2026-07-15 使用 `tests/test_stage2d0_cascade_contract.py:43-146` 的 coordinated fixture 和公开 API：

- seed 29、removal count 1：Random selected `[12]`，Related selected `[12]`，Cascade closure `[12]`，均只改 `van_0`；Greedy selected `[7]` 并删除 `sortie:0`。四者输入 State 均保持不变。
- 强制 ordinary Random/Related selected launch/recovery customer `5`：实际新增 unassigned 顺序为 `[5,7]`，整条 `sortie:0` 被删除，故 selected 与 actual 不同。
- 在同一 fixture 的 State copy 上令一条 sortie 含 `[7,9]`，仅 selected `7`：实际新增 unassigned 为 `[7,9]`。
- 把 selected van customer `9` 放在 external sortie anchor `5` 之前：删除后 anchor 的真实 route position 从 2 变 1，但 sortie dict 及其 `launch_position=2` 保持逐字段相等。对象 equality 因而不能发现全部语义 footprint。

无法从 post-state 可靠恢复的事实包括：原 service mode、原 route index/邻接 block、被删 sortie 的 customer order、launch/recovery vans/nodes/positions、drone identity、carrier transfer、原 coordination links，以及 closure/selection/deletion 的真实执行次序。

