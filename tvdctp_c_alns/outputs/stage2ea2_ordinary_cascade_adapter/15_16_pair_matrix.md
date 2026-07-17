# 16-pair compatibility matrix

| Destroy / Repair | Global | Local | Regret | Cascade |
| --- | --- | --- | --- | --- |
| Random | B | B | A | A |
| Greedy | A | A | A | A |
| Related | B | B | A | A |
| Cascade | B | B | A | A |

- A — contract-compatible and fixture-feasible: **10**.
- B — contract-compatible but fixture-infeasible/returned incomplete: **6**.
- C — contract-incompatible: **0**.
- D — crashed or state-polluted: **0**.

Therefore `A+B=16`, `C=0`, `D=0`. Planned destroy-major indices are not a
production registry and no action mapping was added.
