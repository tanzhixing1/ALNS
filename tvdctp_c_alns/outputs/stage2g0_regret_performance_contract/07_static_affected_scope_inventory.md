# Static Affected-Scope Inventory

The exact matrix is in `07a_static_affected_scope_matrix.csv`.

Van insertion directly edits one target route, its primary-route mirror,
service mode and unassigned. Timing propagation begins at the inserted arc but
must include all downstream nodes and every sortie/recovery/carrier relation
connected through the fixed-point synchronization graph. Other route geometry
and stage-1/container decisions are unchanged.

Drone insertion directly appends one concrete sortie and edits all customers in
that sortie. It can couple the launch and recovery route timelines, transfer a
physical drone between vans, delay later relaunches, change dynamic carried-drone
capacity, and change waiting/feasibility/cost derived facts. Cross-van recovery
therefore requires a two-route dependency closure.

Whole-bundle candidates are **NOT APPLICABLE TO TRUE REGRET-2**. Cascade repair
logic is not imported into this contract.
