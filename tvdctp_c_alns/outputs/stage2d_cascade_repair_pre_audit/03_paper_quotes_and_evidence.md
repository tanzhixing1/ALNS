# Paper quotes and evidence

Quotes are kept short and tied to a precise location. “Cannot support” records the limit of each passage.

| Location | Short original excerpt | Chinese interpretation | Supports | Cannot support |
|---|---|---|---|---|
| Page 27, lines 613-620 | “forming a unified structure of affected routes and sub-routes that must be jointly updated” | 修改会沿多级依赖传播，受影响路线与无人机子路线应统一更新 | Cascade is structural and cross-modal | Exact bundle representation or candidate algorithm |
| Page 30, lines 690-694 | “removes a subset of customer nodes ... and places them into an unserved set” | Destroy 产生本轮未服务集合 | Repair source is destroy-produced unserved customers | Cascade bundle partition details |
| Page 31, lines 711-719, Eq. (93) | “recursively expanded ... All customers in R*, together with their associated drone sub-routes, are removed simultaneously” | Removal computes dependency闭包并同时移除关联子路线 | `R*` and dependency propagation belong to removal | Repair fallback or insertion order |
| Page 31, lines 720-726 | “not a simple multi-node deletion strategy” | Cascade removal is structural, including downstream vehicle/drone effects | Removal must preserve structural dependency information | That every downstream customer is always included |
| Page 32, lines 743-746 | “a bundle of customers selected for joint insertion ... formed from customer sets removed together” | Bundle 是由共同移除客户形成的联合插入集合 | Bundle exists explicitly and comes from removal | Resource objects are themselves bundle members |
| Page 32, Eq. (95), lines 745-749 | `pi*(B) = argmin ... f(S +_pi B)` | Select the best full-objective joint bundle strategy | Objective-based joint candidate choice | Exact enumeration, tie-break, or empty-set handling |
| Page 32, lines 749-753 | “does not insert customers independently but restores interdependent structures coordinately” | Prohibits treating the intended operator as independent customer insertion | Joint multi-node semantics | Whether a heuristic may approximate `Omega(B)` |
| Page 32, lines 750-753 | “may need simultaneous adjustment of launch and receiving van routes” | Van-drone repair may jointly modify both associated routes | Associated external anchors/routes may need structural adjustment | Arbitrary unrelated route modification |
| Page 33, lines 782-787 | “removed customer nodes are partitioned into multiple bundles ... each bundle is reconstructed jointly” | `R*` is dependency partitioned and processed bundle-by-bundle | Removal-to-repair data flow and scope | Bundle processing order |
| Page 34, Algorithm 1, steps 8-14 | “Partition R* ... Construct ... Omega(B) ... Reinsert bundle B ... jointly reconstruct” | Formal pipeline is partition, joint strategy, objective choice, coordinated reconstruction | Core Stage 2D semantics | Global fallback, failure policy, exhaustive implementation |

## Paper-unspecified details

- Exact dependency graph construction beyond examples.
- Exact partition algorithm when dependency relations overlap.
- Bundle processing order and deterministic tie-breaks.
- Exact search/enumeration method for `Omega(B)`.
- Empty `Omega(B)` behavior and atomic rollback policy.
- Whether another repair operator may be used as fallback.
- Handling unrelated pre-existing unserved customers.
- Exact limits on modifying served nodes that are associated anchors rather than bundle customers.
