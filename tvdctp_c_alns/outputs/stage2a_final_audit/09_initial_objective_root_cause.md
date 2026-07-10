# Initial Objective Root Cause

## Initial objective root cause: PASS

| Run | high_floor_ratio | Instance fingerprint | Initial objective |
| --- | ---: | --- | ---: |
| Previous reconstruction | 0.35 | `6cbc5686a43d752af34b24e7d74194a71704a721befc84607e09383ea58fb8ea` | 1484.491723819093 |
| Current regression fixture | 0.15 | `b76654c6fcdedd62f3c6c56a916035962b89908e49bc02320c782c0b59d55dfc` | 1177.590654086155 |

The runs use different config and different instance fingerprints because the generated high-floor flags differ. No other config field, fixed dimension, seed, commit, objective implementation, or entry path difference is needed to reproduce the delta. The values therefore cannot be interpreted as an algorithm improvement/regression on the same instance.

`1484.491724` and `1177.590654` come from different effective instance configurations; they do not represent objective improvement or degradation on an identical instance.
