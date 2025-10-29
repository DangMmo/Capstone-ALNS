# --- START OF FILE insertion_logic.py (UPDATED WITH CAPACITY CHECK FIX) ---

import copy
import heapq
import itertools
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

# Import from other modules
from data_structures import SERoute, FERoute, Solution

if TYPE_CHECKING:
    from problem_parser import ProblemInstance, Customer, Satellite

class InsertionProcessor:
    def __init__(self, problem: "ProblemInstance"):
        self.problem = problem

    def _calculate_insertion_delay_and_feasibility(
        self, 
        route: SERoute, 
        customer: "Customer", 
        pos_to_insert: int,
        prev_node_id: int, 
        next_node_id: int
    ) -> Optional[Tuple[float, float]]:
        """
        Hàm nội bộ để tính toán sự trễ (delay) và kiểm tra các ràng buộc
        khi chèn `customer` vào giữa `prev_node_id` và `next_node_id`.
        
        BÂY GIỜ BAO GỒM KIỂM TRA TẢI TRỌNG CHẠY DỌC TUYẾN ĐẦY ĐỦ.
        
        Trả về: Tuple (total_delay_at_next_node, cost_increase) nếu khả thi, ngược lại None.
        """
        problem = route.problem
        
        # --- 1. KIỂM TRA TẢI TRỌNG ĐẦY ĐỦ ---
        # Tạo danh sách node tạm thời để mô phỏng
        temp_nodes_id = route.nodes_id[:pos_to_insert] + [customer.id] + route.nodes_id[pos_to_insert:]
        
        # Tính tổng tải trọng giao hàng mới
        new_delivery_load = route.total_load_delivery
        if customer.type == 'DeliveryCustomer':
            new_delivery_load += customer.demand
        
        # Kiểm tra tổng tải trọng giao hàng ban đầu
        if new_delivery_load > problem.se_vehicle_capacity + 1e-6:
            return None
            
        # Mô phỏng tải trọng chạy dọc tuyến
        running_load = new_delivery_load
        for node_id in temp_nodes_id[1:-1]: # Bỏ qua hai node satellite
            cust_obj = problem.node_objects[node_id]
            if cust_obj.type == 'DeliveryCustomer':
                running_load -= cust_obj.demand
            else: # PickupCustomer
                running_load += cust_obj.demand
            
            # Kiểm tra tại mỗi điểm
            if running_load < -1e-6 or running_load > problem.se_vehicle_capacity + 1e-6:
                return None

        # --- 2. TÍNH TOÁN DELAY THỜI GIAN ---
        prev_obj = problem.node_objects[prev_node_id % problem.total_nodes]
        
        departure_at_prev = route.service_start_times.get(prev_node_id, 0.0) + prev_obj.service_time
        arrival_at_customer = departure_at_prev + problem.get_travel_time(prev_obj.id, customer.id)
        start_service_at_customer = max(arrival_at_customer, customer.ready_time)

        if start_service_at_customer > customer.due_time + 1e-6:
            return None
        
        departure_at_customer = start_service_at_customer + customer.service_time
        new_arrival_at_next = departure_at_customer + problem.get_travel_time(customer.id, next_node_id % problem.total_nodes)
        
        old_arrival_at_next = route.service_start_times.get(next_node_id, 0.0) - route.waiting_times.get(next_node_id, 0.0)
        total_delay = new_arrival_at_next - old_arrival_at_next
        
        # --- 3. TÍNH TOÁN CHI PHÍ TĂNG THÊM ---
        cost_increase = (problem.get_distance(prev_obj.id, customer.id) + 
                         problem.get_distance(customer.id, next_node_id % problem.total_nodes) - 
                         problem.get_distance(prev_obj.id, next_node_id % problem.total_nodes))

        return total_delay, cost_increase

    def find_best_insertion_for_se_route(self, route: SERoute, customer: "Customer") -> Optional[Dict]:
        """
        Sử dụng FTS Filter và kiểm tra tải trọng đầy đủ để tìm vị trí chèn tốt nhất.
        """
        best_candidate = {"pos": None, "cost_increase": float('inf')}
        
        if len(route.nodes_id) < 2: 
            return None

        for i in range(len(route.nodes_id) - 1):
            pos_to_insert = i + 1
            prev_node_id, next_node_id = route.nodes_id[i], route.nodes_id[i+1]

            # Tính toán delay và kiểm tra khả thi (bao gồm cả tải trọng đầy đủ)
            result = self._calculate_insertion_delay_and_feasibility(
                route, customer, pos_to_insert, prev_node_id, next_node_id
            )
            
            if result is None:
                continue
            
            total_delay, cost_increase = result

            # --- BỘ LỌC FTS ---
            if total_delay > route.forward_time_slacks.get(next_node_id, 0.0) + 1e-6:
                continue
            
            # Nếu vượt qua tất cả các bộ lọc, đây là một ứng viên hợp lệ
            if cost_increase < best_candidate["cost_increase"]:
                best_candidate["pos"] = pos_to_insert
                best_candidate["cost_increase"] = cost_increase
        
        if best_candidate["pos"] is None:
            return None
        return best_candidate

# ... (Phần còn lại của file: _recalculate_fe_route..., find_best_global_insertion_option, find_k_best_global_insertion_options giữ nguyên y hệt như phiên bản FTS trước)
def _recalculate_fe_route_and_check_feasibility(fe_route: FERoute, problem: "ProblemInstance") -> Tuple[Optional[float], bool]:
    if not fe_route.serviced_se_routes:
        fe_route.total_dist = 0.0
        fe_route.schedule = []
        fe_route.calculate_route_properties()
        return 0.0, True
    depot = problem.depot
    sats_to_visit = {se.satellite for se in fe_route.serviced_se_routes}
    sats_list = sorted(list(sats_to_visit), key=lambda s: problem.get_distance(depot.id, s.id))
    schedule, current_time, current_load = [], 0.0, sum(se.total_load_delivery for se in fe_route.serviced_se_routes)
    schedule.append({'activity': 'DEPART_DEPOT', 'node_id': depot.id, 'load_change': current_load, 'load_after': current_load, 'arrival_time': 0.0, 'start_svc_time': 0.0, 'departure_time': 0.0})
    last_node_id, route_deadlines = depot.id, set()
    for satellite in sats_list:
        arrival_at_sat = current_time + problem.get_travel_time(last_node_id, satellite.id)
        se_routes = [r for r in fe_route.serviced_se_routes if r.satellite == satellite]
        del_load_at_sat = sum(r.total_load_delivery for r in se_routes)
        current_load -= del_load_at_sat
        schedule.append({'activity': 'UNLOAD_DELIV', 'node_id': satellite.id, 'load_change': -del_load_at_sat, 'load_after': current_load, 'arrival_time': arrival_at_sat, 'start_svc_time': arrival_at_sat, 'departure_time': arrival_at_sat})
        latest_se_finish = 0
        for se_route in se_routes:
            se_route.service_start_times[se_route.nodes_id[0]] = arrival_at_sat
            se_route.calculate_full_schedule_and_slacks()
            for cust in se_route.get_customers():
                if hasattr(cust, 'due_time') and se_route.service_start_times.get(cust.id, float('inf')) > cust.due_time + 1e-6:
                    return None, False
                if hasattr(cust, 'deadline'):
                    route_deadlines.add(cust.deadline)
            latest_se_finish = max(latest_se_finish, se_route.service_start_times.get(se_route.nodes_id[-1], 0))
        pickup_load_at_sat = sum(r.total_load_pickup for r in se_routes)
        departure_from_sat = latest_se_finish
        current_load += pickup_load_at_sat
        schedule.append({'activity': 'LOAD_PICKUP', 'node_id': satellite.id, 'load_change': pickup_load_at_sat, 'load_after': current_load, 'arrival_time': latest_se_finish, 'start_svc_time': latest_se_finish, 'departure_time': departure_from_sat})
        current_time, last_node_id = departure_from_sat, satellite.id
    arrival_at_depot = current_time + problem.get_travel_time(last_node_id, depot.id)
    schedule.append({'activity': 'ARRIVE_DEPOT', 'node_id': depot.id, 'load_change': -current_load, 'load_after': 0, 'arrival_time': arrival_at_depot, 'start_svc_time': arrival_at_depot, 'departure_time': arrival_at_depot})
    fe_route.schedule = schedule
    fe_route.calculate_route_properties()
    effective_deadline = min(route_deadlines) if route_deadlines else float('inf')
    if arrival_at_depot > effective_deadline + 1e-6:
        return None, False
    return fe_route.total_dist, True

def find_best_global_insertion_option(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor) -> Dict:
    best_k_options = find_k_best_global_insertion_options(customer, solution, insertion_processor, k=1)
    if best_k_options:
        return best_k_options[0]
    return {'total_cost_increase': float('inf')}

def find_k_best_global_insertion_options(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor, k: int) -> List[Dict]:
    problem = solution.problem
    best_options_heap = []
    counter = itertools.count()
    def add_option_to_heap(cost_increase, option_details):
        count = next(counter)
        if len(best_options_heap) < k:
            heapq.heappush(best_options_heap, (-cost_increase, count, option_details))
        elif cost_increase < -best_options_heap[0][0]:
            heapq.heapreplace(best_options_heap, (-cost_increase, count, option_details))
    # Kịch bản 1: Chèn vào SE route hiện có
    for se_route in solution.se_routes:
        if not se_route.serving_fe_routes:
            continue
        best_local_insertion = insertion_processor.find_best_insertion_for_se_route(se_route, customer)
        if not best_local_insertion or best_local_insertion["pos"] is None:
            continue
        fe_route = list(se_route.serving_fe_routes)[0]
        original_global_cost = se_route.total_dist + fe_route.total_dist
        temp_fe_route = copy.deepcopy(fe_route)
        try:
            temp_se_ref = next(r for r in temp_fe_route.serviced_se_routes if r.satellite.id == se_route.satellite.id and r.nodes_id == se_route.nodes_id)
        except StopIteration:
            continue
        temp_se_ref.insert_customer_at_pos(customer, best_local_insertion['pos'])
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
        if is_feasible:
            total_increase = (temp_se_ref.total_dist + new_fe_cost) - original_global_cost
            option = {
                'total_cost_increase': total_increase,
                'type': 'insert_into_existing_se',
                'se_route': se_route,
                'se_pos': best_local_insertion['pos']
            }
            add_option_to_heap(total_increase, option)
    # Kịch bản 2: Tạo SE route mới
    for satellite in problem.satellites:
        temp_new_se = SERoute(satellite, problem)
        temp_new_se.insert_customer_at_pos(customer, 1)
        se_cost = temp_new_se.total_dist
        # Kịch bản 2b: Tạo FE route mới
        temp_fe_for_new = FERoute(problem)
        temp_fe_for_new.add_serviced_se_route(temp_new_se)
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_new, problem)
        if is_feasible:
            total_increase = se_cost + (new_fe_cost if new_fe_cost is not None else float('inf'))
            option = {
                'total_cost_increase': total_increase,
                'type': 'create_new_se_new_fe',
                'new_satellite': satellite
            }
            add_option_to_heap(total_increase, option)
        # Kịch bản 2a: Mở rộng FE route hiện có
        for fe_route in solution.fe_routes:
            current_fe_delivery_load = sum(r.total_load_delivery for r in fe_route.serviced_se_routes)
            if current_fe_delivery_load + temp_new_se.total_load_delivery > problem.fe_vehicle_capacity:
                continue
            original_fe_cost = fe_route.total_dist
            temp_fe_route = copy.deepcopy(fe_route)
            temp_fe_route.add_serviced_se_route(temp_new_se)
            new_fe_cost_expand, is_feasible_expand = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
            if is_feasible_expand:
                total_increase_expand = se_cost + (new_fe_cost_expand - original_fe_cost)
                option = {
                    'total_cost_increase': total_increase_expand,
                    'type': 'create_new_se_expand_fe',
                    'new_satellite': satellite,
                    'fe_route': fe_route
                }
                add_option_to_heap(total_increase_expand, option)
    sorted_options = sorted([opt for cost, count, opt in best_options_heap], key=lambda x: x['total_cost_increase'])
    return sorted_options


# --- END OF FILE insertion_logic.py ---