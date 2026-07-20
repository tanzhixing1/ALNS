# Invalid Operator Mode Fail-fast Check

Command parameters: 4 orders, 4 customers, 1 container, 2 transshipments, 1 iteration, seed 42, `--operator-mode papre`.

- Process exit code: `2` (non-zero)
- External wall time: `1.136285700 s`
- Failure source: argparse rejected `papre` as an invalid choice
- Algorithm started: no
- Fallback to `paper_mode`: no
- Fallback to `extended_mode`: no

Result: **PASS**. The invalid mode failed explicitly before algorithm execution. Raw console output is in `invalid_mode_stdout.txt`.
