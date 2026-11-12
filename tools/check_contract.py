"""Integration safety net. Run any time:   python tools/check_contract.py [--mock]

--mock  validates the sample files in contract/ (use while the real results don't exist yet)
default validates results/*.json produced by the real code and compares them to contract/golden_classical.json
Exit code 0 = OK, 1 = problems (printed).
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.contract import load_instance, canonical, model_objective, is_feasible  # noqa: E402

problems = []
def need(d, keys, where):
    for k in keys:
        if k not in d: problems.append(f"{where}: missing key '{k}'")

def check_classical(path):
    d = json.loads(Path(path).read_text())
    need(d, ["instance", "optimum_model", "optimum_true", "methods", "all_feasible"], "classical")
    row = ["assignment", "model_objective", "true_route_length", "routes", "loads"]
    for k in ("optimum_model", "optimum_true"):
        if k in d: need(d[k], row, f"classical.{k}")
    names = {m.get("method") for m in d.get("methods", [])}
    for must in ("brute_force", "greedy"):
        if must not in names: problems.append(f"classical.methods: missing '{must}'")
    for m in d.get("methods", []):
        need(m, ["method", "assignment", "feasible", "model_objective", "true_route_length", "runtime_s"], "classical.methods[]")
    g = json.loads((ROOT / "contract" / "golden_classical.json").read_text())
    if "optimum_model" in d:
        if canonical(d["optimum_model"]["assignment"]) != canonical(g["optimum_model"]["assignment"]):
            problems.append("classical: optimum_model assignment differs from golden")
        if abs(d["optimum_model"]["model_objective"] - g["optimum_model"]["model_objective"]) > 1e-6:
            problems.append("classical: optimum_model objective differs from golden")
    if "optimum_true" in d and abs(d["optimum_true"]["true_route_length"] - g["optimum_true"]["true_route_length"]) > 1e-6:
        problems.append("classical: optimum_true length differs from golden")
    if len(d.get("all_feasible", [])) != g["n_feasible_canonical"]:
        problems.append(f"classical: all_feasible should hold {g['n_feasible_canonical']} canonical feasible assignments")

def check_pareto(path):
    d = json.loads(Path(path).read_text())
    if not isinstance(d, list) or not d: problems.append("pareto: must be a non-empty list"); return
    for r in d: need(r, ["beta", "assignment", "loads", "model_objective", "true_route_length"], "pareto[]")

def check_quantum(path):
    d = json.loads(Path(path).read_text())
    need(d, ["instance", "num_qubits", "penalty", "exact_eigen", "circuit", "runs"], "quantum")
    if "exact_eigen" in d: need(d["exact_eigen"], ["assignment", "energy", "matches_model_optimum"], "quantum.exact_eigen")
    if "circuit" in d: need(d["circuit"], ["depth", "num_qubits", "image"], "quantum.circuit")
    if not d.get("runs"): problems.append("quantum: 'runs' is empty")
    for r in d.get("runs", []):
        need(r, ["reps", "seed", "optimizer", "maxiter", "final_energy", "best_feasible_assignment", "best_feasible_model_objective",
                 "prob_feasible", "prob_optimum", "runtime_s", "energy_history", "top_samples"], "quantum.runs[]")
        for s in r.get("top_samples", []):
            need(s, ["bitstring", "assignment", "prob", "feasible", "model_objective"], "quantum.runs[].top_samples[]")

def main():
    mock = "--mock" in sys.argv
    base = ROOT / ("contract" if mock else "results")
    names = ("sample_classical_reference.json", "sample_pareto_classical.json", "sample_quantum_results.json") if mock else \
            ("classical_reference.json", "pareto_classical.json", "quantum_results.json")
    inst = load_instance()
    g = json.loads((ROOT / "contract" / "golden_classical.json").read_text())
    if canonical(g["optimum_model"]["assignment"]) != tuple(g["optimum_model"]["assignment"]): problems.append("golden not canonical")
    if abs(model_objective(inst, g["optimum_model"]["assignment"]) - g["optimum_model"]["model_objective"]) > 1e-6 or not is_feasible(inst, g["optimum_model"]["assignment"]):
        problems.append("contract.py disagrees with golden file (someone changed contract.py or the instance!)")
    for nm, fn in zip(names, (check_classical, check_pareto, check_quantum)):
        p = base / nm
        if p.exists(): fn(p); print(f"checked {p.relative_to(ROOT)}")
        else: print(f"(not found yet) {p.relative_to(ROOT)}")
    if problems:
        print("\nPROBLEMS:"); [print(" -", x) for x in problems]; sys.exit(1)
    print("\nCONTRACT OK")

main()
