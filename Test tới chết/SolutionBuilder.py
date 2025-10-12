# --- START OF FILE SolutionBuilder.py (REFACTORED) ---

import math
import random
import copy
from Parser import ProblemInstance
from DataStructures import SERoute, FERoute, Solution

# =============================================================================
# CAC HAM HO TRO (GIU NGUYEN)
# =============================================================================
def _get_deadline_for_sort(customer):
    return getattr(customer, 'deadline', float('inf'))

def _get_total_cost_of_se_routes(se_routes):
    return sum(r.total_dist for r in se_routes)

def _find_cluster_satellite(customer_cluster, problem):
    if not customer_cluster: return None
    avg_x = sum(c.x for c in customer_cluster) / len(customer_cluster)
    avg_y = sum(c.y for c in customer_cluster) / len(customer_cluster)
    return min(problem.satellites, key=lambda s: math.sqrt((s.x - avg_x)**2 + (s.y - avg_y)**2))

# =============================================================================
# GIAI DOAN 1A: XAY DUNG VA TOI UU HOA NOI BO CUM (CAC HAM LNS GIU NGUYEN)
# =============================================================================
def _build_initial_routes_for_cluster(home_satellite, customer_cluster, problem):
    # ... (Giữ nguyên code của hàm này)
    routes = []
    customers_to_serve = sorted(list(customer_cluster), key=_get_deadline_for_sort)
    served_customers = []

    made_insertion_in_pass = True
    while made_insertion_in_pass:
        made_insertion_in_pass = False
        customers_for_this_pass = [c for c in customers_to_serve if c not in served_customers]

        for customer in customers_for_this_pass:
            best_choice = {"type": None, "cost": float('inf')}

            for route in routes:
                insertion_info = route.find_best_insertion_pos(customer)
                if insertion_info and insertion_info["cost_increase"] < best_choice["cost"]:
                    best_choice.update({"type": "existing", "route": route, "pos": insertion_info["pos"], "cost": insertion_info["cost_increase"]})
            
            if customer.demand <= problem.se_vehicle_capacity:
                temp_new_route = SERoute(home_satellite, problem)
                temp_new_route.insert_customer_at_pos(customer, 1)
                arrival = problem.get_travel_time(home_satellite.id, customer.id)
                start_svc = max(arrival, customer.ready_time)
                if start_svc <= customer.due_time and temp_new_route.is_feasible_under_proxy_deadline():
                    cost = temp_new_route.total_dist
                    if cost < best_choice["cost"]:
                        best_choice.update({"type": "new", "pos": 1, "cost": cost})

            if best_choice["type"]:
                if best_choice["type"] == "existing":
                    best_choice["route"].insert_customer_at_pos(customer, best_choice["pos"])
                elif best_choice["type"] == "new":
                    new_route = SERoute(home_satellite, problem)
                    new_route.insert_customer_at_pos(customer, best_choice["pos"])
                    routes.append(new_route)
                served_customers.append(customer)
                made_insertion_in_pass = True
                break
    
    unserved_in_cluster = [c for c in customer_cluster if c not in served_customers]
    return routes, unserved_in_cluster


def _greedy_insertion(routes, removed_customers, home_satellite, problem):
    # ... (Giữ nguyên code của hàm này)
    unserved = sorted(list(removed_customers), key=_get_deadline_for_sort)

    for customer in unserved:
        best_choice = {"type": None, "cost": float('inf')}

        for route in routes:
            if not route.get_customers(): continue
            info = route.find_best_insertion_pos(customer)
            if info and info["cost_increase"] < best_choice["cost"]:
                best_choice.update({"type": "existing", "route": route, "pos": info["pos"], "cost": info["cost_increase"]})
        
        if customer.demand <= problem.se_vehicle_capacity:
            temp_route = SERoute(home_satellite, problem)
            temp_route.insert_customer_at_pos(customer, 1)
            arrival = problem.get_travel_time(home_satellite.id, customer.id)
            start_svc = max(arrival, customer.ready_time)
            if start_svc <= customer.due_time and temp_route.is_feasible_under_proxy_deadline():
                cost = temp_route.total_dist
                if cost < best_choice["cost"]:
                    best_choice.update({"type": "new", "pos": 1, "cost": cost})
        
        if best_choice["type"] == "existing":
            best_choice["route"].insert_customer_at_pos(customer, best_choice["pos"])
        elif best_choice["type"] == "new":
            new_route = SERoute(home_satellite, problem)
            new_route.insert_customer_at_pos(customer, best_choice["pos"])
            routes.append(new_route)

def _random_removal(routes, customers_in_routes, num_to_remove):
    # ... (Giữ nguyên code của hàm này)
    if not customers_in_routes: return []
    num_to_remove = min(num_to_remove, len(customers_in_routes))
    removed_customers = random.sample(customers_in_routes, num_to_remove)
    cust_to_route_map = {c.id: r for r in routes for c in r.get_customers()}
    for cust in removed_customers:
        if cust.id in cust_to_route_map:
            cust_to_route_map[cust.id].remove_customer(cust)
    return removed_customers

def build_and_optimize_routes_for_cluster(home_satellite, customer_cluster, problem, lns_iterations):
    # ... (Giữ nguyên code của hàm này)
    initial_routes, unserved_in_cluster = _build_initial_routes_for_cluster(home_satellite, customer_cluster, problem)
    
    if lns_iterations == 0 or not initial_routes:
        return initial_routes, unserved_in_cluster

    print(f"    -> Cum {home_satellite.id}: Bat dau LNS voi {lns_iterations} vong lap...")
    current_routes = initial_routes
    best_routes = copy.deepcopy(current_routes)
    best_cost = _get_total_cost_of_se_routes(best_routes)

    for i in range(lns_iterations):
        working_routes = copy.deepcopy(current_routes)
        customers_on_routes = [c for r in working_routes for c in r.get_customers()]
        if not customers_on_routes: continue

        num_to_remove = max(1, int(len(customers_on_routes) * random.uniform(0.2, 0.4)))
        removed_customers = _random_removal(working_routes, customers_on_routes, num_to_remove)
        
        _greedy_insertion(working_routes, removed_customers, home_satellite, problem)
        
        working_routes = [r for r in working_routes if r.get_customers()]
        working_cost = _get_total_cost_of_se_routes(working_routes)

        if working_cost < best_cost:
            best_routes = copy.deepcopy(working_routes)
            best_cost = working_cost
        
        if working_cost < _get_total_cost_of_se_routes(current_routes):
            current_routes = copy.deepcopy(working_routes)

    return best_routes, unserved_in_cluster

# =============================================================================
# GIAI DOAN 1B: "GIẢI CỨU" KHÁCH HÀNG LIÊN CỤM (GIU NGUYEN)
# =============================================================================
def _rescue_unserved_customers_globally(global_unserved, all_routes):
    # ... (Giữ nguyên code của hàm này, nó sẽ được gọi từ main_cluster_first.py)
    if not global_unserved:
        return
        
    made_rescue = False
    customers_to_rescue = sorted(list(global_unserved), key=_get_deadline_for_sort)
    rescued_customers = []

    for customer in customers_to_rescue:
        best_choice = {"cost": float('inf')}
        for route in all_routes:
            info = route.find_best_insertion_pos(customer)
            if info and info["cost_increase"] < best_choice["cost"]:
                best_choice.update({"route": route, "pos": info["pos"], "cost": info["cost_increase"]})
        
        if "route" in best_choice:
            if not made_rescue:
                 print(f"  Bat dau giai cuu...")
                 made_rescue = True
            print(f"    -> Da giai cuu KH {customer.id} vao tuyen cua Ve tinh {best_choice['route'].satellite.id}")
            best_choice["route"].insert_customer_at_pos(customer, best_choice["pos"])
            rescued_customers.append(customer)

    for cust in rescued_customers:
        global_unserved.remove(cust)
    
    if not made_rescue:
        print("  Khong the giai cuu them khach hang nao.")


# =============================================================================
# LOGIC XAY DUNG TUYEN FE (GIU NGUYEN)
# =============================================================================
def _build_fe_routes_parallel_insertion(solution, satellite_reqs, problem, use_deadline):
    # ... (Giữ nguyên code của hàm này)
    unvisited_sat_ids = set(satellite_reqs.keys())
    open_fe_routes = []
    while unvisited_sat_ids:
        best_action = {"cost": float('inf')}
        for sat_id in unvisited_sat_ids:
            for i, route in enumerate(open_fe_routes):
                for pos in range(1, len(route.nodes_id)):
                    temp_route = copy.deepcopy(route)
                    temp_route.nodes_id.insert(pos, sat_id)
                    is_feasible, _ = _is_fe_route_feasible(temp_route, satellite_reqs, problem, use_deadline)
                    if is_feasible:
                        prev_node_id, next_node_id = temp_route.nodes_id[pos-1], temp_route.nodes_id[pos+1]
                        cost_increase = problem.get_distance(prev_node_id, sat_id) + problem.get_distance(sat_id, next_node_id) - problem.get_distance(prev_node_id, next_node_id)
                        if cost_increase < best_action["cost"]:
                            best_action = {"cost": cost_increase, "type": "insert", "satellite_id": sat_id, "route_index": i, "pos": pos}
            
            temp_new_route = FERoute(problem)
            temp_new_route.nodes_id.insert(1, sat_id)
            is_feasible, _ = _is_fe_route_feasible(temp_new_route, satellite_reqs, problem, use_deadline)
            if is_feasible:
                cost = problem.get_distance(problem.depot.id, sat_id) + problem.get_distance(sat_id, problem.depot.id)
                if cost < best_action["cost"]:
                    best_action = {"cost": cost, "type": "new_route", "satellite_id": sat_id}

        if best_action.get("type") == "insert":
            action = best_action
            open_fe_routes[action["route_index"]].nodes_id.insert(action["pos"], action["satellite_id"])
            unvisited_sat_ids.remove(action["satellite_id"])
        elif best_action.get("type") == "new_route":
            action = best_action
            new_route = FERoute(problem)
            new_route.nodes_id.insert(1, action["satellite_id"])
            open_fe_routes.append(new_route)
            unvisited_sat_ids.remove(action["satellite_id"])
        else:
            break

    for route in open_fe_routes:
        is_feasible, final_schedule = _is_fe_route_feasible(route, satellite_reqs, problem, use_deadline)
        if not is_feasible:
             continue
        route.schedule = final_schedule
        for sat_id in route.nodes_id[1:-1]:
            req = satellite_reqs[sat_id]
            route.add_satellite(req['obj'], req['delivery_load'], req['pickup_load'], req.get('deadline', float('inf')))
        route.update_route_info()
    solution.fe_routes = open_fe_routes

def _is_fe_route_feasible(route, satellite_reqs, problem, use_deadline):
    # ... (Giữ nguyên code của hàm này)
    current_time = 0.0
    delivery_load_total = sum(satellite_reqs.get(sid, {}).get('delivery_load', 0) for sid in route.nodes_id if sid != problem.depot.id)
    current_pickup_load = 0.0
    schedule = {problem.depot.id: {'arrival': 0.0, 'departure': 0.0}}
    if delivery_load_total > problem.fe_vehicle_capacity:
        return False, None
    route_deadline = float('inf')
    if use_deadline:
        deadlines = [satellite_reqs.get(sid, {}).get('deadline', float('inf')) for sid in route.nodes_id if sid != problem.depot.id]
        if deadlines: route_deadline = min(deadlines)
    for i in range(len(route.nodes_id) - 1):
        prev_node_id, curr_node_id = route.nodes_id[i], route.nodes_id[i+1]
        travel_time = problem.get_travel_time(prev_node_id, curr_node_id)
        arrival_time = current_time + travel_time
        if curr_node_id == problem.depot.id:
            if use_deadline and arrival_time > route_deadline: return False, None
            schedule['final_arrival'] = arrival_time
        else:
            req = satellite_reqs.get(curr_node_id)
            if not req: return False, None
            start_work_time = max(arrival_time, req.get('earliest_se_delivery_arrival', 0), req.get('latest_se_pickup_arrival', 0))
            departure_time = start_work_time + req['obj'].service_time
            schedule[curr_node_id] = {'arrival': arrival_time, 'departure': departure_time}
            current_time = departure_time
            delivery_load_total -= req['delivery_load']
            current_pickup_load += req['pickup_load']
            if current_pickup_load > problem.fe_vehicle_capacity: return False, None
            if (delivery_load_total + current_pickup_load) > problem.fe_vehicle_capacity: return False, None
    return True, schedule

# =============================================================================
# HAM MOI: GIAI QUYET MOT BAI TOAN CON (MOT CUM)
# =============================================================================
def solve_sub_problem(problem, customer_cluster, lns_iterations, use_deadline, 
                      simultaneous_fe_pu_del, allow_fe_split):
    """
    Giai quyet bai toan 2E-VRP cho mot cum khach hang duy nhat.
    Tra ve mot tuple: (fe_routes, se_routes, unserved_customers) cho cum nay.
    """
    # Giai doan 1A: Xay dung va toi uu tuyen SE cho cum
    home_satellite = _find_cluster_satellite(customer_cluster, problem)
    if not home_satellite:
        return [], [], customer_cluster

    se_routes, unserved_in_cluster = build_and_optimize_routes_for_cluster(
        home_satellite, customer_cluster, problem, lns_iterations
    )

    if not se_routes:
        return [], [], customer_cluster

    # Giai doan 2: Xay dung tuyen FE chi cho cac ve tinh duoc su dung trong cum nay
    fe_routes = []
    active_satellites = {r.satellite for r in se_routes if r.get_customers()}
    if active_satellites:
        satellite_reqs = {}
        for sat in active_satellites:
            routes_for_sat = [r for r in se_routes if r.satellite == sat]
            if not routes_for_sat: continue
            
            req = { 'earliest_se_delivery_arrival': min(r.service_start_times.get(sat.dist_id, float('inf')) for r in routes_for_sat),
                   'latest_se_pickup_arrival': max(r.service_start_times.get(sat.coll_id, float('-inf')) for r in routes_for_sat),
                   'delivery_load': sum(r.total_load_delivery for r in routes_for_sat),
                   'pickup_load': sum(r.total_load_pickup for r in routes_for_sat), 'obj': sat }
            if use_deadline:
                deadlines = [c.deadline for r in routes_for_sat for c in r.get_customers() if hasattr(c, 'deadline')]
                req['deadline'] = min(deadlines) if deadlines else float('inf')
            satellite_reqs[sat.id] = req

        # Can mot doi tuong Solution tam thoi de goi ham build FE
        temp_solution = Solution(problem)
        if simultaneous_fe_pu_del:
            _build_fe_routes_parallel_insertion(temp_solution, satellite_reqs, problem, use_deadline)
        else:
            # Logic cho SPD (neu co)
            pass
        fe_routes = temp_solution.fe_routes

    # Giai doan 3: Hau xu ly trong pham vi cum
    # Xac dinh xem co tuyen SE nao bi loai bo do khong the xay dung tuyen FE hop le
    actually_served_satellite_ids = {s_id for r in fe_routes for s_id in r.nodes_id if s_id != problem.depot.id}
    final_se_routes = [r for r in se_routes if r.satellite.id in actually_served_satellite_ids]
    
    all_served_ids = {c.id for r in final_se_routes for c in r.get_customers()}
    final_unserved_customers = [c for c in customer_cluster if c.id not in all_served_ids]

    return fe_routes, final_se_routes, final_unserved_customers

# --- END OF FILE SolutionBuilder.py (REFACTORED) ---