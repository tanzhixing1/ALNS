# Native Weakly Connected Bundle Partition

The Native path now partitions the graph induced by `R*` into weakly connected components. Direction is ignored only for component membership; original directed edges remain available in the audit trace. The ordinary adapter partition is untouched.

Contract checks execute before removal:

```text
union(bundle.customer_ids) == R*
sum(bundle sizes) == len(R*)
all pairwise intersections are empty
```

Bundle order follows the earliest component member in closure discovery order. Each component's `customer_ids` and `dependency_order` use stable ascending customer ID. This order is **PAPER UNSPECIFIED; DETERMINISTIC ENGINEERING ORDER**. The legacy repair-recognized semantics string is retained unchanged because Cascade repair is frozen.

The focused matrix covers one component, multiple components, directed-edge weak connectivity, repeated/cross-sortie customer connections, singleton components, exact union, disjointness and stable order.
