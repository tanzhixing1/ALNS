# State.copy Cost and Mutation Ratio

Every copy duplicates mutable roots for transshipment/truck/van routes,
tractor/container structures, homes and carrier maps, sorties, order/container
assignments, service modes, unassigned, metadata and timing. Seven large roots
use `deepcopy`: tractor routes, container routes, van routes, sorties,
order assignments, container assignments and timing.

- Actual heavy calls: 17,786; total
  23.877473 s; mean
  0.001342487 s.
- P50/P90/P95/P99: 0.001391450 /
  0.001777950 /
  0.001924675 /
  0.002428390 s.
- Share of clean Regret wall: 19.80%.
- Independent 24-copy `tracemalloc` sample: about
  44817 retained bytes
  per complete copy. Its timed mean is slower because tracing was enabled and is
  not substituted for the production timing above.
- Exact-scoring candidate copies retained: 0; discarded after scoring:
  17,743. The selected descriptor is applied
  again to the working State.

Direct `_apply_move` mutates 4/18 copied mutable roots for van moves
(22.22%) and 3/18 for drone moves
(16.67%); candidate-volume weighted root ratio is
16.70%. Recursive post-evaluation representative ratios,
including derived timing/cost/checker facts, are recorded in `08a`; the linked
multi-customer/relaunch case changed only 9.09%
of projected leaves.

Conclusion: **yes**—almost every exact candidate copies the complete State while
the insertion itself mutates a small route/sortie/service/unassigned locality;
derived timing then propagates beyond that direct locality.
