"""OWNER: USAMA — only USAMA's AI agent edits this file.
See AGENTS.md for signatures and schemas. Import shared items from src.contract.
Pure Python standard library only (no qiskit).
"""
from __future__ import annotations

import itertools
import math
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from src.contract import (
    ROOT,
    Instance,
    all_assignments,
    canonical,
    is_feasible,
    load_instance,
    loads,
    model_objective,
    write_json,
)


def tour_length(inst: Instance, order: Sequence[int]) -> float:
    """Return total length of tour depot(0) -> order[0] -> ... -> order[-1] -> depot(0)."""
    if not order:
        return 0.0
    d = inst.dist(0, order[0])
    for a, b in zip(order[:-1], order[1:]):
        d += inst.dist(a, b)
    d += inst.dist(order[-1], 0)
    return d


def route_length(inst: Instance, customers: Sequence[int]) -> Tuple[float, List[int]]:
    """Exact shortest tour depot->customers->depot by brute-force permutations; return (length, order). Empty list -> (0.0, [])."""
    cust_list = list(customers)
    if not cust_list:
        return 0.0, []
    if len(cust_list) == 1:
        c = cust_list[0]
        return 2.0 * inst.dist(0, c), [c]

    best_len = float("inf")
    best_order: List[int] = []
    for p in itertools.permutations(sorted(cust_list)):
        l = tour_length(inst, p)
        if l < best_len - 1e-12:
            best_len = l
            best_order = list(p)
    return best_len, best_order


def evaluate_assignment(inst: Instance, y: Sequence[int]) -> Dict[str, Any]:
    """Dict with assignment(list), feasible, model_objective, true_route_length (sum of both vans' exact tours), routes {"A":[...],"B":[...]}, loads [L_A, L_B]."""
    y_tup = tuple(int(v) for v in y)
    custs_a = [i + 1 for i, v in enumerate(y_tup) if v == 0]
    custs_b = [i + 1 for i, v in enumerate(y_tup) if v == 1]
    len_a, route_a = route_length(inst, custs_a)
    len_b, route_b = route_length(inst, custs_b)
    la, lb = loads(inst, y_tup)
    return {
        "assignment": list(y_tup),
        "feasible": is_feasible(inst, y_tup),
        "model_objective": model_objective(inst, y_tup),
        "true_route_length": len_a + len_b,
        "routes": {"A": route_a, "B": route_b},
        "loads": [la, lb],
    }


def brute_force(inst: Instance) -> Dict[str, Any]:
    """Enumerate all assignments, keep canonical + feasible ones, return best-by-model_objective plus the full list; time it with time.perf_counter (runtime_s)."""
    t0 = time.perf_counter()
    all_canon_feasible: List[Dict[str, Any]] = []
    seen = set()
    best_eval: Dict[str, Any] | None = None
    best_obj = float("inf")

    for y in all_assignments(inst.n):
        c = canonical(y)
        if c in seen:
            continue
        seen.add(c)
        if is_feasible(inst, c):
            ev = evaluate_assignment(inst, c)
            all_canon_feasible.append(ev)
            if ev["model_objective"] < best_obj:
                best_obj = ev["model_objective"]
                best_eval = ev

    all_canon_feasible.sort(key=lambda item: tuple(item["assignment"]))
    elapsed = time.perf_counter() - t0
    assert best_eval is not None, "No feasible assignment found"

    return {
        "method": "brute_force",
        "assignment": list(best_eval["assignment"]),
        "feasible": best_eval["feasible"],
        "model_objective": best_eval["model_objective"],
        "true_route_length": best_eval["true_route_length"],
        "runtime_s": elapsed,
        "routes": best_eval["routes"],
        "loads": best_eval["loads"],
        "all_feasible": all_canon_feasible,
    }


def greedy(inst: Instance) -> Dict[str, Any]:
    """Sweep heuristic — sort customers by polar angle around the depot; for every cut of that circular order into two groups, keep feasible splits; choose lowest model_objective. Must return a feasible result."""
    t0 = time.perf_counter()
    dx, dy = inst.depot
    angles = sorted(
        range(1, inst.n + 1),
        key=lambda i: math.atan2(inst.coords[i - 1][1] - dy, inst.coords[i - 1][0] - dx),
    )
    n = len(angles)
    best_eval: Dict[str, Any] | None = None
    best_obj = float("inf")

    for start in range(n):
        for length in range(1, n):
            group_a = {angles[(start + k) % n] for k in range(length)}
            y = canonical(tuple(0 if (i + 1) in group_a else 1 for i in range(n)))
            if is_feasible(inst, y):
                obj = model_objective(inst, y)
                if obj < best_obj:
                    best_obj = obj
                    best_eval = evaluate_assignment(inst, y)

    elapsed = time.perf_counter() - t0
    assert best_eval is not None, "Greedy sweep found no feasible assignment"

    return {
        "method": "greedy",
        "assignment": list(best_eval["assignment"]),
        "feasible": best_eval["feasible"],
        "model_objective": best_eval["model_objective"],
        "true_route_length": best_eval["true_route_length"],
        "runtime_s": elapsed,
        "routes": best_eval["routes"],
        "loads": best_eval["loads"],
    }


def simulated_annealing(inst: Instance, seed: int = 42) -> Dict[str, Any]:
    """Single-bit flips, energy = model_objective + 1000*(max(0,L_A-Q)+max(0,L_B-Q)), geometric cooling, 3000 steps, deterministic; return best feasible found."""
    t0 = time.perf_counter()
    rng = random.Random(seed)

    def energy(y_cand: Tuple[int, ...]) -> float:
        la, lb = loads(inst, y_cand)
        pen = 1000.0 * (max(0, la - inst.capacity) + max(0, lb - inst.capacity))
        return model_objective(inst, y_cand) + pen

    y = tuple(rng.choice([0, 1]) for _ in range(inst.n))
    curr_e = energy(y)

    best_feas_y: Tuple[int, ...] | None = None
    best_feas_obj = float("inf")
    if is_feasible(inst, y):
        best_feas_y = canonical(y)
        best_feas_obj = model_objective(inst, y)

    t_start = 50.0
    t_end = 0.001
    steps = 3000
    cooling = (t_end / t_start) ** (1.0 / steps)
    t_curr = t_start

    for _ in range(steps):
        idx = rng.randrange(inst.n)
        cand = list(y)
        cand[idx] = 1 - cand[idx]
        cand_tup = tuple(cand)
        cand_e = energy(cand_tup)
        de = cand_e - curr_e

        if de < 0 or rng.random() < math.exp(-de / max(t_curr, 1e-9)):
            y = cand_tup
            curr_e = cand_e
            if is_feasible(inst, y):
                obj = model_objective(inst, y)
                if obj < best_feas_obj:
                    best_feas_obj = obj
                    best_feas_y = canonical(y)
        t_curr *= cooling

    elapsed = time.perf_counter() - t0
    assert best_feas_y is not None, "SA found no feasible assignment"
    best_eval = evaluate_assignment(inst, best_feas_y)

    return {
        "method": "simulated_annealing",
        "assignment": list(best_eval["assignment"]),
        "feasible": best_eval["feasible"],
        "model_objective": best_eval["model_objective"],
        "true_route_length": best_eval["true_route_length"],
        "runtime_s": elapsed,
        "routes": best_eval["routes"],
        "loads": best_eval["loads"],
    }


def pareto_sweep(inst: Instance, betas: Sequence[float]) -> List[Dict[str, Any]]:
    """For each beta find the exact optimum among feasible assignments using model_objective(inst, y, beta=b); rows {beta, assignment, loads, model_objective, true_route_length}."""
    seen = set()
    canon_feas: List[Tuple[int, ...]] = []
    for y in all_assignments(inst.n):
        c = canonical(y)
        if c not in seen and is_feasible(inst, c):
            seen.add(c)
            canon_feas.append(c)

    rows: List[Dict[str, Any]] = []
    for b in betas:
        best_c: Tuple[int, ...] | None = None
        best_obj = float("inf")
        for c in canon_feas:
            obj = model_objective(inst, c, beta=b)
            if obj < best_obj:
                best_obj = obj
                best_c = c
        assert best_c is not None
        ev = evaluate_assignment(inst, best_c)
        rows.append({
            "beta": b,
            "assignment": ev["assignment"],
            "loads": ev["loads"],
            "model_objective": best_obj,
            "true_route_length": ev["true_route_length"],
        })
    return rows


def run_classical(inst: Instance | None = None) -> Dict[str, Any]:
    """Build and write results/classical_reference.json and results/pareto_classical.json."""
    if inst is None:
        inst = load_instance()

    bf = brute_force(inst)
    gr = greedy(inst)
    sa = simulated_annealing(inst, seed=42)

    all_feasible = bf["all_feasible"]
    optimum_model = min(all_feasible, key=lambda x: x["model_objective"])
    optimum_true = min(all_feasible, key=lambda x: x["true_route_length"])

    methods = [
        {
            "method": "brute_force",
            "assignment": bf["assignment"],
            "feasible": bf["feasible"],
            "model_objective": bf["model_objective"],
            "true_route_length": bf["true_route_length"],
            "runtime_s": bf["runtime_s"],
        },
        {
            "method": "greedy",
            "assignment": gr["assignment"],
            "feasible": gr["feasible"],
            "model_objective": gr["model_objective"],
            "true_route_length": gr["true_route_length"],
            "runtime_s": gr["runtime_s"],
        },
        {
            "method": "simulated_annealing",
            "assignment": sa["assignment"],
            "feasible": sa["feasible"],
            "model_objective": sa["model_objective"],
            "true_route_length": sa["true_route_length"],
            "runtime_s": sa["runtime_s"],
        },
    ]

    ref = {
        "instance": inst.name,
        "optimum_model": {
            "assignment": optimum_model["assignment"],
            "model_objective": optimum_model["model_objective"],
            "true_route_length": optimum_model["true_route_length"],
            "routes": optimum_model["routes"],
            "loads": optimum_model["loads"],
        },
        "optimum_true": {
            "assignment": optimum_true["assignment"],
            "model_objective": optimum_true["model_objective"],
            "true_route_length": optimum_true["true_route_length"],
            "routes": optimum_true["routes"],
            "loads": optimum_true["loads"],
        },
        "methods": methods,
        "all_feasible": [
            {
                "assignment": row["assignment"],
                "model_objective": row["model_objective"],
                "true_route_length": row["true_route_length"],
                "routes": row["routes"],
                "loads": row["loads"],
            }
            for row in all_feasible
        ],
    }

    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    write_json(results_dir / "classical_reference.json", ref)

    betas = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2]
    pareto_data = pareto_sweep(inst, betas)
    write_json(results_dir / "pareto_classical.json", pareto_data)

    return ref


if __name__ == "__main__":
    ref = run_classical()
    print("Classical baselines completed.")
    print(f"Optimum Model: {ref['optimum_model']['assignment']} (obj={ref['optimum_model']['model_objective']:.4f}, route={ref['optimum_model']['true_route_length']:.4f})")
    print(f"Optimum True:  {ref['optimum_true']['assignment']} (obj={ref['optimum_true']['model_objective']:.4f}, route={ref['optimum_true']['true_route_length']:.4f})")
    print(f"{'Method':<20} {'Assignment':<22} {'Feasible':<10} {'Model Obj':<12} {'Route Len':<12} {'Runtime (s)':<12}")
    print("-" * 88)
    for m in ref["methods"]:
        asgn_str = str(m["assignment"])
        print(f"{m['method']:<20} {asgn_str:<22} {str(m['feasible']):<10} {m['model_objective']:<12.4f} {m['true_route_length']:<12.4f} {m['runtime_s']:<12.6f}")
