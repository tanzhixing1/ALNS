# Operator Registry and Mode Contract

Default and legacy-missing mode resolve to `paper_mode` in config, solver, main CLI, diagnostics, tests, and recorded experiments. Canonical CLI spelling is `--operator-mode`; the underscore typo fails fast.

Paper registry:

- destroy order: Random, Greedy, Related, Native Cascade;
- repair order: Global, Local, True Regret-2, Cascade;
- exact Cartesian product: 16 actions;
- IDs: continuous `0..15`, no missing, extra, duplicate, or hole;
- fingerprint: `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1`;
- action 15: `cascade_aware_removal × cascade_repair`.

Action 15's approved canonical flow reaches one snapshot validation candidate in its fixed traces. Exact checker baselines are paper `910` / objective `653`, extended `885` / objective `608`. These call counts are strict regression expectations, not paper rules.

Extended registry:

- explicit `extended_mode` only;
- 7 destroys × 5 repairs = 35 approved actions;
- paper IDs 0–15 preserve identical pair meanings; extended-only IDs are 16–34;
- fingerprint: `588c3c20cc1b34c66bb90f4e6e3296af5397f1ad4ba671b07d59f1f15a446514`;
- no fallback between modes, pair masking, reroll, or flat action sampling.

The code action IDs, exact Python registry layout, and fingerprints are **APPROVED ENGINEERING DECISIONS**. `extended_mode` is **EXTENDED-MODE ONLY** and is not part of the frozen paper baseline.

Evidence: Stage 2E.1 contract; Stage 2F.1.1; F2 54/54 mode file and two main smokes; final targeted registry/default/exact nodes.
