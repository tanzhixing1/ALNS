# Candidate Infeasibility Analysis

## Paper Action 15

- Processed bundle: `[7,9,10]`.
- Snapshot application: customer 9 restored to `van_0`; customers 7 and 10 restored as drone sorties launched/recovered at 9.
- Bundle customers remaining unassigned: none.
- Allowed later-bundle unassigned set: `[5,6,8,11,14]`; actual candidate set matches exactly.
- Canonical checker additionally reports the exact unassigned list; the Stage 2D wrapper is allowed to ignore only that exact missing-service message.
- Retained hard violations: customers 8, 11 and 14 are high-floor but currently have `service_mode=unassigned`, not drone.
- Involved route/sortie: not the restored `[7,9,10]` structures; the violations refer exclusively to customers in the later bundle.

## Extended Action 15

- Processed bundle: `[5,6,8,11,14]`.
- Snapshot application: customer 5 restored to `van_0`; sorties `[6,11]` and `[14,8]` restored at node 5 with their original drones/carriers.
- Bundle customers remaining unassigned: none.
- Allowed later-bundle unassigned set: `[7,9,10]`; actual candidate set matches exactly.
- Retained hard violation: customer 10 is high-floor but temporarily `unassigned`, not drone.
- Again, the violating customer belongs to the later bundle, not the applied snapshot bundle.

## Classification

The failure is not caused by an omitted route, wrong launch/recovery anchor, wrong carrier, wrong customer membership, or misread `dependency_order`. Every restored structure matches its pre-destroy snapshot and the strict bundle/scope validator has already passed.

It is a natural hard-feasibility result under the already-approved Stage 2D policy: full canonical validation is applied to an intermediate bundle State; only the exact allowed-unassigned message may be suppressed, while wrong-mode/high-floor violations remain strict. The remaining high-floor customers are deliberately deferred to a later bundle, so Ψ(B) becomes empty and the existing atomic-failure rule returns `repair_base`.

```text
CANDIDATE NATURALLY INFEASIBLE UNDER FROZEN HARD-FEASIBILITY BOUNDARY
NO SNAPSHOT OR BUNDLE FIELD DEFECT
```

