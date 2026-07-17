from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest

import alns_solver
import diagnose_calns
import main
import operator_modes
import operators
from config import ALNSConfig, build_config
from dataset_loader import generate_toy_data
from feasibility import check_solution_feasible
from objective import objective
from operator_modes import (
    ACTION_REGISTRY_SCHEMA_VERSION,
    EXTENDED_ACTION_SPECS,
    EXTENDED_DESTROY_ORDER,
    EXTENDED_REPAIR_ORDER,
    PAPER_ACTION_SPECS,
    PAPER_DESTROY_ORDER,
    PAPER_REPAIR_ORDER,
    ActionIdentityError,
    ConfigurationError,
    ExtendedOperatorRegistryError,
    OperatorMode,
    PaperOperatorRegistryError,
    action_for_id,
    action_id_for_pair,
    build_action_registry,
    extended_action_registry,
    paper_action_registry,
    resolve_operator_mode,
)


PAPER_FINGERPRINT = "08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1"
EXTENDED_FINGERPRINT = "588c3c20cc1b34c66bb90f4e6e3296af5397f1ad4ba671b07d59f1f15a446514"

BASELINE_P_DESTROY = (
    "random_customer_removal",
    "random_customer_removal",
    "greedy_removal",
    "random_customer_removal",
    "related_customer_removal",
    "cascade_aware_removal",
    "cascade_aware_removal",
    "related_customer_removal",
    "related_customer_removal",
    "related_customer_removal",
    "greedy_removal",
    "random_customer_removal",
)
BASELINE_P_REPAIR = (
    "regret_repair",
    "best_mode_repair",
    "best_mode_repair",
    "cascade_repair",
    "best_mode_repair",
    "greedy_van_repair",
    "cascade_repair",
    "best_mode_repair",
    "regret_repair",
    "cascade_repair",
    "best_mode_repair",
    "regret_repair",
)
BASELINE_P_ACCEPTED = (
    True,
    False,
    True,
    True,
    True,
    False,
    False,
    True,
    True,
    False,
    True,
    True,
)
BASELINE_P_FINAL_OBJECTIVE = 789.5462929944308
BASELINE_P_FINAL_FINGERPRINT = (
    "9de8f7ba48e3e29c3d7853e257c3515f9c86b4749cc4ce0d0493e051465fe583"
)
BASELINE_P_OBJECTIVE_CALLS = 653
BASELINE_P_CHECKER_CALLS = 909
BASELINE_P_RNG_DIGEST = "0ef1b46c0559070d2546d0261ec49177635ed842cdeb4b5fb8820c671da5bf3b"

BASELINE_E_DESTROY = (
    "random_customer_removal",
    "random_customer_removal",
    "random_customer_removal",
    "drone_task_removal",
    "greedy_removal",
    "related_customer_removal",
    "switch_transshipment_operator",
    "cascade_aware_removal",
    "greedy_removal",
    "route_segment_removal",
    "route_segment_removal",
    "related_customer_removal",
)
BASELINE_E_REPAIR = (
    "best_mode_repair",
    "greedy_van_repair",
    "greedy_drone_repair",
    "cascade_repair",
    "cascade_repair",
    "greedy_van_repair",
    "greedy_drone_repair",
    "cascade_repair",
    "greedy_drone_repair",
    "regret_repair",
    "cascade_repair",
    "greedy_van_repair",
)
BASELINE_E_FINAL_OBJECTIVE = 789.5462929944308
BASELINE_E_FINAL_FINGERPRINT = (
    "3f8ec1b603fbb1d564063ba9a2d432148c4252af93e0e6b9305a0097f46bbf0f"
)
BASELINE_E_OBJECTIVE_CALLS = 608
BASELINE_E_CHECKER_CALLS = 884
BASELINE_E_RNG_DIGEST = "57273a01c37b67814e439fbf7d5f4617e124eda6c3020aefd905f3e09f4525d5"


def _state_fingerprint(state) -> str:
    return hashlib.sha256(repr(state.cache_signature()).encode("utf-8")).hexdigest()


def _registry(mode: OperatorMode = OperatorMode.PAPER):
    return build_action_registry(
        mode, operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS
    )


def _baseline_run(mode: OperatorMode):
    config = build_config(
        num_customers=10,
        num_orders=10,
        num_transshipments=2,
        num_containers=1,
        iterations=12,
        seed=42,
        max_no_improve=100,
        early_stop_enabled=False,
        collect_full_candidate_diagnostics=True,
        operator_mode=mode,
    )
    data = generate_toy_data(config)
    config.alns.random_seed = 29
    rng_trace = []
    original_choice = alns_solver._roulette_choice
    original_accept = alns_solver._accept

    def traced_choice(rng, names, weights):
        rng_trace.append(("choice_before", copy.deepcopy(rng.bit_generator.state)))
        selected = original_choice(rng, names, weights)
        rng_trace.append(("choice_after", copy.deepcopy(rng.bit_generator.state)))
        return selected

    def traced_accept(rng, *args):
        rng_trace.append(("accept_before", copy.deepcopy(rng.bit_generator.state)))
        accepted = original_accept(rng, *args)
        rng_trace.append(("accept_after", copy.deepcopy(rng.bit_generator.state)))
        return accepted

    alns_solver._roulette_choice = traced_choice
    alns_solver._accept = traced_accept
    try:
        result = alns_solver.run_c_alns(data, config)
    finally:
        alns_solver._roulette_choice = original_choice
        alns_solver._accept = original_accept
    rng_payload = json.dumps(rng_trace, sort_keys=True, separators=(",", ":"))
    rng_digest = hashlib.sha256(rng_payload.encode("utf-8")).hexdigest()
    return config, data, result, rng_digest


@pytest.fixture(scope="module")
def baseline_runs():
    return {
        OperatorMode.PAPER: _baseline_run(OperatorMode.PAPER),
        OperatorMode.EXTENDED: _baseline_run(OperatorMode.EXTENDED),
    }


@pytest.mark.parametrize(
    "value, expected",
    [
        ("paper_mode", OperatorMode.PAPER),
        ("extended_mode", OperatorMode.EXTENDED),
        (OperatorMode.PAPER, OperatorMode.PAPER),
        (OperatorMode.EXTENDED, OperatorMode.EXTENDED),
    ],
)
def test_operator_mode_accepts_only_canonical_values(value, expected) -> None:
    assert resolve_operator_mode(value) is expected


@pytest.mark.parametrize(
    "value", [None, "", "paper", "extended", "default", "all", "auto", "papre", 1]
)
def test_invalid_explicit_operator_mode_fails(value) -> None:
    with pytest.raises(ConfigurationError):
        resolve_operator_mode(value)


def test_config_default_and_legacy_missing_field_are_paper() -> None:
    config = build_config()
    assert config.alns.operator_mode is OperatorMode.PAPER
    legacy = ALNSConfig()
    del legacy.operator_mode
    assert resolve_operator_mode(getattr(legacy, "operator_mode", OperatorMode.PAPER)) is (
        OperatorMode.PAPER
    )


def test_build_config_rejects_explicit_none_and_typo() -> None:
    with pytest.raises(ConfigurationError):
        build_config(operator_mode=None)
    with pytest.raises(ConfigurationError):
        build_config(operator_mode="papre")


def test_cli_defaults_to_paper_mode(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py"])
    assert main.parse_args().operator_mode == OperatorMode.PAPER.value


def test_cli_accepts_explicit_extended_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        sys, "argv", ["main.py", "--operator-mode", OperatorMode.EXTENDED.value]
    )
    assert main.parse_args().operator_mode == OperatorMode.EXTENDED.value


def test_cli_rejects_noncanonical_mode(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--operator-mode", "extended"])
    with pytest.raises(SystemExit):
        main.parse_args()


def test_paper_orders_and_exact_action_mapping_are_frozen() -> None:
    registry = _registry()
    assert registry.destroy_names == PAPER_DESTROY_ORDER
    assert registry.repair_names == PAPER_REPAIR_ORDER
    assert tuple(
        (item.action_id, item.destroy_name, item.repair_name)
        for item in registry.actions
    ) == PAPER_ACTION_SPECS


def test_paper_action_ids_pairs_and_cartesian_product_are_complete() -> None:
    registry = _registry()
    assert tuple(action.action_id for action in registry.actions) == tuple(range(16))
    assert len({action.action_id for action in registry.actions}) == 16
    pairs = {(action.destroy_name, action.repair_name) for action in registry.actions}
    assert len(pairs) == 16
    assert pairs == {
        (destroy_name, repair_name)
        for destroy_name in PAPER_DESTROY_ORDER
        for repair_name in PAPER_REPAIR_ORDER
    }


def test_registry_mapping_is_independent_of_input_dict_order() -> None:
    destroy = dict(reversed(tuple(operators.DESTROY_OPERATORS.items())))
    repair = dict(reversed(tuple(operators.REPAIR_OPERATORS.items())))
    reordered = paper_action_registry(destroy, repair)
    assert reordered.actions == _registry().actions
    assert reordered.fingerprint == PAPER_FINGERPRINT


def test_registry_fingerprints_are_frozen_and_schema_versioned() -> None:
    paper = paper_action_registry(operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS)
    extended = extended_action_registry(
        operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS
    )
    assert paper.schema_version == ACTION_REGISTRY_SCHEMA_VERSION
    assert paper.fingerprint == PAPER_FINGERPRINT
    assert extended.fingerprint == EXTENDED_FINGERPRINT


def test_registry_fingerprint_is_stable_in_another_process() -> None:
    code = (
        "import operators; from operator_modes import paper_action_registry; "
        "print(paper_action_registry(operators.DESTROY_OPERATORS, "
        "operators.REPAIR_OPERATORS).fingerprint)"
    )
    output = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    assert output == PAPER_FINGERPRINT


@pytest.mark.parametrize("missing", PAPER_DESTROY_ORDER)
def test_missing_any_paper_destroy_fails_fast(missing) -> None:
    destroy = dict(operators.DESTROY_OPERATORS)
    destroy.pop(missing)
    with pytest.raises(PaperOperatorRegistryError):
        paper_action_registry(destroy, operators.REPAIR_OPERATORS)


@pytest.mark.parametrize("missing", PAPER_REPAIR_ORDER)
def test_missing_any_paper_repair_fails_fast(missing) -> None:
    repair = dict(operators.REPAIR_OPERATORS)
    repair.pop(missing)
    with pytest.raises(PaperOperatorRegistryError):
        paper_action_registry(operators.DESTROY_OPERATORS, repair)


def test_missing_paper_pair_never_degrades_to_fifteen(monkeypatch) -> None:
    monkeypatch.setattr(operator_modes, "PAPER_ACTION_SPECS", PAPER_ACTION_SPECS[:-1])
    with pytest.raises(PaperOperatorRegistryError):
        paper_action_registry(operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS)


def test_paper_failure_never_falls_back_to_extended() -> None:
    destroy = dict(operators.DESTROY_OPERATORS)
    destroy.pop("greedy_removal")
    with pytest.raises(PaperOperatorRegistryError):
        build_action_registry(OperatorMode.PAPER, destroy, operators.REPAIR_OPERATORS)


def test_extended_failure_never_falls_back_to_paper() -> None:
    repair = dict(operators.REPAIR_OPERATORS)
    repair.pop("greedy_drone_repair")
    with pytest.raises(ExtendedOperatorRegistryError):
        build_action_registry(OperatorMode.EXTENDED, operators.DESTROY_OPERATORS, repair)


def test_extra_and_unapproved_operators_are_excluded() -> None:
    destroy = {"unapproved_destroy": lambda *args: None, **operators.DESTROY_OPERATORS}
    repair = {"unapproved_repair": lambda *args: None, **operators.REPAIR_OPERATORS}
    paper = paper_action_registry(destroy, repair)
    extended = extended_action_registry(destroy, repair)
    assert "unapproved_destroy" not in paper.destroy_names
    assert "unapproved_repair" not in paper.repair_names
    assert "unapproved_destroy" not in extended.destroy_names
    assert "unapproved_repair" not in extended.repair_names
    assert len(paper.actions) == 16
    assert len(extended.actions) == 35


def test_extended_registry_is_explicit_and_preserves_paper_ids() -> None:
    registry = _registry(OperatorMode.EXTENDED)
    assert registry.destroy_names == EXTENDED_DESTROY_ORDER
    assert registry.repair_names == EXTENDED_REPAIR_ORDER
    assert tuple(
        (item.action_id, item.destroy_name, item.repair_name)
        for item in registry.actions
    ) == EXTENDED_ACTION_SPECS
    assert tuple(
        (item.action_id, item.destroy_name, item.repair_name)
        for item in registry.actions[:16]
    ) == PAPER_ACTION_SPECS
    assert registry.actions[16].action_id == 16


def test_bidirectional_lookup_and_invalid_lookup_contract() -> None:
    registry = _registry()
    for action in registry.actions:
        assert action_for_id(registry, action.action_id) == action
        assert action_id_for_pair(
            registry, action.destroy_name, action.repair_name
        ) == action.action_id
    with pytest.raises(ActionIdentityError):
        action_for_id(registry, -1)
    with pytest.raises(ActionIdentityError):
        action_id_for_pair(registry, "unknown", "unknown")


def test_registry_and_action_identity_are_immutable() -> None:
    registry = _registry()
    assert isinstance(registry.actions, tuple)
    with pytest.raises(FrozenInstanceError):
        registry.actions[0].action_id = 99
    with pytest.raises(FrozenInstanceError):
        registry.mode = OperatorMode.EXTENDED


def test_default_paper_run_matches_preimplementation_baseline(baseline_runs) -> None:
    config, data, result, rng_digest = baseline_runs[OperatorMode.PAPER]
    assert config.alns.operator_mode is OperatorMode.PAPER
    assert result.operator_mode is OperatorMode.PAPER
    assert result.action_registry_fingerprint == PAPER_FINGERPRINT
    assert tuple(item["destroy"] for item in result.history) == BASELINE_P_DESTROY
    assert tuple(item["repair"] for item in result.history) == BASELINE_P_REPAIR
    assert tuple(item["accepted"] for item in result.history) == BASELINE_P_ACCEPTED
    assert rng_digest == BASELINE_P_RNG_DIGEST
    assert objective(result.best_state, data, config)[0] == pytest.approx(
        BASELINE_P_FINAL_OBJECTIVE
    )
    assert _state_fingerprint(result.best_state) == BASELINE_P_FINAL_FINGERPRINT
    assert check_solution_feasible(result.best_state, data, config) == (True, [])


def test_paper_history_records_exact_action_identity_without_flat_sampling(
    baseline_runs,
) -> None:
    _, _, result, _ = baseline_runs[OperatorMode.PAPER]
    registry = _registry()
    assert [
        item["action_id"] for item in result.history
    ] == [
        registry.action_id_for_pair(item["destroy"], item["repair"])
        for item in result.history
    ]
    assert all(item["operator_mode"] == "paper_mode" for item in result.history)
    assert all(
        item["action_registry_fingerprint"] == PAPER_FINGERPRINT
        for item in result.history
    )


def test_paper_search_work_matches_preimplementation_baseline(baseline_runs) -> None:
    _, _, result, _ = baseline_runs[OperatorMode.PAPER]
    assert result.profile["objective_calls"] == BASELINE_P_OBJECTIVE_CALLS
    assert result.profile["check_solution_feasible_calls"] == BASELINE_P_CHECKER_CALLS
    assert result.profile["destroy"]["calls"] == 12
    assert sum(row["calls"] for row in result.profile["repair"].values()) == 12


def test_explicit_extended_run_matches_preimplementation_baseline(baseline_runs) -> None:
    config, data, result, rng_digest = baseline_runs[OperatorMode.EXTENDED]
    assert config.alns.operator_mode is OperatorMode.EXTENDED
    assert tuple(item["destroy"] for item in result.history) == BASELINE_E_DESTROY
    assert tuple(item["repair"] for item in result.history) == BASELINE_E_REPAIR
    assert rng_digest == BASELINE_E_RNG_DIGEST
    assert objective(result.best_state, data, config)[0] == pytest.approx(
        BASELINE_E_FINAL_OBJECTIVE
    )
    assert _state_fingerprint(result.best_state) == BASELINE_E_FINAL_FINGERPRINT
    assert result.profile["objective_calls"] == BASELINE_E_OBJECTIVE_CALLS
    assert result.profile["check_solution_feasible_calls"] == BASELINE_E_CHECKER_CALLS


def test_action_diagnostics_do_not_enter_business_state_or_cache_signature(
    baseline_runs,
) -> None:
    _, _, result, _ = baseline_runs[OperatorMode.PAPER]
    assert "action_id" not in result.best_state.metadata
    assert "operator_mode" not in result.best_state.metadata
    assert _state_fingerprint(result.best_state) == BASELINE_P_FINAL_FINGERPRINT


def test_diagnostic_config_default_is_paper_mode() -> None:
    config = diagnose_calns.make_config(seed=17, iterations=1, early_stop=False)
    assert config.alns.operator_mode is OperatorMode.PAPER


def test_diagnostic_operator_sets_resolve_modes_explicitly() -> None:
    assert diagnose_calns.operator_mode_for_set("paper_4x4") is OperatorMode.PAPER
    assert diagnose_calns.operator_mode_for_set("current") is OperatorMode.EXTENDED
    with pytest.raises(ValueError):
        diagnose_calns.operator_mode_for_set("automatic")


def test_legacy_missing_mode_field_runs_as_paper() -> None:
    config = build_config(
        num_customers=3,
        num_orders=3,
        iterations=0,
        seed=17,
        max_no_improve=None,
        early_stop_enabled=False,
    )
    del config.alns.operator_mode
    data = generate_toy_data(config)
    result = alns_solver.run_c_alns(data, config)
    assert result.operator_mode is OperatorMode.PAPER
    assert result.action_registry_fingerprint == PAPER_FINGERPRINT


def test_invalid_run_mode_fails_before_initial_solution(monkeypatch) -> None:
    config = build_config(num_customers=3, num_orders=3, iterations=1)
    data = generate_toy_data(config)
    config.alns.operator_mode = None

    def forbidden(*args, **kwargs):
        raise AssertionError("initial solution must not run for an invalid mode")

    monkeypatch.setattr(alns_solver, "initial_solution", forbidden)
    with pytest.raises(ConfigurationError):
        alns_solver.run_c_alns(data, config)


def test_native_cascade_pair_has_frozen_action_fifteen() -> None:
    registry = _registry()
    assert registry.action_id_for_pair(
        "cascade_aware_removal", "cascade_repair"
    ) == 15


def test_adaptive_weights_remain_separate_per_operator(baseline_runs) -> None:
    _, _, result, _ = baseline_runs[OperatorMode.PAPER]
    assert tuple(result.destroy_weights) == PAPER_DESTROY_ORDER
    assert tuple(result.repair_weights) == PAPER_REPAIR_ORDER
    assert not hasattr(result, "action_weights")


def test_no_action_mask_or_stage2f_policy_is_added() -> None:
    config = build_config()
    assert not hasattr(config.alns, "action_mask")
    assert not hasattr(config.alns, "policy")
    assert not hasattr(config.alns, "ppo")


def test_mode_and_registry_are_resolved_once_before_iterations(monkeypatch) -> None:
    calls = []
    original = alns_solver.build_action_registry

    def recording(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(alns_solver, "build_action_registry", recording)
    config = build_config(
        num_customers=3,
        num_orders=3,
        iterations=2,
        seed=17,
        max_no_improve=None,
        early_stop_enabled=False,
    )
    data = generate_toy_data(config)
    result = alns_solver.run_c_alns(data, config)
    assert calls == [OperatorMode.PAPER]
    assert "t_operator_mode_resolution" in result.phase_timings
    assert "t_action_registry_construction" in result.phase_timings


@pytest.mark.parametrize("seed", [17, 29, 41])
def test_paper_mode_is_deterministic_for_three_fixed_seeds(seed) -> None:
    outcomes = []
    for _ in range(2):
        config = build_config(
            num_customers=3,
            num_orders=3,
            iterations=2,
            seed=seed,
            max_no_improve=None,
            early_stop_enabled=False,
        )
        data = generate_toy_data(config)
        result = alns_solver.run_c_alns(data, config)
        outcomes.append(
            (
                tuple((row["destroy"], row["repair"], row["action_id"]) for row in result.history),
                tuple(row["accepted"] for row in result.history),
                _state_fingerprint(result.best_state),
            )
        )
    assert outcomes[0] == outcomes[1]
