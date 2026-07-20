# Known Gaps and Prohibited Claims

| Gap ID | Description | Classification | Impact | Accepted for freeze | Future stage |
|---|---|---|---|---|---|
| KG-CAS-01 | Potential truck/warehouse downstream customer dependency is not represented | KNOWN CONSERVATIVE REPRESENTATION GAP | Native R* may be conservative outside represented predicates | YES, disclosed | future paper/model evidence stage |
| KG-CAS-02 | Broad same-van/route/container/carrier relations are not automatically customer graph edges | KNOWN CONSERVATIVE REPRESENTATION GAP | avoids invented over-propagation; may omit an unformalized dependency | YES | future contract expansion only with evidence |
| KG-CAS-03 | Native graph is customer-only; non-customer facts stay in snapshots/affected scope | KNOWN CONSERVATIVE REPRESENTATION GAP | graph cannot express a dependency without two customer endpoints | YES | future representation stage |
| KU-NAT-01 | Standalone Native seed domain/count/order and exact NumPy RNG call are not specified by paper | PAPER UNSPECIFIED + APPROVED ENGINEERING DECISION | affects deterministic trajectory, not current internal consistency | YES | preserve in 2G |
| KU-NAT-02 | weak-component bundle partition and component ordering are not fully specified | PAPER UNSPECIFIED + APPROVED ENGINEERING DECISION | one deterministic legal partition selected | YES | preserve in 2G |
| KU-NAT-03 | ascending customer-ID `dependency_order` is not paper-specified | PAPER UNSPECIFIED + APPROVED ENGINEERING DECISION | deterministic strategy order | YES | preserve in 2G |
| KU-REP-01 | Ω(B), stable tie rules, Path B and empty-Ψ behavior are engineering details | PAPER PARTIAL/UNSPECIFIED + APPROVED ENGINEERING DECISION | defines reproducible interface and atomicity | YES | preserve in 2G |
| KP-REG-01 | True Regret-2 remains slow on drone-heavy candidate sets | performance gap | correct runs can be long; no semantic defect shown | YES | Stage 2G |
| KP-MED-01 | medium regression took 397.85 s in the accepted restart and historically exceeded 901 s | performance/validation gap | raises CI/runtime budget needs | YES | Stage 2G/CI planning |
| KS-PPO-01 | PPO/RL work has not begun | OUT OF STAGE 2 SCOPE | no learned policy in baseline | YES | Stage 3 only |
| KE-EXT-01 | 35-action extended catalog is not the paper baseline | EXTENDED-MODE ONLY | explicit experiments may differ from paper trajectory | YES | remain explicit-only |

Prohibited statements:

- all truck-level dependencies are implemented;
- Cascade removal is a unique or word-for-word reproduction of every unspecified paper detail;
- objective `811.9529412450966` is a global optimum;
- Stage 3 PPO/RL is complete;
- Regret performance has been solved;
- `extended_mode` belongs to the paper baseline.

All are avoided in this audit.
