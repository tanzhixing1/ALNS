# Small Main Smoke

## Default mode

Real production entry, 10 orders/customers, one container, two transshipments, 10 iterations, seed 42, with no operator-mode argument:

- exit 0;
- initial objective `829.203`;
- best objective `811.9529412450966`;
- canonical feasibility true; violations empty; penalty 0;
- history has 10 complete rows, all `paper_mode`, paper fingerprint `08a24ddd...55d71a1`;
- observed action IDs: `13,15,7,11,4,8,11,15,0,13`;
- action 15 occurred naturally at iterations 2 and 8; no weight/seed/reroll manipulation;
- summary/history/route/load/plot artifacts present;
- output does not claim a global optimum.

## Explicit mode

The canonical CLI command with `--operator-mode paper_mode` also exited 0 and produced the same objective, feasibility, violation set, action sequence, IDs, registry fingerprint, and business output as default mode.

The task text's underscore spelling `--operator_mode paper_mode` was attempted once and correctly rejected by argparse as an unrecognized argument. This is expected fail-fast behavior under the frozen canonical CLI contract; there was no silent fallback. The successful explicit run uses the production-supported hyphen spelling.

## Lifecycle and fixed action evidence

The main history exercised Native+Cascade directly. Independent fixed Action 15 traces verify exact context cleanup and final-best context absence; solver lifecycle tests verify initial/current/best ownership. No fallback, reroll, masking, or context leak occurred.

```text
SMALL MAIN SMOKE PASS
```
