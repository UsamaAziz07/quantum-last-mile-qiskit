"""Fleet-size adapter for city scenarios beyond the original two-van model.

Small tours reuse src.classical.route_length. Small scenarios enumerate capacity-
feasible fleet partitions; larger ones use explicitly labelled classical heuristics.
The frozen two-van QAOA model is never presented as a multi-vehicle solver.
"""
from functools import lru_cache
import time

from src.classical import route_length


def fleet_plans(inst, fleet_size, manual=None):
    start = time.perf_counter()

    @lru_cache(maxsize=None)
    def tour(customers):
        if len(customers) <= 8:
            distance, order = route_length(inst, customers)
            return distance, tuple(order)
        # Explicit large-tour extension; exact factorial routing is impractical here.
        remaining = set(customers)
        order, point = [], 0
        while remaining:
            nearest = min(remaining, key=lambda c:(inst.dist(point,c),c))
            order.append(nearest)
            remaining.remove(nearest)
            point = nearest
        def length(path):
            full = [0,*path,0]
            return sum(inst.dist(a,b) for a,b in zip(full,full[1:]))
        for _ in range(5):
            improved = False
            for i in range(len(order)-1):
                for j in range(i+2,len(order)+1):
                    candidate = order[:i]+order[i:j][::-1]+order[j:]
                    if length(candidate) < length(order)-1e-9:
                        order = candidate
                        improved = True
            if not improved:
                break
        return length(order), tuple(order)

    def evaluate(y, label):
        routes, loads, distance = {}, [], 0.0
        for v in range(fleet_size):
            stops = tuple(i+1 for i,a in enumerate(y) if a == v)
            cost, order = tour(stops)
            routes[chr(65+v)] = list(order)
            loads.append(sum(inst.demands[i-1] for i in stops))
            distance += cost
        return {"assignment":list(y),"feasible":max(loads,default=0)<=inst.capacity,
                "model_objective":distance,"true_route_length":distance,"routes":routes,
                "loads":loads,"label":label,"family":"classical","runtime_s":time.perf_counter()-start}

    if manual is not None:
        if not isinstance(manual,list) or len(manual) != inst.n or any(type(v) is not int or not 0 <= v < fleet_size for v in manual):
            raise ValueError("Assign every delivery to one of the available vehicles.")
        row = evaluate(manual,"Manual allocation")
        if not row["feasible"]:
            raise ValueError("A vehicle is overloaded. Reassign deliveries or increase vehicle capacity.")
        return [row], None, None

    if inst.n <= 8:
        best = None
        count = 0
        assignment = [0]*inst.n
        loads = [0]*fleet_size
        def search(i, used):
            nonlocal best, count
            if i == inst.n:
                count += 1
                row = evaluate(assignment,"Exact fleet plan")
                if best is None or row["true_route_length"] < best["true_route_length"]-1e-9:
                    best = row
                return
            for v in range(min(used+1,fleet_size)):
                if loads[v]+inst.demands[i] > inst.capacity:
                    continue
                assignment[i] = v
                loads[v] += inst.demands[i]
                search(i+1,max(used,v+1))
                loads[v] -= inst.demands[i]
        search(0,0)
        if best is None:
            raise ValueError("No capacity-feasible plan exists. Increase capacity or add vehicles.")
        best["runtime_s"] = time.perf_counter()-start
        return [best], best["true_route_length"], count

    plans = []
    for mode in range(3):
        # Capacity-aware assignment with bounded backtracking. Different spatial
        # preferences yield competing plans; none is labelled globally optimal.
        order = sorted(range(inst.n),key=lambda i:(-inst.demands[i],i))
        assignments = [-1]*inst.n
        groups = [[] for _ in range(fleet_size)]
        loads = [0]*fleet_size
        visited = 0
        def place(depth):
            nonlocal visited
            visited += 1
            if visited > 100_000:
                return False
            if depth == len(order):
                return True
            customer = order[depth]
            def preference(v):
                nearby = min((inst.dist(customer+1,j+1) for j in groups[v]),default=inst.dist(0,customer+1))
                if mode == 1:
                    return (loads[v],nearby,v)
                if mode == 2:
                    return (abs(loads[v]+inst.demands[customer]-inst.total_demand/fleet_size),nearby,v)
                return (nearby,loads[v],v)
            seen_empty = False
            for v in sorted(range(fleet_size),key=preference):
                if loads[v]+inst.demands[customer] > inst.capacity:
                    continue
                if not groups[v]:
                    if seen_empty:
                        continue
                    seen_empty = True
                assignments[customer] = v
                groups[v].append(customer)
                loads[v] += inst.demands[customer]
                if place(depth+1):
                    return True
                groups[v].pop()
                loads[v] -= inst.demands[customer]
            return False
        if place(0):
            plans.append(evaluate(assignments, ["Proximity plan","Balanced fleet","Load-aware plan"][mode]))
    if not plans:
        raise ValueError("No feasible plan found within the search budget. Add capacity or reduce deliveries.")
    return plans, None, None
