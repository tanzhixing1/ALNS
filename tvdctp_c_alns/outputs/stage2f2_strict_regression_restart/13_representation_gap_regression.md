# Known Conservative Representation Gap Regression

The approved customer predicate inventory remains closed to:

- NCD-A same drone sub-route (symmetric arcs);
- NCD-B explicit customer-to-customer launch/recovery order (directed arc).

Passing focused/full tests confirm represented relationships build edges, preserve direction/rank/provenance, and propagate through the ordered fixed point.

The following remain intentionally unrepresented and were not invented as customer edges:

- potential truck/warehouse downstream dependency;
- broad same-van or same-route dependency;
- broad same-truck-route dependency;
- broad same-container/warehouse dependency;
- carrier/resource links without two explicit customer endpoints.

Non-customer route, truck, warehouse, carrier and coordination facts remain snapshot affected scope only. The unrelated-customer, non-customer-anchor, non-customer-coordination, and same-route-noncontiguous tests all passed. No report claims all truck-level dependencies are implemented.

```text
KNOWN CONSERVATIVE REPRESENTATION GAPS PRESERVED
```
