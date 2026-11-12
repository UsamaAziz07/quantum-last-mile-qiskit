# 05 — DEFENSE CHEAT SHEET (everyone should be able to answer these simply)

**Plain-English concepts**
- **Qubit:** a quantum bit; before measuring it can be a mix of 0 and 1. Here: one qubit = one customer's van choice.
- **QUBO:** "Quadratic Unconstrained Binary Optimisation": minimise a function made of 0/1 variables with squares and pairwise products. Constraints are turned into penalty terms.
- **Ising Hamiltonian:** the QUBO rewritten with ±1 spins; its lowest-energy state = best solution. Quantum circuits can act on it directly.
- **QAOA:** alternate two operations p times — a "cost" step that favours good solutions and a "mixer" step that explores — with angles tuned by a classical optimiser. Output: a probability distribution over bitstrings; we hope the best ones are most likely.
- **Slack variables:** extra bits that turn "load ≤ capacity" into an equation so it fits a QUBO.
- **Penalty weight:** how strongly we punish rule violations; too small → infeasible answers, too large → flat, hard landscape.
- **Hybrid:** quantum circuit + classical optimiser loop; classical code also does exact routing.

**Likely judge questions**
1. *Why quantum for 6 customers?* Not needed practically — brute force is instant. Goal is a correct, validated mapping that shows the method; it scales conceptually to bigger sizes where classical search explodes, but we claim no speedup.
2. *How do you know the result is right?* Brute force over all 64 assignments + exact TSP; NumPyMinimumEigensolver on the same QUBO gives the same optimum.
3. *Why QAOA?* Designed for combinatorial optimisation; QUBO maps directly to its cost Hamiltonian.
4. *Why was the answer not always optimal?* Shallow depth, local minima in the optimiser, probabilistic sampling, penalty tuning — we report probability of optimum and gap.
5. *Why a proxy objective?* True route length (TSP) isn't quadratic; compactness proxy is, so we use hybrid: quantum assignment, classical exact routing; we measure the true length afterward.
6. *What did the quantum part really do?* Produced the assignment distribution we decode and evaluate — it is the solver of the assignment stage.
7. *Would it run on real hardware?* Possibly but noise and circuit depth (all-to-all couplings, slack qubits) would degrade results; we only simulated.
8. *How does it scale?* Qubits ≈ n + slack bits (K=2); K vans with one-hot → n·K qubits; simulation cost doubles per qubit.
9. *What would you do next?* More vans, time windows, real road distances, warm-start QAOA, hardware runs, noise study.
10. *Did you use AI?* Yes — AI assistants helped write code and docs; credited in README; we reviewed and can explain every component.
