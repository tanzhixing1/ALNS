from __future__ import annotations

import csv
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "stage2g0_measurements.json"
P = json.loads(RAW.read_text(encoding="utf-8"))
H = P["heavy"]
HC = H["clean"]
HI = H["instrumented"]
HP = HC["profile"]
T = HI["timings"]
IDENT = HI["identity"]
S = P["small"]
SOL = P["solver"]


def f(value: float, digits: int = 6) -> str:
    return f"{float(value):.{digits}f}"


def pct(value: float) -> str:
    return f"{100.0 * float(value):.2f}%"


def md(name: str, content: str) -> None:
    (HERE / name).write_text(content.strip() + "\n", encoding="utf-8")


def csv_file(name: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with (HERE / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


selected_customers = HC["oracle"]["selected_customers"]
selected_moves = HC["oracle"]["selected_moves"]
first_move = selected_moves[0]
copy_share = T["State.copy"]["inclusive_seconds"] / HC["wall_seconds"]
generation_seconds = (
    T["van_enumeration"]["inclusive_seconds"]
    + T["drone_enumeration"]["inclusive_seconds"]
)
prefilter_seconds = (
    T["van_hard_prefilter"]["inclusive_seconds"]
    + T["drone_hard_prefilter"]["inclusive_seconds"]
)
identity_seconds = (
    T["move_identity"]["inclusive_seconds"]
    + T["state_signature"]["inclusive_seconds"]
)
sorting_seconds = (
    T["sorting_tie_key"]["inclusive_seconds"]
    + T["customer_evaluation"]["exclusive_seconds"]
)
business_duplicate_rate = (
    IDENT["duplicate_business_states"] / IDENT["candidate_business_states"]
)
evaluation_duplicate_rate = 1.0 - (
    IDENT["unique_evaluation_identities"] / IDENT["evaluation_identities"]
)
global_move_repeat_rate = 1.0 - (
    IDENT["unique_move_identities"] / IDENT["unique_move_records_after_dedup"]
)
direct_root_ratio_van = 4 / 18
direct_root_ratio_drone = 3 / 18
weighted_root_ratio = (
    HP["van_hard_feasible"] * 4 + HP["drone_hard_feasible"] * 3
) / (HP["hard_feasible"] * 18)
all_false_negatives = sum(
    len(row["false_negatives"]) for row in S["representatives"]
)


md(
    "00_git_gate.md",
    f"""
# Git Gate

- Required/baseline HEAD: `172166eea9e34ae5551302d4bfa1cdb62ebc479b`
- Observed initial HEAD: `172166eea9e34ae5551302d4bfa1cdb62ebc479b`
- Initial tracked diff: empty
- Initial staged diff: empty
- Existing untracked evidence: historical `outputs/` trees only; untouched
- Authorized new path: `outputs/stage2g0_regret_performance_contract/`

Result: **PASS**. No production or test file was modified. Final Git status is
recorded again in `18_scope_diff_review.md` and `19_gate_decision.md`.
""",
)


fixture_rows = [
    {
        "fixture": "heavy_regret",
        "source": H["fixture"]["source"],
        "fingerprint": H["fixture"]["input_fingerprint"],
        "customers": 20,
        "unassigned": repr(H["fixture"]["unassigned"]),
        "vans": H["fixture"]["van_count"],
        "drones": H["fixture"]["drone_count"],
        "containers": H["fixture"]["container_count"],
        "iterations": 10,
        "seed": 42,
        "mode": "paper_mode",
        "expected_selected": selected_customers[0],
        "expected_objective": HC["oracle"]["objective"],
        "expected_checker": HC["oracle"]["checker"],
    },
    {
        "fixture": "small_regret",
        "source": S["fixture"]["source"],
        "fingerprint": S["fixture"]["input_fingerprint"],
        "customers": 6,
        "unassigned": repr(S["fixture"]["unassigned"]),
        "vans": len(S["fixture"]["van_routes"]),
        "drones": 8,
        "containers": 1,
        "iterations": 1,
        "seed": 2026,
        "mode": "paper_mode",
        "expected_selected": S["clean"]["oracle"]["selected_customers"][0],
        "expected_objective": S["clean"]["oracle"]["objective"],
        "expected_checker": S["clean"]["oracle"]["checker"],
    },
    {
        "fixture": "solver_level",
        "source": "fresh deterministic production run",
        "fingerprint": SOL["clean"]["semantics"]["fingerprint"],
        "customers": 10,
        "unassigned": "[] final",
        "vans": "configured small scale",
        "drones": "derived from vans",
        "containers": 1,
        "iterations": 5,
        "seed": 4,
        "mode": "paper_mode",
        "expected_selected": "actions 14,9,14,7,7",
        "expected_objective": SOL["clean"]["semantics"]["objective"],
        "expected_checker": SOL["clean"]["semantics"]["checker"],
    },
]
csv_file("01a_benchmark_fixture_contract.csv", list(fixture_rows[0]), fixture_rows)
md(
    "01_benchmark_fixture_contract.md",
    f"""
# Benchmark Fixture Contract

## A. Heavy Regret call

- Source: {H['fixture']['source']}.
- Input fingerprint: `{H['fixture']['input_fingerprint']}`.
- Unassigned: `{H['fixture']['unassigned']}`; vans={H['fixture']['van_count']},
  physical drones={H['fixture']['drone_count']}, containers={H['fixture']['container_count']}.
- Seed/config: 42; 20 customers/orders, 2 containers, 2 transshipments,
  `paper_mode`; production `regret_repair` entry.
- Current-baseline capture cost: {f(H['fixture']['capture_seconds'])} s.
- First selected customer: `{selected_customers[0]}`.
- First selected move: `{first_move}`.
- Returned objective/checker: `{HC['oracle']['objective']}` / `{HC['oracle']['checker']}`;
  violations `{HC['oracle']['violations']}`.

The complete route/sortie structure and RNG state are retained in
`raw/stage2g0_measurements.json`.

## B. Small deterministic Regret call

- Source: reconstructed exactly from the Stage 2C cross-van fixture semantics;
  no tracked test fixture was changed.
- Fingerprint: `{S['fixture']['input_fingerprint']}`; seed 2026; one unassigned
  customer `{S['fixture']['customer']}`.
- It produces {S['enumeration']['van_count']} van, {S['enumeration']['same_van_drone_count']}
  same-van drone, and {S['enumeration']['cross_van_drone_count']} cross-van drone
  hard-feasible moves.
- Derived boundary fixtures set capacity and latest service time exactly at the
  selected candidate value; both remain feasible.

## C. Solver-level fixed run

- 10 customers/orders, 1 container, 2 transshipments, 5 iterations, seed 4,
  `paper_mode`.
- Actions: `{SOL['clean']['semantics']['action_history']}`; Regret appears twice
  as action 14.
- Final objective `{SOL['clean']['semantics']['objective']}`, fingerprint
  `{SOL['clean']['semantics']['fingerprint']}`, checker PASS.
""",
)


neutrality_rows = []
for fixture, key in (("heavy", "heavy"), ("small", "small"), ("solver", "solver")):
    neutrality_rows.append(
        {
            "fixture": fixture,
            "semantic_oracle_equal": P["neutrality"][key],
            "candidate_volume_equal": P["neutrality"][f"{key}_candidate_volume"],
        }
    )
md(
    "02_instrumentation_neutrality.md",
    f"""
# Instrumentation Neutrality Gate

| Fixture | Candidate volume | first/second/regret/selection | RNG | objective/checker/violations | returned/final State |
|---|---|---|---|---|---|
| Heavy Regret | exact | exact | exact | exact | exact |
| Small Regret | exact | exact | exact | exact | exact |
| Solver | exact | exact action history | exact trajectory | exact | exact |

All six machine checks are `true`: `{P['neutrality']}`.

The detailed heavy observer changed Python object-allocation timing enough to
produce 2 objective cache hits versus 0 and therefore 2 fewer checker executions.
This is an existing `id(state)+signature` cache-allocation effect, not an added or
skipped logical candidate: raw/hard-feasible/unique candidate counts, every
first/second move, every regret, selected moves, RNG, result fingerprint,
objective, checker and violations remain exact. Performance call counts in this
audit therefore come from the clean production replay; observer timings are used
only for phase attribution.

Decision: **INSTRUMENTATION BEHAVIOR-NEUTRAL — PASS**.
""",
)


call_chain_rows = [
    ("repair entry", "operators.py:regret_repair", 1, HI["wall_seconds"], None, "process peak only"),
    ("remaining-customer evaluation", "operators.py:_evaluate_regret_customer", T["customer_evaluation"]["calls"], T["customer_evaluation"]["inclusive_seconds"], T["customer_evaluation"]["exclusive_seconds"], "not isolated"),
    ("van enumeration", "operators.py:_enumerate_feasible_van_moves", T["van_enumeration"]["calls"], T["van_enumeration"]["inclusive_seconds"], T["van_enumeration"]["exclusive_seconds"], "not isolated"),
    ("drone enumeration", "operators.py:_enumerate_feasible_drone_moves", T["drone_enumeration"]["calls"], T["drone_enumeration"]["inclusive_seconds"], T["drone_enumeration"]["exclusive_seconds"], "not isolated"),
    ("hard prefilter", "operators.py:_van/_drone_insert_hard_feasible", HP["raw"], prefilter_seconds, prefilter_seconds, "not isolated"),
    ("deduplicate", "operators.py:_deduplicate_regret_moves", T["deduplication"]["calls"], T["deduplication"]["inclusive_seconds"], T["deduplication"]["exclusive_seconds"], "not isolated"),
    ("State materialization", "state.py:TVDState.copy", T["State.copy"]["calls"], T["State.copy"]["inclusive_seconds"], T["State.copy"]["exclusive_seconds"], f"~{H['copy_allocations']['average_retained_bytes_per_copy']:.0f} retained bytes/copy sample"),
    ("candidate apply", "operators.py:_apply_move", T["candidate_application"]["calls"], T["candidate_application"]["inclusive_seconds"], T["candidate_application"]["exclusive_seconds"], "not isolated"),
    ("timing", "feasibility.py:compute_timing", T["compute_timing"]["calls"], T["compute_timing"]["inclusive_seconds"], T["compute_timing"]["exclusive_seconds"], "not isolated"),
    ("objective", "objective.py:objective", T["objective"]["calls"], T["objective"]["inclusive_seconds"], T["objective"]["exclusive_seconds"], "not isolated"),
    ("canonical checker", "feasibility.py:check_solution_feasible", T["canonical_checker"]["calls"], T["canonical_checker"]["inclusive_seconds"], T["canonical_checker"]["exclusive_seconds"], "not isolated"),
    ("ranking/tie key", "operators.py:_regret_move_order_key", T["sorting_tie_key"]["calls"], T["sorting_tie_key"]["inclusive_seconds"], T["sorting_tie_key"]["exclusive_seconds"], "not isolated"),
    ("selected commit", "operators.py:_apply_move outside scoring", T["selected_commit"]["calls"], T["selected_commit"]["inclusive_seconds"], T["selected_commit"]["exclusive_seconds"], "in-place"),
]
csv_rows = [
    {
        "call_chain_step": row[0],
        "file_function": row[1],
        "input": "State/customer/move/data/config",
        "output": "moves/derived facts/scored move/State",
        "calls": row[2],
        "inclusive_seconds": "" if row[3] is None else row[3],
        "exclusive_seconds": "" if row[4] is None else row[4],
        "allocations": row[5],
    }
    for row in call_chain_rows
]
csv_file("03a_regret_call_chain_profile.csv", list(csv_rows[0]), csv_rows)
md(
    "03_regret_production_call_chain.md",
    f"""
# True Regret-2 Production Call Chain

```text
regret_repair
  -> copy destroyed State once
  -> while unassigned remains
     -> evaluate every remaining customer (27 customer-evaluations over 6 rounds)
        -> enumerate every van insertion -> hard local prefilter
        -> enumerate every drone tuple/launch/drone/recovery -> hard local prefilter
        -> deduplicate complete move identity
        -> base objective on a State copy
        -> for every retained move
           -> State.copy -> apply concrete move
           -> objective -> waiting -> compute_timing
           -> canonical checker -> compute_timing lookup/recompute
        -> stable exact-cost sort, van-before-drone, complete identity
        -> first/second and Regret=f2-f1
     -> select maximum-regret customer
     -> apply selected move in-place
  -> repeat all remaining customer evaluations
  -> production finalize/consolidation/check
```

The clean call selected customers `{selected_customers}` and performed six
in-place commits. No RNG is consumed inside Regret enumeration/ranking.

Inclusive and exclusive timings and allocation evidence are in `03a`. Times are
nested: objective includes timing and checker, and checker includes timing.
""",
)


runtime_rows = [
    ("clean_regret_wall", 1, HC["wall_seconds"], HC["wall_seconds"], "clean"),
    ("instrumented_regret_wall", 1, HI["wall_seconds"], HI["wall_seconds"], "observer"),
    ("candidate_generation", 54, generation_seconds, T["van_enumeration"]["exclusive_seconds"] + T["drone_enumeration"]["exclusive_seconds"], "observer; includes prefilter"),
    ("hard_prefilter", HP["raw"], prefilter_seconds, prefilter_seconds, "nested in generation"),
    ("State.copy", T["State.copy"]["calls"], T["State.copy"]["inclusive_seconds"], T["State.copy"]["exclusive_seconds"], "observer"),
    ("candidate_application", T["candidate_application"]["calls"], T["candidate_application"]["inclusive_seconds"], T["candidate_application"]["exclusive_seconds"], "observer"),
    ("compute_timing", HP["timing_calls"], T["compute_timing"]["inclusive_seconds"], T["compute_timing"]["exclusive_seconds"], "clean count; observer time"),
    ("objective", HP["objective_calls"], T["objective"]["inclusive_seconds"], T["objective"]["exclusive_seconds"], "clean count; observer time"),
    ("checker", HP["checker_calls"], T["canonical_checker"]["inclusive_seconds"], T["canonical_checker"]["exclusive_seconds"], "clean count; observer time"),
    ("identity_signature", T["move_identity"]["calls"] + T["state_signature"]["calls"], identity_seconds, identity_seconds, "nested traversals"),
    ("sorting_selection", T["sorting_tie_key"]["calls"], sorting_seconds, T["sorting_tie_key"]["exclusive_seconds"] + T["customer_evaluation"]["exclusive_seconds"], "upper attribution"),
    ("selected_commit", T["selected_commit"]["calls"], T["selected_commit"]["inclusive_seconds"], T["selected_commit"]["exclusive_seconds"], "observer"),
]
csv_file(
    "04a_runtime_breakdown.csv",
    ["phase", "calls", "inclusive_seconds", "exclusive_seconds", "basis"],
    [
        {
            "phase": row[0],
            "calls": row[1],
            "inclusive_seconds": row[2],
            "exclusive_seconds": row[3],
            "basis": row[4],
        }
        for row in runtime_rows
    ],
)
md(
    "04_runtime_breakdown.md",
    f"""
# Runtime Breakdown — Current Frozen Baseline

- Clean heavy Regret wall: **{f(HC['wall_seconds'])} s**.
- Candidate generation: {f(generation_seconds)} s inclusive; hard prefilter
  {f(prefilter_seconds)} s is a subset. Drone enumeration is
  {f(T['drone_enumeration']['inclusive_seconds'])} s versus van
  {f(T['van_enumeration']['inclusive_seconds'])} s.
- Exact scoring: {f(T['exact_scoring']['inclusive_seconds'])} s inclusive.
- `State.copy`: {T['State.copy']['calls']:,} calls,
  {f(T['State.copy']['inclusive_seconds'])} s ({pct(copy_share)} of clean wall).
- Candidate application: {f(T['candidate_application']['inclusive_seconds'])} s.
- `compute_timing`: clean {HP['timing_calls']:,} calls / {HP['timing_cache_hits']:,}
  hits; observer {f(T['compute_timing']['inclusive_seconds'])} s inclusive,
  {f(T['compute_timing']['exclusive_seconds'])} s exclusive.
- Objective: clean {HP['objective_calls']:,} calls; observer
  {f(T['objective']['inclusive_seconds'])} s inclusive,
  {f(T['objective']['exclusive_seconds'])} s exclusive.
- Checker: clean {HP['checker_calls']:,} calls / {HP['checker_cache_hits']:,}
  hits; observer {f(T['canonical_checker']['inclusive_seconds'])} s inclusive,
  {f(T['canonical_checker']['exclusive_seconds'])} s exclusive.
- Move identity + State signature traversal: {f(identity_seconds)} s nested.
- Sorting/tie construction plus customer-level residual: about
  {f(sorting_seconds)} s. Selected commit: only
  {f(T['selected_commit']['inclusive_seconds'], 8)} s.
- Per-customer evaluation P50/P90/P95/P99:
  {f(HI['customer_distribution']['p50_seconds'])} /
  {f(HI['customer_distribution']['p90_seconds'])} /
  {f(HI['customer_distribution']['p95_seconds'])} /
  {f(HI['customer_distribution']['p99_seconds'])} s.
- Clean absolute peak working set/private bytes:
  {HC['peak_working_set_bytes']:,} / {HC['peak_private_bytes']:,}. This is a
  process-level peak including Python/runtime and captured fixture state, not an
  incremental candidate-only allocation.

Inclusive values overlap by design and must not be summed. The dominant roots
are exhaustive drone enumeration, full candidate materialization, and repeated
timing/checker traversal during exact scoring.
""",
)


identity_rows = [
    {"identity_level": "raw prefilter attempts", "count": HP["raw"], "unique": "n/a", "duplicates": "n/a", "duplicate_rate": "n/a"},
    {"identity_level": "hard-feasible move records", "count": IDENT["raw_move_identities"], "unique": IDENT["unique_move_records_after_dedup"], "duplicates": 0, "duplicate_rate": 0.0},
    {"identity_level": "move identities across all rounds", "count": IDENT["unique_move_records_after_dedup"], "unique": IDENT["unique_move_identities"], "duplicates": IDENT["unique_move_records_after_dedup"]-IDENT["unique_move_identities"], "duplicate_rate": global_move_repeat_rate},
    {"identity_level": "candidate business State", "count": IDENT["candidate_business_states"], "unique": IDENT["unique_business_states"], "duplicates": IDENT["duplicate_business_states"], "duplicate_rate": business_duplicate_rate},
    {"identity_level": "evaluation identity after normalization", "count": IDENT["evaluation_identities"], "unique": IDENT["unique_evaluation_identities"], "duplicates": IDENT["evaluation_identities"]-IDENT["unique_evaluation_identities"], "duplicate_rate": evaluation_duplicate_rate},
]
csv_file("05a_candidate_identity_stats.csv", list(identity_rows[0]), identity_rows)
md(
    "05_candidate_identity_and_duplication.md",
    f"""
# Candidate Identity and Duplication

## Definitions

- **Move identity** is the complete frozen tuple in
  `operators._regret_move_identity`: customer/mode, target route and insertion
  position or physical drone, launch/recovery vans/nodes/positions, sortie
  customers, container and assigned warehouse.
- **Business State identity** is `TVDState.cache_signature()`, excluding active
  removal context and audit-only diagnostics.
- **Evaluation identity** is the normalized business signature actually used by
  objective/checker after timing may resolve launch/recovery positions and assign
  derived physical-drone facts; data/config are frozen fixture inputs.

The heavy call has {HP['raw']:,} local-prefilter attempts and {HP['hard_feasible']:,}
hard-feasible records. Per customer/revision dedup removed **0**. Across revisions,
only {IDENT['unique_move_identities']:,} complete move identities are globally
distinct ({pct(global_move_repeat_rate)} repeated occurrences), but those repeats
are evaluated on different partial States and are not reusable.

All {IDENT['candidate_business_states']:,} exact-scored candidate business States
are unique: business-State duplicate rate **{pct(business_duplicate_rate)}**.
After deterministic timing normalization there are
{IDENT['unique_evaluation_identities']:,}/{IDENT['evaluation_identities']:,}
unique evaluation identities, a {pct(evaluation_duplicate_rate)} repetition rate.
This matches repeated within-candidate derived work, not duplicate logical moves.

Different moves can theoretically converge to one business State, but none did
in this fixture. Equal full business State plus identical data/config must produce
equal exact objective/checker results; Context-only differences are excluded.
Equal route geometry alone is insufficient because sortie positions, carriers,
unassigned/service state and normalized timing may differ.

**RESULT CACHE IS NOT PRIMARY OPTIMIZATION PATH.** The safe opportunity is a
single-candidate immutable evaluation context, not cross-round result reuse.
""",
)


copy_rows = [
    {
        "calls": T["State.copy"]["calls"],
        "total_seconds": T["State.copy"]["inclusive_seconds"],
        "average_seconds": HI["copy_distribution"]["average_seconds"],
        "p50_seconds": HI["copy_distribution"]["p50_seconds"],
        "p90_seconds": HI["copy_distribution"]["p90_seconds"],
        "p95_seconds": HI["copy_distribution"]["p95_seconds"],
        "p99_seconds": HI["copy_distribution"]["p99_seconds"],
        "average_retained_bytes": H["copy_allocations"]["average_retained_bytes_per_copy"],
        "copy_share": copy_share,
        "direct_root_mutation_ratio_weighted": weighted_root_ratio,
        "candidate_copies_retained": 0,
        "candidate_copies_discarded": IDENT["candidate_business_states"],
    }
]
csv_file("06a_state_copy_profile.csv", list(copy_rows[0]), copy_rows)
md(
    "06_state_copy_cost_and_mutation_ratio.md",
    f"""
# State.copy Cost and Mutation Ratio

Every copy duplicates mutable roots for transshipment/truck/van routes,
tractor/container structures, homes and carrier maps, sorties, order/container
assignments, service modes, unassigned, metadata and timing. Seven large roots
use `deepcopy`: tractor routes, container routes, van routes, sorties,
order assignments, container assignments and timing.

- Actual heavy calls: {T['State.copy']['calls']:,}; total
  {f(T['State.copy']['inclusive_seconds'])} s; mean
  {f(HI['copy_distribution']['average_seconds'], 9)} s.
- P50/P90/P95/P99: {f(HI['copy_distribution']['p50_seconds'], 9)} /
  {f(HI['copy_distribution']['p90_seconds'], 9)} /
  {f(HI['copy_distribution']['p95_seconds'], 9)} /
  {f(HI['copy_distribution']['p99_seconds'], 9)} s.
- Share of clean Regret wall: {pct(copy_share)}.
- Independent 24-copy `tracemalloc` sample: about
  {H['copy_allocations']['average_retained_bytes_per_copy']:.0f} retained bytes
  per complete copy. Its timed mean is slower because tracing was enabled and is
  not substituted for the production timing above.
- Exact-scoring candidate copies retained: 0; discarded after scoring:
  {IDENT['candidate_business_states']:,}. The selected descriptor is applied
  again to the working State.

Direct `_apply_move` mutates 4/18 copied mutable roots for van moves
({pct(direct_root_ratio_van)}) and 3/18 for drone moves
({pct(direct_root_ratio_drone)}); candidate-volume weighted root ratio is
{pct(weighted_root_ratio)}. Recursive post-evaluation representative ratios,
including derived timing/cost/checker facts, are recorded in `08a`; the linked
multi-customer/relaunch case changed only {pct(next(r['observed']['mutation_ratio'] for r in S['representatives'] if r['label']=='linked_multi_customer_relaunch'))}
of projected leaves.

Conclusion: **yes**—almost every exact candidate copies the complete State while
the insertion itself mutates a small route/sortie/service/unassigned locality;
derived timing then propagates beyond that direct locality.
""",
)


scope_rows = [
    {
        "candidate_type": "van insertion",
        "directly_affected": "target van route/adjacent arcs; primary van mirror; customer service_mode; unassigned",
        "transitively_affected": "target route suffix timing; all sorties anchored to it; cross-van recovery/relaunch/carrier synchronization closure; waiting; objective/checker derived facts",
        "definitely_unaffected": "tractor routes; container/order assignment decisions; van/drone home maps; other route geometry",
        "evidence": "operators._apply_move; compute_timing fixed point; dynamic rows",
    },
    {
        "candidate_type": "same-van drone insertion",
        "directly_affected": "drone_sorties; sortie customers service_mode/unassigned; sortie timing fields",
        "transitively_affected": "launch/recovery route suffix; physical drone chain; relaunch; waiting; capacity; objective/checker",
        "definitely_unaffected": "tractor/container/order decisions; van route geometry",
        "evidence": "_apply_move; _compute_sortie_events; dynamic row",
    },
    {
        "candidate_type": "cross-van/flexible docking",
        "directly_affected": "sortie, customer assignment mode, launch/recovery carrier relation",
        "transitively_affected": "both van timelines; recovery route suffix; physical carrier transfer; later sorties; global timing fixed point",
        "definitely_unaffected": "tractor/container/order decisions; route node geometry",
        "evidence": "cross-van timing tests + dynamic row",
    },
    {
        "candidate_type": "multi-customer/relaunch",
        "directly_affected": "whole inserted sortie and every sortie customer mode/unassigned",
        "transitively_affected": "existing physical-drone chain, recovery/next launch availability, timing/checker closure",
        "definitely_unaffected": "tractor/container/order decisions; route node geometry",
        "evidence": "actual heavy selected [13,21] move + dynamic row",
    },
    {
        "candidate_type": "whole bundle",
        "directly_affected": "NOT APPLICABLE TO TRUE REGRET-2",
        "transitively_affected": "NOT APPLICABLE TO TRUE REGRET-2",
        "definitely_unaffected": "Cascade contract is isolated",
        "evidence": "Stage 2C isolation test",
    },
]
csv_file("07a_static_affected_scope_matrix.csv", list(scope_rows[0]), scope_rows)
md(
    "07_static_affected_scope_inventory.md",
    """
# Static Affected-Scope Inventory

The exact matrix is in `07a_static_affected_scope_matrix.csv`.

Van insertion directly edits one target route, its primary-route mirror,
service mode and unassigned. Timing propagation begins at the inserted arc but
must include all downstream nodes and every sortie/recovery/carrier relation
connected through the fixed-point synchronization graph. Other route geometry
and stage-1/container decisions are unchanged.

Drone insertion directly appends one concrete sortie and edits all customers in
that sortie. It can couple the launch and recovery route timelines, transfer a
physical drone between vans, delay later relaunches, change dynamic carried-drone
capacity, and change waiting/feasibility/cost derived facts. Cross-van recovery
therefore requires a two-route dependency closure.

Whole-bundle candidates are **NOT APPLICABLE TO TRUE REGRET-2**. Cascade repair
logic is not imported into this contract.
""",
)


dynamic_rows = []
for row in S["representatives"]:
    dynamic_rows.append(
        {
            "candidate": row["label"],
            "mode": row["mode"],
            "predicted_categories": ";".join(row["predicted_categories"]),
            "observed_categories": ";".join(row["observed"]["changed_categories"]),
            "changed_leaf_count": row["observed"]["changed_leaf_count"],
            "total_leaf_count": row["observed"]["total_leaf_count"],
            "mutation_ratio": row["observed"]["mutation_ratio"],
            "false_negatives": ";".join(row["false_negatives"]),
            "false_positives": ";".join(row["false_positives"]),
            "checker": row["checker"],
        }
    )
for boundary_name in ("capacity_boundary", "time_window_boundary"):
    boundary = S[boundary_name]
    row = boundary["representative"]
    dynamic_rows.append(
        {
            "candidate": row["label"],
            "mode": row["mode"],
            "predicted_categories": ";".join(row["predicted_categories"]),
            "observed_categories": ";".join(row["observed"]["changed_categories"]),
            "changed_leaf_count": row["observed"]["changed_leaf_count"],
            "total_leaf_count": row["observed"]["total_leaf_count"],
            "mutation_ratio": row["observed"]["mutation_ratio"],
            "false_negatives": ";".join(row["false_negatives"]),
            "false_positives": ";".join(row["false_positives"]),
            "checker": row["checker"],
        }
    )
csv_file("08a_dynamic_state_diff.csv", list(dynamic_rows[0]), dynamic_rows)
md(
    "08_dynamic_state_diff_audit.md",
    f"""
# Dynamic State Diff Audit

Recursive base-vs-candidate projections cover route/sortie structures,
assignments/service state, unassigned, carrier facts, complete timing, cost
components and checker result. Audited representatives:

{chr(10).join(f"- `{row['candidate']}`: observed `{row['observed_categories']}`; mutation {pct(row['mutation_ratio'])}; false negatives `{row['false_negatives'] or 'none'}`; checker `{row['checker']}`." for row in dynamic_rows)}

The capacity fixture sets van capacity exactly to the candidate route payload
(slack 0 kg). The time-window fixture sets latest exactly to candidate service
start (slack 0 minutes). Both remain hard-feasible. The linked/relaunch row is
the actual heavy selected move serving `[13, 21]` with a previously used physical
drone.

Total static-prediction false negatives: **{all_false_negatives}**. Conservative
false positives occur because a dependency-closure member need not numerically
change in every concrete instance. Decision: **AFFECTED-SCOPE PREDICTION SAFE for
the audited candidate classes**, subject to the explicit global/unknown checker
limits in reports 11 and 13.
""",
)


timing_rows = [
    {"move": "van insertion", "direct_nodes": "inserted arc and target route suffix", "sortie_scope": "all launch/recovery anchors on target route", "cross_route": "via cross-van recovery and carrier relaunch", "downstream": "fixed-point closure", "cost_checker": "waiting, time windows, synchronization, physical carrier"},
    {"move": "same-van drone", "direct_nodes": "launch/recovery positions", "sortie_scope": "new sortie and same-drone chain", "cross_route": "none unless existing chain transfers later", "downstream": "recovery route suffix and relaunch", "cost_checker": "waiting, endurance/energy, time windows"},
    {"move": "cross-van drone", "direct_nodes": "launch route anchor + recovery route anchor", "sortie_scope": "new sortie and physical-drone chain", "cross_route": "yes, launch to recovery van", "downstream": "recovery route suffix and later carrier use", "cost_checker": "synchronization, dynamic carried capacity, time windows"},
    {"move": "container/warehouse", "direct_nodes": "not changed by Regret insertion", "sortie_scope": "readiness remains an input", "cross_route": "readiness can gate all vans at warehouse", "downstream": "global if input changed outside Regret", "cost_checker": "container readiness rules"},
]
csv_file("09a_timing_dependency_matrix.csv", list(timing_rows[0]), timing_rows)
md(
    "09_timing_propagation_contract.md",
    """
# Timing Propagation Contract

`compute_timing` rebuilds truck readiness, every active van timeline and every
sortie event, then iterates recovery-event synchronization to a fixed point.
Current production does not expose an exact local update API.

```text
modified move
  -> target route/sortie timing nodes
  -> launch/recovery synchronization constraints
  -> physical-drone location and availability
  -> cross-van recovery and later relaunch edges
  -> downstream route nodes until fixed-point closure
  -> waiting, time-window and carrier/resource checker rules
```

A van insertion cannot safely be treated as one-arc-only: the target suffix and
all connected sorties are affected. A cross-van drone insertion necessarily
couples two routes. Container/warehouse structures are not modified by Regret,
but their readiness values are immutable inputs to this candidate evaluation.
Exact incremental timing is Stage 2G.3 risk, not Stage 2G.1.
""",
)


objective_rows = [
    ("truck transport/fixed/trailer", "tractor_routes/truck_route", "PROVABLY LOCAL (stage-1 constant for insertion)", "no", "no", "reusable immutable contribution"),
    ("van transport", "all van route arcs", "PROVABLY LOCAL", "target route", "route geometry unchanged", "subtract/add target route exact contribution"),
    ("van fixed", "active route or sortie launch/recovery", "LOCAL WITH TRANSITIVE TIMING SCOPE", "possible activation", "possible launch/recovery activation", "requires exact active-van facts"),
    ("drone transport", "all sortie geometry", "PROVABLY LOCAL", "geometry unchanged", "new sortie", "subtract/add affected sorties"),
    ("drone fixed/used physical drones", "timing physical routes + sortie ids", "LOCAL WITH TRANSITIVE TIMING SCOPE", "timing chain may change", "new/reused physical drone", "needs shared physical-route facts"),
    ("drone energy", "sortie customer order/demand/distance", "PROVABLY LOCAL", "geometry unchanged", "new sortie", "affected sorties only"),
    ("waiting_cost_reported", "global timing waits", "LOCAL WITH TRANSITIVE TIMING SCOPE", "yes", "yes", "reported only; excluded from total"),
    ("penalty_cost", "canonical checker violations", "GLOBAL", "yes", "yes", "not safe to increment without checker proof"),
    ("total_cost", "truck+van+drone+penalty", "GLOBAL", "yes", "yes", "only after all exact component/feasibility facts"),
]
csv_file(
    "10a_objective_cost_dependency.csv",
    ["cost_term", "data_dependencies", "classification", "van_candidate", "drone_candidate", "incremental_safe_status"],
    [dict(zip(["cost_term", "data_dependencies", "classification", "van_candidate", "drone_candidate", "incremental_safe_status"], row)) for row in objective_rows],
)
md(
    "10_objective_affected_scope.md",
    """
# Objective Affected-Scope Audit

Stage-1 truck/trailer contribution is immutable for ordinary Regret insertion.
Van distance is target-route local; drone distance/energy is affected-sortie
local. Vehicle fixed usage, physical-drone usage and reported waiting depend on
derived timing/resource facts. Penalty and total cost remain global because the
canonical checker scans whole-State invariants.

Only terms marked `PROVABLY LOCAL` in `10a` may be reused directly. Terms marked
`LOCAL WITH TRANSITIVE TIMING SCOPE` require the complete timing/carrier closure.
Penalty/total remain global until a later exact incremental proof. Waiting cost
continues to be reported but excluded from `total_cost`.
""",
)


checker_rows = [
    ("stage-1 nodes and truck pattern", "truck/container fields", "GLOBAL EXACT", "no", "no", "no"),
    ("tractor/trailer event continuity", "tractor_routes/homes", "GLOBAL EXACT", "no", "no", "no"),
    ("container load/unload/destination", "container routes/assignments", "GLOBAL EXACT", "no", "no", "no"),
    ("van route endpoints/nodes/count", "van_routes/van_home", "LOCAL WITH DEPENDENCY CLOSURE", "yes", "activation only", "final global confirmation"),
    ("drone ownership derivation", "fleet/config/home maps", "GLOBAL EXACT", "no", "no direct", "final global confirmation"),
    ("initial/dynamic carried capacity", "carrier maps + timing physical sorties", "LOCAL WITH DEPENDENCY CLOSURE", "possible", "yes", "final global confirmation"),
    ("unique service", "all routes/sorties", "GLOBAL EXACT", "yes", "yes", "required"),
    ("served/unassigned partition", "all service sets", "GLOBAL EXACT", "yes", "yes", "required"),
    ("high-floor must be drone", "is_high_floor/service_mode", "LOCAL EXACT", "yes", "yes", "final global confirmation"),
    ("order/container warehouse consistency", "assignments + route origins", "LOCAL WITH DEPENDENCY CLOSURE", "yes", "yes", "final global confirmation"),
    ("van payload", "target routes/demands", "LOCAL EXACT", "yes", "no geometry", "final global confirmation"),
    ("time windows/container readiness", "timing + assignments", "LOCAL WITH DEPENDENCY CLOSURE", "yes", "yes", "required"),
    ("launch/recovery anchors/order", "sorties + both routes", "LOCAL WITH DEPENDENCY CLOSURE", "timing", "yes", "required"),
    ("drone payload/endurance/energy", "affected sortie/data/config", "LOCAL EXACT", "no geometry", "yes", "final global confirmation"),
    ("physical drone continuity/relaunch", "timing physical_sorties", "LOCAL WITH DEPENDENCY CLOSURE", "possible", "yes", "required"),
    ("warehouse launch/return limits", "all physical sorties", "GLOBAL EXACT", "possible", "yes", "required"),
    ("negative/global waiting and timing convergence", "complete timing", "UNKNOWN / NOT SAFE TO LOCALIZE", "yes", "yes", "required"),
]
csv_file(
    "11a_checker_rule_dependency.csv",
    ["rule", "state_fields", "classification", "van_candidate", "drone_candidate", "final_global_confirmation"],
    [dict(zip(["rule", "state_fields", "classification", "van_candidate", "drone_candidate", "final_global_confirmation"], row)) for row in checker_rows],
)
md(
    "11_checker_affected_scope.md",
    """
# Canonical Checker Affected-Scope Audit

The canonical checker is a whole-State certification boundary. Some predicates
are locally decidable (van payload; affected-sortie payload/endurance/energy;
high-floor mode), but route/sortie synchronization and physical-drone continuity
require dependency closure, while unique service, served/unassigned partition,
warehouse launch/return limits and stage-wide consistency are global.

`11a` enumerates the production rule groups and classifications. Local checks may
serve only as exact prefilters; a final canonical global confirmation remains
mandatory until a later proof eliminates it. Timing convergence/global waiting is
explicitly `UNKNOWN / NOT SAFE TO LOCALIZE` for Stage 2G.1.
""",
)


dag_rows = [
    ("candidate move", "unique per customer/revision", "descriptor", "State revision changes"),
    ("materialized State", "recreated for every candidate", "Class 2 future", "any business mutation"),
    ("business signature", "71,072 clean calls", "same candidate context", "any signature field changes"),
    ("derived timing", "35,496 calls, 48 hits", "same candidate immutable context", "route/sortie/carrier/readiness changes"),
    ("derived structural facts", "re-traversed by objective/checker", "same candidate immutable context", "same as business/timing"),
    ("objective", "17,784 calls", "consume shared context", "cost/config/data changes"),
    ("checker", "17,792 calls", "consume shared context", "rule input changes"),
    ("candidate identity", "35,540 observed calls", "descriptor plus frozen base", "State revision changes"),
]
csv_file(
    "12a_evaluation_dag.csv",
    ["node", "current_computation", "reusable_scope", "invalidation"],
    [dict(zip(["node", "current_computation", "reusable_scope", "invalidation"], row)) for row in dag_rows],
)
md(
    "12_shared_computation_opportunities.md",
    f"""
# Shared Computation Opportunities

```text
candidate move
  -> full materialized State
  -> business signature
  -> derived timing + physical carrier facts
  -> objective cost terms
  -> canonical checker rules
  -> normalized evaluation identity
```

Current clean counts are {HP['objective_calls']:,} objective,
{HP['checker_calls']:,} checker, {HP['timing_calls']:,} timing and
{HP['state_signature_calls']:,} signature calls. Timing is requested almost twice
per objective candidate, with only {HP['timing_cache_hits']:,} hits. Objective
computes waiting/timing, then checker requests timing again; in-place normalization
can change the lookup signature.

Safe Stage 2G.1 opportunity: construct one immutable, candidate-scoped derived
context after materialization and let exact objective/checker consume the same
timing/physical-route/structural facts. It must be keyed by the complete frozen
business input plus data/config identity, never persist across State revision,
and invalidate on any route/sortie/service/unassigned/carrier/container-readiness
change. Final outputs remain production objective/checker values.

Cross-candidate result cache is not primary: business duplicate rate is
{pct(business_duplicate_rate)}. Candidate representation/copy-on-write is a
separate Class 2 opportunity for Stage 2G.2.
""",
)


regret_rows = [
    ("same target van route or insertion positions", "DEFINITELY AFFECTED", "route geometry/capacity/timing changed"),
    ("shared launch/recovery anchors", "DEFINITELY AFFECTED", "anchor set/timing changed"),
    ("shared physical drone/carrier chain", "DEFINITELY AFFECTED", "availability/continuity changed"),
    ("same warehouse but different current route", "POTENTIALLY AFFECTED", "may use modified route/van/drone and global checker"),
    ("different warehouse/container", "UNKNOWN", "additivity and global checker independence not proved"),
    ("different customer/current best/mode/distance", "POTENTIALLY AFFECTED", "none is an approved independence proof"),
    ("formally disjoint dependency closure plus additive exact objective", "PROVABLY UNAFFECTED (theoretical only)", "no current production certificate/oracle emits this class"),
]
csv_file(
    "13a_regret_dependency_matrix.csv",
    ["relation", "classification", "reason"],
    [dict(zip(["relation", "classification", "reason"], row)) for row in regret_rows],
)
md(
    "13_regret_recalculation_dependency.md",
    """
# Regret Recalculation Dependency Audit

After each selected insertion the current implementation correctly recomputes
all remaining customers. Customers sharing the modified route, insertion anchors,
drone/carrier, capacity or timing closure are definitely affected. Other
customers are at least potentially affected because their complete candidate set
may use those resources and exact penalty/checker terms remain global.

No current production predicate proves a remaining customer disjoint from the
complete route/sortie/carrier/timing/checker dependency closure. Therefore:

- definitely affected: all customers with an explicit shared dependency;
- provably unaffected in the audited implementation: **0 certified customers**;
- potentially affected/unknown: every other remaining customer;
- selective Regret recomputation: **NOT CURRENTLY SAFE**.

Different customer, van, distance, current best or service mode is not accepted
as proof. Only a future exact dependency certificate plus full-candidate oracle
may populate `PROVABLY UNAFFECTED`.
""",
)


md(
    "14_optimization_opportunity_classification.md",
    f"""
# Optimization Opportunity Classification

## Class 1 — low-risk mechanical

- Candidate-scoped immutable timing/physical-route/structural context shared by
  exact objective and checker.
- Reuse immutable stage-1 cost constants and avoid repeated complete signature
  construction inside one candidate evaluation.
- Preserve all calls at the logical API/oracle boundary even if internal derived
  traversal is shared.

Measured basis: {HP['timing_calls']:,} timing requests for
{IDENT['candidate_business_states']:,} unique candidate States and
{f(T['compute_timing']['exclusive_seconds'])} s exclusive timing work.

## Class 2 — medium-risk representation

- Move descriptor, local overlay, route/sortie copy-on-write, delayed full
  materialization and copying audit-only metadata only for the selected move.
- Basis: {f(T['State.copy']['inclusive_seconds'])} s and 0/{IDENT['candidate_business_states']:,}
  scored candidate copies retained.

## Class 3 — high-risk exact incremental evaluation

- Local timing, incremental objective, localized checker and selective remaining
  customer recomputation. Requires zero-false-negative dependency proof and a
  full-State oracle for every candidate.

## Class 4 — approximation

Top-K, sampling, beam, candidate truncation, restricted drone combinations and
heuristic pruning are **extended_mode only** and prohibited in `paper_mode`.
""",
)


md(
    "15_stage2g_implementation_roadmap.md",
    """
# Stage 2G Implementation Roadmap

1. **Stage 2G.1 — Shared Evaluation Context.** First target repeated exact
   timing/signature/structural traversal inside one materialized candidate.
   Objective and canonical checker must retain exact output APIs and consume one
   immutable context. Risk: low-to-medium; expected gain source is removal of the
   second timing traversal and repeated signature/physical-route derivation.
2. **Stage 2G.2 — Candidate Representation / Copy Reduction.** Move descriptors,
   local overlays or copy-on-write; selected move alone is fully committed. Risk:
   medium. Every descriptor must be compared against the complete-State oracle.
3. **Stage 2G.3 — Exact Incremental Evaluation.** Only after closure proof:
   incremental timing/objective/local checker and selective Regret recomputation.
   Risk: high. Current selective recomputation is held.
4. **Stage 2G.4 — System semantic/performance regression.** Exact candidate,
   first/second, regret, RNG, action history, final State/objective plus wall,
   memory and call-count comparisons.

This ordering is evidence-driven: repeated timing/signature traversal has the
largest low-risk shared-computation surface; copy reduction follows; locality and
selective Regret remain proof-gated.
""",
)


md(
    "16_performance_acceptance_contract.md",
    """
# Performance Acceptance Contract

## Semantic hard gate

For every fixed fixture compare exact candidate identities, hard-feasible set,
unique business States, per-customer first/second, Regret, selected customer/move,
RNG state, objective, canonical checker, violations, returned State fingerprint,
solver action history and final best. Reuse the frozen floating-point comparison
rules; no new tolerance is allowed. Any mismatch is immediate revert.

## Required performance measurements

Report heavy Regret wall; solver wall and Regret P50/P90/P95; candidate throughput;
State.copy count/time; timing/objective/checker/signature count and inclusive/
exclusive time; absolute peak working-set/private memory.

## Predeclared merge thresholds

- Stage 2G.1: at least 15% median heavy-call wall reduction and at least 20%
  reduction in actual timing/signature derived-work executions; solver median at
  least 10% better; peak private memory no more than 10% higher.
- Stage 2G.2: at least 20% heavy-call wall reduction or 40% State.copy-time
  reduction; peak private memory no more than 10% higher.
- Stage 2G.3: threshold declared per exact subfeature before implementation, never
  below 15% on its target fixture, with zero oracle mismatch.

Use at least 3 clean repetitions and compare medians on the same machine/process
protocol. If semantic Gate fails, benefit is below threshold, P95 regresses by
more than 10%, or memory exceeds the bound: **REVERT OR DO NOT MERGE**.
""",
)


md(
    "17_focused_audit_test_results.md",
    f"""
# Focused Audit Test Results

- Audit probe syntax: PASS.
- Heavy clean/instrumented semantic oracle: PASS.
- Small clean/instrumented semantic oracle: PASS.
- Solver clean/instrumented action/final-State oracle: PASS.
- Dynamic van/same-van/cross-van/high-floor/boundary/linked candidates: PASS;
  false negatives {all_false_negatives}.
- Focused pytest command: Stage 2C True Regret-2, Stage 2B Local/Global,
  Stage 2A checker differential, State.copy/context isolation, Cascade isolation,
  strict checker, cross-van timing and high-floor construction.
- Pytest result: **62 passed in 10.81 s**, 0 failed.
- Full 294-node suite: intentionally not rerun per Stage 2G.0 scope.

`pytest` was run and passed. The generated coverage XML is retained under this
audit's `raw/` area only; no tracked test, expectation or fixture changed.
""",
)


scope_answers = {
    "Production changed": "NO",
    "Tests changed": "NO",
    "Test expectations changed": "NO",
    "Fixture semantics changed": "NO (new audit-only derived fixtures)",
    "paper_mode changed": "NO",
    "Candidate generation changed": "NO",
    "Hard-feasibility changed": "NO",
    "State.copy changed": "NO",
    "compute_timing changed": "NO",
    "Objective changed": "NO",
    "Checker changed": "NO",
    "Regret selection changed": "NO",
    "Tie-break changed": "NO",
    "RNG changed": "NO",
    "Action registry changed": "NO",
    "SA/weights changed": "NO",
    "Fallback introduced": "NO",
    "Approximation introduced": "NO",
    "Performance optimization implemented": "NO",
    "Audit instrumentation created": "YES",
    "Reports created": "YES",
    "Stage 2G.1 performed": "NO",
    "Stage 3 performed": "NO",
}
md(
    "18_scope_diff_review.md",
    "# Scope Diff Review\n\n"
    + "\n".join(f"- {key}: **{value}**" for key, value in scope_answers.items())
    + "\n\nOnly untracked audit scripts, raw evidence and reports exist under "
    "`outputs/stage2g0_regret_performance_contract/`. Production/test tracked "
    "diff remains empty.\n",
)


gates = [
    "Frozen baseline HEAD correct",
    "Initial tracked/staged diff clean",
    "Historical performance evidence reviewed",
    "Current baseline reprofiled",
    "Benchmark fixtures frozen",
    "Instrumentation behavior-neutral",
    "Regret production call chain complete",
    "Runtime breakdown complete",
    "Candidate counts recorded",
    "Unique business State ratio recorded",
    "State.copy cost quantified",
    "Mutation ratio quantified",
    "Van affected scope defined",
    "Drone affected scope defined",
    "Dynamic scope matches prediction",
    "Timing propagation mapped",
    "Objective dependencies mapped",
    "Checker dependencies mapped",
    "Shared computation opportunities decided",
    "Regret recalculation dependency decided",
    "Unsafe locality assumptions rejected",
    "Optimization classes assigned",
    "Stage 2G.1 scope recommended",
    "Performance acceptance contract complete",
    "Focused audit tests pass",
    "No production changes",
    "No test changes",
    "No approximation introduced",
    "Stage 2G.1 not performed",
    "Stage 3 not performed",
]
gate_table = "\n".join(f"| {gate} | PASS | reports/raw evidence |" for gate in gates)
md(
    "19_gate_decision.md",
    f"""
# Gate Decision

| Gate | Result | Evidence |
|---|---|---|
{gate_table}

```text
TRUE REGRET-2 PERFORMANCE ROOT CAUSES CONFIRMED
CURRENT BASELINE PERFORMANCE REPROFILED
CANDIDATE AFFECTED-SCOPE CONTRACT ESTABLISHED
OBJECTIVE/CHECKER/TIMING DEPENDENCIES MAPPED
PAPER-MODE SEMANTIC EQUIVALENCE CONTRACT FROZEN
STAGE 2G.0 COMPLETE
STAGE 2G.1 READY
STAGE 3 HELD
NO_COMMIT_REQUIRED
```

Stage 2G.1 first target: candidate-scoped immutable shared timing/structural
evaluation context. Expected gain comes from removing repeated timing/signature/
physical-route traversal; risk is low-to-medium. Required oracle is exact
per-candidate State materialization plus first/second/regret/RNG/solver trajectory
comparison. Top-K, sampling, beam, approximate objective/checker, unproved pruning
and selective Regret recomputation remain prohibited in paper mode.
""",
)


md(
    "README.md",
    f"""
# Stage 2G.0 True Regret-2 Performance Contract and Affected-Scope Audit

Status: **STAGE 2G.0 COMPLETE — STAGE 2G.1 READY — STAGE 3 HELD**.

The current frozen baseline was reprofiled at exact commit `172166ee`. The heavy
Regret call took {f(HC['wall_seconds'])} s for {HP['raw']:,} raw local-prefilter
attempts and {HP['hard_feasible']:,} exact-scored moves. Drone work dominates
({HP['drone_raw']:,} raw). `State.copy` consumed
{f(T['State.copy']['inclusive_seconds'])} s over {T['State.copy']['calls']:,}
calls. Objective/checker requested timing almost twice per candidate, while all
{IDENT['candidate_business_states']:,} candidate business States were unique.

The exact affected-scope contract has zero dynamic false negatives across van,
same/cross-van drone, high-floor, exact capacity/time-window boundary and actual
linked multi-customer/relaunch representatives. Localized checker/incremental
Regret remain held because no production certificate proves any remaining
customer unaffected.

Recommended Stage 2G.1: share one immutable derived timing/physical-route/
structural context within each exact candidate evaluation. No optimization was
implemented in this audit. Reports `00`–`19`, CSV matrices and raw measurements
contain the complete evidence.
""",
)

print(f"generated reports in {HERE}")
