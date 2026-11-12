# 06 — TEAM PROMPTS: USAMA · FATIMA · KHATTAK (3 parallel AIs, one synced codebase)

**Usama is the GitHub owner:** he creates the repo (U0), does the final release (U4) and submits the form. Khattak does integration (K3).

**Why this won't break:** each person owns *different files*, all code imports one frozen `src/contract.py`, and the pieces talk only through 3 JSON files with fixed schemas. `tools/check_contract.py` tells you in 1 second if anything is out of sync. A golden answer (`contract/golden_classical.json`) proves the code is right.

## 0. Setup (everyone, 10 min)
1. Download `qlogistics_skeleton.zip`, unzip to a folder called `qlogistics`.
2. **Antigravity:** File → Open Folder → `qlogistics` (the whole folder is the "attachment"; the agent reads the files itself). **Codex:** open a terminal in the folder and run `codex` (or the IDE extension). If you only have a chat AI (no folder access), attach the files listed under each prompt.
3. Every prompt below starts with the same *preamble*. Copy prompts exactly; replace nothing except `<...>`.
4. **Quota tips:** one prompt at a time; paste error text instead of explaining; if Antigravity runs out, paste the same prompt into Codex (all state is in the files, so tools are interchangeable).
5. Python 3.10–3.12 on every machine. Fatima sends the exact Qiskit versions (her `requirements.txt`) as soon as F1 finishes — others install from it.

### Ownership (never edit someone else's files)
| Person | Owns | Role |
|---|---|---|
| **Usama** | `src/classical.py`, `tests/test_classical.py`, `docs/architecture.*`, `docs/make_report.py`, `docs/Report.docx`, classical result JSONs | **GitHub repo + final release + form submission**, classical baselines, diagram, report |
| **Fatima** | `src/qubo_model.py`, `src/quantum_solver.py`, `tests/test_quantum.py`, `requirements.txt`, `docs/quantum_notes.md`, `docs/pitch_script_final.md`, quantum result files | Quantum (QAOA) + pitch script + video narrator |
| **Khattak** | `src/evaluate.py`, `src/run_demo.py`, `tests/test_pipeline.py`, `README.md`, `demo.ipynb`, `.gitignore`, results tables/figures | Evaluation + integration (merge and run everything) |

---
## 1. USAMA — GitHub owner, classical baselines, diagram, report

### U0 — GitHub setup (Usama only, BEFORE Fatima and Khattak start coding, 10 min)
Create an empty **public** GitHub repo `quantum-last-mile-qiskit`; add Fatima and Khattak as collaborators (Settings → Collaborators). Then in the unzipped folder:
```bash
git init && git add . && git commit -m "Skeleton + frozen contract"
git branch -M main
git remote add origin https://github.com/<usama-username>/quantum-last-mile-qiskit.git
git push -u origin main
```
Message the team the repo URL. Fatima and Khattak then run `git clone <that url>` and work inside that clone (or use the zip if Git is a hassle — see Section 5). Then start U1.


### U1 — Classical baselines (start now, ~45 min)
**Attach/open:** whole folder (needs `AGENTS.md`, `01_PROJECT_SPEC.md`, `src/contract.py`, `contract/golden_classical.json`).
```text
I am USAMA. Read AGENTS.md, 01_PROJECT_SPEC.md, src/contract.py and contract/golden_classical.json first.
You may edit ONLY: src/classical.py, tests/test_classical.py, results/classical_reference.json, results/pareto_classical.json. Never touch other files.
Implement src/classical.py with the exact entry points in AGENTS.md. Pure Python standard library only (no qiskit). Import Instance, load_instance, all_assignments, canonical, loads, is_feasible, model_objective, write_json from src.contract — do not duplicate their logic.
1) route_length(inst, customers): exact shortest tour depot->customers->depot by brute-force permutations; return (length, order). Empty list -> (0.0, []).
2) evaluate_assignment(inst, y): dict with assignment(list), feasible, model_objective, true_route_length (sum of both vans' exact tours), routes {"A":[...],"B":[...]}, loads [L_A, L_B].
3) brute_force(inst): enumerate all assignments, keep canonical + feasible ones, return best-by-model_objective plus the full list; time it with time.perf_counter (runtime_s).
4) greedy(inst): sweep heuristic — sort customers by polar angle around the depot; for every cut of that circular order into two groups, keep feasible splits; choose lowest model_objective. Must return a feasible result.
5) simulated_annealing(inst, seed=42): single-bit flips, energy = model_objective + 1000*(max(0,L_A-Q)+max(0,L_B-Q)), geometric cooling, 3000 steps, deterministic; return best feasible found.
6) pareto_sweep(inst, betas): for each beta find the exact optimum among feasible assignments using model_objective(inst, y, beta=b); rows {beta, assignment, loads, model_objective, true_route_length}.
7) run_classical(inst=None): build and write results/classical_reference.json (schema in AGENTS.md: optimum_model, optimum_true, methods [brute_force, greedy, simulated_annealing], all_feasible = the 13 canonical feasible rows) and results/pareto_classical.json (betas 0,0.05,0.1,0.2,0.3,0.5,1,2). `python -m src.classical` runs it and prints a small table.
8) tests/test_classical.py: brute force reproduces contract/golden_classical.json (assignment (0,1,1,0,0,0), objective 44.7691, true length 41.4972, 13 canonical feasible); route_length hand-checked cases; greedy and SA are feasible; all outputs JSON-serialisable.
Finish only when all pass: pytest tests/test_classical.py -q ; python -m src.classical ; python tools/check_contract.py. Reply with 5 lines max: what was done + any problem.
```
**When done (git):**
```bash
git add src/classical.py tests/test_classical.py results/classical_reference.json results/pareto_classical.json
git commit -m "Usama: classical baselines" && git pull --rebase && git push
```
(or `python tools/pack.py usama` and send the zip to Khattak).

### U2 — Architecture diagram (parallel with U1, ~20 min)
**Attach:** `01_PROJECT_SPEC.md` (Mermaid block inside).
```text
I am USAMA. Read AGENTS.md and the Mermaid architecture block in 01_PROJECT_SPEC.md. Edit ONLY docs/architecture.mmd, docs/make_architecture.py, docs/architecture.png.
Create docs/architecture.mmd (the Mermaid source, cleaned up) and docs/make_architecture.py that draws the same pipeline as a clean left-to-right box-and-arrow diagram with matplotlib only (no network), classical blocks in blue, quantum blocks (QUBO->Ising, QAOA circuit on Aer simulator) in purple, a loop arrow between QAOA and the COBYLA optimiser, two input branches (instance JSON) and the evaluation block merging quantum and classical baseline outputs. Save a 200-dpi docs/architecture.png with readable fonts for a Word report. Run it and show me the result.
```

### U3 — Report as .docx (start AFTER integration gives `results/summary.json`; ~40 min)
**Attach:** `03_REPORT_OUTLINE.md`, `01_PROJECT_SPEC.md`, `05_DEFENSE_QA.md`, and the integrated `results/` folder + `docs/architecture.png`.
```text
I am USAMA. Read 03_REPORT_OUTLINE.md, 01_PROJECT_SPEC.md, results/summary.json, results/results.csv, results/quantum_results.json, results/classical_reference.json, docs/quantum_notes.md. Edit ONLY docs/make_report.py and docs/Report.docx.
Write docs/make_report.py (python-docx; pip install python-docx if missing) that builds docs/Report.docx, 6-8 pages, following 03_REPORT_OUTLINE.md section by section. EVERY number (qubits, probabilities, gaps, runtimes, route lengths) must be read from the results JSON/CSV at build time — no typed numbers — so the report always matches the repo. Embed docs/architecture.png and the figures in results/*.png with captions. Include the instance table, QUBO description, results table, classical comparison, an HONEST limitations section (proxy objective, slack qubits, penalty tuning, p-depth, simulator only, tiny instance classically trivial, no speedup claim, anything that failed — read it from the real results), originality (hybrid cluster-first/route-second + Pareto balance trade-off), credits (Qiskit docs; AI assistants used), repo link placeholder https://github.com/<usama-username>/quantum-last-mile-qiskit and video link placeholder. Plain beginner-friendly language. Run it and tell me the page count.
```

### U4 — GITHUB final release for judges (after Khattak's integration passes AND Fatima's video link + your report exist)
**Attach/open:** the integrated repo folder.
```text
I am USAMA, final release manager. In this release step ONLY, I may edit README.md, but only to insert links and fix setup/run wording; do not change anything else in it. The code is integrated. Do these steps in order and show each result; stop and tell me if a step fails:
1) Run python tools/check_contract.py, pytest -q, and python -m src.run_demo. Confirm results/ now contains results.csv, summary.json, convergence.png, probability_histogram.png, route_map.png, pareto.png, comparison.png, qaoa_circuit.png, classical_reference.json, pareto_classical.json, quantum_results.json.
2) Update README.md: check that the results table matches results/summary.json (if not, STOP and tell me — Khattak owns those numbers); insert the Report link <REPORT_LINK_OR_docs/Report.docx> and the video link <VIDEO_LINK>; make sure Setup + Run sections are correct; make sure a "Credits" line says Qiskit documentation was used as reference and AI coding assistants (Antigravity/Codex) assisted with code.
3) Fresh-clone test: in a temporary directory run git clone <REPO_URL> test_clone; cd test_clone; python -m venv .venv; activate; pip install -r requirements.txt; python -m src.run_demo; pytest -q. Everything must pass from the clone, not from the working folder. If it fails, fix only the cause and repeat.
4) Check hygiene: no secrets or tokens, no huge files, .gitignore excludes .venv, results/ and docs/ files are committed, README renders.
5) Commit with a clear message, then git push origin main, then git tag v1.0-submission && git push origin v1.0-submission.
6) Confirm the repo is PUBLIC and print the final URL, the last commit hash and timestamp (must be before 11:59pm on 12 Nov 2026). After this push make NO further commits.
If git push asks for authentication and you cannot do it, print the exact commands for me to run myself.
```
**Manual fallback if the agent can't push:**
```bash
git add -A && git commit -m "Final submission" && git push origin main
git tag v1.0-submission && git push origin v1.0-submission
```

---
## 2. FATIMA — QUBO + QAOA (quantum core), notes, script

### F1 — Environment + QUBO model (start now; send versions to team within 30–40 min)
**Attach/open:** whole folder.
```text
I am FATIMA. Read AGENTS.md, 01_PROJECT_SPEC.md, src/contract.py and contract/golden_classical.json first.
You may edit ONLY: src/qubo_model.py, tests/test_quantum.py, requirements.txt, docs/quantum_notes.md. Never touch other files. Do NOT import src/classical.py anywhere.
Step 1 (environment): create a venv (Python 3.10-3.12) and install qiskit, qiskit-aer, qiskit-algorithms, qiskit-optimization, numpy, scipy, matplotlib, pandas, pytest. Verify these imports run: from qiskit_algorithms import QAOA, NumPyMinimumEigensolver; from qiskit_algorithms.optimizers import COBYLA; from qiskit_optimization import QuadraticProgram; from qiskit_optimization.algorithms import MinimumEigenOptimizer; from qiskit_optimization.converters import QuadraticProgramToQubo; and a Sampler (qiskit.primitives StatevectorSampler or Sampler, whichever works with qiskit-algorithms). If the newest qiskit conflicts with qiskit-algorithms, pin qiskit<2 and matching versions. Write the exact working versions with == pins into requirements.txt and print them for me to send to my teammates.
Step 2 (src/qubo_model.py): implement build_qp(inst), to_qubo(qp), decode(x, n) per AGENTS.md. Variables y_1..y_n binary (name them y0..y5). Objective = inst.alpha * sum_{i<j} D_ij * (y_i*y_j + (1-y_i)*(1-y_j)) + inst.beta * (2*L_B - D)^2 where L_B = sum(d_i*y_i), D = total demand — expanded as linear+quadratic terms WITH the constant, so qp.objective.evaluate(y) == contract.model_objective(inst,y) exactly for ALL 64 y. Constraints: L_B <= capacity and L_B >= D - capacity (two linear constraints). to_qubo uses QuadraticProgramToQubo (choose and document a penalty; return it); report the number of qubits after conversion (expected about 12). decode keeps the first n entries as the assignment tuple (slack variables ignored).
Step 3 (tests/test_quantum.py): (a) qp.objective.evaluate(y) == model_objective for all y; (b) the constraints accept exactly the feasible y (contract.is_feasible); (c) solving the QUBO with NumPyMinimumEigensolver through MinimumEigenOptimizer then decode gives canonical == (0,1,1,0,0,0) (golden); (d) print qubit count. Run pytest tests/test_quantum.py -q. Reply in 5 lines max with the pinned versions and qubit count.
```
**Then immediately message the team:** the contents of `requirements.txt`.
**Git:** `git add src/qubo_model.py tests/test_quantum.py requirements.txt` → commit → `git pull --rebase` → `git push`.

### F2 — QAOA runner (after F1, ~60 min)
```text
I am FATIMA. You may edit ONLY: src/quantum_solver.py, tests/test_quantum.py, results/quantum_results.json, results/qaoa_circuit.png. Read AGENTS.md (schema for quantum_results.json) and contract/sample_quantum_results.json.
Implement src/quantum_solver.py: run_all(inst=None, reps_list=(1,2,3), seeds=(0,1,2,3,4), maxiter=200) and a __main__ so `python -m src.quantum_solver` works. Use src.qubo_model.build_qp/to_qubo. Find the optimum yourself with contract helpers (all_assignments, is_feasible, model_objective, canonical) — do not import classical.py.
For each (reps, seed): run qiskit_algorithms QAOA(sampler=<exact statevector sampler>, optimizer=COBYLA(maxiter=maxiter), reps=reps, initial_point=<random, seeded by seed>, callback recording the energy history) on the QUBO operator. Get the final probability distribution over bitstrings. IMPORTANT: Qiskit bitstrings are little-endian (qubit 0 = rightmost character): convert so that in our output the bitstring reads LEFT-to-RIGHT in variable order (first n characters = y0..y5, slack after) and verify with a unit test. For each run record per schema: final_energy, best_feasible_assignment (highest-probability state whose first-n bits are feasible per contract.is_feasible, else null) and its model_objective, prob_feasible (probability mass of feasible states), prob_optimum (mass on the optimum OR its mirror image), runtime_s, energy_history, top_samples (top 8 states plus the 2 most likely infeasible ones, with bitstring, assignment, prob, feasible, model_objective or null).
Also record: num_qubits, penalty, exact_eigen {assignment, energy, matches_model_optimum} from NumPyMinimumEigensolver, and circuit {depth, num_qubits, image} for the reps=1 ansatz drawn (decomposed) and saved to results/qaoa_circuit.png.
The whole run must finish in under 4 minutes; if too slow lower maxiter/seeds and tell me. Be honest: do not tune results to look good; if QAOA p=1 has low prob_optimum, that is a valid finding. Write results/quantum_results.json via contract.write_json. Verify: python -m src.quantum_solver ; python tools/check_contract.py ; pytest tests/test_quantum.py -q. Reply in 6 lines max: best prob_optimum per reps, prob_feasible, runtime.
```
**Git:** add `src/quantum_solver.py tests/test_quantum.py results/quantum_results.json results/qaoa_circuit.png`.

### F3 — Notes, pitch script, video (notes now; script/video after integration)
**Attach:** `04_PITCH_AND_DEMO_SCRIPT.md`, `05_DEFENSE_QA.md`, `results/summary.json` (later).
```text
I am FATIMA. Edit ONLY docs/quantum_notes.md and docs/pitch_script_final.md. Read 01_PROJECT_SPEC.md, 04_PITCH_AND_DEMO_SCRIPT.md, 05_DEFENSE_QA.md, src/qubo_model.py, src/quantum_solver.py and (if present) results/summary.json.
1) docs/quantum_notes.md: a 1-page beginner explanation of exactly what OUR code does: variables->qubits, QUBO, slack qubits, penalty, Ising Hamiltonian, QAOA layers, COBYLA loop, how probabilities are read, what p means, and 6 likely judge questions with 2-sentence answers specific to our implementation.
2) docs/pitch_script_final.md: the final 2:45 script (timed table like 04_PITCH_AND_DEMO_SCRIPT.md) with the REAL numbers from results/summary.json, speaker labels (USAMA / FATIMA / KHATTAK — each speaks about their own part), a 20-second terminal-demo plan (what command, what to show, what to trim), and a rehearsal checklist. Keep under 420 words total spoken.
```
**Video:** record with OBS/Zoom (screen + voice), ≤ 3:00, upload to Drive → "Anyone with the link", test in incognito.

---
## 3. KHATTAK — evaluation, integration

### K1 — evaluate.py (start now using the sample files; ~50 min)
**Attach/open:** whole folder (uses `contract/sample_*.json` as stand-in data).
```text
I am KHATTAK. Read AGENTS.md, 01_PROJECT_SPEC.md, src/contract.py, and the files contract/sample_classical_reference.json, contract/sample_pareto_classical.json, contract/sample_quantum_results.json (these are MOCK data with the real schema).
You may edit ONLY: src/evaluate.py, tests/test_pipeline.py, results/results.csv, results/summary.json and figure PNGs in results/ (not qaoa_circuit.png). Matplotlib + pandas only.
Implement src/evaluate.py: main(results_dir="results", mock=False) — if mock=True or the real JSON files are missing, read the contract/sample_*.json files instead (print a loud warning "MOCK DATA"). CLI: python -m src.evaluate [--mock]. It reads ONLY the three JSON files (never imports classical.py or quantum_solver.py).
Outputs: (a) results/results.csv: rows for each classical method (brute_force, greedy, simulated_annealing) and for QAOA per reps (best run, median run, mean prob_optimum) with columns method, assignment, feasible, model_objective, true_route_length, gap_to_optimum_pct (vs optimum_true), prob_optimum, prob_feasible, runtime_s. (b) results/summary.json: num_qubits, circuit_depth, optimum_model_assignment, optimum_true_length, best_qaoa_assignment, best_qaoa_true_length, qaoa_gap_pct, prob_optimum_by_reps (mean and max), prob_feasible_by_reps, exact_eigen_match, brute_force_runtime_s, qaoa_total_runtime_s, mock(bool). (c) figures, 200 dpi, readable, titled: results/convergence.png (energy history by reps), results/probability_histogram.png (top samples of the best run: optimum green, other feasible blue, infeasible red), results/route_map.png (depot + 6 customers, optimum routes in two colours, labelled), results/pareto.png (beta vs true route length and load imbalance), results/comparison.png (bar chart of true route length per method).
tests/test_pipeline.py: evaluate.main(mock=True) produces all files. Run it and show me the figures' file names. Reply in 5 lines max.
```
**Git:** `git add src/evaluate.py tests/test_pipeline.py` (+ generated results only after real data exists).

### K2 — run_demo, README, Colab notebook (~45 min; can start in parallel, finish after integration)
**Attach:** `01_PROJECT_SPEC.md`, `03_REPORT_OUTLINE.md`, `AGENTS.md`.
```text
I am KHATTAK. Edit ONLY: src/run_demo.py, README.md, demo.ipynb, tests/test_pipeline.py, .gitignore. Read AGENTS.md, 01_PROJECT_SPEC.md, 03_REPORT_OUTLINE.md.
1) src/run_demo.py: main() = from src.classical import run_classical; from src.quantum_solver import run_all; from src.evaluate import main as evaluate_main — run them in that order, time each stage, then print a clean summary table (optimum route length, QAOA best, gap %, prob_optimum per p, prob_feasible, qubits, total time). `python -m src.run_demo` must work from a fresh clone. Catch ImportError and print a clear "pip install -r requirements.txt" message. Add flag --fast (reps 1 and 2 seeds only) for quick checks.
2) README.md for judges: title, 3-line summary, problem + motivation, formulation (variables, objective, constraints, instance), why QAOA (hybrid cluster-first / route-second), architecture (embed docs/architecture.png), repo layout, SETUP (python -m venv, pip install -r requirements.txt) and ONE run command, expected output sample, results table (read real numbers from results/summary.json after the demo runs — paste them in), classical/exact comparison, honest limitations, team (Usama, Fatima, Khattak), credits (Qiskit docs; AI assistants used: Antigravity/Codex), links placeholders for report + video. Keep it skimmable.
3) demo.ipynb for Google Colab: cell 1 = !git clone https://github.com/<usama-username>/quantum-last-mile-qiskit.git ; cd into it; cell 2 = !pip install -q -r requirements.txt ; cell 3 = !python -m src.run_demo ; cell 4 = display the PNGs in results/ and print results/summary.json. Valid .ipynb JSON.
4) .gitignore for Python/venv/zip files. Report in 5 lines.
```

### K3 — INTEGRATION (when Usama + Fatima have pushed, ~30 min)
**Do by hand first:**
```bash
git pull
pip install -r requirements.txt
python tools/check_contract.py --mock       # contract itself fine
python -m src.classical                     # Usama's part
python -m src.quantum_solver                # Fatima's part
python tools/check_contract.py              # real files match schemas AND golden answer
python -m src.run_demo
pytest -q
```
**If ALL pass → commit and push the regenerated results, then tell Usama and Fatima "integration passed":**
```bash
git add results README.md demo.ipynb && git commit -m "Khattak: integrated real results" && git pull --rebase && git push
```
**If anything fails, use the fix prompt below instead. If something fails → paste into your agent:**
```text
I am KHATTAK, integration lead. The integrated project fails. Read AGENTS.md. Here is the exact command and full error output:
<PASTE COMMAND AND TRACEBACK>
Diagnose which owner's file is responsible (see the ownership table). Do NOT edit that file yourself. Write a fix request for the owner: file name, line, exact problem, and the exact change needed, in under 8 lines I can paste to their AI. Only if the problem is in MY files (src/evaluate.py, src/run_demo.py, README.md, demo.ipynb, tests/test_pipeline.py) fix it directly and re-run the failing command.
```
**Owner-fix prompt (Usama/Fatima paste this with Khattak's message):**
```text
I am <NAME>. Read AGENTS.md. Integration found a problem in my file: <PASTE KHATTAK'S FIX REQUEST>. Edit ONLY my own files. Keep all function signatures and JSON schemas unchanged. After the fix run: <my tests> and python tools/check_contract.py. Reply in 3 lines.
```

---
## 4. Timeline (start ≈ now)
| T+ | Usama | Fatima | Khattak |
|---|---|---|---|
| 0:00 | **U0 create repo, share URL** | Clone repo | Clone repo, start K1 |
| 0:15 | U1 + U2 | F1 → **send versions** | K1 |
| 1:30 | push U1/U2 | F2 | K2 (README draft, run_demo) |
| 3:00 | push | push F2, start F3 notes | K3 integration (**checkpoint**) |
| 4:00 | fix requests | fix requests | fix loop → real run, push results |
| 4:30 | U3 report | F3 script | finalise README numbers |
| 6:00 | report done | record video (all three speak) | upload video, send link to Usama |
| 7:30 | **U4 GitHub release + fresh clone test** | | check links in incognito |
| 8:30 | **Usama submits the form** | everyone checks links | |
| **9:30pm** | Hard stop on changes | | Form submitted by 10:30pm |

**If behind:** QAOA with reps 1–2 and 3 seeds is enough; skip SA and notebook; keep golden check, README, report, video.

## 5. How to combine files from different computers
**Path A (Git, preferred):** everyone pushes ONLY their own files to `main` (`git pull --rebase` before `git push`). Since files never overlap, there are no merge conflicts.
**Path B (no Git for a person):** run `python tools/pack.py <name>` → sends `<name>_deliverable.zip` (only their files). Khattak unzips it **over** the repo folder (nothing gets overwritten because owners differ), then runs K3.
**Always before sending:** run `python tools/check_contract.py` (should print CONTRACT OK or "not found yet") and tell Khattak your Python + Qiskit version (`python --version`, `pip show qiskit`).
**Never:** edit `src/contract.py`, `config/instance.json`, `contract/*`, `tools/*`, `AGENTS.md`. If you think they're wrong, tell the others in the chat — one person changes it and re-sends to all.

## 6. Final submission checklist (Usama submits the form)
- [ ] Repo public, README has setup + single run command, fresh-clone test passed, tag `v1.0-submission`
- [ ] `docs/Report.docx` includes architecture diagram, results, classical comparison, limitations, repo + video links
- [ ] Video ≤ 3:00 on Drive, "Anyone with the link", opens in incognito
- [ ] Last commit before 11:59pm 12 Nov 2026
- [ ] Form submitted https://forms.gle/jSRrXaHkjVb7G7AK8 — screenshot confirmation
