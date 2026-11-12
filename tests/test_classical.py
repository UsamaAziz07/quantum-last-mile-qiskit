"""OWNER: USAMA.
Tests for classical baselines:
- brute force reproduces contract/golden_classical.json
- route_length on known/hand-checked cases
- greedy and simulated annealing are feasible
- all outputs JSON-serialisable
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from src.classical import (
    brute_force,
    evaluate_assignment,
    greedy,
    pareto_sweep,
    route_length,
    run_classical,
    simulated_annealing,
)
from src.contract import ROOT, canonical, is_feasible, load_instance


@pytest.fixture
def inst():
    return load_instance()


def test_route_length_empty(inst):
    length, order = route_length(inst, [])
    assert length == 0.0
    assert order == []


def test_route_length_hand_checked_cases(inst):
    # Customer 1 at (4, 3): distance to depot (0,0) is 5.0. Tour 0 -> 1 -> 0 is 10.0.
    length, order = route_length(inst, [1])
    assert math.isclose(length, 10.0, rel_tol=1e-9)
    assert order == [1]

    # Customers 2 at (5, 5) and 3 at (6, 2):
    # dist(0, 2) = sqrt(25 + 25) = sqrt(50) = 7.0710678...
    # dist(2, 3) = sqrt(1 + 9) = sqrt(10) = 3.1622776...
    # dist(3, 0) = sqrt(36 + 4) = sqrt(40) = 6.3245553...
    # Tour length = sqrt(50) + sqrt(10) + sqrt(40) = 16.55790079237...
    expected_tour = math.sqrt(50) + math.sqrt(10) + math.sqrt(40)
    length, order = route_length(inst, [2, 3])
    assert math.isclose(length, expected_tour, rel_tol=1e-9)
    assert set(order) == {2, 3}


def test_brute_force_reproduces_golden(inst):
    golden_path = ROOT / "contract" / "golden_classical.json"
    golden = json.loads(golden_path.read_text())

    res = brute_force(inst)
    assert canonical(res["assignment"]) == tuple(golden["optimum_model"]["assignment"])
    assert math.isclose(res["model_objective"], golden["optimum_model"]["model_objective"], abs_tol=1e-6)
    assert math.isclose(res["true_route_length"], golden["optimum_model"]["true_route_length"], abs_tol=1e-6)
    assert res["feasible"] is True

    # 13 canonical feasible assignments
    all_feas = res["all_feasible"]
    assert len(all_feas) == golden["n_feasible_canonical"]
    assert len(all_feas) == 13

    golden_map = {tuple(row["assignment"]): row for row in golden["all_feasible"]}
    for row in all_feas:
        asgn = tuple(row["assignment"])
        assert asgn in golden_map, f"Unexpected assignment: {asgn}"
        g = golden_map[asgn]
        assert math.isclose(row["model_objective"], g["model_objective"], abs_tol=1e-6)
        assert math.isclose(row["true_route_length"], g["true_route_length"], abs_tol=1e-6)
        assert row["loads"] == g["loads"]
        assert row["routes"] == g["routes"]


def test_evaluate_assignment(inst):
    # Test golden optimal assignment
    ev = evaluate_assignment(inst, (0, 1, 1, 0, 0, 0))
    assert ev["feasible"] is True
    assert math.isclose(ev["model_objective"], 44.76910575008613, abs_tol=1e-6)
    assert math.isclose(ev["true_route_length"], 41.4972128429564, abs_tol=1e-6)
    assert ev["loads"] == [7, 5]
    assert ev["routes"] == {"A": [1, 4, 5, 6], "B": [2, 3]}


def test_greedy_is_feasible(inst):
    res = greedy(inst)
    assert res["feasible"] is True
    assert is_feasible(inst, res["assignment"]) is True
    assert len(res["assignment"]) == inst.n
    assert res["method"] == "greedy"
    assert res["runtime_s"] >= 0.0


def test_simulated_annealing_is_feasible_and_deterministic(inst):
    res1 = simulated_annealing(inst, seed=42)
    res2 = simulated_annealing(inst, seed=42)
    assert res1["feasible"] is True
    assert is_feasible(inst, res1["assignment"]) is True
    assert res1["assignment"] == res2["assignment"]
    assert math.isclose(res1["model_objective"], res2["model_objective"], abs_tol=1e-9)
    assert res1["method"] == "simulated_annealing"


def test_pareto_sweep(inst):
    betas = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2]
    rows = pareto_sweep(inst, betas)
    assert len(rows) == len(betas)
    for r, b in zip(rows, betas):
        assert r["beta"] == b
        assert is_feasible(inst, r["assignment"]) is True
        assert "loads" in r
        assert "model_objective" in r
        assert "true_route_length" in r


def test_outputs_json_serialisable(inst):
    ref = run_classical(inst)
    # Check that json serialization succeeds
    s = json.dumps(ref)
    assert len(s) > 0

    pareto_path = ROOT / "results" / "pareto_classical.json"
    pareto_data = json.loads(pareto_path.read_text())
    assert isinstance(pareto_data, list)
    assert len(pareto_data) == 8
