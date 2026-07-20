# Memory Profile

The initial baseline sampler was invalid and returned zero, so baseline peak memory
is recorded as **unavailable**, not as `0` and not guessed.

The corrected prototype sampler measured three focused runs:

| Repetition | Peak working set bytes | Peak private bytes |
|---:|---:|---:|
| 1 | 1,049,153,536 | 1,579,188,224 |
| 2 | 1,047,212,032 | 1,579,487,232 |
| 3 | 1,048,465,408 | 1,579,507,712 |
| Median | 1,048,465,408 | 1,579,487,232 |

Because the baseline peak is unavailable, the required `<=20%` increase cannot be
proven. The memory gate is therefore **NOT ESTABLISHED**, never treated as PASS.
The prototype was reverted, so final production adds no persistent cache memory.
