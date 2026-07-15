# Context 生命周期与存放位置

## Option 1：DestroyResult

`DestroyResult(state, context)` 类型最显式，但会把当前 `DestroyOperator -> TVDState` 契约（`operators.py:50`）改为 union/new type，并波及：

- solver pair invocation `destroyed = DESTROY_OPERATORS[...]`（`alns_solver.py:146-147`）；
- registry type、所有直接 operator tests/diagnostics；
- repair public signatures或增加统一 unwrap layer；
- State.copy 本身较清晰，但测试和外部 API 迁移面大。

正确性可做强，但 A.1 的接口/回归风险最高，不是当前仓库的最小侵入路径。

## Option 2：Ephemeral State metadata（推荐）

使用一个保留键（例如 `_active_removal_structural_context`）临时附着在 destroyed candidate。context 内部只含 frozen values；`TVDState.copy()` 已对 metadata `deepcopy`（`state.py:300-326`），未来测试必须证明没有可变引用共享。

强制规则：

- business projection、objective/checker、`cache_signature`、cache key 永远忽略该键；
- context 默认不可业务序列化；尝试持久化 active State 应 fail closed 或先显式 consume；
- destroy entry 断言无 active context；不能只“顺便覆盖”；
- repair public boundary 必须 exactly-once detach/consume。Global/Local/Regret 即使不用内容也要验证最小 envelope 并清除；Cascade 在 local variable 中 normalize/validate；
- repair 的所有 success/failure return path 均断言 returned State 无 active raw context；Cascade 的 native transient metadata继续由 `_finish_cascade_result` 清除（`operators.py:3513-3538`）；
- solver 在 repair 返回后、acceptance/current/best 更新前再断言 context-free（pair 调用在 `alns_solver.py:145-148`）；
- repair failure candidate 与 context 一起丢弃，不把 active context 放回 input/current；
- nested repair（当前 `greedy_drone_repair` 可调用 `greedy_van_repair`，`operators.py:2528-2544`）只由最外层 boundary consume，内部调用必须识别已消费状态，避免 double-consume。

推荐生命周期：

```text
persistent current/best: no active context
destroy entry: assert absent
destroy exit: destroyed candidate carries one active context
repair entry: detach/consume exactly once
repair success: return context-free candidate
repair failure: return context-free failure candidate; caller discards as today
accept/current/best: assert absent
```

推荐通过共享 repair-boundary decorator/helper覆盖**直接函数调用和 registry 调用**，而不是只在 ALNS loop line 147 清理。A.1 必须为五个当前 registered repairs 均加生命周期测试，以免 Cascade destroy + ordinary repair 把 stale metadata 带入 persistent State。

## 比较结论

| 维度 | Option 1 | Option 2 |
| --- | --- | --- |
| 最小侵入 | 低 | 高 |
| 接口显式性 | 高 | 中；靠严格 capability/lifecycle guard |
| 当前 State.copy 适配 | 新 wrapper | 已支持 deepcopy |
| 直接测试/API 影响 | 大 | 可保持签名 |
| A.1 实施复杂度 | 高 | 中 |
| persistent 泄漏防护 | 类型层 | boundary + solver 双断言 |

## Gate

**LIFECYCLE DESIGN PASS**

推荐 Option 2，但只有“repair 边界 exactly-once consume + 所有返回路径清除 + solver persistent guard”一起实施才算通过。

