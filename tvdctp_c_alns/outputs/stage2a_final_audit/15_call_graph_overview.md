# Call Graph Overview

Profile entry → `build_config` → `generate_toy_data` → `run_c_alns` → `initial_solution` / `consolidate_drone_sorties` → `objective` → `check_solution_feasible`.

ALNS iteration: operator selection → destroy → repair → local feasibility → candidate apply → objective/full checker → SA acceptance → current/best update.
