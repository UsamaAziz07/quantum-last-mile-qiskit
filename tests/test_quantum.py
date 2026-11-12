"""Tests for quantum QUBO formulation and exact eigensolver reproduction of golden results."""
from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qiskit_algorithms import NumPyMinimumEigensolver
from qiskit_optimization.algorithms import MinimumEigenOptimizer

from src.contract import all_assignments, canonical, is_feasible, load_instance, model_objective
from src.qubo_model import build_qp, decode, to_qubo


def test_qp_objective_all_assignments():
    """(a) qp.objective.evaluate(y) == model_objective for all 64 y."""
    inst = load_instance()
    qp = build_qp(inst)
    for y in all_assignments(inst.n):
        val_qp = qp.objective.evaluate(list(y))
        val_contract = model_objective(inst, y)
        assert math.isclose(val_qp, val_contract, abs_tol=1e-6), (
            f"Assignment {y}: QP objective {val_qp} != contract objective {val_contract}"
        )


def test_qp_constraints_accept_feasible_only():
    """(b) the constraints accept exactly the feasible y (contract.is_feasible)."""
    inst = load_instance()
    qp = build_qp(inst)
    for y in all_assignments(inst.n):
        assert qp.is_feasible(list(y)) == is_feasible(inst, y), (
            f"Feasibility mismatch for {y}: QP says {qp.is_feasible(list(y))}, contract says {is_feasible(inst, y)}"
        )


def test_qubo_numpy_eigensolver_golden():
    """(c) solving the QUBO with NumPyMinimumEigensolver gives canonical == (0,1,1,0,0,0)."""
    inst = load_instance()
    qp = build_qp(inst)
    qubo, _ = to_qubo(qp, penalty=50.0)

    solver = MinimumEigenOptimizer(NumPyMinimumEigensolver())
    result = solver.solve(qubo)
    decoded = decode(result.x, inst.n)
    canon = canonical(decoded)

    golden_assignment = (0, 1, 1, 0, 0, 0)
    golden_objective = 44.76910575008613

    assert canon == golden_assignment, f"Decoded canonical assignment {canon} != golden {golden_assignment}"
    assert math.isclose(result.fval, golden_objective, abs_tol=1e-4), (
        f"QUBO ground state objective {result.fval} != golden {golden_objective}"
    )


def test_qubit_count():
    """(d) print qubit count and verify expected conversion size (~12 qubits)."""
    inst = load_instance()
    qp = build_qp(inst)
    qubo, _ = to_qubo(qp)
    num_qubits = qubo.get_num_binary_vars()
    print(f"\nQUBO Qubit count: {num_qubits}")
    assert num_qubits == 12


def test_decode_formats():
    """Verify decode works for dict, string, list, numpy array."""
    import numpy as np

    arr = np.array([0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0])
    assert decode(arr, 6) == (0, 1, 1, 0, 0, 0)
    assert decode("011000101000", 6) == (0, 1, 1, 0, 0, 0)
    assert decode([0, 1, 1, 0, 0, 0], 6) == (0, 1, 1, 0, 0, 0)
    assert decode({"y0": 0, "y1": 1, "y2": 1, "y3": 0, "y4": 0, "y5": 0}, 6) == (0, 1, 1, 0, 0, 0)
