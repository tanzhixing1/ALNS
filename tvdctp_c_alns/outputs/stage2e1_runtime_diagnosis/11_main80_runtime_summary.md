# True `main.py` 80-iteration Runtime Summary

The 40-iteration diagnostic completed without contract errors or unbounded stalls, so the gated real production command was run with a 3,600-second external limit.

Configuration: 20 orders, 20 customers, 2 containers, 2 transshipments, 80 iterations, seed 42, explicit `paper_mode`, otherwise production defaults.

- Process exit code: `0`
- Completed iterations: `80 / 80`
- External wall time: `2776.331017700 s` (about 46.27 minutes)
- Solver-reported runtime: `2075.4630972000305 s` (about 34.59 minutes)
- Unattributed outer time: `700.8679205 s`; it includes production data generation/evaluation/output/process teardown, but no persisted phase breakdown exists, so finer attribution is unavailable.
- Initial objective: `1484.4917238190928`
- Best objective: `1070.9374426979527`
- Final feasibility: `True`
- Final violations: none
- Time-window violations: `0`
- History rows: `80`
- Accepted iterations: `35`
- Global-best updates: `10`
- Operator mode in every row: `paper_mode`
- Registry fingerprint in every row: `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1`
- Selected action IDs: all stable IDs `0..15` occurred; every recorded pair matches the paper registry.
- First 40 action IDs exactly match the 40-iteration diagnostic replay.

Action counts: `0:6, 1:6, 2:9, 3:4, 4:4, 5:7, 6:3, 7:4, 8:5, 9:3, 10:4, 11:5, 12:5, 13:6, 14:6, 15:3`.

The earlier `901.648 s` run did not prove a deadlock: the same deterministic workload completes when allowed more time. However, the exact iteration reached and last pair started by that original timed-out process are unavailable because that run persisted neither history nor a trace before termination. They are not reconstructed by guesswork.

The 40-iteration solver time (`596.0500 s`) suggested a simple linear estimate near `1192 s`; a conservative diagnostic limit of `1800 s` was therefore plausible. The actual solver took `2075.46 s`, and total process time was `2776.33 s`, showing that bursty late regret calls and substantial non-solver/teardown cost make linear extrapolation optimistic. A future unchanged 80-iteration validation should allow approximately 3,600 seconds in this environment.
