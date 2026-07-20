# Other Operator Isolation

Temporary focused tests verified that Global, Local, and Cascade repairs did not
construct the prototype Regret cache. Existing Stage 2C, Stage 2D, Stage 2E-A.1,
Stage 2E-A.2, and Stage 2E.1 tests were included in the later non-medium regression.

The prototype was fully reverted. Final `git diff` contains no production changes,
which gives exact isolation for:

- Global repair;
- Local repair;
- Native Cascade repair;
- ordinary Cascade adapter;
- all destroy operators;
- paper and extended action registries;
- objective and checker functions;
- SA and adaptive weights.

Other-repair median timing regression was not benchmarked because the focused gate
failed before downstream performance gates. No performance PASS is claimed.
