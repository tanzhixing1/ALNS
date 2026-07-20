# Atomic Removal Membership Safety

## Selected path

**Path B — isolated working-copy validation.**

There is no separate authoritative static helper that exactly predicts every `_remove_customer` co-removal side effect. Native removal therefore:

1. copies the caller State and clears stale disposable metadata on the copy;
2. captures the pre-destroy projection and original unassigned membership;
3. builds the full graph, `R*`, bundles and all snapshots before mutation;
4. executes `_remove_customers` on the isolated copy in closure discovery order;
5. computes `newly_unassigned = post_unassigned - pre_existing_unassigned`;
6. requires `newly_unassigned == R*` before attaching contract/context;
7. raises `RemovalContextContractError` with `ATOMIC CO-REMOVAL CONTRACT VIOLATION` on any missing or out-of-`R*` member.

No failure path returns a candidate, partial bundle, snapshot or active context. There is no fallback and `R*` is never enlarged after observing side effects.

## Evidence

- All four canonical fixtures: exact newly-unassigned membership equals `R*` in both runs.
- Side-effect fixture: removing drone customer 8 implicitly unassigns sortie service, while closure already contains the customer recovery anchor 6; final new membership is exactly `{6,8}`.
- Poisoned authoritative-removal test: an injected out-of-`R*` unassignment fails fast; caller business signature and metadata remain unchanged and no context is attached.
- Snapshots are immutable and captured before the isolated mutation.
