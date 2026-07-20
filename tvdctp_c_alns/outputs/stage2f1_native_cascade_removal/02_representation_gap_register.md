# Representation Gap Register

## Represented dependency implementation gaps to fix in Stage 2F.1

1. `DroneSortieFact` already represents all customer-valued launch, service and recovery nodes, but the old implementation queries mutable State sortie dictionaries and does not retain explicit rank/provenance. NCD-A will implement this from the pre-destroy projection.
2. `CoordinationEdgeFact(edge_kind="launch-recovery-order")` explicitly represents a directed node-to-node coordination fact. When both exact endpoints are customers, NCD-B will preserve that direction, rank and provenance.
3. The old Native partition is per-sortie intersection and can overlap. Stage 2F.1 will partition the corrected induced graph into verified weak components.

Classification: **REPRESENTED DEPENDENCY IMPLEMENTATION GAP**. These items must be corrected for Stage 2F.1 to complete.

## Known conservative representation gaps

| Gap | Current evidence limitation | Stage 2F.1 treatment | Stage 2F.2 evidence-gap plan |
|---|---|---|---|
| Truck/warehouse downstream propagation | Truck/container/warehouse facts do not encode a traceable customer→customer impact edge for a decision change | Do not infer a customer edge; retain affected truck/warehouse snapshot scope | Add a fixture proving that unsupported truck-level structure is recorded but does not falsely enlarge R* |
| General van-route downstream propagation | Route positions/segments show adjacency but do not state that all same-route customers are cascade-dependent | Do not connect all customers sharing a van or route | Add explicit exclusion fixtures and revisit only if an authoritative customer impact fact is introduced |
| Carrier transfer / linked-sortie customer propagation | `CarrierTransferFact` identifies sortie, drone and launch/recovery vans, not two customer endpoints or a linked next sortie | Preserve carrier snapshots; do not guess customer endpoints | Add cross-van and repeated-drone evidence-gap fixtures; require schema evidence before any later predicate |
| Other coordination edges | Existing `van-drone-launch` / `van-drone-recovery` edges connect resources, not customers | Exclude from the customer-only graph | Assert resource identifiers and non-customer anchors never enter R* |

Classification: **KNOWN CONSERVATIVE REPRESENTATION GAP**. These gaps are recorded, are not claimed covered, and do not by themselves block Stage 2F.1.

No `RemovalStructuralContext`, `CascadeBundleSnapshot`, or `StructuralProjection` schema expansion is required.
