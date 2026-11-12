# Quantum Last-Mile Delivery Assignment

> **Qiskit Fall Fest 2026 — Logistics & Transportation**

We assign six delivery customers to two capacity-limited vans.
QAOA searches a QUBO assignment; exact classical routing evaluates each van.
We compare the quantum samples with brute force, greedy, and simulated annealing baselines.

## Problem and motivation

Small courier teams need routes that are short without overloading one driver. Vehicle
routing is combinatorial, so even a small dispatch decision is a useful optimization
case study. Our instance has one depot, six customers, two identical vans, total demand
12, and capacity 7 per van.

## Formulation

Each customer has one binary variable `y_i`: `0` assigns van A and `1` assigns van B.
The model minimizes

```text
alpha * sum(distance(i,j) for customers sharing a van)
  + beta * (load_B - load_A)^2
```

with both van loads at most 7. The QUBO conversion adds slack variables for the
capacity inequalities. The six assignment variables plus slack use about 12 qubits.
The QUBO is a compactness proxy; after assignment, exact brute-force TSP routes give
the true route length.

## Why QAOA?

QAOA directly maps a binary quadratic objective to an Ising Hamiltonian and alternates
problem cost and mixer layers. Our hybrid **cluster-first / route-second** design uses
QAOA for the assignment and classical exact TSP for each van. This keeps the quantum
part small, interpretable, and easy to check against exhaustive search.

## Architecture

![Architecture](docs/architecture.png)

The source diagram is maintained separately in `docs/architecture.*`; the pipeline is
instance JSON → QUBO → QAOA samples → feasibility decoding → exact routes → reports.

## Repository layout

| Path | Purpose |
|---|---|
| `src/contract.py` | Frozen instance and objective contract |
| `src/classical.py` | Exact and heuristic baselines |
| `src/qubo_model.py` | Quadratic program and QUBO conversion |
| `src/quantum_solver.py` | QAOA/Aer runs and circuit output |
| `src/evaluate.py` | CSV, summary, and figures |
| `src/run_demo.py` | End-to-end runner |
| `results/` | JSON, CSV, circuit image, and plots |
| `tests/` | Focused contract and pipeline checks |

## Setup and run

### Interactive local dashboard

After installing the requirements below, run `python app/server.py --open`, or
double-click `app/start.cmd` on Windows. You can also open
<http://127.0.0.1:8765>. The dashboard includes a 3D route view with animated vans,
solver comparisons, manual customer assignments, and real QAOA experiments with
live energy updates. New experiments stay in the app session and do not overwrite
the submission results. The map uses synthetic coordinates; van playback is
illustrative, not a traffic or travel-time simulation. Sampler measurements are
stochastic, so repeated quantum runs can differ. No extra packages or runtime
internet connection are needed. Stop the server with Ctrl+C.

### Pakistan city map

Open <http://127.0.0.1:8765/city> after starting the local dashboard. Choose Islamabad,
Lahore, or Peshawar; place a depot and delivery stops; set delivery loads; then solve.
Custom scenarios support 1–40 deliveries and 1–8 vehicles with a shared depot.
Every vehicle starts and returns there. Set vehicle capacity and each delivery's
demand. Automatic allocation assigns stops and computes each van's required load
from its route. Manual allocation preserves your stop-to-vehicle assignments,
validates capacity, and calculates the stop order. Idle vehicles remain at the depot.

Road-access checks happen before planning. When a destination is more than 150 m
from a connected road, or its nearest road cannot connect back to the depot, the
app finds a reachable road-side collection point. Every parcel remains in the plan
and capacity calculations. The map shows the requested destination with a cross,
the collection point separately, and a dashed off-road gap. Disconnected road
segments trigger a bounded nearest-candidate search (up to 32 candidates); this
does not certify the globally nearest possible collection location. If no nearby
connected candidate is found, depot collection is labelled explicitly. Service
outages are reported rather than treated as inaccessible deliveries.

The original quantum comparison supports two vehicles and 2–8 deliveries, subject
to a 14-qubit local simulation limit. Other fleet sizes use a classical adapter
which reuses `src.classical.route_length` for tours of up to eight stops. Small
custom scenarios enumerate feasible fleet partitions; larger ones use labelled
capacity-aware assignment and route heuristics. Heuristic and manual plans are
never presented as certified global optima. Quantum controls are disabled when
the original model cannot represent the scenario.
The app projects the neighborhood coordinates into kilometres and calls the existing
`src.classical` and `src.quantum_solver` implementations. QAOA's supported automatic
QUBO penalty option handles the different city-coordinate scale. Frozen benchmark
files and submission results are not changed by city experiments.

**The existing Python code chooses the assignment and stop order.** OpenFreeMap
provides streets; OSRM's Route endpoint only supplies road geometry through that
fixed stop order. No external optimization or stop-reordering API is used. The
optimizer still minimizes the original straight-line compactness/balance model;
road distance and estimated duration are labelled separately and are not guaranteed
road-optimal or traffic-aware. Stops may snap to nearby roads.

MapLibre GL JS 5.12.0 and Three.js 0.160.1 are bundled with licenses in
`app/static/vendor/`. City maps and road visuals need internet; no API keys or payment
details are needed. Public services receive the displayed/requested locations. OSRM
requests are cached in memory and globally limited to one per 1.1 seconds; heavy use
requires your own routing service. Set `QLOGISTICS_OSRM_URL` to its base URL if needed.
Map attribution stays visible. Sources: [OpenFreeMap](https://openfreemap.org/),
[OSRM](https://project-osrm.org/), [usage policy](https://routing.openstreetmap.de/about.html).

### Terminal demo

Use Python 3.10–3.12. On Windows PowerShell, set `$env:MPLBACKEND = "Agg"`
before running the solver or demo to save figures without Tk window cleanup errors.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
python -m src.run_demo
```

For a quick check, use `python -m src.run_demo --fast`. The evaluator can also use
the checked-in schema fixtures with `python -m src.evaluate --mock`.

## Expected output

The demo prints the exact route, QAOA route and gap, qubit count, probabilities for
each repetition, and stage timings. The checked-in integration summary reports:

| Quantity | Value |
|---|---:|
| Exact optimum route length | 41.4972 |
| Best QAOA route length | 41.4972 |
| QAOA gap | 0.00% |
| Qubits | 12 |
| Exact-eigen match | true |

The authoritative numbers after a run are in `results/summary.json`.

## Classical comparison

Brute force over 64 assignments is the exact reference. Greedy and simulated annealing
provide inexpensive baselines. QAOA is evaluated by feasible assignment probability,
optimum probability, and route-length gap. At this instance size, classical exhaustive
search is expected to be faster; this project makes no quantum-advantage claim.

## Honest limitations

This is a six-customer simulator experiment, not a production route planner. The QUBO
objective is a proxy for route distance, slack qubits increase circuit size, penalty
weights and optimizer seeds affect QAOA, and noisy hardware may reduce solution
quality. Larger fleets, time windows, road-network distances, and hardware execution
are natural next steps.

## Team and credits

- **Usama** — classical baselines and report
- **Fatima** — QUBO and quantum solver
- **Khattak** — integration, evaluation, demo, and presentation assets

We used Qiskit documentation and tutorials as reference for API guidance and credit
the Qiskit open-source project. AI coding assistants (Google Antigravity / Codex)
assisted with code scaffolding, tests, and documentation; all formulations, results,
and analysis were directed and verified by the team.

- **Report:** [`docs/Report.docx`](docs/Report.docx)
- **Video:** *[VIDEO_LINK — to be inserted by Usama before deadline]*
- **Repository:** https://github.com/UsamaAziz07/quantum-last-mile-qiskit
