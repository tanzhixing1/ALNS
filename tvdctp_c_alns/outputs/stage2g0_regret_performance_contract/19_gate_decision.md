# Gate Decision

| Gate | Result | Evidence |
|---|---|---|
| Frozen baseline HEAD correct | PASS | reports/raw evidence |
| Initial tracked/staged diff clean | PASS | reports/raw evidence |
| Historical performance evidence reviewed | PASS | reports/raw evidence |
| Current baseline reprofiled | PASS | reports/raw evidence |
| Benchmark fixtures frozen | PASS | reports/raw evidence |
| Instrumentation behavior-neutral | PASS | reports/raw evidence |
| Regret production call chain complete | PASS | reports/raw evidence |
| Runtime breakdown complete | PASS | reports/raw evidence |
| Candidate counts recorded | PASS | reports/raw evidence |
| Unique business State ratio recorded | PASS | reports/raw evidence |
| State.copy cost quantified | PASS | reports/raw evidence |
| Mutation ratio quantified | PASS | reports/raw evidence |
| Van affected scope defined | PASS | reports/raw evidence |
| Drone affected scope defined | PASS | reports/raw evidence |
| Dynamic scope matches prediction | PASS | reports/raw evidence |
| Timing propagation mapped | PASS | reports/raw evidence |
| Objective dependencies mapped | PASS | reports/raw evidence |
| Checker dependencies mapped | PASS | reports/raw evidence |
| Shared computation opportunities decided | PASS | reports/raw evidence |
| Regret recalculation dependency decided | PASS | reports/raw evidence |
| Unsafe locality assumptions rejected | PASS | reports/raw evidence |
| Optimization classes assigned | PASS | reports/raw evidence |
| Stage 2G.1 scope recommended | PASS | reports/raw evidence |
| Performance acceptance contract complete | PASS | reports/raw evidence |
| Focused audit tests pass | PASS | reports/raw evidence |
| No production changes | PASS | reports/raw evidence |
| No test changes | PASS | reports/raw evidence |
| No approximation introduced | PASS | reports/raw evidence |
| Stage 2G.1 not performed | PASS | reports/raw evidence |
| Stage 3 not performed | PASS | reports/raw evidence |

```text
TRUE REGRET-2 PERFORMANCE ROOT CAUSES CONFIRMED
CURRENT BASELINE PERFORMANCE REPROFILED
CANDIDATE AFFECTED-SCOPE CONTRACT ESTABLISHED
OBJECTIVE/CHECKER/TIMING DEPENDENCIES MAPPED
PAPER-MODE SEMANTIC EQUIVALENCE CONTRACT FROZEN
STAGE 2G.0 COMPLETE
STAGE 2G.1 READY
STAGE 3 HELD
NO_COMMIT_REQUIRED
```

Stage 2G.1 first target: candidate-scoped immutable shared timing/structural
evaluation context. Expected gain comes from removing repeated timing/signature/
physical-route traversal; risk is low-to-medium. Required oracle is exact
per-candidate State materialization plus first/second/regret/RNG/solver trajectory
comparison. Top-K, sampling, beam, approximate objective/checker, unproved pruning
and selective Regret recomputation remain prohibited in paper mode.
