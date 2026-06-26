# CVRP Notebook 复盘笔记：ALNS 中一个解如何变化

这份笔记复盘 `examples/capacitated_vehicle_routing_problem.ipynb` 的核心逻辑。重点不是画图或数据读取，而是看清楚 ALNS 如何从一个初始解出发，不断“破坏 - 修复 - 接受/拒绝 - 更新最优解”。

## 1. CVRP 中一个解长什么样

在 notebook 里，一个 CVRP 解由 `CvrpState` 表示，核心变量是：

```python
routes = [[1, 2, 3], [4, 5]]
unassigned = []
```

含义：

- `routes`：车辆路线列表，每个子列表是一辆车服务的客户顺序。
- `unassigned`：暂时没有被安排进任何路线的客户，通常由 destroy 算子产生。
- `objective()`：计算所有路线的总距离，ALNS 用它判断一个解好不好。

仓库节点 `0` 不放进路线中，路线成本计算时会自动加上：

```python
0 -> route customers -> 0
```

## 2. ALNS 主循环

可以把 `result = alns.iterate(init, select, accept, stop)` 理解成下面这段伪代码：

```python
current = init
best = init

重复直到 stop：
    选 destroy 和 repair
    destroyed = destroy(current)
    candidate = repair(destroyed)

    判断 candidate 是否接受

    如果接受：
        current = candidate

    如果 candidate 比 best 好：
        best = candidate

最终返回 best
```

对应 notebook 中的对象：

```python
alns.add_destroy_operator(random_removal)
alns.add_repair_operator(greedy_repair)

select = RouletteWheel([25, 5, 1, 0], 0.8, 1, 1)
accept = RecordToRecordTravel.autofit(init.objective(), 0.02, 0, num_iterations)
stop = MaxIterations(num_iterations)

result = alns.iterate(init, select, accept, stop)
```

解释：

- `add_destroy_operator(...)`：注册破坏算子。
- `add_repair_operator(...)`：注册修复算子。
- `RouletteWheel(...)`：选择本轮用哪个 destroy/repair 算子。当前 notebook 里只有一个 destroy 和一个 repair，所以选择作用不明显。
- `RecordToRecordTravel.autofit(...)`：接受准则，允许接受一些略差的解，帮助跳出局部最优。
- `MaxIterations(...)`：停止条件，这里表示最多迭代固定次数。
- `result.best_state`：整个搜索过程中见过的最好解。

## 3. 一个解的完整链路变化

### 第 1 步：`nearest_neighbor()` 生成初始解

```python
init = nearest_neighbor()
```

它用最近邻规则构造一个可行初始解：

```python
init.routes = [[...], [...], ...]
init.unassigned = []
```

这一步不是 ALNS 的搜索过程，只是给 ALNS 一个起点。

### 第 2 步：`destroy(current)` 破坏当前解

基础版本使用：

```python
destroyed = random_removal(current, rng)
```

它会从 `current.routes` 中随机选一些客户删除。

例如：

```python
current.routes = [[1, 2, 3], [4, 5]]
current.unassigned = []
```

如果删除客户 `2` 和 `5`，则变成：

```python
destroyed.routes = [[1, 3], [4]]
destroyed.unassigned = [2, 5]
```

关键动作：

```python
destroyed = state.copy()
```

先复制当前解，避免直接破坏原来的 `current`。

```python
destroyed.unassigned.append(customer)
```

把被删除客户加入待修复列表。

```python
route = destroyed.find_route(customer)
route.remove(customer)
```

找到客户所在路线，并从路线中删除。

### 第 3 步：`destroyed.unassigned` 产生

`unassigned` 是 destroy 和 repair 之间的桥。

destroy 负责把客户从路线里拿出来：

```python
routes -> routes + unassigned
```

repair 再负责把这些客户放回去：

```python
routes + unassigned -> routes
```

所以 ALNS 的一次迭代，本质上是：

```text
完整解 -> 残缺解 -> 新的完整解
```

### 第 4 步：`greedy_repair(destroyed)` 修复残缺解

```python
candidate = greedy_repair(destroyed, rng)
```

它会不断从 `unassigned` 中取出客户，并插回路线。

关键动作：

```python
customer = state.unassigned.pop()
```

从待修复客户中取出一个客户。

```python
route, idx = best_insert(customer, state)
```

寻找把该客户插入哪条路线、哪个位置，能够让距离增加最少。

```python
if route is not None:
    route.insert(idx, customer)
else:
    state.routes.append([customer])
```

如果找到可行插入位置，就插入原有路线；如果所有路线都插不进去，就新开一条路线。

例如：

```python
destroyed.routes = [[1, 3], [4]]
destroyed.unassigned = [2, 5]
```

修复后可能得到：

```python
candidate.routes = [[1, 2, 3], [4, 5]]
candidate.unassigned = []
```

### 第 5 步：`best_insert()` 找成本增加最小的位置

`best_insert(customer, state)` 会枚举：

- 每一条路线；
- 每一个可插入位置。

例如：

```python
route = [1, 3]
customer = 2
```

可插入位置有：

```python
[2, 1, 3]
[1, 2, 3]
[1, 3, 2]
```

对于每个位置，用 `insert_cost(...)` 计算距离增加量。

插入位置在 `pred` 和 `succ` 之间时：

```python
delta = dist[pred][customer] + dist[customer][succ] - dist[pred][succ]
```

意思是：

```text
新增两条边：pred -> customer，customer -> succ
删除一条旧边：pred -> succ
```

`best_insert` 最后选 `delta` 最小的位置。

### 第 6 步：`can_insert()` 检查容量约束

```python
total = data["demand"][route].sum() + data["demand"][customer]
return total <= data["capacity"]
```

含义：

- 先算当前路线已有客户需求；
- 再加上待插入客户需求；
- 如果不超过车辆容量，就允许插入。

这就是 CVRP 的核心约束检查。

### 第 7 步：得到 `candidate solution`

repair 完成后，得到一个新的完整解：

```python
candidate.routes = [[...], [...], ...]
candidate.unassigned = []
candidate.objective()
```

此时 `candidate.objective()` 可以计算总距离。

candidate 可能比 current 好，也可能比 current 差。

### 第 8 步：`accept/reject` 决定是否替换 current

`RecordToRecordTravel` 决定 candidate 是否被接受。

如果 candidate 被接受：

```python
current = candidate
```

如果 candidate 被拒绝：

```python
current 保持不变
```

注意：即使 candidate 比 current 差，也可能被接受。这样 ALNS 才有机会跳出局部最优。

### 第 9 步：更新 `best_state`

无论 candidate 是否比 current 稍差，只要它比历史最好解更好：

```python
best = candidate
```

最终：

```python
solution = result.best_state
```

得到整个搜索过程中见过的最好路线方案。

## 4. `random_removal` 和 `string_removal` 的区别

基础破坏算子：

```python
random_removal()
```

特点：

- 随机删除客户；
- 简单；
- 适合入门；
- 对问题结构利用较少。

进阶破坏算子：

```python
string_removal()
```

特点：

- 随机选一个中心客户；
- 找它附近的客户；
- 从相关路线中删除连续片段；
- 更像是在重构一个局部区域；
- 通常比纯随机删除更有效。

可以这样理解：

```text
random_removal：随机挖几个点
string_removal：挖掉一小片相关区域
```

这也是 notebook 结果变好的原因：更懂问题结构的 destroy 算子，能创造更有价值的重构机会。

## 5. 迁移到 Truck-Van-Drone 问题时要改什么

CVRP notebook 给出的不是最终模型，而是一套框架。

需要保留的思想：

- 用 `State` 表示一个完整解；
- 用 `objective()` 评价解；
- 用 destroy 拿掉一部分服务安排；
- 用 repair 重新插入；
- 用 accept/reject 控制搜索；
- 用 best_state 保存历史最好方案。

需要改造的地方：

- `routes` 不再只是车辆路线，可能要表示 truck、van、drone 的协同路径。
- `unassigned` 不一定只是客户，也可能包含被拆掉的转运关系或无人机任务。
- `can_insert()` 要检查容量、续航、同步、转运、时间窗等约束。
- `insert_cost()` 要计算距离、时间、等待、转运成本、迟到惩罚等综合代价。
- `random_removal()` 可以升级为删除某些客户、转运点、无人机 sortie。
- `string_removal()` 可以升级为围绕某个转运点或局部区域进行破坏。

一句话：

```text
CVRP 的核心是“客户插入车辆路线”；
Truck-Van-Drone 的核心是“客户服务方式 + 转运关系 + 多载具同步”的重新安排。
```

## 6. 最重要的记忆版

```text
nearest_neighbor
    生成初始完整解

destroy
    从 routes 中删除客户
    放入 unassigned

repair
    从 unassigned 取客户
    找最便宜的可行插入位置
    插回 routes

candidate
    修复后的新完整解

accept/reject
    决定 candidate 是否成为 current

best_state
    保存历史最好解
```

ALNS 的关键不是“随机乱试”，而是：

```text
有控制地破坏当前解，再用聪明的规则修复它。
```
