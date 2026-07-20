# RNG and Determinism

- Each of 16 pairs ran twice; all recorded stable fields matched.
- Random and Related final stream digest: `6d5f81475e1e419dfbf72367d4d3b0ef26a57b5668b320d82f98ba052018cce1`.
- Greedy final stream digest: `6b1deb4fb11923d5a698f8b90d6e2cc7b2e247c417c329dbbdee14e0e1854292`.
- Native used exactly one seed `choice` call on the sorted eligible domain.
- Graph construction, closure, partition, snapshot, Path B validation, and removal consumed zero RNG.
- The four non-trivial Native fixtures repeated identically.
- Ordinary stream positions exactly matched Stage 2E baselines.

Result: **PASS**.

