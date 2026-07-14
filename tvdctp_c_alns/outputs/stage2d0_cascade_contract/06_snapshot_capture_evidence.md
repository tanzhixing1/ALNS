# Snapshot capture evidence

The capture call occurs after the existing `bundles` list is complete and before `_record_destroy_diagnostics`, `_remove_customers`, and `_remove_duplicate_unassigned`. Every structural field is read from that intact pre-removal State.

| Evidence case | Assertions |
|---|---|
| Original service | Stored mode equals the source `service_mode` before destroy |
| Van customer | Source van ID, absolute route position, local route segment, home warehouse, order container, assigned warehouse |
| Same-van drone | Source drone ID, sub-route, launch/recovery node and position, same launch/recovery van, unchanged carrier |
| Cross-van drone | Source launch van, recovery van, positions, initial/launch/recovery carrier, transfer `True`, both affected route segments |
| Multiple bundles | Distinct stable bundle IDs and disjoint sortie snapshots in the controlled fixture |
| Missing data | Optional fields remain `None`; unresolved route association is labelled unresolved rather than defaulted |

Focused evidence is implemented in `tests/test_stage2d0_cascade_contract.py`. The test fixture includes van service, same-van recovery, and cross-van carrier transfer. The paper PDF was not modified.
