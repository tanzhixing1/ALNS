# Cache Key Contract (Prototype, Not Accepted)

The evaluated key was the deterministic SHA-256 digest of the existing
`State.cache_signature()` representation. It included the existing business-state
projection used by objective/checker caching and excluded diagnostics, action ID,
operator mode, active removal context, elapsed time, object identity, UUID, and
Python's randomized `hash()`.

Namespaces were distinct:

- `objective`
- `canonical_checker`
- `timing`

The lifetime was one `regret_repair` invocation and cleanup ran in `finally`.
Different calls, iterations, runs, configs, and datasets shared no prototype cache.

This contract passed the temporary key/scope tests, but the implementation failed
the performance gate and was reverted. There is no Stage 2E.2 cache in final
production code.
