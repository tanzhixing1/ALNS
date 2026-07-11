# Cross-van recovery check

The real two-route fixture produced 31 unique feasible Regret candidates: 7 van and 24 drone. The drone set contained 15 same-van and 9 cross-van strategies.

A candidate with launch on `van_0` and recovery on `van_1` was selected directly from Ω(i), applied through `_apply_move`, and passed `check_solution_feasible` with no violations.

Its exact delta was -9830.896 and full-objective equivalence error was below `7e-13`. No recovery-van restriction, nearest-node rule, threshold, or cross-van pruning was added.
