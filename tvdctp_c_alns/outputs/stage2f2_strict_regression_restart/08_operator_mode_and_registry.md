# Operator Mode and Registry

- Default: `paper_mode`.
- Canonical values only: `paper_mode`, `extended_mode`.
- Paper registry: 16 actions, exact continuous IDs 0–15, fingerprint `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1`.
- ID 15: `cascade_aware_removal + cascade_repair`.
- Missing pairs and invalid/typo modes: fail fast.
- No paper↔extended fallback, no action masking, no flat action sampling.
- Extended registry: 35-action complete approved Cartesian product, fingerprint `588c3c20cc1b34c66bb90f4e6e3296af5397f1ad4ba671b07d59f1f15a446514`; paper IDs 0–15 retain identical meaning; no holes, extras, missing or duplicates.

The complete Stage 2E.1 file passed 54/54. Default and explicit canonical main smoke histories both use paper fingerprint, identical actions/IDs and identical business results.
