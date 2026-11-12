"""OWNER: KHATTAK. Pipeline checks using the frozen mock contract files."""
import json

from src import evaluate


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
