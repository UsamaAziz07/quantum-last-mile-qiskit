"""Zip ONLY the files you own so a teammate can drop them into the shared repo without conflicts.
Usage:  python tools/pack.py usama|fatima|khattak     ->  <name>_deliverable.zip   (send via WhatsApp/Drive)
"""
import sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OWNERS = {
    "usama": ["src/classical.py", "tests/test_classical.py", "results/classical_reference.json", "results/pareto_classical.json", "docs/architecture.mmd", "docs/architecture.png", "docs/make_architecture.py", "docs/make_report.py", "docs/Report.docx"],
    "fatima": ["src/qubo_model.py", "src/quantum_solver.py", "tests/test_quantum.py", "requirements.txt", "results/quantum_results.json",
               "results/qaoa_circuit.png", "docs/quantum_notes.md", "docs/pitch_script_final.md"],
    "khattak": ["src/evaluate.py", "src/run_demo.py", "tests/test_pipeline.py", "README.md", "demo.ipynb", ".gitignore", "results/results.csv", "results/summary.json"],
}
who = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
if who not in OWNERS: sys.exit("usage: python tools/pack.py usama|fatima|khattak")
out = ROOT / f"{who}_deliverable.zip"
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in OWNERS[who]:
        p = ROOT / rel
        if p.exists(): z.write(p, rel); n += 1; print("added  ", rel)
        else: print("MISSING", rel, "(ok if optional)")
print(f"\n{out.name}: {n} files. Send it to Khattak and say which Python/qiskit versions you used.")
