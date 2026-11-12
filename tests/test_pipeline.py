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


def test_dashboard_routes_match_submission(monkeypatch):
    """The UI adapter preserves recorded solver choices and the golden benchmark."""
    from app import server
    from src.contract import is_feasible

    monkeypatch.setattr(server, "SESSION_QUANTUM", None)
    data = server.dashboard_data()
    assert data["source"] == "recorded"
    assert abs(data["optimum"] - 41.4972128429564) < 1e-8
    assert data["feasible_count"] == 13
    assert {row["family"] for row in data["candidates"]} == {"classical", "quantum"}
    for row in data["candidates"]:
        assert is_feasible(server.INST, row["assignment"])
        assert sorted(row["routes"]["A"] + row["routes"]["B"]) == list(range(1, 7))
        assert row["true_route_length"] >= data["optimum"] - 1e-8


def test_dashboard_session_does_not_overwrite_results(monkeypatch):
    """A completed local experiment replaces only the in-memory quantum data."""
    from app import server

    path = server.ROOT / "results" / "quantum_results.json"
    before = path.read_bytes()
    quantum = json.loads(before)
    quantum["runs"] = quantum["runs"][:1]
    monkeypatch.setattr(server, "SESSION_QUANTUM", quantum)
    data = server.dashboard_data()
    assert data["source"] == "session"
    assert len(data["quantum"]["runs"]) == 1
    assert path.read_bytes() == before


def test_city_adapter_calls_existing_solvers_without_network(monkeypatch):
    from app import city
    from src.contract import is_feasible

    monkeypatch.setattr(city, "provider_request", lambda *_: (_ for _ in ()).throw(AssertionError("Solving must stay local")))
    for name, preset in city.PRESETS.items():
        scene = city.build_scene({"city":name,"points":preset["points"]})
        inst = city.instance_from_scene(scene)
        assert inst.depot == (0.0,0.0)
        assert scene["quantum"] is None
        assert len(scene["candidates"]) == 4
        for row in scene["candidates"]:
            # The adapter must show the same order and objective as the real code.
            expected = city.evaluate_assignment(inst, row["assignment"])
            assert row["routes"] == expected["routes"]
            assert row["model_objective"] == expected["model_objective"]
            assert is_feasible(inst, row["assignment"])


def test_city_road_service_preserves_python_stop_order(monkeypatch):
    from app import city
    from urllib.parse import unquote

    scene = city.build_scene({"city":"islamabad","points":city.PRESETS["islamabad"]["points"]})
    calls = []

    def fake_request(path):
        calls.append(path)
        return {"routes":[{"distance":1000,"duration":120,"geometry":{"type":"LineString","coordinates":[[73,33],[73.01,33.01]]}}]}

    monkeypatch.setattr(city, "provider_request", fake_request)
    row = scene["candidates"][0]
    result = city.road_geometry(scene,row)
    for i, van in enumerate(("A","B")):
        order = [0,*row["routes"][van],0]
        expected = ";".join(",".join(f"{v:.6f}" for v in scene["points"][n]) for n in order)
        assert "/route/v1/driving/" + expected + "?" in unquote(calls[i])
        assert result["routes"][i]["order"] == order
        assert "/trip/" not in calls[i]
    assert result["distance_km"] == 2
    assert result["duration_minutes"] == 4


def test_city_qubo_uses_original_objective_and_safe_penalty():
    import math
    from app import city
    from src.contract import all_assignments, model_objective
    from src.qubo_model import build_qp, to_qubo

    inst, _, _ = city.geographic_instance({"city":"islamabad","points":city.PRESETS["islamabad"]["points"]})
    qp = build_qp(inst)
    for y in all_assignments(inst.n):
        assert math.isclose(qp.objective.evaluate(list(y)),model_objective(inst,y),abs_tol=1e-8)
    _, converter = to_qubo(qp,penalty=None)
    objectives = [model_objective(inst,y) for y in all_assignments(inst.n)]
    assert converter.penalty > max(objectives)-min(objectives)


def test_city_rejects_bad_loads_and_distant_points():
    import pytest
    from app import city

    body = {"city":"islamabad","points":[p[:] for p in city.PRESETS["islamabad"]["points"]]}
    with pytest.raises(ValueError,match="14"):
        city.geographic_instance({**body,"demands":[3]*6})
    body["points"][1] = [74,34]
    with pytest.raises(ValueError,match="15 km"):
        city.geographic_instance(body)


def test_custom_fleet_exact_plan_and_auto_loads():
    import math
    from app import city

    points = city.PRESETS["islamabad"]["points"][:5]
    scene = city.build_scene({"city":"islamabad","points":points,"demands":[1]*4,"fleet_size":4,"capacity":1})
    inst = city.instance_from_scene(scene)
    row = scene["candidates"][0]
    assert scene["exact"] is True
    assert scene["quantum_enabled"] is False
    assert row["loads"] == [1]*4
    assert sorted(c for stops in row["routes"].values() for c in stops) == [1,2,3,4]
    assert math.isclose(row["true_route_length"],2*sum(inst.dist(0,c) for c in range(1,5)))


def test_manual_allocation_preserved_and_overload_rejected():
    import pytest
    from app import city

    body = {"city":"islamabad","points":city.PRESETS["islamabad"]["points"],"fleet_size":3,"capacity":7,
            "allocation_mode":"manual","assignments":[0,0,1,1,2,2]}
    scene = city.build_scene(body)
    row = scene["candidates"][0]
    assert row["assignment"] == body["assignments"]
    assert row["loads"] == [5,4,3]
    assert scene["quantum_enabled"] is False
    assert scene["exact"] is False
    with pytest.raises(ValueError,match="overloaded"):
        city.build_scene({**body,"assignments":[0]*6})


def test_larger_scenario_has_feasible_uncertified_plans():
    from app import city

    depot = city.PRESETS["islamabad"]["points"][0]
    points = [depot]+[[depot[0]+.002*(i%4+1),depot[1]+.002*(i//4+1)] for i in range(12)]
    scene = city.build_scene({"city":"islamabad","points":points,"demands":[1]*12,"fleet_size":3,"capacity":5})
    assert scene["optimum"] is None
    assert scene["exact"] is False
    assert scene["quantum_enabled"] is False
    for row in scene["candidates"]:
        assert sum(row["loads"]) == 12
        assert max(row["loads"]) <= 5
        assert sorted(c for stops in row["routes"].values() for c in stops) == list(range(1,13))


def test_two_van_custom_delivery_count_keeps_quantum_support():
    from app import city

    scene = city.build_scene({"city":"islamabad","points":city.PRESETS["islamabad"]["points"][:5],"demands":[1]*4})
    assert scene["fleet_size"] == 2
    assert scene["quantum_enabled"] is True
    assert len(scene["instance"]["coords"]) == 4
