# Stage 2E-A.0 — 论文接口边界

## 结论

论文明确给出四个 destroy、四个 repair、全部 `4×4=16` 个组合，并明确 Cascade removal 的递归 removal-set closure 与 Multi-node cascade repair 对 bundle 的联合重建语义；论文没有披露普通 destroy 到 Cascade repair 的结构数据接口。本阶段选择通用 pre-destroy `RemovalStructuralContext`，是工程实现选择，不是论文规定。

## 证据边界

| 命题 | 结论 | 证据 |
| --- | --- | --- |
| 4 个 destroy | 论文明确 | 既有定向复核 `outputs/stage2e_paper_operator_mode/00_paper_operator_evidence.md`：PDF pp.30–31, lines 690–727 |
| 4 个 repair | 论文明确 | 同上：PDF pp.31–32, lines 728–754 |
| 全部 16 个组合 | 论文明确 | 同上：Figure 3、Eq.(103)、PDF p.36 lines 835–845 |
| Cascade removal closure | 论文明确 | `outputs/stage2d_cascade_repair_pre_audit/03_paper_quotes_and_evidence.md`：Eq.(93), p.31 lines 711–719 |
| bundle 与 `Ω(B)` 联合重建 | 论文明确 | 同上：p.32 lines 743–753、Algorithm 1 steps 8–14 |
| 普通 destroy 的结构输出接口 | 论文未明确 | 目标段落与 Algorithm 1 均未给出 |
| 普通 destroy 后如何 partition bundle | 论文未明确 | 无规则、伪代码或作者源码 |
| dependency order / external boundary | 论文未明确 | Algorithm 1 未给 bundle 内顺序或边界冻结规则 |
| snapshot、State copy 或其他载体 | 论文未明确 | 无数据类型或调用接口 |

论文中的 `B` 是客户集合；route、sortie、launch/recovery、carrier 与 coordination 是相关重建结构，不是当然的 bundle 成员。公式（93）规定 removal set closure，不直接规定 bundle partition 或 dependency order。

## 本阶段 implementation choice

采用：

```text
RemovalStructuralContext (raw, objective facts)
        ↓
normalize_for_cascade_repair(context) (repair-specific interpretation)
        ↓
List[CascadeBundleSnapshot]
        ↓
existing cascade_repair
```

不得表述为论文明确要求 `RemovalStructuralContext`、`CascadeBundleSnapshot`、source fingerprint 或本报告的 adapter 规则。这些都是为补齐论文未披露接口而作的、可验证且保守的实现选择。

