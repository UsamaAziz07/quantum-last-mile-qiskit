# 00 — HANDOFF SUMMARY (paste this at the start of any new chat/tool)

## Context
Team of beginners in **Qiskit Fall Fest 2026 Hackathon** (Quantum Optimization Challenge). Deadline **12 Nov 2026, 11:59pm**, ~10 h left when started. No commits after deadline.
Submission (all four): GitHub repo (README, reproducible Qiskit code) · Report .docx (results, classical/exact comparison, honest limitations, architecture diagram) · ≤3-min video (Drive, anyone-with-link) · Form: https://forms.gle/jSRrXaHkjVb7G7AK8
Rubric (100): A Problem validity 20 · B Meaningful quantum use 25 · C Implementation & validation 25 · D Originality 15 · E Presentation & defense 15.
Dos: small simulator instance, quantum does real work, README, honesty about limits, links work. Don'ts: other domains, copied code (credit reused), video >3 min, late commits.

## Decisions made
- **Domain:** Logistics & Transportation. **Problem:** assign 6 customers to 2 capacity-limited vans (last-mile delivery); minimise compactness-proxy distance + β·load imbalance; capacity Q=7, demands [3,2,3,1,2,1] (beta=0.1).
- **Language:** Python 3.11. **Stack:** qiskit, qiskit-aer, qiskit-algorithms, qiskit-optimization, numpy, scipy, matplotlib, pandas, pytest. **Editor:** Antigravity (build + GitHub), VS Code/Colab fallback.
- **Algorithm:** QAOA on QUBO (~12 qubits incl. slack), COBYLA, p=1–3, simulator.
- **Baselines:** brute force (64 assignments + exact TSP), greedy, NumPyMinimumEigensolver check.
- **Design:** hybrid cluster-first (quantum), route-second (classical exact).

## Files produced (all in the downloadable pack)
`ANTIGRAVITY_INSTRUCTIONS.md` (=AGENTS.md) · `01_PROJECT_SPEC.md` · `02_TASKS_PARALLEL.md` · `03_REPORT_OUTLINE.md` · `04_PITCH_AND_DEMO_SCRIPT.md` · `05_DEFENSE_QA.md` · `qlogistics_skeleton.zip` (repo skeleton: README, requirements, config/instance.json, src/ stubs with TODOs, tests/).

## Status checklist (update as you go)
- [x] Domain/problem/spec decided · [x] skeleton + instructions written
- [ ] T1 code built & pushed · [ ] diagram · [ ] report · [ ] script · [ ] video · [ ] QA · [ ] form submitted
Final numbers (fill from results/summary.json): optimum length ___ · QAOA best ___ · gap ___% · P(opt) ___ · feasibility rate ___ · qubits ___ · runtime ___

## Known risks
Qiskit version conflicts (pin versions; fallback hand-built QAOA) · QAOA may return infeasible/suboptimal states (report honestly) · Antigravity quota (one step per prompt; continue elsewhere with this file).

## Prompt to continue in a new chat
"I'm continuing a hackathon project. Read the summary below and the attached spec. Help me with: [task]. Keep answers short; I'm a beginner."

## UPDATE — team split (Usama / Fatima / Khattak)
- `06_TEAM_PROMPTS.md` holds ALL prompts (U1-U3, F1-F3, K1-K4), ownership table, integration + GitHub steps.
- Code sync: frozen `src/contract.py` + `contract/golden_classical.json` + JSON schemas; run `python tools/check_contract.py [--mock]` anytime. `python tools/pack.py <name>` zips a person's files.
- Instance now: demands [3,2,3,1,2,1], Q=7, beta=0.1, 2 clusters (east 1-3, west 4-6). Golden: model optimum y=(0,1,1,0,0,0), objective 44.7691, true route length 41.4972, 13 canonical feasible assignments. beta>=0.2 flips optimum to balanced loads (6/6) with true length 48.03 (Pareto story).
- Ownership: Usama = classical.py + diagram + Report.docx; Fatima = qubo_model/quantum_solver + notes + pitch script/video; Khattak = evaluate/run_demo/README/notebook/GitHub/integration.

- UPDATE: Usama is also the GitHub owner (U0 repo setup, U4 final release + tag + form submission). Khattak = evaluation + integration only.
