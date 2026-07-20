# Solver Loop, SA, and Adaptive Weights Contract

`run_c_alns` resolves the operator mode and builds its strict registry once before iterations. A single `np.random.default_rng(config.alns.random_seed)` owns search randomness and is passed to selection, destroy, repair, and SA acceptance.

Per iteration:

1. independently roulette-select destroy and repair from their current weights;
2. map the pair through the frozen action registry and record its action ID;
3. destroy a copy of `current`, then repair that disposable candidate;
4. require the returned candidate to have no active removal context;
5. evaluate objective and canonical feasibility;
6. reject infeasible candidates without SA/current/best mutation;
7. update `best` only for a feasible strict global improvement;
8. accept a feasible candidate as `current` if it improves current cost or passes `exp(-(candidate-current)/T)`;
9. assign the approved outcome score `(5,3,1,0)` and accumulate independent destroy/repair statistics;
10. at the segment interval, apply `(1-reaction)*old + reaction*(score/count)`; cool temperature; append complete history.

Termination is maximum iterations plus configurable positive no-improvement early stop. The early-stop choice and exact default parameters are **APPROVED ENGINEERING DECISIONS**, not claimed as paper-explicit. Final objective/checker calls certify `best`, and infeasible final best raises.

The loop has no paper↔extended fallback, repair fallback, pair reroll, action mask, or flat action sampling. Selection is independent destroy/repair roulette; registry lookup only identifies the already selected pair.

SA and adaptive selection are **PAPER EXPLICIT/PARTIAL** at the algorithm level. Temperature defaults, scores, reaction interval, exact update code, early stop, NumPy Generator, call order, and action history schema are **APPROVED ENGINEERING DECISIONS**.

Evidence: exact selection/search-work tests, mode fingerprints, deterministic 16-pair runs, full 294-node evidence, and identical default/explicit smoke histories. Frozen blobs: `alns_solver.py`=`14cb1b2a6c010dd84b2230a80bd21b6549611b82`; `operator_modes.py`=`747b4db093c3cc15868bdb41eba2f2e9a6354298`.
