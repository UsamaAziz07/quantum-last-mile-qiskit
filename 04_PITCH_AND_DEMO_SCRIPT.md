# 04 — 3-MINUTE PITCH & DEMO SCRIPT (HARD LIMIT 3:00 — aim for 2:45)

| Time | On screen | Say (≈ words) |
|------|-----------|---------------|
| 0:00–0:20 | Title slide | "Delivery companies must decide which van serves which customer, under capacity limits, while keeping routes short and workloads fair. That is vehicle routing — NP-hard." (45) |
| 0:20–0:55 | Formulation slide: 6 customers, 2 vans, one qubit per customer | "We encode each customer as one qubit: 0 = van A, 1 = van B. The cost adds distance between customers sharing a van plus a load-imbalance penalty. Capacity becomes constraints, converted into a QUBO of about 12 qubits." (75) |
| 0:55–1:20 | Architecture diagram | "Hybrid pipeline: Qiskit builds the QUBO, QAOA on the Aer simulator samples assignments, a classical optimizer tunes the angles, then exact routing evaluates each van's tour." (50) |
| 1:20–2:10 | Terminal: `python -m src.run_demo` | "One command reproduces everything. Here the exact brute-force optimum is X km. QAOA with p=… finds the optimum with probability …, best feasible solution gap …%." (≈85) |
| 2:10–2:40 | Results plots (histogram + Pareto) | "Distance and fairness compete: raising β balances loads but lengthens routes." (45) |
| 2:40–3:00 | Limitations slide | "Honestly: this runs on a simulator, 12 qubits is trivial for classical search, no speedup is claimed, and slack qubits and penalty tuning limit QAOA. Next: more vans, time windows, real hardware. Thank you." (45) |

Tips: record at 1080p, mic close, rehearse twice with a timer, trim terminal waiting time. Upload to Google Drive → "Anyone with the link" → test in incognito. Fill X, p, % from `results/summary.json`.
