# Stage 2D 与原有 Pair 的最强回归契约

## Cascade + Cascade：严格逐序列等价

同 initial State、seed、config、removal size，改造前/后记录并比较：

- initial selection、final closure、deletion attempt order、actual unassignment order、RNG method/args/results；
- current native bundle partition/order、canonical snapshot contents、affected scope、bundle IDs/fingerprints；
- 每 bundle raw strategy generation sequence、feasible sequence、stable-identity unique sequence；
- selected strategy identity、完整 objective、final business fingerprint、full checker tuple；
- failure path/atomic rollback、complexity canaries。

只允许新增 wrapper/raw-context metadata，且 repair 返回前必须清除。现有 legacy removal oracle 与 RNG test位于 `tests/test_stage2d0_cascade_contract.py:161-199,244-267`；Stage 2D repair顺序/identity/feasibility tests位于 `tests/test_stage2d1_cascade_repair.py:114-176,238-344,495-535,594-628`。

## 原本兼容的其他 12 pairs

4 destroy × Global/Local/Regret，在同 fixture/seed/config 下逐 pair 比较：destroy selected IDs、selection/deletion/actual order、repair raw/feasible/unique candidate sequence（按各 operator适用 trace）、selected move/result、objective breakdown、final business fingerprint、full feasibility/violations 与完整 RNG trace。只“最终 feasible”不够。

特别包括 Cascade destroy + 三个 ordinary repair：repair boundary须消费/清除 raw context和 legacy transient contract，不得改变候选顺序或让 metadata进入 current/best。

## 新解锁的 3 pairs

Random/Greedy/Related + Cascade 必须分别证明：

- 通过受信 capability validator 与 ordinary adapter；
- bundles 来自真实 pre facts/atomic edges；无边客户 singleton；
- union==R、互斥、R 不扩大、external 不进入；
- precedence 与 boundary validation通过后才进入真实 `Ω(B)`；
- missing/tampered context fail closed，不伪造 metadata、不走 fallback；
- destroy input State 与 persistent current/best 不污染；成功/失败返回均 context-free。

## 测试矩阵

至少覆盖：van singleton、连续 removed block、两个不连续 same-route singleton、multi-customer sortie、selected anchor导致 collateral actual set、cross-van launch/recovery、carrier transfer、external anchor position shift、multi-atomic component、precedence cycle/tamper、pre-existing unassigned、empty R、stale fingerprint、copy isolation、跨三次 fixed-seed determinism。

