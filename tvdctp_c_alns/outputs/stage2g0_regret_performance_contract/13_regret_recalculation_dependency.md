# Regret Recalculation Dependency Audit

After each selected insertion the current implementation correctly recomputes
all remaining customers. Customers sharing the modified route, insertion anchors,
drone/carrier, capacity or timing closure are definitely affected. Other
customers are at least potentially affected because their complete candidate set
may use those resources and exact penalty/checker terms remain global.

No current production predicate proves a remaining customer disjoint from the
complete route/sortie/carrier/timing/checker dependency closure. Therefore:

- definitely affected: all customers with an explicit shared dependency;
- provably unaffected in the audited implementation: **0 certified customers**;
- potentially affected/unknown: every other remaining customer;
- selective Regret recomputation: **NOT CURRENTLY SAFE**.

Different customer, van, distance, current best or service mode is not accepted
as proof. Only a future exact dependency certificate plus full-candidate oracle
may populate `PROVABLY UNAFFECTED`.
