# Repair Call Graphs

- `greedy_van_repair` → `_best_van_move` / `_best_drone_move` / `_best_drone_move_for_customers` → `_drone_insert_hard_feasible` → `check_solution_feasible` → `objective`
- `greedy_drone_repair` → `_best_van_move` / `_best_drone_move` / `_best_drone_move_for_customers` → `_drone_insert_hard_feasible` → `check_solution_feasible` → `objective`
- `best_mode_repair` → `_best_van_move` / `_best_drone_move` / `_best_drone_move_for_customers` → `_drone_insert_hard_feasible` → `check_solution_feasible` → `objective`
- `regret_repair` → `_best_van_move` / `_best_drone_move` / `_best_drone_move_for_customers` → `_drone_insert_hard_feasible` → `check_solution_feasible` → `objective`
- `cascade_repair` → `_best_van_move` / `_best_drone_move` / `_best_drone_move_for_customers` → `_drone_insert_hard_feasible` → `check_solution_feasible` → `objective`
