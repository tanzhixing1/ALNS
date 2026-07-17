# Atomic edge rules

Only direct immutable pre-destroy facts create edges:

- adjacent R customers in an ordered van route;
- adjacent R customers in the same original sortie;
- explicit launch-anchor/customer and customer/recovery-anchor relations;
- an adjacent same-physical-drone sortie pair only when the first has a real
  carrier transfer and its recovery carrier equals the next launch carrier;
- stable explicit customer-to-customer coordination facts.

Same route, same drone, same warehouse/container, distance, time-window or ID
similarity never creates an edge. A same-node launch/recovery anchor is one
membership/launch precedence edge: the complete two-ended event remains in the
snapshot, while the customer-level order does not create an artificial
`anchor→customer→same anchor` cycle. Genuine multi-customer precedence cycles
raise a controlled adapter error.
