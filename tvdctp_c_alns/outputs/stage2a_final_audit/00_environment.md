# Environment

- git commit: `854f557d097f8dfe3874af5b3871f449a7f5cec0`
- git status before audit: clean for tracked source files (`git status --short --untracked-files=no`)
- final untracked path: `tvdctp_c_alns/outputs/stage2a_final_audit/` (requested audit artifacts; not algorithm code and not committed)
- Python version: `3.12.13 (main, Mar  3 2026, 15:01:35) [MSC v.1944 64 bit (AMD64)]`
- pytest version: `9.1.1`
- working directory: `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns`
- profile script path: `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\alns_solver.py` (`run_c_alns`)
- data generator path: `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\dataset_loader.py` (`generate_toy_data`)
- config builder path: `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\config.py` (`build_config`)
- audit driver: `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\_stage2a_audit_tmp.py` (temporary; deleted after run)
- random seed: `42`
- num_orders: `20`
- num_customers: `20`
- num_transshipments: `3`
- num_containers: `2`
- iterations: `10`

The audit generated route artifacts through `evaluation.evaluate_and_save`; no algorithm source was modified.
