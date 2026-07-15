# Producer capabilities

Capabilities are defined centrally by immutable trusted
`ProducerDescriptor`s, not accepted as arbitrary strings.

All four producers declare:

1. `structural_context_v1`
2. `immutable_pre_projection`
3. `authoritative_post_diff`
4. `selection_order`
5. `deletion_order`
6. `mutation_footprint`
7. `external_boundary_facts`

Cascade additionally declares:

1. `cascade_dependency_trace`
2. `cascade_native_partition`
3. `cascade_native_order`

Validation rejects an unregistered source, unsupported schema/context version,
or any capability tuple different from its trusted descriptor. These
capabilities are evidence only in A.1; Cascade repair does not consume them and
ordinary destroy contexts are not adapted into Cascade bundles.
