# Operator Mode and Registry

- Default mode from config/CLI tests: `paper_mode`.
- Legal modes: exactly `paper_mode`, `extended_mode`.
- Paper actions: 16, IDs 0..15 continuous and unique.
- Action 15: Native Cascade + Cascade.
- Missing paper entries and invalid spellings: fail fast.
- No paper/extended fallback in either direction.
- Extended registry: frozen complete allowlist, no missing/extra/duplicate pair or ID hole, paper IDs preserved.
- Action masking: absent.
- Reroll: absent.
- Fallback: absent.

Registry construction in the pair probe reproduced the frozen destroy-major table exactly. The grouped Stage 2E.1 run later failed two checker-call-count assertions; registry/action identity assertions themselves passed.

