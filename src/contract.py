"""SHARED CONTRACT — FROZEN. Single source of truth for data types and cost definitions.

Nobody edits this file alone. It is imported by classical.py, qubo_model.py, quantum_solver.py, evaluate.py.
Conventions
  * Index 0 = depot, 1..n = customers.   Assignment y = tuple of n ints (0/1); y[i-1] is the van of customer i.
  * 0 = van A, 1 = van B.  Vans are identical, so y and its mirror (1-y) are the same solution -> use canonical().
  * Bitstring <-> assignment: bit i (left to right) = y[i] for the n decision variables; slack qubits come AFTER.
"""
from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Tuple

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "instance.json"
RESULTS_DIR = ROOT / "results"

Assignment = Tuple[int, ...]


@dataclass(frozen=True)
class Instance:
    name: str
    depot: Tuple[float, float]
    coords: Tuple[Tuple[float, float], ...]   # customers 1..n
    demands: Tuple[int, ...]                  # customers 1..n
    num_vehicles: int
    capacity: int
    alpha: float
    beta: float
    seed: int

    @property
    def n(self) -> int:
        return len(self.coords)

    @property
    def total_demand(self) -> int:
        return sum(self.demands)

    def point(self, i: int) -> Tuple[float, float]:
        return self.depot if i == 0 else self.coords[i - 1]

    def dist(self, i: int, j: int) -> float:
        """Euclidean distance between nodes i, j (0 = depot, 1..n customers)."""
        (x1, y1), (x2, y2) = self.point(i), self.point(j)
        return math.hypot(x1 - x2, y1 - y2)


def load_instance(path: str | Path = DEFAULT_CONFIG) -> Instance:
    cfg = json.loads(Path(path).read_text())
    custs = sorted(cfg["customers"], key=lambda c: c["id"])
    inst = Instance(
        name=cfg["name"],
        depot=tuple(cfg["depot"]),
        coords=tuple(tuple(c["xy"]) for c in custs),
        demands=tuple(int(c["demand"]) for c in custs),
        num_vehicles=int(cfg["num_vehicles"]),
        capacity=int(cfg["vehicle_capacity"]),
        alpha=float(cfg["weights"]["alpha_distance"]),
        beta=float(cfg["weights"]["beta_balance"]),
        seed=int(cfg.get("seed", 42)),
    )
    assert inst.num_vehicles == 2, "contract supports exactly 2 vans"
    return inst


def all_assignments(n: int) -> Iterator[Assignment]:
    return itertools.product((0, 1), repeat=n)


def canonical(y) -> Assignment:
    """Mirror-invariant form: customer 1 always on van A (0)."""
    y = tuple(int(v) for v in y)
    return y if y[0] == 0 else tuple(1 - v for v in y)


def loads(inst: Instance, y) -> Tuple[int, int]:
    """(L_A, L_B) = total demand on van A and van B."""
    lb = sum(d for d, v in zip(inst.demands, y) if v == 1)
    return inst.total_demand - lb, lb


def is_feasible(inst: Instance, y) -> bool:
    la, lb = loads(inst, y)
    return la <= inst.capacity and lb <= inst.capacity


def model_objective(inst: Instance, y, alpha: float | None = None, beta: float | None = None) -> float:
    """f(y) = alpha * sum_{i<j} D_ij*[y_i==y_j] + beta*(L_B-L_A)^2.   (the QUBO's objective, without penalties)"""
    a = inst.alpha if alpha is None else alpha
    b = inst.beta if beta is None else beta
    n = inst.n
    comp = sum(inst.dist(i + 1, j + 1) for i in range(n) for j in range(i + 1, n) if y[i] == y[j])
    la, lb = loads(inst, y)
    return a * comp + b * (lb - la) ** 2


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2))
