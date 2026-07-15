# Stage 2E-A.1 pre-implementation behavior baseline

Captured before any Stage 2E-A.1 production-source change.

- Audit commit / starting baseline: `e5d6ca16beb2dea928cbf2717352edf408d141c6`
- Fixture: real coordinated Stage 2D fixture from `tests/test_stage2d0_cascade_contract.py`
- Destroy count: one customer; fresh NumPy PCG64 seed `29` per run
- Input business fingerprint: `b9f9ede9f8a413b4e214e3afa4d98e9111c0e79b6945e9e57e9bc64a0a5048dc`
- RNG-before digest: `6b1deb4fb11923d5a698f8b90d6e2cc7b2e247c417c329dbbdee14e0e1854292`
- Source State remained unchanged in every run: **YES**

The fingerprint values in this file are SHA-256 digests of the baseline
`TVDState.cache_signature()` representation. They are regression evidence, not
a redefinition of the canonical or Stage 2D fingerprints.

## Four destroy baselines

| Destroy | Selection order | Selected/final R* | Deletion/actual-unassignment order | Output fingerprint | RNG-after |
| --- | --- | --- | --- | --- | --- |
| Random | `[12]` | `[12]` | `[12]` | `994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978` | `6d5f81475e1e419dfbf72367d4d3b0ef26a57b5668b320d82f98ba052018cce1` |
| Greedy | ranking winner `[7]` | `[7]` | `[7]` | `ade2fc27ba74b9753cd49b4f68f1ff6e08d9773140ae99c000c7d11a82f846eb` | unchanged from RNG-before |
| Related | seed `[12]` | `[12]` | `[12]` | `994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978` | `6d5f81475e1e419dfbf72367d4d3b0ef26a57b5668b320d82f98ba052018cce1` |
| Cascade | initial `[12]` | `[12]` | `[12]` | `994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978` | `6d5f81475e1e419dfbf72367d4d3b0ef26a57b5668b320d82f98ba052018cce1` |

For all four rows, `actually_unassigned_customer_ids` is exactly the displayed
actual-unassignment order for this fixture. Tests also use anchor and
multi-customer-sortie counterexamples where selected and actually-unassigned
sets differ; equality is not assumed by the implementation.

### Shared output structural facts for Random, Related, and Cascade

- Van routes: `van_0=[3,5,9,10,11,3]`, `van_1=[3,6,3]`.
- Drone sorties remain `(drone_0, van_0->van_0, 5,[7],5)` and
  `(drone_1, van_0->van_1, 3,[8],6)`.
- Service mode changes only for customer `12`: `van -> unassigned`.
- Drone initial-carrier map remains
  `drone_0/1->van_0`, `drone_2/3->van_1`,
  `drone_4/5->van_2`, `drone_6/7->van_3`.
- Pre-existing business metadata remains present; ordinary destroys add no
  Cascade metadata.

### Greedy-specific output facts

- The single pre-state trial/ranking winner is customer `7`; Greedy consumes no
  RNG.
- Van routes are unchanged from the input fixture.
- Sortie `drone_0: van_0->van_0, 5,[7],5` is removed; the cross-van sortie for
  customer `8` remains unchanged.
- Service mode changes only for customer `7`: `drone -> unassigned`.

### Related-specific evidence

- Seed customer: `12`.
- Static distance order: `[12,9,5,6,11,8,10,7]`.
- Selection and output equal Random for this fixture, while the selection
  mechanism remains the existing distance ranking.

### Cascade-specific evidence

- Initial set: `[12]`; final closure `R*`: `[12]`; dependency trace: empty.
- Native partition and dependency order: `[[12]]` and `[[12]]`.
- Native affected scope:
  `selected_transshipment:3`, `container:0`, `van:van_0:4-6`; no sortie,
  launch/recovery, carrier, or coordination-edge IDs.
- Old contract schema/source: `1` / `cascade_aware_removal`.
- Old destroy call ID:
  `85e5862611154e12ca70c77ed253dd4c4e0b0ee5d825033781752b690e2e7176`.
- Old bundle fingerprint:
  `8eb99601571e8554f1c68edeaaa34f67241af5172cc7ed7bc4f47c4d56c51d9c`.
- Old Cascade contract is current at this baseline.

## Current 16-pair compatibility and exact result baseline

The action numbers below are audit/planned destroy-major, repair-minor labels;
they are **not** current production registry IDs.

| Pair | Removed order | Candidate-sequence digest if exposed | Selected result | Objective | Final fingerprint | Feasible | Contract |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| Random + Global | `[12]` | not exposed | returned | 40927.316361140 | `819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76` | No | compatible |
| Random + Local | `[12]` | `1ec78cd24b2d10f4736eb8f85c9fc9edd4d55b8b4f64e9e1afbc5068155bc943` | returned | 40927.316361140 | `819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76` | No | compatible |
| Random + Regret | `[12]` | `b4b209050fc7fea02d550e14e0c0d39b1827a9bd03f4c754168e64d7961a7b65` | returned | 926.373751792 | `3f8b9bc597f3be2a267ad88c5a6c2640e877eb395973824a7c40a204956ac7fc` | Yes | compatible |
| Random + Cascade | `[12]` | no bundle candidates | failure | 10926.095429883 | `994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978` | No | **incompatible** |
| Greedy + Global | `[7]` | not exposed | returned | 765.252317540 | `da4451935d067199fc880bbde649a891258dc027df8b833b3e8bbeaaf9217e76` | Yes | compatible |
| Greedy + Local | `[7]` | `d023cf038d2c5cfcebb09f30a18ee16a7f5188478bbae33833368832761ea74f` | returned | 773.150287337 | `95a1746970f9d4d18841f0261f05f6a4d1783c92923359249b2e1db510aeb933` | Yes | compatible |
| Greedy + Regret | `[7]` | `1b8736acc5cf5a18cc4290b707a063626fa914f861eeeaabe12baba84e68626d` | returned | 765.252317540 | `da4451935d067199fc880bbde649a891258dc027df8b833b3e8bbeaaf9217e76` | Yes | compatible |
| Greedy + Cascade | `[7]` | no bundle candidates | failure | 10762.799812194 | `ade2fc27ba74b9753cd49b4f68f1ff6e08d9773140ae99c000c7d11a82f846eb` | No | **incompatible** |
| Related + Global | `[12]` | not exposed | returned | 40927.316361140 | `819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76` | No | compatible |
| Related + Local | `[12]` | `1ec78cd24b2d10f4736eb8f85c9fc9edd4d55b8b4f64e9e1afbc5068155bc943` | returned | 40927.316361140 | `819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76` | No | compatible |
| Related + Regret | `[12]` | `b4b209050fc7fea02d550e14e0c0d39b1827a9bd03f4c754168e64d7961a7b65` | returned | 926.373751792 | `3f8b9bc597f3be2a267ad88c5a6c2640e877eb395973824a7c40a204956ac7fc` | Yes | compatible |
| Related + Cascade | `[12]` | no bundle candidates | failure | 10926.095429883 | `994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978` | No | **incompatible** |
| Cascade + Global | `[12]` | not exposed | returned | 40927.316361140 | `819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76` | No | compatible |
| Cascade + Local | `[12]` | `1ec78cd24b2d10f4736eb8f85c9fc9edd4d55b8b4f64e9e1afbc5068155bc943` | returned | 40927.316361140 | `819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76` | No | compatible |
| Cascade + Regret | `[12]` | `b4b209050fc7fea02d550e14e0c0d39b1827a9bd03f4c754168e64d7961a7b65` | returned | 926.373751792 | `3f8b9bc597f3be2a267ad88c5a6c2640e877eb395973824a7c40a204956ac7fc` | Yes | compatible |
| Cascade + Cascade | `[12]` | `5723032f866258bfdca59723af105deca19f9880202acd8d20e8886e1b2ea010` | success | 927.880274816 | `56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e` | Yes | compatible |

Candidate-sequence digests include stable candidate identities, counts and
selection fields only; diagnostic wall-clock timing fields are deliberately
excluded.

All pair runs start from a freshly recreated fixture and seed. Random,
Related, and Cascade consume the same one `choice` call; Greedy consumes none.
The target matrix is therefore **13 contract-compatible, 3 explicitly
contract-incompatible, crashed/polluted 0**. Stage 2E-A.1 must preserve this
matrix and must not unlock planned labels 3, 7, or 11.
