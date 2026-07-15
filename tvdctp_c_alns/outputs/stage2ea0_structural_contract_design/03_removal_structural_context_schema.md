# RemovalStructuralContext 最小 Schema

## 定义

`RemovalStructuralContext` 是本次 destroy 的 ephemeral、immutable、repair-agnostic 原始事实。它不含 `repair_bundles`、`cascade_strategy`、selected repair、repair candidate 或 objective value。

集合定义：

- `selected_removed_customer_ids`：producer 最终明确提交给删除流程的唯一客户集合；普通 destroy 是选中集合，Cascade 是现有 closure `R*`。它不等于 RNG initial seeds。
- `actually_unassigned_customer_ids`：`post.unassigned - pre.unassigned`，并以观测到的首次 transition 顺序保存；还要交叉验证相应 service transition。
- `mutation_footprint`：pre/post structural projection 的实际差异实体与片段，不是 selected IDs 的预测闭包。
- `external_boundary_entities`：与 footprint 有直接结构关系、但不在 actual set 的客户/资源；它们不进入 bundle。

另存 `customer_selection_order`（Random 抽样顺序、Greedy rank、Related distance rank、Cascade initial RNG seeds）、`deletion_attempt_order`（公共 helper 实际迭代）和 `actual_unassignment_order`，避免把三种顺序混称 `removal_order`。

## 字段矩阵

“FP/cache”说明字段是否直接进入 business fingerprint/cache key；context 全体都不进入，只有其引用的 pre/post business projection 各自计算 fingerprint。

| Field | Raw fact | Required | Capture time / post recoverable | Producer | Repair-specific | FP/cache | Serialize | Ephemeral |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `schema_version` | Yes | Yes | construction / N/A | all 4 | No | context-ID only / No | Yes | Yes |
| `context_id` | derived stable fact | Yes | after post fingerprint / No | all 4 | No | self excluded / No | Yes | Yes |
| `source_destroy_operator` | Yes | Yes | entry / No | all 4 | No | context-ID / No | Yes | Yes |
| `structural_context_version` | Yes | Yes | construction | all 4 | No | context-ID / No | Yes | Yes |
| `producer_capabilities` | producer declaration | Yes | entry / registry validation | all 4 | No | No/No | Yes | Yes |
| `pre_destroy_business_fingerprint` | derived business fact | Yes | pre / No | all 4 | No | is FP / No | Yes | Yes |
| `post_destroy_business_fingerprint` | derived business fact | Yes | post / Yes | all 4 | No | is FP / No | Yes | Yes |
| `selected_removed_customer_ids` | Yes | Yes | selection/closure / not reliably | all 4 | No | No/No | Yes | Yes |
| `customer_selection_order` | Yes | Yes | selection / No | all 4 | No | context-ID input / No | Yes | Yes |
| `deletion_attempt_order` | Yes | Yes | during existing loop / No | all 4 | No | context-ID input / No | Yes | Yes |
| `actually_unassigned_customer_ids` | Yes | Yes | pre/post + event order / set only recoverable | all 4 | No | context-ID input / No | Yes | Yes |
| `actual_unassignment_order` | Yes | Yes | mutation / post list can often recover, event verifies | all 4 | No | context-ID input / No | Yes | Yes |
| `customer_service_facts` | Yes | Yes for affected/boundary | pre / No | all 4 | No | part of pre FP only / No | Yes | Yes |
| `route_position_facts` | Yes | when route-related | pre / No | all 4 | No | pre FP only / No | Yes | Yes |
| `route_segment_facts` | Yes | when route mutated/boundary | pre + post diff / No | all 4 | No | pre/post FP only / No | Yes | Yes |
| `drone_sortie_facts` | Yes | when sortie related | pre / No after deletion | all 4 | No | pre FP only / No | Yes | Yes |
| `launch_recovery_facts` | Yes | when sortie related | pre / No | all 4 | No | pre FP only / No | Yes | Yes |
| `carrier_transfer_facts` | Yes | when sortie related | pre / No | all 4 | No | pre FP only / No | Yes | Yes |
| `coordination_edge_facts` | Yes | when represented | pre / No | all 4 | No | pre FP only / No | Yes | Yes |
| `mutation_footprint` | actual diff | Yes | post / Yes only with pre projection | all 4 | No | No/No | Yes | Yes |
| `external_boundary_entities` | derived raw relationship fact | Yes (may be empty) | pre + footprint / No | all 4 | No | No/No | Yes | Yes |
| `external_boundary_projection` | business invariant baseline | Yes (may be empty) | pre / No | all 4 | No | pre FP only / No | Yes | Yes |
| `cascade_dependency_trace` | producer evidence | No | closure time / No | Cascade only | No；removal evidence | No/No | Yes | Yes |
| `cascade_native_partition_evidence` | producer evidence | No | before deletion / No | Cascade only | No；native fact | No/No | Yes | Yes |
| `cascade_native_dependency_order` | producer evidence | No | before deletion / No | Cascade only | No；native fact | No/No | Yes | Yes |

所有字段均要求 stable primitive/frozen serialization，不保留 live `TVDState`、mutable route/sortie dict 或对象地址。raw context 不直接命名或存储 repair bundle。Cascade-only evidence 是当前 producer 的客观输出，不是所有 destroy 的必填字段。

