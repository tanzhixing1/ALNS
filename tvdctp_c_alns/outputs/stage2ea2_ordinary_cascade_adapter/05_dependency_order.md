# Dependency order

Bundle membership and dependency order are separate. Directed precedence comes
from source route order, source sortie order, launch/service/recovery order,
verified carrier transitions and explicit coordination order.

Kahn topological sorting uses first structural occurrence as its stable
tie-break. It never uses sorted customer IDs as an unstructured fallback. A
fixture with route order `10→9` verifies dependency order `(10,9)` even though
the context's set-normalized actual IDs are `(9,10)`.

Cycles are controlled contract-construction failures; no edge is silently
removed and no cyclic component is split.
