# Exact-tie determinism

**Implementation choice: the paper does not specify exact objective ties.**

The focused test constructs two different complete `BundleReconstructionStrategy` objects, assigns both the identical complete objective, and evaluates candidate lists in original and reversed input order.

Assertions passed:

- identities differ and both strategies remain present;
- selection key is `(objective, stable full identity)`;
- three selections choose the same strategy;
- reversing input order does not change selection;
- resulting State fingerprint is identical;
- dict/set/hash/generation order is not used;
- objective cost is not a deduplication key;
- no van-before-drone or drone-before-van preference is added.

The three fixed-seed end-to-end runs also selected the same identity hashes:

- bundle 0000: `42832e97f7f1bfc4d2a72fcfba1c83b5df50c2a80830e6c46a5b1c225abc50fa`
- bundle 0001: `dd62319263ce6e2bc5678e280e5ab93867c703dc941251d2f9b1beb556c78745`

Result: PASS
