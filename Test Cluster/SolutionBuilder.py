# --- START OF FILE SolutionBuilder.py (FIXED FE ROUTE CREATION) ---

import math
from Parser import ProblemInstance
from DataStructures import SERoute, FERoute, Solution 

# --- CÁC HÀM HELPER GIỮ NGUYÊN ---

def _find_cluster_satellite(customer_cluster, problem):
    if not customer_cluster: 
        return None
    avg_x = sum(c.x for c in customer_cluster) / len(customer_cluster)
    avg_y = sum(c.y for c in customer_cluster) / len(customer_cluster)
    return min(problem.satellites, key=lambda s: math.sqrt((s.x - avg_x)**2 + (s.y - avg_y)**2))

def _build_se_routes_for_cluster(solution, home_satellite, customer_cluster):
    problem = solution.problem
    unserved_customers_in_cluster = list(customer_cluster)
    routes_for_satellite = []
    
    current_satellite_delivery_load = sum(
        r.total_load_delivery for r in solution.se_routes if r.satellite == home_satellite
    )

    while unserved_customers_in_cluster:
        best_insertion_info = {"customer": None, "route": None, "pos": -1, "cost": float('inf')}
        for customer in unserved_customers_in_cluster:
            fe_capacity_violated = False
            if customer.type == 'DeliveryCustomer':
                if current_satellite_delivery_load + customer.demand > problem.fe_vehicle_capacity:
                    fe_capacity_violated = True
            if fe_capacity_violated: continue
            for route in routes_for_satellite:
                pos, cost_increase = route.find_best_insertion_pos(customer)
                if pos is not None and cost_increase < best_insertion_info["cost"]:
                    best_insertion_info.update({"customer": customer, "route": route, "pos": pos, "cost": cost_increase})
            cost_for_new_route = (problem.get_distance(home_satellite.id, customer.id) + 
                                  problem.get_distance(customer.id, home_satellite.id))
            if (customer.demand <= problem.se_vehicle_capacity):
                arrival_at_cust = 0 + problem.get_distance(home_satellite.id, customer.id)
                start_service = max(arrival_at_cust, customer.ready_time)
                if start_service <= customer.due_time and cost_for_new_route < best_insertion_info["cost"]:
                    best_insertion_info.update({"customer": customer, "route": None, "pos": 1, "cost": cost_for_new_route})
        if best_insertion_info["customer"] is None: break
        best_customer = best_insertion_info["customer"]
        best_route = best_insertion_info["route"]
        best_pos = best_insertion_info["pos"]
        if best_route is None:
            new_route = SERoute(home_satellite, problem)
            new_route.insert_customer_at_pos(best_customer, best_pos)
            solution.se_routes.append(new_route)
            routes_for_satellite.append(new_route)
        else:
            best_route.insert_customer_at_pos(best_customer, best_pos)
        if best_customer.type == 'DeliveryCustomer':
            current_satellite_delivery_load += best_customer.demand
        unserved_customers_in_cluster.remove(best_customer)
        if best_customer in solution.unserved_customers:
             solution.unserved_customers.remove(best_customer)


def _build_fe_routes(solution, use_deadline):
    """
    Hàm helper chuyên dụng để xây dựng (hoặc xây dựng lại) toàn bộ các tuyến FE.
    """
    problem = solution.problem
    solution.fe_routes = [] # Bắt đầu bằng việc xóa các tuyến FE cũ
    
    active_satellites = {r.satellite for r in solution.se_routes if r.get_customers()}
    if not active_satellites:
        return # Không có vệ tinh nào cần phục vụ
        
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
        first_sat = None
        sorted_by_dist = sorted(list(unvisited_satellites), key=lambda s: problem.get_distance(problem.depot.id, s.id))
        if sorted_by_dist: first_sat = sorted_by_dist[0]
        if first_sat:
            unvisited_satellites.remove(first_sat)
            req = satellite_reqs[first_sat.id]
            deadline_to_add = req.get('deadline', float('inf')) if use_deadline else float('inf')
            new_fe_route.add_satellite(first_sat, req['delivery_load'], req['pickup_load'], deadline=deadline_to_add)
            travel_time = problem.get_distance(current_node_id, first_sat.id)
            arrival_time = current_time + travel_time
            departure_time = max(arrival_time, req.get('earliest_arrival', 0)) + first_sat.service_time
            new_fe_route.schedule[first_sat.id] = {'arrival': arrival_time, 'departure': departure_time}
            current_load, current_time, current_node_id = req['delivery_load'], departure_time, first_sat.id
            while True:
                best_next_sat, min_insertion_cost = None, float('inf')
                for sat in unvisited_satellites:
                    req_next = satellite_reqs.get(sat.id)
                    if not req_next or current_load + req_next['delivery_load'] > problem.fe_vehicle_capacity: continue
                    travel_time_to_next = problem.get_distance(current_node_id, sat.id)
                    if current_time + travel_time_to_next > req_next.get('latest_departure', float('inf')): continue
                    if travel_time_to_next < min_insertion_cost: min_insertion_cost, best_next_sat = travel_time_to_next, sat
                if best_next_sat:
                    unvisited_satellites.remove(best_next_sat)
                    req_best = satellite_reqs[best_next_sat.id]
                    deadline_to_add = req_best.get('deadline', float('inf')) if use_deadline else float('inf')
                    new_fe_route.add_satellite(best_next_sat, req_best['delivery_load'], req_best['pickup_load'], deadline=deadline_to_add)
                    arrival_time = current_time + min_insertion_cost
                    departure_time = max(arrival_time, req_best.get('earliest_arrival', 0)) + best_next_sat.service_time
                    new_fe_route.schedule[best_next_sat.id] = {'arrival': arrival_time, 'departure': departure_time}
                    current_load += req_best['delivery_load']
                    current_time, current_node_id = departure_time, best_next_sat.id
                else: break
        else: break
        if len(new_fe_route.get_satellites_visited()) > 0:
            new_fe_route.update_route_info()
            solution.fe_routes.append(new_fe_route)

def _rescue_unserved_customers(solution, use_deadline):
    """
    Cố gắng phục vụ các khách hàng còn lại bằng cách thử chèn vào mọi khả năng.
    *** PHIÊN BẢN ĐÃ SỬA LỖI KIỂM TRA FE CAPACITY ***
    """
    problem = solution.problem
    customers_to_rescue = list(solution.unserved_customers)
    if not customers_to_rescue:
        return

    print(f"\n--- PHA GIAI CUU: Co {len(customers_to_rescue)} khach hang can giai cuu ---")
    
    rescued_customers = []
    
    for customer in customers_to_rescue:
        best_rescue_option = {"cost": float('inf'), "action": None}

        # Tạo một dictionary để theo dõi tổng tải giao hàng hiện tại của mỗi vệ tinh đang hoạt động
        active_satellites_delivery_load = {
            sat: sum(r.total_load_delivery for r in solution.se_routes if r.satellite == sat)
            for sat in {r.satellite for r in solution.se_routes}
        }

        # --- Duyệt qua tất cả các vệ tinh đang hoạt động ---
        for satellite in active_satellites_delivery_load.keys():
            
            # <<< SỬA LỖI 1: Thêm kiểm tra FE Capacity trước khi thử chèn >>>
            is_fe_capacity_ok = True
            if customer.type == 'DeliveryCustomer':
                current_load = active_satellites_delivery_load.get(satellite, 0)
                if current_load + customer.demand > problem.fe_vehicle_capacity:
                    is_fe_capacity_ok = False
            
            if not is_fe_capacity_ok:
                continue # Bỏ qua vệ tinh này vì nó sẽ bị quá tải FE

            # Cấp 1: Thử chèn vào các tuyến SE hiện có của vệ tinh
            for route in [r for r in solution.se_routes if r.satellite == satellite]:
                pos, cost_increase = route.find_best_insertion_pos(customer)
                if pos is not None and cost_increase < best_rescue_option["cost"]:
                    best_rescue_option.update({
                        "cost": cost_increase,
                        "action": ("insert_existing_se", route, customer, pos)
                    })

            # Cấp 2: Thử tạo tuyến SE mới từ vệ tinh hiện có
            cost_for_new_route = (problem.get_distance(satellite.id, customer.id) + 
                                  problem.get_distance(customer.id, satellite.id))
            if customer.demand <= problem.se_vehicle_capacity:
                arrival_at_cust = 0 + problem.get_distance(satellite.id, customer.id)
                start_service = max(arrival_at_cust, customer.ready_time)
                if start_service <= customer.due_time and cost_for_new_route < best_rescue_option["cost"]:
                    best_rescue_option.update({
                        "cost": cost_for_new_route,
                        "action": ("create_new_se", satellite, customer, 1)
                    })
        
        # Cấp 3: Vẫn giữ nguyên vì nó tạo ra hạ tầng mới, không bị ảnh hưởng bởi tải hiện tại
        if best_rescue_option["action"] is None:
            closest_satellite = min(problem.satellites, key=lambda s: problem.get_distance(s.id, customer.id))
            # Kiểm tra FE capacity cho trường hợp tạo hạ tầng mới
            if not (customer.type == 'DeliveryCustomer' and customer.demand > problem.fe_vehicle_capacity):
                cost_for_new_infra = (problem.get_distance(closest_satellite.id, customer.id) + 
                                    problem.get_distance(customer.id, closest_satellite.id) +
                                    problem.get_distance(problem.depot.id, closest_satellite.id) * 2)
                if customer.demand <= problem.se_vehicle_capacity:
                    arrival_at_cust = 0 + problem.get_distance(closest_satellite.id, customer.id)
                    start_service = max(arrival_at_cust, customer.ready_time)
                    if start_service <= customer.due_time and cost_for_new_infra < best_rescue_option["cost"]:
                        best_rescue_option.update({"cost": cost_for_new_infra, "action": ("create_new_infra", closest_satellite, customer, 1)})
        
        # Thực hiện hành động giải cứu
        if best_rescue_option["action"] is not None:
            action_type, target, cust, pos = best_rescue_option["action"]
            
            if action_type == "insert_existing_se":
                route = target
                route.insert_customer_at_pos(cust, pos)
                print(f"    - [Giai cuu - Cap 1] Da chen KH {cust.id} vao tuyen SE cua ve tinh {route.satellite.id}.")
            
            elif action_type == "create_new_se":
                satellite = target
                new_route = SERoute(satellite, problem)
                new_route.insert_customer_at_pos(cust, pos)
                solution.se_routes.append(new_route)
                print(f"    - [Giai cuu - Cap 2] Da tao tuyen SE moi cho KH {cust.id} tai ve tinh {satellite.id}.")

            elif action_type == "create_new_infra":
                satellite = target
                new_se_route = SERoute(satellite, problem)
                new_se_route.insert_customer_at_pos(cust, pos)
                solution.se_routes.append(new_se_route)
                # Tuyến FE sẽ được tạo lại ở cuối, nên không cần tạo riêng ở đây
                print(f"    - [Giai cuu - Cap 3] Da tao ha tang SE moi cho KH {cust.id} qua ve tinh {satellite.id}. Tuyen FE se duoc tao lai.")
            
            rescued_customers.append(cust)

    # Cập nhật lại danh sách khách hàng chưa được phục vụ
    for cust in rescued_customers:
        if cust in solution.unserved_customers:
            solution.unserved_customers.remove(cust)
            
    # Tái xây dựng lại toàn bộ các tuyến FE sau khi đã có những thay đổi
    if rescued_customers: # Chỉ xây dựng lại nếu có sự thay đổi
        print("    - Tai xay dung lai toan bo cac tuyen FE sau khi giai cuu...")
        _build_fe_routes(solution, use_deadline)

# --- HÀM CHÍNH, ĐÃ ĐƯỢC CẤU TRÚC LẠI ---
def construct_solution(problem, clusters, use_deadline=True):
    deadline_status = "CO AP DUNG DEADLINE" if use_deadline else "BO QUA DEADLINE"
    print(f"\nBat dau xay dung giai phap ({deadline_status})...")
    
    solution = Solution(problem)
    
    if not clusters:
        print("CANH BAO: Danh sach cum trong, khong the xay dung loi giai.")
        return solution

    # GIAI ĐOẠN 1: Xây dựng lời giải SE ban đầu
    print(f"--- GIAI DOAN 1: Xay dung loi giai SE ban dau ({deadline_status}) ---")
    for i, customer_cluster in enumerate(clusters):
        if not customer_cluster: continue
        home_satellite = _find_cluster_satellite(customer_cluster, problem)
        if home_satellite is None: continue
        _build_se_routes_for_cluster(solution, home_satellite, customer_cluster)
        
    print(f"  => Da tao xong {len(solution.se_routes)} tuyen SE ban dau.")
    
    # GIAI ĐOẠN 2: Xây dựng lời giải FE ban đầu
    print("\n--- GIAI DOAN 2: Xay dung loi giai FE ban dau ---")
    _build_fe_routes(solution, use_deadline)
    print(f"  => Da tao xong {len(solution.fe_routes)} tuyen FE ban dau.")

    initial_unserved_count = len(solution.unserved_customers)
    if initial_unserved_count > 0:
        unserved_ids = [c.id for c in solution.unserved_customers]
        print(f"\n=> Xay dung ban dau hoan tat. Co {initial_unserved_count} khach hang chua duoc phuc vu: {unserved_ids}")
    else:
        print("\n=> Xay dung ban dau hoan tat. Tat ca khach hang da duoc phuc vu.")

    # GIAI ĐOẠN 3: Pha giải cứu (nếu cần)
    if initial_unserved_count > 0:
        _rescue_unserved_customers(solution, use_deadline)

    # TÍNH TOÁN KẾT QUẢ CUỐI CÙNG
    solution.calculate_total_cost()
    print(f"\nGIAI PHAP HOAN THANH VOI TONG CHI PHI: {solution.total_cost:.2f}")

    final_unserved_count = len(solution.unserved_customers)
    if final_unserved_count > 0:
        unserved_ids = [c.id for c in solution.unserved_customers]
        print(f"CANH BAO (SAU GIAI CUU): Van con {final_unserved_count} khach hang khong the phuc vu: {unserved_ids}")

    return solution

# --- END OF FILE SolutionBuilder.py ---