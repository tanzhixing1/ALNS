# Paper Cascade repair semantics

## 1. Repair input

The general repair section says repair operators reinsert customers from the unserved set. The specific Multi-node Cascade Repair definition narrows its input to bundles `B` formed from customer sets removed together by Cascade Removal. Algorithm 1 first computes `R*`, then partitions `R*` into bundles using dependency relationships.

Therefore the paper-level Cascade repair input is: the current partially destroyed solution plus the final cascade-removed customer set represented as dependency bundles. It is not defined as an arbitrary list of all currently unserved customers.

## 2. Repair scope

For each bundle, the paper reinserts the bundle and jointly reconstructs its associated vehicle routes, drone sub-routes, and coordination relationships. The paper does not authorize a generic sweep over unrelated unserved customers. Treatment of unrelated pre-existing unserved customers is **Paper unspecified** because the paper's normal ALNS flow assumes the candidate starts from a feasible solution and the destroy step creates the unserved set.

## 3. Essential difference from ordinary repair

Cascade repair is not independent per-customer insertion. It constructs `Omega(B)` for the whole dependency bundle, evaluates a joint strategy, and restores coupled truck-van-drone structures together. Explicit examples include warehouse reassignment requiring van-route reconstruction and a disrupted drone sortie requiring simultaneous launch- and receiving-van adjustment.

## 4. Whether the paper defines bundles

Yes. A bundle is explicitly a set of customers selected for joint insertion and formed from customer sets removed together during Cascade Removal. Algorithm 1 says the final removal set is partitioned according to structural dependency relationships.

## 5. Bundle contents

The mathematical bundle `B` contains customer nodes. The paper also requires reconstruction of associated objects, but does not state that those objects are members of `B` itself.

| Object | Explicit bundle member? | Paper treatment |
|---|---:|---|
| Customer | YES | `B` is a customer bundle |
| Container | NO | Not named as a bundle member |
| Transshipment / warehouse | NO | Warehouse reassignment is an example of an associated truck-level change |
| Van | NO | Associated van routes may need reconstruction |
| Drone | NO | Drone coordination must remain consistent |
| Drone sortie / sub-route | NO | Associated sub-routes are removed/reconstructed |
| Launch node | NO | Part of associated sortie/route coordination |
| Recovery node | NO | Part of associated sortie/route coordination |
| Physical carrier | Paper unspecified | Receiving van is discussed; no standalone carrier object contract is defined |
| Downstream customers | Conditional | Included only when structurally dependent and therefore in `R*`/a bundle |
| Truck / tractor / trailer | NO as bundle members | Truck-van consistency and route reconstruction are required |
| Time synchronization relation | NO | A feasibility/coordination condition, not a bundle member |

## 6. Processing order

Algorithm 1 loops “for each bundle” and updates the current solution after each joint insertion. It does not specify bundle ordering, tie-breaking, or an internal customer order because the intended insertion is joint. The next bundle is naturally evaluated against the updated solution, but the paper does not provide a separate candidate-cache or recomputation rule.

## 7. Candidate generation

The paper constructs a feasible strategy set `Omega(B)` for the whole bundle, under drone payload/endurance, vehicle-route feasibility, truck-van consistency, van-drone consistency, and time windows. It does not say to call Global greedy, Local greedy, Regret, or a per-customer generic repair. The exact enumeration/search algorithm for `Omega(B)` is **Paper unspecified**.

## 8. Selection criterion

Equation (95) selects the joint strategy minimizing the full objective `f(S +_pi B)`. This is full candidate objective evaluation. Comparing objective increments is equivalent only when all candidates share the same base State.

## 9. Global fallback

**Paper unspecified.** No fallback to Global/Local/Regret, no repair-all-unserved sweep, and no skip/fail rule is described for `Omega(B)=empty`.

## 10. Dynamic recomputation

Algorithm 1 reconstructs one bundle into the current solution inside a loop. This implies that subsequent bundles see the updated solution. It does not specify sequential recomputation within a bundle because the bundle strategy is joint.

## 11. Removal/repair boundary

- Cascade Removal chooses/expands `R*`, determines structural dependency closure, removes customer nodes plus associated route/sub-route/coordination structures, and partitions the removed set into bundles.
- Cascade Repair receives those bundles, constructs and selects joint feasible strategies, reinserts each bundle, and reconstructs associated structures.
- Missing dependency closure, missing bundle partition, and missing structural context are removal/input-contract issues and must not be silently reimplemented inside Stage 2D.
