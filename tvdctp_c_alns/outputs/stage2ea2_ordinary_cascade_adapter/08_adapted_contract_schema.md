# Adapted contract schema

The existing `CascadeBundleSnapshot` is reused unchanged. Adapted values use:

- `source_operator`: the true Random/Greedy/Related source;
- `source_destroy_call_id`: `ordinary-adapter:v1:<full-context-id>:<revision>`;
- `source_state_fingerprint`: A.1 pre structural fingerprint;
- `customer_ids`: actual-R component in structural dependency order;
- existing customer, route, sortie, launch/recovery, carrier, truck/warehouse
  and affected-scope snapshot fields;
- dependency semantics `ordinary adapter v1 structural precedence`.

The ephemeral contract metadata also retains adapter version, full context ID,
post fingerprint, exact actual-R and external-boundary evidence. Bundle and
contract fingerprints cover the complete snapshot. Native schema values and
fingerprints are unchanged.
