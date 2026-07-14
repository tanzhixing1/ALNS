# Stage 2D multi-drone candidate coverage

This directory closes the final Stage 2D candidate-coverage question around
`_first_drone_for_van()`.

Result: named drones are **not strictly symmetric** in a live State. A decisive
real-model counterexample showed the first-only implementation could miss a
feasible second drone. The shared Stage 2C/Stage 2D enumerator now retains every
concrete candidate admitted by the existing hard-feasibility logic.

Files `00` through `06` contain the semantic audit, counterexample, before/after
mechanism, Stage 2C/2D impact, and Omega(B) disclosure boundary. Files `07` and
`08` contain test output. Files `09` through `12` contain determinism, complexity,
scope, and the final gate.

No Stage 2E, Stage 2F, or Stage 3 work is included.
