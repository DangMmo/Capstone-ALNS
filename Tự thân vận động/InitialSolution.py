# File: InitialSolution.py (LOGIC MỚI, CẤU TRÚC CŨ)

import random
from DataStructures import SERoute, FERoute, Solution

def find_best_insertion_pos(route, customer):
    """
    Tìm vị trí và chi phí chèn tốt nhất cho khách hàng.
    Hàm này giữ nguyên như các phiên bản trước.
    """
    best_pos, min_cost_increase = None, float('inf')
    for i in range(1, len(route.nodes_id)):
        prev_node_id, succ_node_id = route.nodes_id[i-1], route.nodes_id[i]
        prev_node_obj = route.problem.node_objects[prev_node_id % route.problem.total_nodes]
        succ_node_obj = route.problem.node_objects[succ_node_id % route.problem.total_nodes]
        if customer.type == 'DeliveryCustomer':
            if route.total_load_delivery + customer.demand > route.problem.se_vehicle_capacity: continue
        else:
            if route.total_load_pickup + customer.demand > route.problem.se_vehicle_capacity: continue
        start_time_prev = route.service_start_times[prev_node_id]
        travel_to_cust = route.problem.get_distance(prev_node_obj.id, customer.id)
        arrival_at_cust = start_time_prev + prev_node_obj.service_time + travel_to_cust
        start_service_cust = max(arrival_at_cust, customer.ready_time)
        if start_service_cust > customer.due_time: continue
        departure_from_cust = start_service_cust + customer.service_time
        travel_to_succ = route.problem.get_distance(customer.id, succ_node_obj.id)
        arrival_at_succ = departure_from_cust + travel_to_succ
        time_shift = arrival_at_succ - route.service_start_times[succ_node_id]
        if time_shift > route.forward_time_slacks[succ_node_id]: continue
        cost_increase = (route.problem.get_distance(prev_node_obj.id, customer.id) +
                         route.problem.get_distance(customer.id, succ_node_obj.id) -
                         route.problem.get_distance(prev_node_obj.id, succ_node_obj.id))
        if cost_increase < min_cost_increase:
            min_cost_increase, best_pos = cost_increase, i
    return best_pos, min_cost_increase

def construct_initial_solution(problem):
    """
    Xây dựng lời giải ban đầu theo cấu trúc "một vòng lặp lớn" nhưng có thêm pha cứu trợ.
    """
    print("\nBat dau xay dung loi giai ban dau (cau truc cu, logic moi)...")
    solution = Solution(problem)
    
    # === PHA 1: CỐ GẮNG XẾP TẤT CẢ KHÁCH HÀNG BẰNG HEURISTIC THAM LAM ===
    print("--- Pha 1: Xay dung tham lam (Greedy Construction) ---")
    
    customers_to_try = [c for c in problem.customers]
    random.shuffle(customers_to_try)
    
    se_routes = []
    total_customers = len(customers_to_try)
    
    for i, customer in enumerate(customers_to_try):
        if (i + 1) % 100 == 0:
            print(f"  Da xu ly {i + 1}/{total_customers} khach hang...")

        best_route_for_cust, best_pos, min_cost = None, None, float('inf')

        # 1. Tìm tuyến và vị trí tốt nhất trong các tuyến hiện có
        for route in se_routes:
            pos, cost_increase = route.find_best_insertion_pos(customer)
            if pos is not None and cost_increase < min_cost:
                min_cost, best_pos, best_route_for_cust = cost_increase, pos, route
        
        # 2. Nếu không được, thử tạo tuyến mới
        if best_route_for_cust is None:
            closest_satellite = min(problem.satellites, key=lambda s: problem.get_distance(customer.id, s.id))
            new_route = SERoute(closest_satellite, problem)
            new_route.calculate_full_schedule_and_slacks()
            
            pos, cost_increase = new_route.find_best_insertion_pos(customer)
            if pos is not None:
                min_cost, best_pos, best_route_for_cust = cost_increase, pos, new_route
                se_routes.append(new_route)

        # 3. Thực hiện chèn NẾU TÌM ĐƯỢC CHỖ
        if best_route_for_cust:
            best_route_for_cust.insert_customer_at_pos(customer, best_pos)
    
    # Cập nhật danh sách khách hàng chưa được phục vụ sau Pha 1
    served_customer_ids = set()
    for route in se_routes:
        for cust_id in route.nodes_id[1:-1]:
            served_customer_ids.add(cust_id)
    solution.unserved_customers = [c.id for c in problem.customers if c.id not in served_customer_ids]
    
    print(f"Pha 1 hoan thanh. So khach hang da phuc vu: {len(served_customer_ids)}")
    print(f"So khach hang con lai: {len(solution.unserved_customers)}")

    # === PHA 2: CỨU TRỢ (RESCUE PHASE) ===
    if solution.unserved_customers:
        print("\n--- Pha 2: Cuu tro cac khach hang con lai ---")
        unserved_customer_objects = [problem.node_objects[cid] for cid in solution.unserved_customers]
        
        for customer in unserved_customer_objects:
            closest_satellite = min(problem.satellites, key=lambda s: problem.get_distance(customer.id, s.id))
            rescue_route = SERoute(closest_satellite, problem)
            rescue_route.calculate_full_schedule_and_slacks()
            pos, _ = rescue_route.find_best_insertion_pos(customer)
            
            if pos is not None:
                rescue_route.insert_customer_at_pos(customer, pos)
                se_routes.append(rescue_route)
            else:
                print(f"CANH BAO CUC DO: Khach hang {customer.id} khong the phuc vu du da dung tuyen rieng.")
                continue

        # Cập nhật lại danh sách chưa phục vụ lần cuối
        served_customer_ids.update(c.id for c in unserved_customer_objects)
        solution.unserved_customers = [c.id for c in problem.customers if c.id not in served_customer_ids]

    solution.se_routes = se_routes
    print(f"Pha 2 hoan thanh. Tong so tuyen SE: {len(solution.se_routes)}")
    if not solution.unserved_customers:
        print("Thanh cong! Tat ca khach hang da duoc phuc vu.")
    else:
        print(f"That bai! Van con {len(solution.unserved_customers)} khach hang khong the phuc vu.")

    # === BƯỚC 3: XÂY DỰNG CÁC TUYẾN FE (Giữ nguyên) ===
    # ... (Toàn bộ logic tạo FE routes được giữ nguyên như các phiên bản trước)
    print("\n--- Buoc 3: Xay dung tuyen FE ---")
    active_satellites = {r.satellite for r in solution.se_routes}
    satellite_reqs = {}
    for sat in active_satellites:
        routes_for_sat = [r for r in solution.se_routes if r.satellite == sat]
        if not routes_for_sat: continue
        satellite_reqs[sat.id] = {
            'earliest_arrival': min(r.service_start_times[sat.dist_id] for r in routes_for_sat),
            'latest_departure': max(r.service_start_times[sat.coll_id] for r in routes_for_sat) + sat.service_time,
            'delivery_load': sum(r.total_load_delivery for r in routes_for_sat),
            'pickup_load': sum(r.total_load_pickup for r in routes_for_sat)
        }
    
    unvisited_satellites = set(active_satellites)
    while unvisited_satellites:
        new_fe_route = FERoute(problem)
        current_time, current_load, current_node_id = 0.0, 0.0, problem.depot.id
        first_sat = min(unvisited_satellites, key=lambda s: problem.get_distance(problem.depot.id, s.id))
        req = satellite_reqs.get(first_sat.id)
        if req and req['delivery_load'] <= problem.fe_vehicle_capacity:
            new_fe_route.nodes_id.insert(-1, first_sat.id)
            new_fe_route.satellite_loads[first_sat.id] = {'delivery_load': req['delivery_load'], 'pickup_load': req['pickup_load']}
            travel_time = problem.get_distance(current_node_id, first_sat.id)
            arrival_time = current_time + travel_time
            departure_time = max(arrival_time + first_sat.service_time, req['latest_departure'])
            current_load, current_time, current_node_id = req['delivery_load'], departure_time, first_sat.id
            unvisited_satellites.remove(first_sat)
            while True:
                best_next_sat, min_insertion_cost = None, float('inf')
                for sat in unvisited_satellites:
                    req_next = satellite_reqs.get(sat.id)
                    if not req_next or current_load + req_next['delivery_load'] > problem.fe_vehicle_capacity: continue
                    travel_time_to_next = problem.get_distance(current_node_id, sat.id)
                    if current_time + travel_time_to_next > req_next['earliest_arrival']: continue
                    if travel_time_to_next < min_insertion_cost:
                        min_insertion_cost, best_next_sat = travel_time_to_next, sat
                if best_next_sat:
                    req_best = satellite_reqs[best_next_sat.id]
                    new_fe_route.nodes_id.insert(-1, best_next_sat.id)
                    new_fe_route.satellite_loads[best_next_sat.id] = {'delivery_load': req_best['delivery_load'], 'pickup_load': req_best['pickup_load']}
                    travel_time = problem.get_distance(current_node_id, best_next_sat.id)
                    arrival_time = current_time + travel_time
                    departure_time = max(arrival_time + best_next_sat.service_time, req_best['latest_departure'])
                    current_load += req_best['delivery_load']
                    current_time, current_node_id = departure_time, best_next_sat.id
                    unvisited_satellites.remove(best_next_sat)
                else:
                    break
        elif first_sat in unvisited_satellites:
            unvisited_satellites.remove(first_sat)
        new_fe_route.update_route_info()
        solution.fe_routes.append(new_fe_route)

    print(f"Da tao xong {len(solution.fe_routes)} tuyen FE.")
    solution.calculate_total_cost()
    print(f"Loi giai ban dau hoan thanh voi tong chi phi: {solution.total_cost:.2f}")

    return solution