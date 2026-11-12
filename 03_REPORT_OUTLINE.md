# 03 — REPORT OUTLINE (.docx, ~6–8 pages) — mapped to the judging rubric

1. **Title + team + repo link + video link**
2. **Problem statement** (≈½ page) — scenario, users, objective, constraints, motivation. *(Rubric A)*
3. **Formulation** — variables, objective, constraints, test instance table (customers, coords, demands), QUBO form, qubit count. *(A, B)*
4. **Algorithm choice & mapping** — why QAOA, QUBO→Ising, circuit structure, parameters (p, optimiser, shots, seeds); alternatives considered. *(B)*
5. **Architecture diagram** — `docs/architecture.png` + 5-line explanation of each block.
6. **Implementation** — Qiskit components used, file layout, how to reproduce (3 commands), versions. *(C)*
7. **Results** — table: method | feasible | route length | gap % | runtime; QAOA probability histogram; convergence plot; route map; Pareto sweep (β). *(C)*
8. **Classical/exact comparison** — brute force optimum vs QAOA; NumPyMinimumEigensolver sanity check; greedy baseline. Explain gaps.
9. **Limitations & reflection (be honest)** — proxy objective vs true routing cost; slack qubit overhead; penalty tuning; QAOA depth/optimiser limits; simulator-only; tiny instance classically trivial; no speedup claim; noise on real hardware; what failed. *(B, C)*
10. **Originality & extensions** — hybrid cluster-first/route-second, Pareto balance trade-off; future: K>2 vans, time windows, real road data, hardware.
11. **Credits** — Qiskit documentation/tutorials adapted, libraries, AI assistants used.

Writing rules: every number must match `results/summary.json`; no claims of "quantum advantage"; short plain sentences.
