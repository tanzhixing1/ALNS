# Read-only Runtime Probe Design

`runtime_probe.py` lives only in this diagnostic output directory. It imports the production modules and invokes the real `build_config`, `generate_toy_data`, `initial_solution`, and `run_c_alns` path.

Instrumentation properties:

- Existing callables are wrapped with `functools.wraps`.
- Durations use `time.perf_counter`.
- Start/end events are written and flushed immediately to JSONL.
- `_roulette_choice` is observed to associate the production-selected action with later phases; the wrapper does not call or advance the RNG.
- Registered destroy/repair functions, objective, canonical checker, ordinary-removal Cascade adapter, and public Cascade bundle enumeration are timed.
- Existing repair diagnostics are copied to events where available. Missing fields remain `unavailable`; production code was not extended to invent them.
- Inputs, State objects, candidates, return values, exception behavior, registry keys, names, weights, and call order are unchanged.
- Periodic Python stacks are emitted every 60 seconds from a daemon observer using `sys._current_frames()`.

An initial experiment using Windows native delayed `faulthandler.dump_traceback_later` produced an access violation during the first 20-iteration attempt. That probe-only incident is preserved in `05_20iter_trace_attempt1_native_crash.jsonl` and `probe_20_attempt1_native_crash_stdout.txt`. The design was changed to keep `faulthandler.enable()` for fatal exceptions and use the read-only Python stack observer for periodic snapshots. The official 20-iteration rerun selected the same deterministic prefix/pair sequence, so no expensive pair was rerolled away.

The runner finishes with `os._exit` only after all trace and stack streams are flushed and closed. This avoids interpreter teardown retaining the probe's large aggregate profiling graph; it does not alter solver execution.
