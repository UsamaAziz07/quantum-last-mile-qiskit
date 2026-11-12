"""Geographic input/visualization adapter; all optimization uses existing src functions.

OSRM connects the exact stop order chosen by src.classical. It never assigns
customers or reorders them. Road estimates are visual context, not solver costs.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from src.contract import Instance, canonical
from src.classical import brute_force, greedy, simulated_annealing, evaluate_assignment
from app.planner import fleet_plans

PROVIDER = os.environ.get("QLOGISTICS_OSRM_URL", "https://router.project-osrm.org").rstrip("/")
NETWORK_LOCK = threading.Lock()
CACHE = {}
LAST_REQUEST = 0.0
PRESETS = {
    "islamabad": {"name": "Islamabad", "center": [73.0479, 33.698], "points": [[73.0479,33.6844],[73.0375,33.7060],[73.0553,33.7110],[73.0652,33.6995],[73.0255,33.6915],[73.0380,33.6760],[73.0630,33.6810]]},
    "lahore": {"name": "Lahore", "center": [74.348,31.52], "points": [[74.3436,31.5204],[74.3510,31.5310],[74.3650,31.5200],[74.3530,31.5050],[74.3290,31.5150],[74.3260,31.5300],[74.3440,31.5400]]},
    "peshawar": {"name": "Peshawar", "center": [71.54,34.00], "points": [[71.5330,34.0050],[71.5460,34.0120],[71.5590,34.0000],[71.5430,33.9890],[71.5200,33.9940],[71.5140,34.0080],[71.5330,34.0180]]},
}


def geographic_instance(body):
    points = body.get("points")
    n = len(points)-1 if isinstance(points,list) else 0
    demands = body.get("demands", [3,2,3,1,2,1] if n == 6 else [1]*n)
    city = body.get("city", "islamabad")
    fleet_size = body.get("fleet_size",2)
    capacity = body.get("capacity",7)
    if city not in PRESETS or not isinstance(points, list) or not 1 <= n <= 40:
        raise ValueError("Choose a city and place a depot plus 1–40 delivery stops.")
    if type(fleet_size) is not int or not 1 <= fleet_size <= 8:
        raise ValueError("Choose 1–8 vehicles.")
    if type(capacity) is not int or not 1 <= capacity <= 120:
        raise ValueError("Vehicle capacity must be an integer from 1 to 120.")
    clean = []
    for p in points:
        if not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p):
            raise ValueError("Every location needs a valid longitude and latitude.")
        if not (60 <= p[0] <= 78 and 23 <= p[1] <= 38):
            raise ValueError("Keep the demo locations within Pakistan's region.")
        clean.append(tuple(float(v) for v in p))
    if len(set(clean)) != len(clean):
        raise ValueError("Each depot and delivery location must be distinct.")
    if not isinstance(demands, list) or len(demands) != n or any(type(v) is not int or not 1 <= v <= 60 for v in demands):
        raise ValueError("Each delivery load must be an integer from 1 to 60.")
    if sum(demands) > fleet_size * capacity or max(demands) > capacity:
        raise ValueError(f"Fleet capacity is {fleet_size * capacity} units; increase capacity or add vehicles.")
    lng0, lat0 = clean[0]
    # Local equirectangular projection in km, suitable for this neighborhood-sized
    # scenario. Once projected, contract.Instance.dist remains the original logic.
    xy = tuple((6371.0088 * math.radians(lng-lng0) * math.cos(math.radians(lat0)),
                6371.0088 * math.radians(lat-lat0)) for lng,lat in clean)
    if any(math.hypot(*p) > 15 for p in xy):
        raise ValueError("Keep all stops within 15 km of the depot for this small-city demo.")
    inst = Instance(name=f"city_{city}", depot=xy[0], coords=xy[1:], demands=tuple(demands),
                    num_vehicles=2, capacity=capacity, alpha=1.0, beta=0.1, seed=42)
    return inst, [list(p) for p in clean], city


def build_scene(body):
    inst, points, city = geographic_instance(body)
    fleet_size = body.get("fleet_size",2)
    allocation_mode = body.get("allocation_mode","auto")
    if allocation_mode not in ("auto","manual"):
        raise ValueError("Choose automatic or manual allocation.")
    if allocation_mode == "manual" or fleet_size != 2 or not 2 <= inst.n <= 8:
        rows, optimum, count = fleet_plans(inst,fleet_size,body.get("assignments",[]) if allocation_mode == "manual" else None)
        return {"id":uuid4().hex,"city":city,"name":PRESETS[city]["name"],"points":points,
                "instance":asdict(inst),"fleet_size":fleet_size,"candidates":rows,"optimum":optimum,
                "feasible_count":count,"quantum":None,"quantum_enabled":False,
                "quantum_reason":"Enable automatic allocation for quantum comparison." if allocation_mode == "manual" else "Quantum comparison supports two vehicles and 2–8 deliveries. This scenario uses classical planning.",
                "objective_label":"Total route distance", "exact":optimum is not None,"allocation_mode":allocation_mode}
    exact = brute_force(inst)
    feasible = exact["all_feasible"]
    if not feasible:
        raise ValueError("No capacity-feasible split exists for these loads.")
    optimum = min(feasible, key=lambda r:r["true_route_length"])
    rows = []
    for result, label in [(exact, "Exact model optimum"), (greedy(inst), "Greedy sweep"),
                           (simulated_annealing(inst), "Annealing")]:
        row = evaluate_assignment(inst, result["assignment"])
        row.update(label=label, family="classical", runtime_s=result["runtime_s"])
        rows.append(row)
    best_route = dict(optimum, label="Exact shortest total", family="classical", runtime_s=exact["runtime_s"], feasible=True)
    rows.insert(0, best_route)
    from src.qubo_model import build_qp, to_qubo
    qubo, _ = to_qubo(build_qp(inst))
    qubits = qubo.get_num_binary_vars()
    return {"id": uuid4().hex, "city": city, "name": PRESETS[city]["name"], "points": points,
            "instance": asdict(inst), "candidates": rows, "optimum": optimum["true_route_length"],
            "feasible_count": len(feasible), "quantum": None,"fleet_size":2,
            "quantum_enabled":qubits<=14,"quantum_reason":"Reduce capacity or deliveries to keep the quantum simulation within 14 qubits." if qubits>14 else "Ready for quantum comparison.",
            "objective_label":"Compactness + load balance","exact":True,"allocation_mode":"auto"}


def instance_from_scene(scene):
    d = scene["instance"]
    return Instance(**{**d,"depot":tuple(d["depot"]),"coords":tuple(tuple(p) for p in d["coords"]),"demands":tuple(d["demands"])})


def add_quantum(scene, quantum):
    inst = instance_from_scene(scene)
    rows = [r for r in scene["candidates"] if r["family"] != "quantum"]
    for run in quantum["runs"]:
        if run["best_feasible_assignment"] is None:
            continue
        row = evaluate_assignment(inst, canonical(run["best_feasible_assignment"]))
        row.update(label=f"QAOA · p={run['reps']} · seed {run['seed']}", family="quantum",
                   runtime_s=run["runtime_s"], prob_feasible=run["prob_feasible"],
                   prob_optimum=run["prob_optimum"], energy_history=run["energy_history"])
        rows.append(row)
    return {**scene, "candidates": rows, "quantum": quantum}


def provider_request(path):
    """Serialize and cache visualization requests; never exceed one request/sec."""
    global LAST_REQUEST
    with NETWORK_LOCK:
        if path in CACHE:
            return CACHE[path]
        delay = 1.1 - (time.monotonic() - LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        LAST_REQUEST = time.monotonic()
        request = Request(PROVIDER + path, headers={"User-Agent":"QuantumLastMile/1.0 (https://github.com/UsamaAziz07/quantum-last-mile-qiskit)","Accept":"application/json"})
        try:
            with urlopen(request, timeout=25) as response:
                raw = response.read(5_000_001)
            if len(raw) > 5_000_000:
                raise ValueError("Route response was too large.")
            result = json.loads(raw)
            if result.get("code") != "Ok":
                raise ValueError(result.get("message", "No drivable route found."))
        except Exception as exc:
            raise RuntimeError("Road visualization unavailable. The Python solution is still valid. " + str(exc)) from exc
        if len(CACHE) >= 128:
            CACHE.pop(next(iter(CACHE)))
        CACHE[path] = result
        return result


def road_geometry(scene, row):
    routes = []
    for van in row["routes"]:
        order = [0, *row["routes"][van], 0]
        if len(order) == 2:
            routes.append({"van":van,"geometry":{"type":"LineString","coordinates":[scene["points"][0]]*2},"distance":0,"duration":0,"order":order})
            continue
        coords = ";".join(",".join(f"{v:.6f}" for v in scene["points"][i]) for i in order)
        # Route endpoint follows supplied waypoints. Never use OSRM's Trip service,
        # which would outsource/reorder the team's chosen route.
        path = "/route/v1/driving/" + coords + "?" + urlencode({"overview":"full","geometries":"geojson","steps":"false","alternatives":"false"})
        result = provider_request(path)
        route = result["routes"][0]
        snapped = result.get("waypoints", [])
        if any(p.get("distance",0) > 500 for p in snapped):
            raise ValueError("A stop is over 500 m from a drivable road. Move it nearer a street.")
        routes.append({"van":van,"geometry":route["geometry"],"distance":route["distance"],"duration":route["duration"],"order":order})
    return {"routes":routes,"distance_km":sum(r["distance"] for r in routes)/1000,
            "duration_minutes":sum(r["duration"] for r in routes)/60,
            "note":"Road estimates follow the Python stop order; the solver optimizes straight-line model costs, not road travel time."}
