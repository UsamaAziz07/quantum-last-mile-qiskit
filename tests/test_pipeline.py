"""OWNER: KHATTAK. Integration checks for evaluation and demo orchestration."""
import json

from src import evaluate, run_demo, quantum_solver


def test_evaluate_mock(tmp_path):
    summary = evaluate.main(tmp_path, mock=True)
    expected = {
        "results.csv",
        "summary.json",
        "convergence.png",
        "probability_histogram.png",
        "route_map.png",
        "pareto.png",
        "comparison.png",
    }
    assert expected == {path.name for path in tmp_path.iterdir()}
    assert summary["mock"] is True
    assert summary["exact_eigen_match"] is True
    assert json.loads((tmp_path / "summary.json").read_text())["num_qubits"] == 12


def test_run_demo_prints_summary(monkeypatch, capsys):
    calls = []

    def fake_classical():
        calls.append("classical")

    def fake_quantum(**kwargs):
        calls.append(("quantum", kwargs))

    def fake_evaluate():
        calls.append("evaluate")
        return {
            "optimum_true_length": 41.4972,
            "best_qaoa_true_length": 41.4972,
            "qaoa_gap_pct": 0.0,
            "num_qubits": 12,
            "prob_optimum_by_reps": {"1": {"mean": 0.04, "max": 0.04}},
            "prob_feasible_by_reps": {"1": 0.4},
        }

    monkeypatch.setattr("src.classical.run_classical", fake_classical)
    monkeypatch.setattr(quantum_solver, "run_all", fake_quantum, raising=False)
    monkeypatch.setattr("src.evaluate.main", fake_evaluate)
    run_demo.main(fast=True)
    assert calls == ["classical", ("quantum", {"reps_list": (1, 2), "seeds": (0, 1)}), "evaluate"]
    assert "Quantum Last-Mile summary" in capsys.readouterr().out
