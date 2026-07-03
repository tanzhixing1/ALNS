from __future__ import annotations

import argparse
from pathlib import Path

from alns_solver import run_c_alns
from config import build_config
from dataset_loader import generate_toy_data
from evaluation import evaluate_and_save
from objective import objective


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "y", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prototype C-ALNS for TVDCTP-T.")
    parser.add_argument("--num_orders", type=int, default=6)
    parser.add_argument("--num_customers", type=int, default=None)
    parser.add_argument("--num_transshipments", type=int, default=2)
    parser.add_argument("--num_containers", type=int, default=1)
    parser.add_argument("--container_origin", type=str, default="port")
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--max_no_improve", type=int, default=100)
    parser.add_argument("--early_stop", type=_parse_bool, nargs="?", const=True, default=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--drone_enabled", type=_parse_bool, nargs="?", const=True, default=True)
    parser.add_argument("--output_dir", type=str, default="outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    num_customers = args.num_customers if args.num_customers is not None else args.num_orders
    config = build_config(
        num_customers=num_customers,
        num_orders=args.num_orders,
        num_transshipments=args.num_transshipments,
        num_containers=args.num_containers,
        container_origin=args.container_origin,
        iterations=args.iterations,
        seed=args.seed,
        drone_enabled=args.drone_enabled,
        output_dir=args.output_dir,
        max_no_improve=args.max_no_improve,
        early_stop_enabled=args.early_stop,
    )
    if not Path(config.output_dir).is_absolute():
        config.output_dir = str(Path(__file__).resolve().parent / config.output_dir)

    data = generate_toy_data(config)
    result = run_c_alns(data, config)
    metrics = evaluate_and_save(result, data, config)

    initial_cost, _ = objective(result.initial_state, data, config)
    print("TVDCTP-T prototype C-ALNS finished")
    print(f"Initial objective: {initial_cost:.3f}")
    print(f"Best objective:    {metrics['best_objective']:.3f}")
    print(f"Feasible:          {metrics['feasible']}")
    print(f"Runtime seconds:   {metrics['runtime_seconds']:.3f}")
    print(f"Selected WH:       {metrics['selected_transshipment']}")
    print(f"Candidate WHs:     {metrics['candidate_transshipment_nodes']}")
    print(f"Truck arrival:     {float(metrics['truck_arrival_time']):.3f} min")
    print(f"Van start:         {float(metrics['van_start_time']):.3f} min")
    print(f"TW violations:     {metrics['num_time_window_violations']}")
    print(
        "Waiting reported: "
        f"van={float(metrics['total_van_waiting_time']):.3f} min, "
        f"drone={float(metrics['total_drone_waiting_time']):.3f} min, "
        f"early={float(metrics['total_early_waiting_time']):.3f} min"
    )
    print("Waiting in objective: False")
    print("Best state:")
    print(result.best_state.pretty_print())
    print(f"Outputs saved to:  {config.output_dir}")


if __name__ == "__main__":
    main()
