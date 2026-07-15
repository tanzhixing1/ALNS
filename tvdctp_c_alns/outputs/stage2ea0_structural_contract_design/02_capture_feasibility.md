# Capture Feasibility Gate

## 方案 A：入口不可变结构投影（推荐）

在 destroy 自己的 working copy 建立后、任何业务 mutation 前捕获一个 immutable structural projection；destroy 保持原选择、closure 和删除流程；结束后以 pre projection 与 post projection 的规范 diff 计算 actual-unassigned、mutation footprint 与 external boundary，再从 pre projection 提取 raw facts。

纯 post diff 无法恢复 selection/deletion 顺序，因此方案 A 需附带一个**非结构增量捕获**：只观察已经发生的 initial selection、最终 selected iterable 的实际 `_remove_customers` 迭代、以及 `mark_unassigned` 形成的新增顺序。它不捕获 route/sortie 内容、不调用 RNG、不改变 iterable；权威结构事实仍全部来自入口 projection。尤其 Cascade set 必须在 `_remove_customers` 原循环内记录，不能预先 sorted 或换成新容器。

### 最小 projection

- customer service mode、pre-unassigned；
- 所有 van route 的稳定 van ID、home、完整节点顺序；
- 所有 sortie 的 source occurrence、drone ID、ordered customers、launch/recovery nodes、van IDs、positions；
- drone initial carrier/home；
- order/container assignment 与 container/truck/warehouse context 的业务 allowlist；
- route endpoints、selected transshipment 等影响 customer/anchor 身份的业务 metadata allowlist；
- 不含 timing、objective cache、diagnostics、Cascade/context metadata。

不需要再 `deepcopy(TVDState)`：现有四个 destroy 已各自 `state.copy()`（`operators.py:233,247,267,584`），新增 capture 可把业务结构规范化为 frozen tuples/dataclasses。这样避免复制无关 timing/cache/diagnostics，也避免 active context 的递归 deepcopy 风险。capture 只读字段，不调用 `objective`、checker、`cache_signature` 或 profile cache；不会消耗 RNG，也不改变当前 cache 命中。

该方案覆盖所有四者，因为它们均在任何业务删除前已确定 working copy，而且所有删除最终经过 `_remove_customers`。Greedy 的 trial copies 不属于最终 destroyed candidate；capture 放在 line 247 后、base objective 前即可完整保存源事实，且不介入 marginal 计算。Cascade 的现有 native snapshot/partition/order继续原样生产。

## 方案 B：每次删除前增量捕获

不推荐作为结构事实权威来源：

- `_remove_customer` 一次可删除共享整条 sortie（`operators.py:200-208`），局部“当前 customer”容易漏记其他 member、launch/recovery、carrier 与两条 van routes；
- 同一 sortie/route 可能多次命中，需要实体去重、片段合并和冲突处理；
- 后一次调用面对的已是 mutated State，无法恢复首次删除前的整体相对位置；
- 为捕捉共享结构会把 repair-specific/structure-specific 逻辑渗入公共删除 helper；
- hook 分布更广，更容易意外改变 helper 顺序或 iterable 物化。它本身不必消耗 RNG，但实施面与回归风险显著更高。

## 行为保持判定

| 必须保持 | 可行性 |
| --- | --- |
| removed set / customer selection order | PASS；只观察现有结果 |
| deletion order | PASS；在现有循环中 append-before-call，不重排 |
| RNG 次数与顺序 | PASS；capture 不接触 rng |
| Greedy marginal | PASS；projection 无 objective/cache side effect |
| Related relatedness | PASS；不改 seed 或 distance sort |
| Cascade closure/native partition | PASS；native evidence 直通 |
| business State mutation | PASS；post diff 观察实际结果，不预测 mutation |

## Gate

**CAPTURE FEASIBILITY PASS**

推荐方案 A：入口 immutable structural projection + 最小执行顺序观察 + authoritative pre/post diff。这里的顺序观察不是方案 B 的结构增量快照；它只补足最终 State 无法表达的执行序列。

