# State.copy isolation

`TVDState.copy()` continues to deep-copy all ordinary metadata, including the
existing mutable Cascade contract/diagnostic structures. It recognizes only
the active raw-context key and safely shares that instance because the entire
`RemovalStructuralContext` descendant graph is immutable.

Evidence:

- copied State and source State share the immutable context identity;
- assignment to a context field raises `FrozenInstanceError`;
- route/sortie/business mutations on the copied State do not affect source;
- no live State/route/sortie object reference is stored;
- all pre/post maps and sequences are immutable canonical records;
- the existing Stage 2D metadata-copy/replacement tests remain passing.
