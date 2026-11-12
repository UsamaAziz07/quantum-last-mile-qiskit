"""OWNER: FATIMA — QAOA quantum solver for 2-van delivery assignment.

Executes QAOA on the QUBO formulation across multiple repetitions (reps) and random seeds,
benchmarks convergence, measures probability of sampling optimal and feasible routes,
and writes results/quantum_results.json and results/qaoa_circuit.png.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Sequence, Tuple

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import NumPyMinimumEigensolver, QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer

from src.contract import (
    RESULTS_DIR,
    Instance,
    all_assignments,
    canonical,
    is_feasible,
    load_instance,
    model_objective,
    write_json,
)
from src.qubo_model import build_qp, decode, to_qubo


def find_model_optimum(inst: Instance) -> Tuple[Tuple[int, ...], float]:
    """Find the golden model optimum using contract helpers without importing classical.py."""
    best_assignment = None
    best_obj = float("inf")
    for y in all_assignments(inst.n):
        if is_feasible(inst, y):
            obj = model_objective(inst, y)
            if obj < best_obj:
                best_obj = obj
                best_assignment = canonical(y)
    if best_assignment is None:
        raise RuntimeError("No feasible assignment found.")
    return best_assignment, best_obj


def convert_bitstring_endianness(qiskit_bitstring: str) -> str:
    """Convert Qiskit little-endian bitstring (qubit 0 rightmost) to left-to-right variable order.

    In the returned bitstring, index i corresponds to variable yi (qubit i).
    The first n characters represent y0..y{n-1}, followed by slack qubits.
    """
    return qiskit_bitstring[::-1]


def save_qaoa_circuit_diagram(operator, output_path: Path | str) -> dict:
    """Draw and save the reps=1 decomposed QAOA ansatz circuit to a PNG image."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ansatz = QAOAAnsatz(cost_operator=operator, reps=1)
    decomposed = ansatz.decompose().decompose().decompose()

    try:
        decomposed.draw(output="mpl", filename=str(p))
    except Exception:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.01, 0.5, decomposed.draw(output="text"), fontfamily="monospace", va="center")
        plt.savefig(str(p), bbox_inches="tight")
        plt.close(fig)

    return {
        "depth": int(decomposed.depth()),
        "num_qubits": int(ansatz.num_qubits),
        "image": "results/qaoa_circuit.png",
    }


def run_all(
    inst: Instance | None = None,
    reps_list: Sequence[int] = (1, 2, 3),
    seeds: Sequence[int] = (0, 1, 2, 3, 4),
    maxiter: int = 200,
) -> dict:
    """Run QAOA across reps and seeds, evaluate metrics, and save output JSON and circuit image."""
    if inst is None:
        inst = load_instance()

    optimum_canonical, optimum_obj = find_model_optimum(inst)

    # 1. Build QP and QUBO
    qp = build_qp(inst)
    penalty_value = 50.0
    qubo, conv = to_qubo(qp, penalty=penalty_value)
    operator, offset = qubo.to_ising()
    num_qubits = qubo.get_num_binary_vars()

    # 2. Exact eigensolver benchmark
    exact_solver = MinimumEigenOptimizer(NumPyMinimumEigensolver())
    exact_res = exact_solver.solve(qubo)
    exact_y = decode(exact_res.x, inst.n)
    exact_matches = canonical(exact_y) == optimum_canonical
    exact_eigen = {
        "assignment": list(exact_y),
        "energy": float(exact_res.fval),
        "matches_model_optimum": bool(exact_matches),
    }

    # 3. Circuit diagram
    circuit_info = save_qaoa_circuit_diagram(operator, RESULTS_DIR / "qaoa_circuit.png")

    # 4. QAOA runs over reps and seeds
    runs: list[dict] = []
    sampler = StatevectorSampler()

    for reps in reps_list:
        for seed in seeds:
            t0 = time.time()
            energy_history: list[float] = []

            def callback(eval_count, params, value, std):
                energy_history.append(float(value))

            rng = np.random.default_rng(seed)
            initial_point = rng.uniform(0, 2 * np.pi, size=2 * reps)

            optimizer = COBYLA(maxiter=maxiter)
            qaoa = QAOA(
                sampler=sampler,
                optimizer=optimizer,
                reps=reps,
                initial_point=initial_point,
                callback=callback,
            )

            res = qaoa.compute_minimum_eigenvalue(operator)
            runtime_s = round(time.time() - t0, 3)

            # Process state probabilities
            all_samples: list[dict] = []
            for qiskit_bs, prob in res.eigenstate.items():
                bs = convert_bitstring_endianness(qiskit_bs)
                y_raw = tuple(int(c) for c in bs[: inst.n])
                feas = is_feasible(inst, y_raw)
                obj = model_objective(inst, y_raw) if feas else None
                all_samples.append({
                    "bitstring": bs,
                    "assignment": list(y_raw),
                    "prob": float(prob),
                    "feasible": bool(feas),
                    "model_objective": float(obj) if obj is not None else None,
                })

            all_samples.sort(key=lambda s: s["prob"], reverse=True)

            # Feasibility and optimality probabilities
            feasible_samples = [s for s in all_samples if s["feasible"]]
            prob_feasible = float(sum(s["prob"] for s in feasible_samples))
            prob_optimum = float(
                sum(s["prob"] for s in all_samples if canonical(tuple(s["assignment"])) == optimum_canonical)
            )

            # Best feasible assignment (highest prob among feasible)
            if feasible_samples:
                best_feas = feasible_samples[0]
                best_feasible_assignment = best_feas["assignment"]
                best_feasible_model_objective = best_feas["model_objective"]
            else:
                best_feasible_assignment = None
                best_feasible_model_objective = None

            # Top samples: top 8 states + 2 most likely infeasible ones
            top_8 = all_samples[:8]
            seen_bs = {s["bitstring"] for s in top_8}
            top_infeasible = [s for s in all_samples if not s["feasible"] and s["bitstring"] not in seen_bs][:2]
            top_samples = top_8 + top_infeasible

            run_record = {
                "reps": int(reps),
                "seed": int(seed),
                "optimizer": "COBYLA",
                "maxiter": int(maxiter),
                "final_energy": float(res.eigenvalue.real),
                "best_feasible_assignment": best_feasible_assignment,
                "best_feasible_model_objective": best_feasible_model_objective,
                "prob_feasible": round(prob_feasible, 6),
                "prob_optimum": round(prob_optimum, 6),
                "runtime_s": runtime_s,
                "energy_history": energy_history,
                "top_samples": top_samples,
            }
            runs.append(run_record)

    output_data = {
        "instance": inst.name,
        "num_qubits": int(num_qubits),
        "penalty": float(penalty_value),
        "exact_eigen": exact_eigen,
        "circuit": circuit_info,
        "runs": runs,
    }

    out_file = RESULTS_DIR / "quantum_results.json"
    write_json(out_file, output_data)
    print(f"Results written to {out_file}")
    return output_data


if __name__ == "__main__":
    run_all()
