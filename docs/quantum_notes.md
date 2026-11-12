# Quantum Notes — QAOA Last-Mile Delivery Assignment

## 1. How Our Code Works (Beginner's Guide)

- **Variables $\to$ Qubits:**  
  We deliver to 6 customers with 2 identical capacity-limited vans. Each customer $i \in \{0,\dots,5\}$ is assigned to van A ($y_i = 0$) or van B ($y_i = 1$). One binary decision variable maps directly to one qubit ($6$ decision qubits $y_0 \dots y_5$).

- **QUBO Formulation (`src/qubo_model.py`):**  
  Quadratic Unconstrained Binary Optimization (QUBO) minimizes a quadratic objective of 0/1 bits. Our objective balances customer clustering compactness ($\alpha \sum_{i<j} D_{ij} [y_i = y_j]$) against van load imbalance ($\beta (L_B - L_A)^2$). We expand $[y_i = y_j] = 2y_i y_j - y_i - y_j + 1$ and $(2L_B - D)^2 = 4L_B^2 - 4DL_B + D^2$ (using $y_i^2 = y_i$) into exact linear, quadratic, and constant terms matching `contract.model_objective` across all 64 assignments.

- **Slack Qubits & Capacity Constraints:**  
  Each van has capacity $Q=7$ out of total demand $D=12$, enforcing $5 \le L_B \le 7$. In `to_qubo()`, Qiskit's `QuadraticProgramToQubo` converts these two inequalities into equalities by adding binary slack variables ($3$ bits for $L_B \le 7$ and $3$ bits for $L_B \ge 5$). This expands our 6 customer variables to **12 total qubits**.

- **Penalty Multiplier:**  
  Constraints are added into the cost objective as squared penalties multiplied by $P = 50.0$. Because the maximum objective gap across valid assignments is $\approx 35$, a penalty of 50 ensures any capacity violation produces a large energy penalty, keeping the QUBO ground state identical to the feasible optimum.

- **Ising Hamiltonian:**  
  Using $y_i = \frac{1 - Z_i}{2}$, Qiskit maps the 12-qubit QUBO into an Ising spin Hamiltonian $H_C = \sum_i h_i Z_i + \sum_{i<j} J_{ij} Z_i Z_j + \text{offset}$. Its ground state (minimum eigenvalue) is the optimal assignment.

- **QAOA Circuit & Layers ($p$ Repetitions):**  
  QAOA starts in an equal superposition $|+\rangle^{\otimes 12}$ and alternates $p$ layers of cost unitary $e^{-i \gamma H_C}$ and transverse mixer unitary $e^{-i \beta \sum X_i}$. The depth of the decomposed elementary circuit is 57 gates for $p=1$.

- **Classical COBYLA Optimization Loop:**  
  The classical COBYLA optimizer iteratively tunes the $2p$ parameters $(\vec{\gamma}, \vec{\beta})$ to minimize the expectation value $\langle H_C \rangle$ evaluated via Qiskit's `StatevectorSampler`.

- **Reading Probabilities & Endianness:**  
  Qiskit bitstrings are little-endian (qubit 0 is rightmost). Our `convert_bitstring_endianness` function reverses bitstrings to variable order left-to-right. The first 6 characters represent $y_0 \dots y_5$, while characters 6–11 represent slack bits.

- **What $p$ Means:**  
  $p$ (`reps`) is the number of QAOA alternating layers. Increasing $p$ increases theoretical approximation capacity: in our benchmarks, maximum $P(\text{optimum})$ rises from $4.49\%$ at $p=1$ to $7.32\%$ at $p=3$, and mean feasible probability increases from $37.93\%$ to $42.85\%$.

---

## 2. Six Likely Judge Questions & Answers

1. **Why do you need 12 qubits to assign just 6 customers?**  
   Each customer requires 1 decision qubit, but encoding the two van capacity constraints ($5 \le L_B \le 7$) into an unconstrained QUBO requires 6 binary slack variables. This results in 12 qubits total (6 decision + 6 slack).

2. **How did you pick the penalty factor of 50.0?**  
   The objective difference between assignments tops out around 35, so a penalty of 50.0 guarantees any capacity violation incurs an energy cost strictly greater than any distance benefit. This was verified by `NumPyMinimumEigensolver`, which cleanly recovered the golden optimum $(0,1,1,0,0,0)$.

3. **Why does QAOA not return the optimal bitstring 100% of the time?**  
   QAOA is an approximate variational heuristic at shallow depth ($p \le 3$) optimized over a non-convex classical parameter landscape with COBYLA. Its output is a probability distribution where the optimum is boosted relative to random guessing, allowing fast classical filtering of the top sampled states.

4. **How did you handle Qiskit's little-endian bitstring convention?**  
   Qiskit places qubit 0 at the rightmost end of the string, which would invert customer ordering if parsed naively. We implemented and unit-tested `convert_bitstring_endianness` to reverse the measured string into left-to-right order ($y_0 \dots y_5$), ensuring exact agreement with classical verification.

5. **Why use an unconstrained clustering QUBO instead of encoding the entire TSP tour into quantum gates?**  
   Encoding order-dependent TSP sequencing directly on quantum hardware requires $O(n^2)$ qubits and prohibitive circuit depth. Our hybrid "cluster-first, route-second" architecture lets QAOA solve the combinatorial assignment into balanced clusters, while classical exact TSP finds the van routes in 2 milliseconds.

6. **How do you verify your quantum implementation is mathematically correct?**  
   We verify that `qp.objective.evaluate(y)` matches `model_objective(inst, y)` across all 64 assignments, and `NumPyMinimumEigensolver` on the 12-qubit QUBO yields the exact golden classical assignment $(0,1,1,0,0,0)$ with objective $44.7691$.
