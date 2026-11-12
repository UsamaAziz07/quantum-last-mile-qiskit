"""Run the complete classical, quantum, and evaluation pipeline."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def _print_summary(summary: dict, timings: dict[str, float]) -> None:
    reps = summary.get("prob_optimum_by_reps", {})
    feasible = summary.get("prob_feasible_by_reps", {})
    print("\nQuantum Last-Mile summary")
    print("=" * 72)
    print(f"{'Optimum route':<24} {summary['optimum_true_length']:.4f}")
    best = summary.get("best_qaoa_true_length")
    print(f"{'QAOA best route':<24} {best:.4f}" if best is not None else f"{'QAOA best route':<24} n/a")
    gap = summary.get("qaoa_gap_pct")
    print(f"{'QAOA gap (%)':<24} {gap:.2f}" if gap is not None else f"{'QAOA gap (%)':<24} n/a")
    print(f"{'Qubits':<24} {summary['num_qubits']}")
    print(f"{'Total pipeline time (s)':<24} {sum(timings.values()):.3f}")
    print("\nPer-repetition probabilities")
    print(f"{'p':<8} {'P(optimum)':<16} {'P(feasible)':<16}")
    print("-" * 40)
    for key in sorted(reps, key=int):
        print(f"{key:<8} {reps[key]['mean']:.4f} (max {reps[key]['max']:.4f})   {feasible.get(key, 0.0):.4f}")
    print("\nStage times (s): " + ", ".join(f"{name}={value:.3f}" for name, value in timings.items()))


def main(fast: bool = False) -> dict:
    try:
        from src.classical import run_classical
        from src.quantum_solver import run_all
        from src.evaluate import main as evaluate_main
    except ImportError as exc:
        raise SystemExit(
            "Missing project dependency. Run: pip install -r requirements.txt"
        ) from exc

    timings: dict[str, float] = {}
    started = time.perf_counter()
    run_classical()
    timings["classical"] = time.perf_counter() - started

    started = time.perf_counter()
    if fast:
        run_all(reps_list=(1, 2), seeds=(0, 1))
    else:
        run_all()
    timings["quantum"] = time.perf_counter() - started

    started = time.perf_counter()
    summary = evaluate_main()
    timings["evaluation"] = time.perf_counter() - started
    _print_summary(summary, timings)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full quantum last-mile demo")
    parser.add_argument("--fast", action="store_true", help="run p=1,2 with seeds 0,1")
    args = parser.parse_args()
    main(fast=args.fast)
