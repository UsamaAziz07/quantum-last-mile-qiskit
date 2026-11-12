"""Local dashboard adapter. Existing solver and frozen submission files stay unchanged."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlparse
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.contract import canonical, load_instance
from src.classical import evaluate_assignment
from app import city

STATIC = Path(__file__).parent / "static"
INST = load_instance()
LOCK = threading.Lock()
SESSION_QUANTUM = None
CITY_STATE = None
JOB = {"status": "idle", "events": [], "error": None}


def read_result(name):
    return json.loads((ROOT / "results" / name).read_text(encoding="utf-8"))


def dashboard_data():
    classical = read_result("classical_reference.json")
    with LOCK:
        quantum = SESSION_QUANTUM or read_result("quantum_results.json")
        source = "session" if SESSION_QUANTUM is not None else "recorded"
    optimum = classical["optimum_true"]["true_route_length"]
    candidates = []

    def candidate(y, label, family, **extra):
        row = evaluate_assignment(INST, canonical(y))
        row.update(label=label, family=family, gap=100 * (row["true_route_length"] / optimum - 1), **extra)
        candidates.append(row)

    names = {"brute_force": "Exact search", "greedy": "Greedy sweep", "simulated_annealing": "Annealing"}
    for row in classical["methods"]:
        candidate(row["assignment"], names.get(row["method"], row["method"]), "classical", runtime_s=row["runtime_s"])
    for i, run in enumerate(quantum["runs"]):
        if run["best_feasible_assignment"] is not None:
            candidate(run["best_feasible_assignment"], f"QAOA · p={run['reps']} · seed {run['seed']}", "quantum",
                      run_index=i, prob_optimum=run["prob_optimum"], prob_feasible=run["prob_feasible"],
                      runtime_s=run["runtime_s"], energy_history=run["energy_history"])
    return {"instance": asdict(INST), "candidates": candidates, "optimum": optimum,
            "quantum": quantum, "source": source, "feasible_count": len(classical["all_feasible"])}


def run_worker(options, city_scene=None):
    global SESSION_QUANTUM, CITY_STATE
    try:
        with tempfile.TemporaryDirectory(prefix="qlogistics-ui-") as out:
            env = {**os.environ, "MPLBACKEND": "Agg", "PYTHONUTF8": "1"}
            if city_scene is not None:
                scene_path = Path(out) / "scene.json"
                scene_path.write_text(json.dumps(city_scene), encoding="utf-8")
                options = {**options, "scene_file": str(scene_path)}
            command = [sys.executable, "-u", str(Path(__file__).with_name("worker.py")), out, json.dumps(options)]
            proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
            log = []
            for line in proc.stdout:
                log.append(line.rstrip())
                if line.startswith("EVENT "):
                    event = json.loads(line[6:])
                    with LOCK:
                        JOB["events"].append(event)
                        JOB["events"] = JOB["events"][-1200:]
            if proc.wait() != 0:
                raise RuntimeError("\n".join(log[-30:]))
            result = json.loads((Path(out) / "quantum_results.json").read_text())
            with LOCK:
                if city_scene is None:
                    SESSION_QUANTUM = result
                elif CITY_STATE is not None and CITY_STATE["id"] == city_scene["id"]:
                    CITY_STATE = city.add_quantum(CITY_STATE, result)
                JOB["status"] = "complete"
                JOB["elapsed"] = round(time.time() - JOB["started"], 2)
    except Exception as exc:
        with LOCK:
            JOB.update(status="failed", error=str(exc))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        payload = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        try:
            path = urlparse(self.path).path
            if path == "/api/data":
                return self.send_json(dashboard_data())
            if path == "/api/city":
                with LOCK:
                    scene = CITY_STATE
                return self.send_json({"scene":scene, "presets":city.PRESETS})
            if path == "/api/job":
                with LOCK:
                    snapshot = dict(JOB, events=list(JOB["events"]))
                return self.send_json(snapshot)
            filename = "index.html" if path == "/" else "city.html" if path in ("/city", "/city/") else path.lstrip("/")
            target = (STATIC / filename).resolve()
            if not target.is_relative_to(STATIC.resolve()) or not target.is_file():
                return self.send_json({"error": "Not found"}, 404)
            mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}.get(target.suffix, "application/octet-stream")
            payload = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self):
        global CITY_STATE
        try:
            # Only same-origin browser requests may start local computations.
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                return self.send_json({"error": "Cross-origin requests are not allowed"}, 403)
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                return self.send_json({"error": "Invalid request size"}, 400)
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                return self.send_json({"error":"Expected a JSON object"}, 400)
            if self.path == "/api/city/scenario":
                scene = city.prepare_scene(body)
                with LOCK:
                    if JOB["status"] == "running":
                        return self.send_json({"error":"Wait for the current experiment before changing scenarios."},409)
                    CITY_STATE = scene
                return self.send_json(scene)
            if self.path == "/api/city/route":
                with LOCK:
                    scene = CITY_STATE
                if scene is None or body.get("id") != scene["id"]:
                    return self.send_json({"error":"The scenario changed. Reload its solutions."},409)
                index = body.get("index")
                if type(index) is not int or not 0 <= index < len(scene["candidates"]):
                    return self.send_json({"error":"Choose a valid solution."},400)
                return self.send_json(city.road_geometry(scene, scene["candidates"][index]))
            if self.path == "/api/preview":
                y = body.get("assignment")
                if not isinstance(y, list) or len(y) != INST.n or any(type(v) is not int or v not in (0, 1) for v in y):
                    return self.send_json({"error": "Provide six binary assignments"}, 400)
                row = evaluate_assignment(INST, y)
                row.update(label="Your assignment", family="manual")
                return self.send_json(row)
            if self.path not in ("/api/run", "/api/city/run"):
                return self.send_json({"error": "Not found"}, 404)
            preset = body.get("preset", "quick")
            presets = {"quick": {"reps_list": [1], "seeds": [0], "maxiter": 60},
                       "balanced": {"reps_list": [1, 2], "seeds": [0, 1], "maxiter": 120},
                       "full": {"reps_list": [1, 2, 3], "seeds": [0, 1, 2, 3, 4], "maxiter": 200}}
            if preset not in presets:
                return self.send_json({"error": "Unknown run preset"}, 400)
            with LOCK:
                if JOB["status"] == "running":
                    return self.send_json({"error": "A solver run is already in progress"}, 409)
                scene = CITY_STATE if self.path == "/api/city/run" else None
                if self.path == "/api/city/run" and (scene is None or scene["id"] != body.get("id")):
                    return self.send_json({"error":"Solve the city scenario first."},409)
                if scene is not None and not scene.get("quantum_enabled",True):
                    return self.send_json({"error":scene["quantum_reason"]},400)
                JOB.update(status="running", events=[], error=None, started=time.time(), preset=preset,
                           mode="city" if scene is not None else "benchmark", scene_id=scene["id"] if scene else None)
            threading.Thread(target=run_worker, args=(presets[preset],scene), daemon=True).start()
            self.send_json({"status": "running"}, 202)
        except (ValueError, TypeError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except RuntimeError as exc:
            self.send_json({"error":str(exc)},502)

    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description="Launch the local Quantum Last-Mile dashboard")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="open the dashboard in your browser")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Quantum Last-Mile → http://127.0.0.1:{args.port}", flush=True)
    if args.open:
        webbrowser.open(f"http://127.0.0.1:{args.port}/city")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
