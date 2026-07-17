# Registry fingerprint

Schema: `stage2e1-action-registry-v1`.

- Paper: `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1`
- Extended: `588c3c20cc1b34c66bb90f4e6e3296af5397f1ad4ba671b07d59f1f15a446514`

The fingerprint is SHA-256 over canonical, sorted-key, compact JSON containing
schema version, mode, and ordered `(action_id, destroy_name, repair_name)`.
Tests freeze the paper value, reverse input dictionary insertion order, and
rebuild it in another process. Python `hash`, object addresses, UUIDs, set repr,
and input dictionary order are not used.
