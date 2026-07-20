# State Copy Profile

For the focused iteration-10 Regret call:

- `State.copy` calls: `17,787`.
- Cumulative measured `State.copy` wall time: `22.288559294538572 s`.
- Exact-scoring candidate States: `17,743`.
- Scoring candidate States retained as final repair State: `0`; the selected move descriptor is reapplied to the working State.
- Copy isolation semantics: unchanged in the evaluated prototype and final baseline.
- `TVDState.copy` implementation: unchanged throughout.

The audit probe's first memory sampler implementation returned zero because its Windows API handle signature was not declared correctly. Baseline peak memory is therefore marked **unavailable from this probe**, rather than guessed. The corrected sampler measured the prototype only; without a valid baseline pair, the memory Gate is **NOT ESTABLISHED** (report 12).

No delayed-copy or shallow-copy optimization was authorized. The repair-local exact-result/timing prototype failed the performance Gate and was reverted.
