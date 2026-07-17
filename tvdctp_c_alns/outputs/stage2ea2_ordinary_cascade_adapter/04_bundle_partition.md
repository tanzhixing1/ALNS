# Bundle partition

Atomic edges are treated as undirected only for membership. Stable connected
components form bundles and isolated nodes form singletons.

Tests prove:

- singleton van `{10}` remains one singleton;
- contiguous route block `{9,10}` forms one bundle;
- non-contiguous same-route `{9,11}` forms two bundles;
- full removed sortie `{7,9}` forms one bundle;
- same-drone sorties without a direct transfer remain separate;
- actual-R union is complete, memberships are disjoint and external-boundary
  customers are excluded.

There is no forced all-R bundle, mode/route/drone grouping or singleton
fallback after construction failure.
