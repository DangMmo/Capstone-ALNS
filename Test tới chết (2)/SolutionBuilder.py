# --- START OF FILE SolutionBuilder.py (STABLE SEQUENTIAL INSERTION - DEADLINE FIX) ---

import math
import random
import copy
from Parser import ProblemInstance
from DataStructures import SERoute, FERoute, Solution

def _get_deadline_for_sort(customer):
    return getattr(customer, 'deadline', float('inf'))

def _get_total_cost_of_se_routes(se_routes):
    return sum(r.total_dist for r in se_routes)

def _find_cluster_satellite(customer_cluster, problem):
    if not customer_cluster: return None
    avg_x = sum(c.x for c in customer_cluster) / len(customer_cluster)
    avg_y = sum(c.y for c in customer_cluster) / len(customer_cluster)
    return min(problem.satellites, key=lambda s: math.sqrt((s.x - avg_x)**2 + (s.y - avg_y)**2))

def _build_initial_routes_for_cluster(home_satellite, customer_cluster, problem):
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
                temp_new_route = SERoute(home_satellite, problem, start_time=0.0)
                insertion_info = temp_new_route.find_best_insertion_pos(customer)
                if insertion_info:
                    temp_new_route.insert_customer_at_pos(customer, insertion_info['pos'])
                    cost = temp_new_route.total_dist
                    if cost < best_choice["cost"]:
                        best_choice.update({"type": "new", "pos": insertion_info['pos'], "cost": cost})
            if best_choice["type"]:
                if best_choice["type"] == "existing":
                    best_choice["route"].insert_customer_at_pos(customer, best_choice["pos"])
                elif best_choice["type"] == "new":
                    new_route = SERoute(home_satellite, problem, start_time=0.0)
                    new_route.insert_customer_at_pos(customer, best_choice["pos"])
                    routes.append(new_route)
                served_customers.append(customer)
                made_insertion_in_pass = True
                break
    unserved_in_cluster = [c for c in customer_cluster if c not in served_customers]
    return routes, unserved_in_cluster

def _greedy_insertion(routes, removed_customers, home_satellite, problem):
    unserved = sorted(list(removed_customers), key=_get_deadline_for_sort)
    for customer in unserved:
        best_choice = {"type": None, "cost": float('inf')}
        for route in routes:
            if not route.get_customers(): continue
            info = route.find_best_insertion_pos(customer)
            if info and info["cost_increase"] < best_choice["cost"]:
                best_choice.update({"type": "existing", "route": route, "pos": info["pos"], "cost": info["cost_increase"]})
        if customer.demand <= problem.se_vehicle_capacity:
            temp_route = SERoute(home_satellite, problem, start_time=0.0)
            info = temp_route.find_best_insertion_pos(customer)
            if info:
                temp_route.insert_customer_at_pos(customer, info['pos'])
                cost = temp_route.total_dist
                if cost < best_choice["cost"]:
                    best_choice.update({"type": "new", "pos": info['pos'], "cost": cost})
        if best_choice["type"] == "existing":
            best_choice["route"].insert_customer_at_pos(customer, best_choice["pos"])
        elif best_choice["type"] == "new":
            new_route = SERoute(home_satellite, problem, start_time=0.0)
            new_route.insert_customer_at_pos(customer, best_choice["pos"])
            routes.append(new_route)

def _random_removal(routes, customers_in_routes, num_to_remove):
    if not customers_in_routes: return []
    num_to_remove = min(num_to_remove, len(customers_in_routes))
    removed_customers = random.sample(customers_in_routes, num_to_remove)
    cust_to_route_map = {c.id: r for r in routes for c in r.get_customers()}
    for cust in removed_customers:
        if cust.id in cust_to_route_map:
            cust_to_route_map[cust.id].remove_customer(cust)
    return removed_customers

def build_and_optimize_routes_for_cluster(home_satellite, customer_cluster, problem, lns_iterations):
    initial_routes, unserved_in_cluster = _build_initial_routes_for_cluster(home_satellite, customer_cluster, problem)
    if lns_iterations == 0 or not initial_routes:
        return initial_routes, unserved_in_cluster
    print(f"    -> Ve tinh {home_satellite.id}: Bat dau LNS voi {lns_iterations} vong lap...")
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

def _rescue_unserved_customers_globally(global_unserved, all_se_routes):
    if not global_unserved: return
    made_rescue = False
    customers_to_rescue = sorted(list(global_unserved), key=_get_deadline_for_sort)
    rescued_customers = []
    for customer in customers_to_rescue:
        best_choice = {"cost": float('inf')}
        for route in all_se_routes:
            info = route.find_best_insertion_pos(customer)
            if info and info["cost_increase"] < best_choice["cost"]:
                best_choice.update({"route": route, "pos": info["pos"], "cost": info["cost_increase"]})
        if "route" in best_choice:
            if not made_rescue:
                 print(f"  Bat dau giai cuu..."); made_rescue = True
            print(f"    -> Da giai cuu KH {customer.id} vao tuyen cua Ve tinh {best_choice['route'].satellite.id}")
            best_choice["route"].insert_customer_at_pos(customer, best_choice["pos"])
            rescued_customers.append(customer)
    for cust in rescued_customers:
        if cust in global_unserved: global_unserved.remove(cust)
    if not made_rescue: print("  Khong the giai cuu them khach hang nao.")

# =============================================================================
# <<< LOGIC XAY DUNG TUYEN FE (ĐƯỢC VIẾT LẠI HOÀN TOÀN - PHIÊN BẢN ỔN ĐỊNH) >>>
# =============================================================================

def _build_fe_schedule_sequential(path, satellite_reqs, problem, use_deadline):
    """
    Hàm này bây giờ là hàm cốt lõi duy nhất.
    Nó xây dựng lịch trình chi tiết và kiểm tra tính khả thi cho một path cho trước.
    Trả về (is_feasible, schedule, cost).
    """
    if not path: return True, [], 0
    
    events_to_schedule, total_delivery_load = [], 0
    path_reqs = {}
    for sat_id in path:
        req = satellite_reqs.get(sat_id)
        if not req: continue
        path_reqs[sat_id] = req
        if req.get('delivery_load', 0) > 1e-6:
            events_to_schedule.append({'sat_id': sat_id, 'activity': 'UNLOAD_DELIV', 'load_change': -req['delivery_load'], 'ert': 0.0})
            total_delivery_load += req['delivery_load']
        if req.get('pickup_load', 0) > 1e-6:
            events_to_schedule.append({'sat_id': sat_id, 'activity': 'LOAD_PICKUP', 'load_change': req['pickup_load'], 'ert': req.get('latest_se_pickup_arrival', 0.0)})
    
    events_to_schedule.sort(key=lambda x: x['ert'])

    if total_delivery_load > problem.fe_vehicle_capacity: return False, None, float('inf')

    final_schedule, current_time, current_load, current_pos_id = [], 0.0, total_delivery_load, problem.depot.id
    final_schedule.append({'node_id': problem.depot.id, 'activity': 'START', 'load_change': total_delivery_load, 'load_after': current_load, 'arrival_time': 0.0, 'start_svc_time': 0.0, 'departure_time': 0.0})

    temp_events = list(events_to_schedule)
    while temp_events:
        best_next_event, best_event_idx, min_finish_time = None, -1, float('inf')
        for i, event in enumerate(temp_events):
            sat_id, sat_obj = event['sat_id'], path_reqs[event['sat_id']]['obj']
            arrival_time = current_time + problem.get_travel_time(current_pos_id, sat_id)
            start_svc_time = max(arrival_time, event['ert'])
            departure_time = start_svc_time + sat_obj.service_time
            temp_load = current_load + event['load_change']
            if not (-1e-6 <= temp_load <= problem.fe_vehicle_capacity + 1e-6): continue
            if departure_time < min_finish_time:
                min_finish_time, best_event_idx = departure_time, i
                
                # <<< SỬA LỖI CỐT LÕI NẰM Ở ĐÂY >>>
                schedule_info = {
                    'node_id': sat_id, 'activity': event['activity'], 
                    'load_change': event['load_change'], 'load_after': temp_load, 
                    'arrival_time': arrival_time, 'start_svc_time': start_svc_time, 
                    'departure_time': departure_time
                }
                # Nếu là sự kiện LOAD_PICKUP, phải thêm thông tin deadline vào
                if event['activity'] == 'LOAD_PICKUP':
                    schedule_info['deadline'] = path_reqs[sat_id].get('deadline', float('inf'))
                
                best_next_event = {'event_data': event, 'schedule_info': schedule_info}
        
        if best_next_event is None: return False, None, float('inf')
        
        final_schedule.append(best_next_event['schedule_info'])
        current_time, current_load, current_pos_id = best_next_event['schedule_info']['departure_time'], best_next_event['schedule_info']['load_after'], best_next_event['schedule_info']['node_id']
        temp_events.pop(best_event_idx)

    final_arrival_time = current_time + problem.get_travel_time(current_pos_id, problem.depot.id)
    route_deadline = float('inf')
    if use_deadline:
        deadlines = [req.get('deadline', float('inf')) for req in path_reqs.values() if req.get('deadline', float('inf')) != float('inf')]
        if deadlines: route_deadline = min(deadlines)
    
    if use_deadline and final_arrival_time > route_deadline: return False, None, float('inf')

    final_schedule.append({'node_id': problem.depot.id, 'activity': 'END', 'load_change': -current_load, 'load_after': 0.0, 'arrival_time': final_arrival_time, 'start_svc_time': final_arrival_time, 'departure_time': final_arrival_time})
    
    cost = final_arrival_time
    return True, final_schedule, cost

def build_fe_routes_with_sequential_insertion(solution, satellite_reqs, problem, use_deadline):
    """
    Xây dựng các tuyến FE bằng Heuristic chèn tuần tự (ổn định và chính xác).
    """
    unserved_sat_ids = set(satellite_reqs.keys())
    fe_routes = []
    
    while unserved_sat_ids:
        new_route = FERoute(problem)
        current_path = []
        
        made_insertion = True
        while made_insertion:
            made_insertion = False
            best_insertion = {'cost_increase': float('inf'), 'sat_id': None, 'new_path': None}
            
            current_reqs = {sid: satellite_reqs[sid] for sid in current_path}
            _, _, current_cost = _build_fe_schedule_sequential(current_path, current_reqs, problem, use_deadline)

            for sat_id in unserved_sat_ids:
                # Thử chèn vào tất cả các vị trí (đơn giản hóa: chỉ chèn vào cuối)
                temp_path = current_path + [sat_id]
                unique_temp_path = list(dict.fromkeys(temp_path))

                temp_reqs = {sid: satellite_reqs[sid] for sid in unique_temp_path}
                is_feasible, _, new_cost = _build_fe_schedule_sequential(unique_temp_path, temp_reqs, problem, use_deadline)
                
                if is_feasible:
                    cost_increase = new_cost - current_cost
                    if cost_increase < best_insertion['cost_increase']:
                        best_insertion = {'cost_increase': cost_increase, 'sat_id': sat_id, 'new_path': unique_temp_path}

            if best_insertion['sat_id']:
                current_path = best_insertion['new_path']
                unserved_sat_ids.remove(best_insertion['sat_id'])
                made_insertion = True
        
        if current_path:
            final_reqs = {sid: satellite_reqs[sid] for sid in current_path}
            is_ok, final_schedule, _ = _build_fe_schedule_sequential(current_path, final_reqs, problem, use_deadline)
            if is_ok:
                new_route.schedule = final_schedule
                new_route.calculate_route_properties()
                fe_routes.append(new_route)
            else:
                print(f"[FATAL ERROR] Could not build final schedule for path {current_path} which was previously feasible.")
                for sid in current_path: unserved_sat_ids.add(sid)
                break
        elif unserved_sat_ids:
            break

    solution.fe_routes = fe_routes
    if unserved_sat_ids:
        print(f"[WARNING] FE Builder: Could not service all satellites. Unserviced: {unserved_sat_ids}")
        solution.unserviced_satellite_reqs = {sat_id: satellite_reqs[sat_id] for sat_id in unserved_sat_ids}


def solve_sub_problem(problem, customer_cluster, lns_iterations, use_deadline, simultaneous_fe_pu_del, allow_fe_split):
    home_satellite = _find_cluster_satellite(customer_cluster, problem)
    if not home_satellite: return [], [], customer_cluster
    se_routes, unserved_in_cluster = build_and_optimize_routes_for_cluster(home_satellite, customer_cluster, problem, lns_iterations)
    if not se_routes: return [], [], customer_cluster
    
    fe_routes, active_satellites = [], {r.satellite for r in se_routes if r.get_customers()}
    if active_satellites:
        satellite_reqs = {}
        for sat in active_satellites:
            routes_for_sat = [r for r in se_routes if r.satellite == sat]
            if not routes_for_sat: continue
            req = {'latest_se_pickup_arrival': max(r.service_start_times.get(r.satellite.coll_id, float('-inf')) for r in routes_for_sat),
                   'delivery_load': sum(r.total_load_delivery for r in routes_for_sat),
                   'pickup_load': sum(r.total_load_pickup for r in routes_for_sat), 'obj': sat}
            if use_deadline:
                deadlines = [c.deadline for r in routes_for_sat for c in r.get_customers() if hasattr(c, 'deadline') and c.deadline != float('inf')]
                req['deadline'] = min(deadlines) if deadlines else float('inf')
            satellite_reqs[sat.id] = req

        temp_solution = Solution(problem)
        build_fe_routes_with_sequential_insertion(temp_solution, satellite_reqs, problem, use_deadline)
        fe_routes = temp_solution.fe_routes

    actually_served_satellite_ids = {s.id for r in fe_routes for s in r.get_satellites_visited()}
    final_se_routes = [r for r in se_routes if r.satellite.id in actually_served_satellite_ids]
    
    for fe_route in fe_routes:
        for event in fe_route.schedule:
            if event['activity'] == 'UNLOAD_DELIV':
                sat_id, se_start_time = event['node_id'], event['departure_time']
                for se_route in final_se_routes:
                    if se_route.satellite.id == sat_id:
                        se_route.service_start_times[se_route.satellite.dist_id] = se_start_time
                        se_route.calculate_full_schedule_and_slacks()

    all_served_ids = {c.id for r in final_se_routes for c in r.get_customers()}
    final_unserved_customers = [c for c in customer_cluster if c.id not in all_served_ids]
    return fe_routes, final_se_routes, final_unserved_customers

# --- END OF FILE SolutionBuilder.py (STABLE SEQUENTIAL INSERTION - DEADLINE FIX) ---