# Native / Ordinary Adapter Boundary

- Native Cascade pairs: adapter call count 0/4; Native bundles and context existed before repair.
- Random/Greedy/Related + Cascade: adapter call count exactly 1 each.
- Random/Greedy/Related + non-Cascade repair: adapter call count 0.
- Adapter output membership equaled ordinary `actually_unassigned` and never enlarged it.
- Native graph and Path B were not used by ordinary destroys.
- Both paths used independent disposable context and left no mutable shared temporary state.

Result: **NATIVE/ADAPTER BOUNDARY PASS**.

