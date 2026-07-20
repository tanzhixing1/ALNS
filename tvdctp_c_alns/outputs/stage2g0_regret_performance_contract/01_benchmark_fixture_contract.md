# Benchmark Fixture Contract

## A. Heavy Regret call

- Source: second regret_repair entry in deterministic 20-customer, 2-container, 10-iteration paper-mode prefix.
- Input fingerprint: `322c9cbceb26cde7319950e575dd3e8a26574643d143036715bedd9f88ad1a17`.
- Unassigned: `[7, 23, 24, 13, 22, 21, 16]`; vans=3,
  physical drones=12, containers=2.
- Seed/config: 42; 20 customers/orders, 2 containers, 2 transshipments,
  `paper_mode`; production `regret_repair` entry.
- Current-baseline capture cost: 26.160563 s.
- First selected customer: `16`.
- First selected move: `['van', 16, 'van_0', [3, 9, 19, 10, 8, 4], 5, 3, 1, 3]`.
- Returned objective/checker: `1128.0529725913307` / `True`;
  violations `[]`.

The complete route/sortie structure and RNG state are retained in
`raw/stage2g0_measurements.json`.

## B. Small deterministic Regret call

- Source: reconstructed exactly from the Stage 2C cross-van fixture semantics;
  no tracked test fixture was changed.
- Fingerprint: `8bee5555ef10a344184347d1edd6f33d52a0fa209fe47f3a4bc42cb54829a4e6`; seed 2026; one unassigned
  customer `6`.
- It produces 7 van, 30
  same-van drone, and 18 cross-van drone
  hard-feasible moves.
- Derived boundary fixtures set capacity and latest service time exactly at the
  selected candidate value; both remain feasible.

## C. Solver-level fixed run

- 10 customers/orders, 1 container, 2 transshipments, 5 iterations, seed 4,
  `paper_mode`.
- Actions: `[14, 9, 14, 7, 7]`; Regret appears twice
  as action 14.
- Final objective `620.3366173230896`, fingerprint
  `51e8f4548076f23b62503176b1e8c7483844a3e5c680ca0b3213d9ec8f901cf5`, checker PASS.
