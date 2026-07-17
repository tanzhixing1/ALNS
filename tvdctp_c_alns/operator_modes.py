from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Tuple


class ConfigurationError(ValueError):
    """Raised when an explicitly supplied operator mode is invalid."""


class OperatorRegistryError(RuntimeError):
    """Base class for strict action-registry construction failures."""


class PaperOperatorRegistryError(OperatorRegistryError):
    """Raised when the complete paper 4 x 4 registry cannot be built."""


class ExtendedOperatorRegistryError(OperatorRegistryError):
    """Raised when the approved extended registry cannot be built."""


class ActionIdentityError(LookupError):
    """Raised when an action id or operator pair is outside a registry."""


class OperatorMode(str, Enum):
    PAPER = "paper_mode"
    EXTENDED = "extended_mode"


PAPER_DESTROY_ORDER = (
    "random_customer_removal",
    "greedy_removal",
    "related_customer_removal",
    "cascade_aware_removal",
)

PAPER_REPAIR_ORDER = (
    "best_mode_repair",
    "greedy_van_repair",
    "regret_repair",
    "cascade_repair",
)

PAPER_ACTION_SPECS = (
    (0, "random_customer_removal", "best_mode_repair"),
    (1, "random_customer_removal", "greedy_van_repair"),
    (2, "random_customer_removal", "regret_repair"),
    (3, "random_customer_removal", "cascade_repair"),
    (4, "greedy_removal", "best_mode_repair"),
    (5, "greedy_removal", "greedy_van_repair"),
    (6, "greedy_removal", "regret_repair"),
    (7, "greedy_removal", "cascade_repair"),
    (8, "related_customer_removal", "best_mode_repair"),
    (9, "related_customer_removal", "greedy_van_repair"),
    (10, "related_customer_removal", "regret_repair"),
    (11, "related_customer_removal", "cascade_repair"),
    (12, "cascade_aware_removal", "best_mode_repair"),
    (13, "cascade_aware_removal", "greedy_van_repair"),
    (14, "cascade_aware_removal", "regret_repair"),
    (15, "cascade_aware_removal", "cascade_repair"),
)

# These orders reproduce the pre-Stage-2E.1 engineering registry. They are
# explicit constants rather than views of mutable operator dictionaries.
EXTENDED_DESTROY_ORDER = (
    "random_customer_removal",
    "greedy_removal",
    "related_customer_removal",
    "route_segment_removal",
    "drone_task_removal",
    "cascade_aware_removal",
    "switch_transshipment_operator",
)

EXTENDED_REPAIR_ORDER = (
    "greedy_van_repair",
    "greedy_drone_repair",
    "best_mode_repair",
    "regret_repair",
    "cascade_repair",
)

# Explicitly approved extended-only pairs. This is deliberately not generated
# from the cartesian product of whatever happens to be registered at runtime.
EXTENDED_ONLY_ACTION_SPECS = (
    (16, "random_customer_removal", "greedy_drone_repair"),
    (17, "greedy_removal", "greedy_drone_repair"),
    (18, "related_customer_removal", "greedy_drone_repair"),
    (19, "cascade_aware_removal", "greedy_drone_repair"),
    (20, "route_segment_removal", "greedy_van_repair"),
    (21, "route_segment_removal", "greedy_drone_repair"),
    (22, "route_segment_removal", "best_mode_repair"),
    (23, "route_segment_removal", "regret_repair"),
    (24, "route_segment_removal", "cascade_repair"),
    (25, "drone_task_removal", "greedy_van_repair"),
    (26, "drone_task_removal", "greedy_drone_repair"),
    (27, "drone_task_removal", "best_mode_repair"),
    (28, "drone_task_removal", "regret_repair"),
    (29, "drone_task_removal", "cascade_repair"),
    (30, "switch_transshipment_operator", "greedy_van_repair"),
    (31, "switch_transshipment_operator", "greedy_drone_repair"),
    (32, "switch_transshipment_operator", "best_mode_repair"),
    (33, "switch_transshipment_operator", "regret_repair"),
    (34, "switch_transshipment_operator", "cascade_repair"),
)

EXTENDED_ACTION_SPECS = PAPER_ACTION_SPECS + EXTENDED_ONLY_ACTION_SPECS

ACTION_REGISTRY_SCHEMA_VERSION = "stage2e1-action-registry-v1"

_DESTROY_DISPLAY = {
    "random_customer_removal": "Random",
    "greedy_removal": "Greedy",
    "related_customer_removal": "Related",
    "cascade_aware_removal": "Cascade",
    "route_segment_removal": "RouteSegment",
    "drone_task_removal": "DroneTask",
    "switch_transshipment_operator": "SwitchTransshipment",
}

_REPAIR_DISPLAY = {
    "best_mode_repair": "Global",
    "greedy_van_repair": "Local",
    "regret_repair": "Regret",
    "cascade_repair": "Cascade",
    "greedy_drone_repair": "DroneGreedy",
}


@dataclass(frozen=True)
class ActionIdentity:
    action_id: int
    destroy_name: str
    repair_name: str
    display_name: str
    mode: OperatorMode
    schema_version: str = ACTION_REGISTRY_SCHEMA_VERSION


@dataclass(frozen=True)
class ActionRegistry:
    mode: OperatorMode
    actions: Tuple[ActionIdentity, ...]
    destroy_names: Tuple[str, ...]
    repair_names: Tuple[str, ...]
    destroy_bindings: Tuple[Tuple[str, Callable[..., object]], ...]
    repair_bindings: Tuple[Tuple[str, Callable[..., object]], ...]
    fingerprint: str
    schema_version: str = ACTION_REGISTRY_SCHEMA_VERSION

    def action_for_id(self, action_id: int) -> ActionIdentity:
        for action in self.actions:
            if action.action_id == action_id:
                return action
        raise ActionIdentityError(
            f"action id {action_id!r} is not registered in {self.mode.value}"
        )

    def action_id_for_pair(self, destroy_name: str, repair_name: str) -> int:
        for action in self.actions:
            if (
                action.destroy_name == destroy_name
                and action.repair_name == repair_name
            ):
                return action.action_id
        raise ActionIdentityError(
            f"operator pair ({destroy_name!r}, {repair_name!r}) is not "
            f"registered in {self.mode.value}"
        )

    def destroy_operator(self, name: str) -> Callable[..., object]:
        for registered_name, operator in self.destroy_bindings:
            if registered_name == name:
                return operator
        raise ActionIdentityError(
            f"destroy operator {name!r} is not registered in {self.mode.value}"
        )

    def repair_operator(self, name: str) -> Callable[..., object]:
        for registered_name, operator in self.repair_bindings:
            if registered_name == name:
                return operator
        raise ActionIdentityError(
            f"repair operator {name!r} is not registered in {self.mode.value}"
        )


def resolve_operator_mode(value: object) -> OperatorMode:
    if isinstance(value, OperatorMode):
        return value
    if isinstance(value, str):
        try:
            return OperatorMode(value)
        except ValueError as exc:
            raise ConfigurationError(
                "operator_mode must be exactly 'paper_mode' or 'extended_mode'; "
                f"received {value!r}"
            ) from exc
    raise ConfigurationError(
        "operator_mode must be exactly 'paper_mode' or 'extended_mode'; "
        f"received {value!r}"
    )


def _registry_error_type(mode: OperatorMode) -> type[OperatorRegistryError]:
    if mode is OperatorMode.PAPER:
        return PaperOperatorRegistryError
    return ExtendedOperatorRegistryError


def _validated_bindings(
    names: Tuple[str, ...],
    operators: Mapping[str, Callable[..., object]],
    *,
    kind: str,
    mode: OperatorMode,
) -> Tuple[Tuple[str, Callable[..., object]], ...]:
    error_type = _registry_error_type(mode)
    bindings = []
    for name in names:
        if name not in operators:
            raise error_type(
                f"{mode.value} requires {kind} operator {name!r}; registry is incomplete"
            )
        operator = operators[name]
        if not callable(operator):
            raise error_type(
                f"{mode.value} {kind} operator {name!r} is not callable"
            )
        bindings.append((name, operator))
    return tuple(bindings)


def _build_identities(
    mode: OperatorMode,
    specs: Tuple[Tuple[int, str, str], ...],
) -> Tuple[ActionIdentity, ...]:
    error_type = _registry_error_type(mode)
    ids = tuple(spec[0] for spec in specs)
    pairs = tuple((spec[1], spec[2]) for spec in specs)
    if ids != tuple(range(len(specs))):
        raise error_type(
            f"{mode.value} action ids must be contiguous 0..{len(specs) - 1}: {ids}"
        )
    if len(set(ids)) != len(ids):
        raise error_type(f"{mode.value} contains duplicate action ids")
    if len(set(pairs)) != len(pairs):
        raise error_type(f"{mode.value} contains duplicate operator pairs")
    if mode is OperatorMode.PAPER:
        expected_pairs = {
            (destroy_name, repair_name)
            for destroy_name in PAPER_DESTROY_ORDER
            for repair_name in PAPER_REPAIR_ORDER
        }
        if len(specs) != 16 or set(pairs) != expected_pairs:
            raise PaperOperatorRegistryError(
                "paper_mode must contain the exact fixed 4 x 4 action table"
            )
    return tuple(
        ActionIdentity(
            action_id=action_id,
            destroy_name=destroy_name,
            repair_name=repair_name,
            display_name=(
                f"{_DESTROY_DISPLAY[destroy_name]} + {_REPAIR_DISPLAY[repair_name]}"
            ),
            mode=mode,
        )
        for action_id, destroy_name, repair_name in specs
    )


def _fingerprint(mode: OperatorMode, actions: Tuple[ActionIdentity, ...]) -> str:
    payload = {
        "schema_version": ACTION_REGISTRY_SCHEMA_VERSION,
        "mode": mode.value,
        "actions": [
            {
                "action_id": action.action_id,
                "destroy_name": action.destroy_name,
                "repair_name": action.repair_name,
            }
            for action in actions
        ],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_action_registry(
    mode: OperatorMode | str,
    destroy_operators: Mapping[str, Callable[..., object]],
    repair_operators: Mapping[str, Callable[..., object]],
) -> ActionRegistry:
    resolved = resolve_operator_mode(mode)
    if resolved is OperatorMode.PAPER:
        specs = PAPER_ACTION_SPECS
        destroy_names = PAPER_DESTROY_ORDER
        repair_names = PAPER_REPAIR_ORDER
    else:
        specs = EXTENDED_ACTION_SPECS
        destroy_names = EXTENDED_DESTROY_ORDER
        repair_names = EXTENDED_REPAIR_ORDER

    destroy_bindings = _validated_bindings(
        destroy_names, destroy_operators, kind="destroy", mode=resolved
    )
    repair_bindings = _validated_bindings(
        repair_names, repair_operators, kind="repair", mode=resolved
    )
    actions = _build_identities(resolved, specs)
    available_destroy = {name for name, _ in destroy_bindings}
    available_repair = {name for name, _ in repair_bindings}
    error_type = _registry_error_type(resolved)
    for action in actions:
        if action.destroy_name not in available_destroy:
            raise error_type(
                f"action {action.action_id} has unresolved destroy {action.destroy_name!r}"
            )
        if action.repair_name not in available_repair:
            raise error_type(
                f"action {action.action_id} has unresolved repair {action.repair_name!r}"
            )

    return ActionRegistry(
        mode=resolved,
        actions=actions,
        destroy_names=destroy_names,
        repair_names=repair_names,
        destroy_bindings=destroy_bindings,
        repair_bindings=repair_bindings,
        fingerprint=_fingerprint(resolved, actions),
    )


def paper_action_registry(
    destroy_operators: Mapping[str, Callable[..., object]],
    repair_operators: Mapping[str, Callable[..., object]],
) -> ActionRegistry:
    return build_action_registry(
        OperatorMode.PAPER, destroy_operators, repair_operators
    )


def extended_action_registry(
    destroy_operators: Mapping[str, Callable[..., object]],
    repair_operators: Mapping[str, Callable[..., object]],
) -> ActionRegistry:
    return build_action_registry(
        OperatorMode.EXTENDED, destroy_operators, repair_operators
    )


def action_for_id(registry: ActionRegistry, action_id: int) -> ActionIdentity:
    return registry.action_for_id(action_id)


def action_id_for_pair(
    registry: ActionRegistry, destroy_name: str, repair_name: str
) -> int:
    return registry.action_id_for_pair(destroy_name, repair_name)
