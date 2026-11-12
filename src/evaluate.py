"""Build evaluation tables and figures from classical and quantum result JSON."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
MOCK_FILES = {
    "classical": ROOT / "contract" / "sample_classical_reference.json",
    "pareto": ROOT / "contract" / "sample_pareto_classical.json",
    "quantum": ROOT / "contract" / "sample_quantum_results.json",
}
REAL_FILES = {
    "classical": ROOT / "results" / "classical_reference.json",
    "pareto": ROOT / "results" / "pareto_classical.json",
    "quantum": ROOT / "results" / "quantum_results.json",
}


def _read_inputs(mock: bool) -> tuple[dict, list[dict], dict, bool]:
    use_mock = mock or not all(path.exists() for path in REAL_FILES.values())
    if use_mock:
        print("!!! MOCK DATA: evaluating contract/sample_*.json !!!")
        paths = MOCK_FILES
    else:
        paths = REAL_FILES
    with paths["classical"].open(encoding="utf-8") as fh:
        classical = json.load(fh)
    with paths["pareto"].open(encoding="utf-8") as fh:
        pareto = json.load(fh)
    with paths["quantum"].open(encoding="utf-8") as fh:
        quantum = json.load(fh)
    return classical, pareto, quantum, use_mock


def _key(assignment: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    values = tuple(int(value) for value in assignment)
    mirror = tuple(1 - value for value in values)
    return min(values, mirror)


def _route_lookup(classical: dict) -> dict[tuple[int, ...], dict]:
    return {
        _key(row["assignment"]): row
        for row in classical.get("all_feasible", [])
    }


def _qaoa_row(run: dict, route_lookup: dict, optimum: float) -> dict:
    assignment = run.get("best_feasible_assignment")
    known = route_lookup.get(_key(assignment)) if assignment is not None else None
    true_length = known.get("true_route_length", float("nan")) if known else float("nan")
    return {
        "method": run.get("_label", f"qaoa_reps_{run['reps']}"),
        "assignment": json.dumps(assignment),
        "feasible": assignment is not None,
        "model_objective": run.get("best_feasible_model_objective", float("nan")),
        "true_route_length": true_length,
        "gap_to_optimum_pct": (
            100 * (true_length - optimum) / optimum
            if not math.isnan(true_length)
            else float("nan")
        ),
        "prob_optimum": run.get("prob_optimum", 0.0),
        "prob_feasible": run.get("prob_feasible", 0.0),
        "runtime_s": run.get("runtime_s", float("nan")),
    }


def _qaoa_summary_rows(runs: list[dict], route_lookup: dict, optimum: float) -> list[dict]:
    rows = []
    for reps in sorted({run["reps"] for run in runs}):
        group = [run for run in runs if run["reps"] == reps]
        best = max(group, key=lambda run: (run.get("prob_optimum", 0.0), -run.get("final_energy", 0.0)))
        ordered = sorted(group, key=lambda run: run.get("final_energy", 0.0))
        median = ordered[len(ordered) // 2]
        mean_probability = sum(run.get("prob_optimum", 0.0) for run in group) / len(group)
        for label, run in (("best", best), ("median", median)):
            labelled = dict(run)
            labelled["_label"] = f"qaoa_reps_{reps}_{label}"
            row = _qaoa_row(labelled, route_lookup, optimum)
            row["prob_optimum"] = mean_probability
            rows.append(row)
    return rows


def _classical_row(row: dict, optimum: float) -> dict:
    true_length = row["true_route_length"]
    return {
        "method": row["method"],
        "assignment": json.dumps(row["assignment"]),
        "feasible": bool(row["feasible"]),
        "model_objective": row["model_objective"],
        "true_route_length": true_length,
        "gap_to_optimum_pct": 100 * (true_length - optimum) / optimum,
        "prob_optimum": float("nan"),
        "prob_feasible": float("nan"),
        "runtime_s": row["runtime_s"],
    }


def _save_convergence(quantum: dict, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    for run in quantum["runs"]:
        ax.plot(run["energy_history"], marker=".", label=f"p={run['reps']}, seed={run['seed']}")
    ax.set(title="QAOA convergence", xlabel="Optimizer iteration", ylabel="Energy")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "convergence.png", dpi=200)
    plt.close(fig)


def _save_probability_histogram(quantum: dict, classical: dict, out: Path) -> None:
    run = max(quantum["runs"], key=lambda item: item.get("prob_optimum", 0.0))
    samples = run.get("top_samples", [])
    optimum = _key(classical["optimum_model"]["assignment"])
    colors = []
    labels = []
    for sample in samples:
        assignment = sample.get("assignment", [])
        if not sample.get("feasible", False):
            colors.append("#d62728")
            labels.append("Infeasible")
        elif _key(assignment) == optimum:
            colors.append("#2ca02c")
            labels.append("Optimum")
        else:
            colors.append("#1f77b4")
            labels.append("Other feasible")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(range(len(samples)), [s.get("prob", 0) for s in samples], color=colors)
    ax.set(title="Top samples from best QAOA run", xlabel="Bitstring", ylabel="Probability")
    ax.set_xticks(range(len(samples)), [s.get("bitstring", "") for s in samples], rotation=60)
    for color, label in (("#2ca02c", "Optimum"), ("#1f77b4", "Other feasible"), ("#d62728", "Infeasible")):
        ax.bar([], [], color=color, label=label)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "probability_histogram.png", dpi=200)
    plt.close(fig)


def _save_route_map(classical: dict, out: Path) -> None:
    optimum = classical["optimum_model"]
    positions = [(0, 0), (1, 2), (2, 1), (3, 3), (4, 0), (5, 2), (6, 1)]
    fig, ax = plt.subplots(figsize=(7, 5))
    for van, color in (("A", "#1f77b4"), ("B", "#ff7f0e")):
        route = optimum["routes"][van]
        points = [positions[0]] + [positions[i] for i in route] + [positions[0]]
        ax.plot([p[0] for p in points], [p[1] for p in points], "o-", color=color, label=f"Van {van}")
    for number, (x, y) in enumerate(positions):
        ax.text(x + 0.08, y + 0.08, "Depot" if number == 0 else f"C{number}")
    ax.set(title="Optimal assignment route map (schematic)", xlabel="Map x", ylabel="Map y")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "route_map.png", dpi=200)
    plt.close(fig)


def _save_pareto(pareto: list[dict], out: Path) -> None:
    frame = pd.DataFrame(pareto)
    imbalance = [abs(load[0] - load[1]) for load in frame["loads"]]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(frame["beta"], frame["true_route_length"], "o-", label="True route length")
    ax.set(title="Distance vs. load-balance trade-off", xlabel="Balance penalty beta", ylabel="True route length")
    ax2 = ax.twinx()
    ax2.plot(frame["beta"], imbalance, "s--", color="#d62728", label="Load imbalance")
    ax2.set_ylabel("Load imbalance")
    fig.tight_layout()
    fig.savefig(out / "pareto.png", dpi=200)
    plt.close(fig)


def _save_comparison(rows: list[dict], out: Path) -> None:
    frame = pd.DataFrame([r for r in rows if not r["method"].startswith("qaoa_")])
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(frame["method"], frame["true_route_length"], color="#4c78a8")
    ax.set(title="Classical method comparison", xlabel="Method", ylabel="True route length")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(out / "comparison.png", dpi=200)
    plt.close(fig)


def main(results_dir: str | Path = "results", mock: bool = False) -> dict:
    classical, pareto, quantum, used_mock = _read_inputs(mock)
    out = Path(results_dir)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    optimum = classical["optimum_true"]["true_route_length"]
    route_lookup = _route_lookup(classical)
    rows = [_classical_row(row, optimum) for row in classical["methods"]]
    rows.extend(_qaoa_summary_rows(quantum["runs"], route_lookup, optimum))
    frame = pd.DataFrame(rows, columns=[
        "method", "assignment", "feasible", "model_objective", "true_route_length",
        "gap_to_optimum_pct", "prob_optimum", "prob_feasible", "runtime_s",
    ])
    frame.to_csv(out / "results.csv", index=False)

    qaoa_by_reps = pd.DataFrame(
        _qaoa_summary_rows(quantum["runs"], route_lookup, optimum)
    )
    best_run = max(quantum["runs"], key=lambda run: run.get("prob_optimum", 0.0))
    best_assignment = best_run.get("best_feasible_assignment")
    best_known = route_lookup.get(_key(best_assignment)) if best_assignment else None
    summary = {
        "num_qubits": quantum["num_qubits"],
        "circuit_depth": quantum["circuit"]["depth"],
        "optimum_model_assignment": classical["optimum_model"]["assignment"],
        "optimum_true_length": optimum,
        "best_qaoa_assignment": best_assignment,
        "best_qaoa_true_length": best_known["true_route_length"] if best_known else None,
        "qaoa_gap_pct": (
            100 * (best_known["true_route_length"] - optimum) / optimum
            if best_known else None
        ),
        "prob_optimum_by_reps": {
            str(reps): {
                "mean": sum(run.get("prob_optimum", 0.0) for run in quantum["runs"] if run["reps"] == reps)
                / len([run for run in quantum["runs"] if run["reps"] == reps]),
                "max": max(run.get("prob_optimum", 0.0) for run in quantum["runs"] if run["reps"] == reps),
            }
            for reps in sorted({run["reps"] for run in quantum["runs"]})
        },
        "prob_feasible_by_reps": {
            str(reps): sum(run.get("prob_feasible", 0.0) for run in quantum["runs"] if run["reps"] == reps)
            / len([run for run in quantum["runs"] if run["reps"] == reps])
            for reps in sorted({run["reps"] for run in quantum["runs"]})
        },
        "exact_eigen_match": quantum["exact_eigen"]["matches_model_optimum"],
        "brute_force_runtime_s": next(r["runtime_s"] for r in classical["methods"] if r["method"] == "brute_force"),
        "qaoa_total_runtime_s": sum(run.get("runtime_s", 0) for run in quantum["runs"]),
        "mock": used_mock,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _save_convergence(quantum, out)
    _save_probability_histogram(quantum, classical, out)
    _save_route_map(classical, out)
    _save_pareto(pareto, out)
    _save_comparison(rows, out)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="use contract sample JSON files")
    args = parser.parse_args()
    main(mock=args.mock)
