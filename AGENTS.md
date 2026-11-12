# TEAM RULES FOR ALL AI CODING AGENTS (Antigravity / Codex) — READ FIRST

Hackathon: Qiskit Fall Fest 2026, Logistics & Transportation. Deadline 12 Nov 2026 11:59pm. No commits after it.
Project: quantum (QAOA) assignment of 6 customers to 2 capacity-limited vans + exact classical baselines. Spec: `01_PROJECT_SPEC.md`.
Three people work IN PARALLEL on DIFFERENT computers. Code stays in sync ONLY through the rules below.

## Rules
1. You are building for ONE person (named in the prompt). Edit ONLY files that person owns (table below). Never edit another owner's files or frozen files.
2. `src/contract.py`, `config/instance.json`, `contract/*`, `tools/*`, `AGENTS.md` are FROZEN. Import from contract.py; never copy its logic. If you think it is wrong, STOP and tell the human.
3. Function names/signatures and JSON schemas below are fixed. Extra helper functions are fine.
4. Deterministic: fixed seeds, no network calls at runtime, runs in < 5 min on a laptop. Python 3.10-3.12.
5. Quantum part must do real work (QAOA output is what we report). Be honest in docstrings/notes about limits. Original code; credit any adapted Qiskit docs example in a comment.
6. Verify yourself: run your own tests and `python tools/check_contract.py` (and `--mock`) before saying done. Paste errors, don't hide them.
7. Be economical with tokens: don't rewrite working files; no unrelated refactors; short answers.
8. GitHub: Usama owns the repo, the final push, the tag and the form. Khattak does integration. Release-step exception: Usama's agent may edit README.md ONLY to insert report/video links.

## Ownership
| Owner | Files |
|---|---|
| USAMA (GitHub owner + classical + report) | `src/classical.py`, `tests/test_classical.py`, `results/classical_reference.json`, `results/pareto_classical.json`, `docs/architecture.*`, `docs/make_architecture.py`, `docs/make_report.py`, `docs/Report.docx` |
| FATIMA (quantum) | `src/qubo_model.py`, `src/quantum_solver.py`, `tests/test_quantum.py`, `requirements.txt`, `results/quantum_results.json`, `results/qaoa_circuit.png`, `docs/quantum_notes.md`, `docs/pitch_script_final.md` |
| KHATTAK (integration) | `src/evaluate.py`, `src/run_demo.py`, `tests/test_pipeline.py`, `README.md`, `demo.ipynb`, `.gitignore`, `results/results.csv`, `results/summary.json`, `results/*.png` (except qaoa_circuit) |

## Conventions (from contract.py)
Index 0 = depot, customers 1..n. Assignment `y` = tuple of n ints (0 = van A, 1 = van B). Vans identical -> compare with `canonical(y)`.
QUBO bitstring: first n bits = y; slack qubits after. Model objective = `contract.model_objective` (no penalties). Feasible = `contract.is_feasible`.
Golden answer (must be reproduced): model optimum = assignment (0,1,1,0,0,0), objective 44.7691, true route length 41.4972; 13 canonical feasible assignments (26 incl. mirrors). See `contract/golden_classical.json`.

## Required function entry points
USAMA `src/classical.py`
- `route_length(inst, customers) -> (float, list[int])` exact TSP depot->...->depot (brute force)
- `evaluate_assignment(inst, y) -> dict` (assignment, feasible, model_objective, true_route_length, routes{"A","B"}, loads)
- `brute_force(inst) -> dict`, `greedy(inst) -> dict`, `simulated_annealing(inst, seed=42) -> dict`, `pareto_sweep(inst, betas) -> list[dict]`
- `run_classical(inst=None) -> dict` writes `results/classical_reference.json` and `results/pareto_classical.json`; `python -m src.classical` calls it.
FATIMA `src/qubo_model.py`, `src/quantum_solver.py`
- `build_qp(inst) -> QuadraticProgram`, `to_qubo(qp) -> (qubo, converter)`, `decode(x, n) -> tuple` (first n entries -> y)
- `run_all(inst=None, reps_list=(1,2,3), seeds=(0,1,2,3,4), maxiter=200) -> dict` writes `results/quantum_results.json`, `results/qaoa_circuit.png`; `python -m src.quantum_solver` calls it. Must NOT import classical.py (use contract helpers to find the optimum).
KHATTAK `src/evaluate.py`, `src/run_demo.py`
- `evaluate.main()` reads the 3 JSON files only -> `results/results.csv`, `results/summary.json`, figures (convergence, probability_histogram, route_map, pareto, comparison_table).
- `run_demo.main()` = `run_classical()` -> `run_all()` -> `evaluate.main()` -> print summary. `python -m src.run_demo`.

## JSON schemas (validated by tools/check_contract.py; examples in contract/sample_*.json)
`classical_reference.json`: instance, optimum_model{assignment, model_objective, true_route_length, routes, loads}, optimum_true{same}, methods[{method, assignment, feasible, model_objective, true_route_length, runtime_s}] (must include "brute_force","greedy"), all_feasible[13 rows].
`pareto_classical.json`: list of {beta, assignment, loads, model_objective, true_route_length}.
`quantum_results.json`: instance, num_qubits, penalty, exact_eigen{assignment, energy, matches_model_optimum}, circuit{depth, num_qubits, image}, runs[{reps, seed, optimizer, maxiter, final_energy, best_feasible_assignment|null, best_feasible_model_objective|null, prob_feasible, prob_optimum, runtime_s, energy_history[], top_samples[{bitstring, assignment, prob, feasible, model_objective|null}]}].
