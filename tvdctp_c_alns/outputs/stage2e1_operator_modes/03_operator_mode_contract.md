# Operator mode contract

Canonical values are only `paper_mode` and `extended_mode`.

- Missing config field (legacy object): `paper_mode`.
- `ALNSConfig` / `build_config()` default: `paper_mode`.
- Explicit `None`, empty string, aliases, typos, or unknown values:
  `ConfigurationError`.
- Extension is enabled only through an explicit config value or
  `--operator-mode extended_mode`.
- Registry contents, operator failures, script location, and extra dictionary
  keys never change the mode.
- `run_c_alns()` resolves the mode and constructs the registry once before the
  initial solution and iteration loop.
