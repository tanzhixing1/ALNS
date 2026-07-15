# Fingerprint 与 Context ID

## Business / structural fingerprint

建立单一 canonical `business_state_projection(state)`；覆盖 `state.cache_signature()` 当前业务字段（`state.py:212-298`）并显式 allowlist `warehouse_ready_time` 等确属业务的 metadata。永久排除：

- `RemovalStructuralContext`、Cascade contract/bundles/repair diagnostics；
- operator logs/profile、timing、objective/checker cached results；
- object address、UUID、non-deterministic repr、runtime counters、trace diagnostics。

```text
pre_fingerprint  = sha256(canonical_json(pre business projection))
post_fingerprint = sha256(canonical_json(post business projection))
```

context 包含两个 digest，但 business projection 永远不读取 context，因而无自引用。现有 `_state_business_fingerprint` 使用 `repr(cache_signature())`（`operators.py:134-136`）；A.1 新设计应改用明确 canonical serialization，同时用 strict regression 证明其 business等价，不悄悄改变 Stage 2D snapshot内容/identity。

## Stable serialization

- UTF-8 JSON，`sort_keys=True`、紧凑 separators、Unicode 不转义；
- tuple/list 保留语义顺序；unordered collection 先按成员 canonical bytes 排序；
- dict key 类型显式编码，禁止依赖 insertion order；
- int/string/bool/null 类型不混淆；float 使用有限 IEEE value 的规范十进制形式，拒绝 NaN/Infinity，业务容差字段在 projection 层按既定精度规范化；
- stable IDs 与 occurrence ordinals来自业务结构，不含 Python hash/address。

在同一 schema 与数值规范下，digest 跨 Python 进程、Windows/Linux 和 dict 构造顺序稳定；schema/数值规范变化必须升 version。

## Deterministic `context_id`

```text
sha256(canonical_json({
  schema_version,
  structural_context_version,
  source_destroy_operator,
  pre_fingerprint,
  post_fingerprint,
  ordered actually_unassigned_customer_ids,
  customer_selection_order,
  deletion_attempt_order,
  actual_unassignment_order
}))
```

禁止 `uuid.uuid4()`、`random.random()` 或任何 `rng.*`；context ID 不消耗算法 RNG。context ID 不进入 business fingerprint/cache key。

## Gate

**FINGERPRINT DESIGN PASS**

