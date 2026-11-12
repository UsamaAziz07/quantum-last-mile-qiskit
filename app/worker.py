"""Run the existing quantum implementation in isolation, streaming actual evaluations."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import quantum_solver as solver


class ObservableQAOA(solver.QAOA):
    def __init__(self, *args, callback=None, **kwargs):
        def observe(count, params, value, metadata):
            if callback:
                callback(count, params, value, metadata)
            print("EVENT " + json.dumps({"evaluation": count, "energy": float(value), "reps": kwargs.get("reps", 1)}), flush=True)
        super().__init__(*args, callback=observe, **kwargs)


if __name__ == "__main__":
    # Adapter only: never modify solver source or overwrite submission results.
    solver.RESULTS_DIR = Path(sys.argv[1])
    solver.QAOA = ObservableQAOA
    options = json.loads(sys.argv[2])
    scene_file = options.pop("scene_file", None)
    if scene_file:
        from app.city import instance_from_scene
        from src.contract import write_json
        scene = json.loads(Path(scene_file).read_text(encoding="utf-8"))
        inst = instance_from_scene(scene)
        original_convert = solver.to_qubo
        penalties = []

        def city_conversion(qp, penalty=None):
            # Same existing converter, using its supported automatic penalty option
            # because city-coordinate scales need not match the frozen benchmark.
            qubo, converter = original_convert(qp, penalty=None)
            penalties.append(float(converter.penalty))
            return qubo, converter

        solver.to_qubo = city_conversion
        result = solver.run_all(inst=inst, **options)
        result["penalty"] = penalties[0]
        write_json(solver.RESULTS_DIR / "quantum_results.json", result)
    else:
        solver.run_all(**options)
