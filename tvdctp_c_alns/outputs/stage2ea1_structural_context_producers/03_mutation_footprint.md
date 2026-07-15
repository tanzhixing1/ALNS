# Authoritative mutation footprint

`diff_structural_projection(pre, post, actual)` is the only footprint source.
Selected customer IDs are never used to predict the footprint.

It records:

- changed van route IDs and minimal prefix/suffix edit intervals with direct
  predecessor/successor boundary nodes;
- stable structural sortie identities removed/added and customer sequences;
- changed launch/recovery links, carrier relations/transfers and coordination
  edges;
- service-mode and unassigned transitions;
- directly touched external customers/resources.

Stable sortie IDs use canonical structural content plus duplicate occurrence
ordinal, so list-index shifts do not misclassify unchanged sorties.

Focused evidence covers:

- van customer removal (`van_0` minimal interval);
- single and multi-customer sortie removal;
- collateral unassignment (`selected=(5,)`, `actual=(5,7)` and a two-customer
  sortie case);
- launch/recovery and coordination-link removal;
- cross-van carrier-transfer removal;
- route boundary precision: removing customer 10 records external customers
  `(9,11)` but not same-route customers 5 or 12.

External entities never enter `actually_unassigned_customer_ids`. Whole-route,
distance, warehouse and container co-membership are not used to broaden the
boundary.
