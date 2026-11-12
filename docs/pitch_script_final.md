# Final 2:45 Video Pitch & Demo Script

Target Duration: **2 minutes 45 seconds** (Hard ceiling: 3:00).  
Total Spoken Word Count: **380 words** (Must remain under 420 words).

---

## Timed Presentation Script

| Time | Slide / Visual | Speaker | Spoken Script | Word Count |
|---|---|---|---|---|
| **0:00–0:25** | Title slide & Last-Mile Map | **USAMA** | Delivery dispatchers face an NP-hard problem daily: assigning delivery stops between limited-capacity vans while keeping driving distance short and driver workload fair. We developed a hybrid quantum-classical pipeline using Qiskit to solve customer assignment for two identical vans serving six delivery stops. | 45 |
| **0:25–0:55** | Formulation slide (Qubits & QUBO) | **FATIMA** | We encode each customer's van assignment as a binary variable and map each to a decision qubit. Capacity bounds are enforced by adding six binary slack variables, producing a 12-qubit QUBO with a 50.0 constraint penalty. Our exact eigensolver verifies that the QUBO ground state perfectly reproduces the classical golden optimum: stops 2 and 3 to Van B, the rest to Van A. | 63 |
| **0:55–1:20** | Architecture & Circuit (`qaoa_circuit.png`) | **FATIMA** | We solve the assignment using QAOA with depth-57 ansatz circuits on Qiskit's Aer statevector simulator, optimizing angles via COBYLA. At depth $p=1$, the optimum is sampled with up to 4.49% probability, rising to 7.32% at $p=3$, with 42.8% of samples strictly feasible. | 44 |
| **1:20–1:45** | Terminal Demo: `python -m src.run_demo` | **KHATTAK** | One command reproduces our entire workflow. Running the demo executes exact classical search, runs 15 QAOA instances in 42 seconds, and evaluates true route lengths with exact TSP. Brute force finds the exact minimum tour of 41.50 kilometers in under 2 milliseconds, matching our quantum ground state. | 47 |
| **1:45–2:15** | Evaluation Plots (`convergence.png`, `pareto.png`) | **KHATTAK** | Post-processing extracts valid tours instantly. Our Pareto analysis reveals the direct operational trade-off: increasing the workload balance weight $\beta$ equalizes van packages but increases total driving distance. QAOA reliably identifies low-energy feasible clusters that feed directly into vehicle routing. | 40 |
| **2:15–2:45** | Limitations & Closing Slide | **USAMA** | We remain honest about current bounds: 12 qubits is classically trivial, and simulator QAOA claims no quantum advantage today. However, this hybrid cluster-first route-second framework establishes a verified template for scaling logistics onto future quantum hardware. Thank you. | 41 |

*(Total Spoken Words: 280 words — well under the 420-word budget, allowing a comfortable, deliberate speaking pace of ~110–120 words per minute).*

---

## 20-Second Terminal Demo Plan

- **Command to run:**
  ```bash
  python -m src.run_demo
  ```
- **What to show on screen:**
  1. Terminal prompt typing `python -m src.run_demo`.
  2. The stage markers completing:
     - `[1/3] Running classical baselines... Done (0.002s)`
     - `[2/3] Running QAOA quantum solver across reps (1, 2, 3)... Done`
     - `[3/3] Generating evaluation tables and figures... Done`
  3. The final clean summary table displaying:
     - Exact optimum tour length: `41.50 km`
     - QAOA best assignment matching golden: `(0, 1, 1, 0, 0, 0)`
     - Qubit count: `12 qubits`
     - Probabilities by $p$: $p=1 (4.5\%), p=2 (4.6\%), p=3 (7.3\%)$
- **What to trim/speed up:**
  - Fast-forward or edit out the 40 seconds of COBYLA optimization iterations so the terminal stage runs in $\approx 15$ seconds on video.

---

## Rehearsal Checklist

- [ ] **Timing:** Confirm total recorded time is between 2:30 and 2:45 (under 3:00 hard limit).
- [ ] **Numbers:** Verify spoke numbers match `results/summary.json` (41.50 km tour, 12 qubits, 7.3% max $P(\text{optimum})$ at $p=3$, 42s runtime).
- [ ] **Audio:** Crisp microphone, balanced levels across all three speakers (USAMA, FATIMA, KHATTAK).
- [ ] **Visuals:** Slides rendered at 1080p; terminal text font size $\ge 18\text{pt}$ for readability.
- [ ] **Upload:** Upload MP4 to Google Drive $\to$ Set permissions to *"Anyone with the link can view"* $\to$ Test link in an incognito window.
