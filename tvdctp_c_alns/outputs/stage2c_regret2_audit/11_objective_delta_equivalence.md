# Objective delta equivalence

Real two-route fixture with one unassigned customer. Base objective: 10598.194603229318.

| Candidate | Base obj | Delta | Base + delta | Full candidate obj | Difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| van | 10598.194603229318 | -9972.721822691594 | 625.4727805377242 | 625.4727805377233 | 9.09e-13 |
| same-van drone | 10598.194603229318 | -9829.124038814834 | 769.0705644144837 | 769.0705644144845 | -7.96e-13 |
| cross-van drone | 10598.194603229318 | -9830.896000000000 | 767.2986032293175 | 767.2986032293181 | -6.82e-13 |

All differences are below `1e-12`. Sorting the three candidates by delta exactly matches sorting by their independently recomputed full candidate objectives.

The large negative deltas are expected: applying the final missing-customer move removes the existing partial-State infeasibility penalty. This is why Regret-specific exact scoring is necessary and why the shared greedy insertion proxy was not reused as the final Regret ranking value.
