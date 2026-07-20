# Known Conservative Representation Gap Regression

Preserved:

- no inferred customer edge merely from a shared van route;
- no inferred customer edge merely from a shared truck route, warehouse, or container;
- carrier/resource identifiers never become customer nodes;
- non-customer route segments remain snapshot scope only;
- current structural customer facts create only NCD-A same-subroute and NCD-B exact launch/recovery customer edges.

Focused exclusions and positive predicate tests passed in the 81-test recheck. The non-trivial Native fixtures also demonstrated represented edges entering R* without unsupported route-wide expansion.

Claim deliberately avoided: all truck-level dependencies are implemented.

Result: **KNOWN CONSERVATIVE REPRESENTATION GAPS PRESERVED**.

