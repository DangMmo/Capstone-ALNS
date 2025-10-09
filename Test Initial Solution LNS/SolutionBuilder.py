# --- START OF FILE SolutionBuilder.py ---

import math
import random
import copy
from Parser import ProblemInstance
from DataStructures import SERoute, FERoute, Solution 

def _build_greedy_initial_se_solution_for_cluster(home_satellite, customer_cluster, problem):
    """Tạo lời giải ban đầu TỐT cho LNS bằng thuật toán chèn tham lam."""
    routes_for_satellite = []
    unserved_customers_in_cluster = list(customer_cluster)
    
    current_satellite_delivery_load = 0 # Giả định tải ban đầu là 0 cho mỗi cụm

    while unserved_customers_in_cluster:
        best_insertion_info = {"customer": None, "route": None, "pos": -1, "cost": float('inf')}
        for customer in unserved_customers_in_cluster:
            # Kiểm tra tải trọng FE (giả định cho cụm này)
            fe_capacity_violated = False
            if customer.type == 'DeliveryCustomer':
                if current_satellite_delivery_load + customer.demand > problem.fe_vehicle_capacity:
                    fe_capacity_violated = True
            if fe_capacity_violated: continue
            
            # Thử chèn vào các tuyến hiện có
            for route in routes_for_satellite:
                pos, cost_increase = route.find_best_insertion_pos(customer)
                if pos is not None and cost_increase < best_insertion_info["cost"]:
                    best_insertion_info.update({"customer": customer, "route": route, "pos": pos, "cost": cost_increase})
            
            # Thử tạo tuyến mới
            cost_for_new_route = (problem.get_distance(home_satellite.id, customer.id) + 
                                  problem.get_distance(customer.id, home_satellite.id))
            if (customer.demand <= problem.se_vehicle_capacity):
                arrival_at_cust = 0 + problem.get_travel_time(home_satellite.id, customer.id)
                start_service = max(arrival_at_cust, customer.ready_time)
                if start_service <= customer.due_time and cost_for_new_route < best_insertion_info["cost"]:
                    best_insertion_info.update({"customer": customer, "route": None, "pos": 1, "cost": cost_for_new_route})
        
        if best_insertion_info["customer"] is None: 
            # Không tìm thấy cách chèn khả thi cho bất kỳ khách hàng nào còn lại
            break 
            
        best_customer = best_insertion_info["customer"]
        best_route = best_insertion_info["route"]
        best_pos = best_insertion_info["pos"]
        
        if best_route is None:
            new_route = SERoute(home_satellite, problem)
            new_route.insert_customer_at_pos(best_customer, best_pos)
            routes_for_satellite.append(new_route)
        else:
            best_route.insert_customer_at_pos(best_customer, best_pos)
            
        if best_customer.type == 'DeliveryCustomer':
            current_satellite_delivery_load += best_customer.demand
            
        unserved_customers_in_cluster.remove(best_customer)
        
    return routes_for_satellite

# --- CÁC HÀM HELPER CHO LNS (Giống phiên bản trước) ---

def _get_total_cost_of_se_routes(se_routes):
    return sum(r.total_dist for r in se_routes)

def _random_removal(routes, customers_in_routes, num_to_remove):
    if not customers_in_routes: return []
    num_to_remove = min(num_to_remove, len(customers_in_routes))
    removed_customers = random.sample(customers_in_routes, num_to_remove)
    cust_to_route_map = {cust.id: route for route in routes for cust in route.get_customers()}
    for cust in removed_customers:
        if cust.id in cust_to_route_map:
            cust_to_route_map[cust.id].remove_customer(cust)
    return removed_customers

def _greedy_insertion(routes, removed_customers, home_satellite, problem):
    unserved = list(removed_customers)
    random.shuffle(unserved)
    for customer in unserved:
        best_insertion_info = {"route": None, "pos": -1, "cost": float('inf')}
        for route in routes:
            if not route.get_customers(): continue
            pos, cost_increase = route.find_best_insertion_pos(customer)
            if pos is not None and cost_increase < best_insertion_info["cost"]:
                best_insertion_info.update({"route": route, "pos": pos, "cost": cost_increase})
        cost_for_new_route = (problem.get_distance(home_satellite.id, customer.id) + 
                              problem.get_distance(customer.id, home_satellite.id))
        if customer.demand <= problem.se_vehicle_capacity:
            arrival_at_cust = 0 + problem.get_travel_time(home_satellite.id, customer.id)
            start_service = max(arrival_at_cust, customer.ready_time)
            if start_service <= customer.due_time and cost_for_new_route < best_insertion_info["cost"]:
                best_insertion_info.update({"route": None, "pos": 1, "cost": cost_for_new_route})
        if best_insertion_info["pos"] != -1:
            if best_insertion_info["route"] is not None:
                best_insertion_info["route"].insert_customer_at_pos(customer, best_insertion_info["pos"])
            else:
                new_route = SERoute(home_satellite, problem)
                new_route.insert_customer_at_pos(customer, best_insertion_info["pos"])
                routes.append(new_route)

def _optimize_se_routes_for_cluster_with_LNS(home_satellite, customer_cluster, problem, iterations):
    if not customer_cluster: return []

    # ===== BƯỚC 1: TẠO LỜI GIẢI BAN ĐẦU TỐT HƠN (Greedy Insertion) =====
    current_routes = _build_greedy_initial_se_solution_for_cluster(home_satellite, customer_cluster, problem)
    best_routes = copy.deepcopy(current_routes)
    
    if not current_routes: return []

    best_cost = _get_total_cost_of_se_routes(best_routes)

    # ===== BƯỚC 2: VÒNG LẶP LNS CHÍNH =====
    if iterations > 0:
        print(f"    -> Bat dau LNS voi {iterations} vong lap...")
    for i in range(iterations):
        working_routes = copy.deepcopy(current_routes)
        customers_in_routes = [c for r in working_routes for c in r.get_customers()]
        if not customers_in_routes: continue
        
        num_to_remove = max(1, int(len(customers_in_routes) * random.uniform(0.2, 0.4)))
        removed_customers = _random_removal(working_routes, customers_in_routes, num_to_remove)
        
        _greedy_insertion(working_routes, removed_customers, home_satellite, problem)
        
        working_routes = [r for r in working_routes if r.get_customers()]

        current_cost = _get_total_cost_of_se_routes(current_routes)
        working_cost = _get_total_cost_of_se_routes(working_routes)
        
        if working_cost < best_cost:
            best_routes = copy.deepcopy(working_routes)
            best_cost = working_cost
        
        if working_cost < current_cost:
            current_routes = copy.deepcopy(working_routes)

    return best_routes

# --- HÀM XÂY DỰNG LỜI GIẢI CHÍNH ---

def _find_cluster_satellite(customer_cluster, problem):
    # (Giữ nguyên)
    if not customer_cluster: return None
    avg_x = sum(c.x for c in customer_cluster) / len(customer_cluster)
    avg_y = sum(c.y for c in customer_cluster) / len(customer_cluster)
    return min(problem.satellites, key=lambda s: math.sqrt((s.x - avg_x)**2 + (s.y - avg_y)**2))

def _build_fe_routes(solution, use_deadline):
    # (Giữ nguyên logic kiểm tra deadline cứng)
    problem = solution.problem
    solution.fe_routes = []
    
    active_satellites = {r.satellite for r in solution.se_routes if r.get_customers()}
    if not active_satellites:
        return
        
    satellite_reqs = {}
    for sat in active_satellites:
        routes_for_sat = [r for r in solution.se_routes if r.satellite == sat]
        if not routes_for_sat: continue
        req = {'earliest_arrival': min(r.service_start_times.get(sat.dist_id, float('inf')) for r in routes_for_sat),
               'latest_departure': max(r.service_start_times.get(sat.coll_id, float('-inf')) for r in routes_for_sat),
               'delivery_load': sum(r.total_load_delivery for r in routes_for_sat),
               'pickup_load': sum(r.total_load_pickup for r in routes_for_sat)}
        if use_deadline:
            sat_deadlines = [c.deadline for r in routes_for_sat for c in r.get_customers() if hasattr(c, 'deadline')]
            req['deadline'] = min(sat_deadlines) if sat_deadlines else float('inf')
        satellite_reqs[sat.id] = req

    unvisited_satellites = set(active_satellites)
    while unvisited_satellites:
        new_fe_route = FERoute(problem)
        current_time, current_load, current_node_id = 0.0, 0.0, problem.depot.id
        
        first_sat = min(unvisited_satellites, key=lambda s: problem.get_distance(problem.depot.id, s.id))
        unvisited_satellites.remove(first_sat)
        req = satellite_reqs[first_sat.id]
        
        deadline_to_add = req.get('deadline', float('inf')) if use_deadline else float('inf')
        new_fe_route.add_satellite(first_sat, req['delivery_load'], req['pickup_load'], deadline=deadline_to_add)
        
        travel_time = problem.get_travel_time(current_node_id, first_sat.id)
        arrival_time = current_time + travel_time
        departure_time = max(arrival_time, req.get('earliest_arrival', 0)) + first_sat.service_time
        new_fe_route.schedule[first_sat.id] = {'arrival': arrival_time, 'departure': departure_time}
        current_load, current_time, current_node_id = req['delivery_load'], departure_time, first_sat.id

        while True:
            best_next_sat, min_insertion_cost = None, float('inf')
            for sat in unvisited_satellites:
                req_next = satellite_reqs.get(sat.id)
                if not req_next: continue
                if current_load + req_next['delivery_load'] > problem.fe_vehicle_capacity: continue
                travel_time_to_next = problem.get_travel_time(current_node_id, sat.id)
                if current_time + travel_time_to_next > req_next.get('latest_departure', float('inf')): continue

                if use_deadline:
                    temp_departure_from_next = max(current_time + travel_time_to_next, req_next.get('earliest_arrival', 0)) + sat.service_time
                    time_to_return_to_depot = problem.get_travel_time(sat.id, problem.depot.id)
                    estimated_arrival_at_depot = temp_departure_from_next + time_to_return_to_depot
                    route_deadline = min(new_fe_route.satellite_deadlines.values()) if new_fe_route.satellite_deadlines else float('inf')
                    next_deadline = req_next.get('deadline', float('inf'))
                    prospective_deadline = min(route_deadline, next_deadline)
                    if estimated_arrival_at_depot > prospective_deadline: continue 

                insertion_cost = problem.get_distance(current_node_id, sat.id)
                if insertion_cost < min_insertion_cost:
                    min_insertion_cost, best_next_sat = insertion_cost, sat

            if best_next_sat:
                unvisited_satellites.remove(best_next_sat)
                req_best = satellite_reqs[best_next_sat.id]
                deadline_to_add = req_best.get('deadline', float('inf')) if use_deadline else float('inf')
                new_fe_route.add_satellite(best_next_sat, req_best['delivery_load'], req_best['pickup_load'], deadline=deadline_to_add)
                travel_time = problem.get_travel_time(current_node_id, best_next_sat.id)
                arrival_time = current_time + travel_time
                departure_time = max(arrival_time, req_best.get('earliest_arrival', 0)) + best_next_sat.service_time
                new_fe_route.schedule[best_next_sat.id] = {'arrival': arrival_time, 'departure': departure_time}
                current_load += req_best['delivery_load']
                current_time, current_node_id = departure_time, best_next_sat.id
            else:
                break
        
        if len(new_fe_route.get_satellites_visited()) > 0:
            new_fe_route.update_route_info()
            final_arrival = new_fe_route.schedule.get('final_arrival', 0.0)
            route_deadline = min(new_fe_route.satellite_deadlines.values()) if new_fe_route.satellite_deadlines else float('inf')
            
            if use_deadline and final_arrival > route_deadline:
                 for sat_obj in new_fe_route.get_satellites_visited():
                     unvisited_satellites.add(sat_obj)
                 print(f"    - CANH BAO: Tuyến FE vừa tạo vi phạm deadline (Về lúc {final_arrival:.2f} > Deadline {route_deadline:.2f}). Bỏ qua tuyến này.")
            else:
                solution.fe_routes.append(new_fe_route)

def _rescue_unserved_customers(solution, use_deadline):
    # Implementation omitted for brevity. Keep your original code here.
    pass

def construct_solution(problem, clusters, use_deadline=True, lns_iterations=0):
    deadline_status = "CO AP DUNG DEADLINE" if use_deadline else "BO QUA DEADLINE"
    lns_status = f"VOI {lns_iterations} VONG LAP LNS/CUM" if lns_iterations > 0 else "CHI DUNG Greedy Heuristic"
    print(f"\nBat dau xay dung giai phap ({deadline_status}, {lns_status})...")
    
    solution = Solution(problem)
    if not clusters:
        print("CANH BAO: Danh sach cum trong.")
        return solution

    print(f"--- GIAI DOAN 1: Xay dung loi giai SE ---")
    for i, customer_cluster in enumerate(clusters):
        if not customer_cluster: continue
        home_satellite = _find_cluster_satellite(customer_cluster, problem)
        if home_satellite is None: continue
        
        print(f"  Cum {i+1}: Dang xu ly {len(customer_cluster)} khach hang...")
        optimized_se_routes = _optimize_se_routes_for_cluster_with_LNS(home_satellite, customer_cluster, problem, lns_iterations)
        solution.se_routes.extend(optimized_se_routes)
        
    all_served_ids = {c.id for r in solution.se_routes for c in r.get_customers()}
    solution.unserved_customers = [c for c in problem.customers if c.id not in all_served_ids]
    
    print(f"  => Da tao xong {len(solution.se_routes)} tuyen SE. So khach hang duoc phuc vu: {len(all_served_ids)}/{len(problem.customers)}")
    
    print("\n--- GIAI DOAN 2: Xay dung loi giai FE ban dau ---")
    _build_fe_routes(solution, use_deadline)
    print(f"  => Da tao xong {len(solution.fe_routes)} tuyen FE ban dau.")

    initial_unserved_count = len(solution.unserved_customers)
    if initial_unserved_count > 0:
        unserved_ids = [c.id for c in solution.unserved_customers]
        print(f"\n=> Xay dung ban dau hoan tat. Co {initial_unserved_count} khach hang chua duoc phuc vu: {unserved_ids}")
    else:
        print("\n=> Xay dung ban dau hoan tat. Tat ca khach hang da duoc phuc vu.")

    if initial_unserved_count > 0:
        _rescue_unserved_customers(solution, use_deadline)

    solution.calculate_total_cost_and_time()
    print(f"\nGIAI PHAP HOAN THANH - Tong chi phi (quang duong): {solution.total_cost:.2f} m | Tong thoi gian: {solution.total_time:.2f} min")

    final_unserved_count = len(solution.unserved_customers)
    if final_unserved_count > 0:
        unserved_ids = [c.id for c in solution.unserved_customers]
        print(f"CANH BAO (SAU GIAI CUU): Van con {final_unserved_count} khach hang khong the phuc vu: {unserved_ids}")

    return solution

# --- END OF FILE SolutionBuilder.py ---