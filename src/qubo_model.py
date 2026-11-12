"""OWNER: FATIMA — QUBO formulation for 2-van vehicle assignment.

Implements build_qp(inst), to_qubo(qp), and decode(x, n) per AGENTS.md.
"""
from __future__ import annotations

from typing import Tuple, Union
import numpy as np
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo

from src.contract import Instance, load_instance


def build_qp(inst: Instance | None = None) -> QuadraticProgram:
    """Build QuadraticProgram for 2-van delivery assignment.

    Decision variables:
      y0..y{n-1} binary: y_i = 0 if customer (i+1) is served by van A, 1 if van B.

    Objective:
      f(y) = alpha * sum_{i<j} D_ij * (y_i*y_j + (1-y_i)*(1-y_j)) + beta * (2*L_B - D)^2
      where L_B = sum(d_i * y_i), D = total demand.
      Expanded as linear + quadratic terms with constant such that:
      qp.objective.evaluate(y) == contract.model_objective(inst, y) for all 2^n assignments.

    Constraints:
      L_B <= capacity
      L_B >= D - capacity
    """
    if inst is None:
        inst = load_instance()

    qp = QuadraticProgram(name="quantum_last_mile_delivery")
    n = inst.n
    d = inst.demands
    D = inst.total_demand
    a = inst.alpha
    b = inst.beta

    # Decision variables y0..y{n-1}
    for i in range(n):
        qp.binary_var(name=f"y{i}")

    # Objective expansion:
    # 1) Compactness: alpha * sum_{i<j} D_ij * (2*y_i*y_j - y_i - y_j + 1)
    # 2) Imbalance: beta * (2*L_B - D)^2 = beta * (4*L_B^2 - 4*D*L_B + D^2)
    #    L_B^2 = sum_i d_i^2 y_i + 2 * sum_{i<j} d_i d_j y_i y_j  (since y_i^2 = y_i)
    #    -4*D*L_B = -4*D * sum_i d_i y_i
    # Total constant:
    dist_sum_all_pairs = sum(inst.dist(i + 1, j + 1) for i in range(n) for j in range(i + 1, n))
    c = a * dist_sum_all_pairs + b * (D ** 2)

    # Linear terms:
    linear: dict[str, float] = {}
    for i in range(n):
        dist_i = sum(inst.dist(i + 1, j + 1) for j in range(n) if j != i)
        lin_val = -a * dist_i + b * (4 * (d[i] ** 2) - 4 * D * d[i])
        linear[f"y{i}"] = float(lin_val)

    # Quadratic terms:
    quadratic: dict[tuple[str, str], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            dist_ij = inst.dist(i + 1, j + 1)
            quad_val = 2 * a * dist_ij + 8 * b * d[i] * d[j]
            quadratic[(f"y{i}", f"y{j}")] = float(quad_val)

    qp.minimize(constant=float(c), linear=linear, quadratic=quadratic)

    # Capacity constraints:
    # L_B <= capacity
    # L_B >= D - capacity
    weights = {f"y{i}": d[i] for i in range(n)}
    qp.linear_constraint(linear=weights, sense="<=", rhs=inst.capacity, name="c_capacity_max_B")
    qp.linear_constraint(linear=weights, sense=">=", rhs=D - inst.capacity, name="c_capacity_min_B")

    return qp


def to_qubo(qp: QuadraticProgram, penalty: float | None = 50.0) -> tuple[QuadraticProgram, QuadraticProgramToQubo]:
    """Convert constrained QuadraticProgram to an unconstrained QUBO via slack variables and penalty.

    Penalty choice:
      A penalty factor of 50.0 is selected and documented. Since the max objective difference
      between assignments is ~35, a penalty of 50.0 ensures that any constraint violation
      imposes an energy penalty strictly exceeding the objective gain, guaranteeing that
      the ground state of the QUBO coincides with the feasible model optimum.

    Returns:
      (qubo, converter): the unconstrained QuadraticProgram and the QuadraticProgramToQubo converter.
    """
    converter = QuadraticProgramToQubo(penalty=penalty)
    qubo = converter.convert(qp)
    return qubo, converter


def decode(x: Union[dict, list, tuple, np.ndarray, str], n: int) -> Tuple[int, ...]:
    """Decode solution vector/bitstring keeping the first n entries as assignment tuple y_0..y_{n-1}.

    Slack variables introduced during QUBO conversion are ignored.
    """
    if isinstance(x, dict):
        return tuple(int(x[f"y{i}"]) if f"y{i}" in x else int(x[i]) for i in range(n))
    if isinstance(x, str):
        return tuple(int(c) for c in x[:n])
    if isinstance(x, np.ndarray):
        return tuple(int(x[i]) for i in range(n))
    return tuple(int(x[i]) for i in range(n))
