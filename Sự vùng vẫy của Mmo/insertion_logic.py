import copy
import heapq
import itertools
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

import config
from data_structures import SERoute, FERoute, Solution
from problem_parser import Customer

if TYPE_CHECKING:
    from problem_parser import ProblemInstance, Satellite
    from transaction import RouteMemento

class InsertionProcessor:
    def __init__(self, problem: "ProblemInstance"):
        self.problem = problem

    # <<< HÀM NÀY SẼ ĐƯỢC THAY THẾ HOÀN TOÀN >>>
    def _calculate_insertion_delay_and_feasibility(
        self, route: SERoute, customer: "Customer", pos_to_insert: int
    ) -> Optional[float]:
        """
        Tính toán chi phí và kiểm tra TÍNH KHẢ THI ĐẦY ĐỦ của việc chèn.
        Phiên bản này không dùng slack mà mô phỏng lại lịch trình để đảm bảo 100% đúng đắn.
        Trả về cost_increase nếu khả thi, ngược lại trả về None.
        """
        problem = route.problem
        
        # --- 1. KIỂM TRA TẢI TRỌNG (Giữ nguyên) ---
        temp_nodes_id = route.nodes_id[:pos_to_insert] + [customer.id] + route.nodes_id[pos_to_insert:]
        
        new_delivery_load = route.total_load_delivery
        if customer.type == 'DeliveryCustomer':
            new_delivery_load += customer.demand
        if new_delivery_load > problem.se_vehicle_capacity + 1e-6:
            return None

        running_load = new_delivery_load
        for node_id in temp_nodes_id[1:-1]:
            cust_obj = problem.node_objects[node_id]
            if cust_obj.type == 'DeliveryCustomer': running_load -= cust_obj.demand
            else: running_load += cust_obj.demand
            if running_load < -1e-6 or running_load > problem.se_vehicle_capacity + 1e-6:
                return None
        
        # --- 2. MÔ PHỎNG LẠI LỊCH TRÌNH VÀ KIỂM TRA THỜI GIAN (LOGIC MỚI) ---
        current_time = route.service_start_times[route.nodes_id[0]]
        last_node_id = route.nodes_id[0]

        for i in range(1, len(temp_nodes_id)):
            current_node_id = temp_nodes_id[i]
            
            # Lấy thông tin của node trước và node hiện tại
            last_node_obj = problem.node_objects[last_node_id % problem.total_nodes]
            current_node_obj = problem.node_objects[current_node_id % problem.total_nodes]

            # Thời gian rời khỏi node trước
            st_last = last_node_obj.service_time if last_node_obj.type != 'Satellite' else 0.0
            departure_at_last = current_time + st_last
            
            # Thời gian đến node hiện tại
            arrival_at_current = departure_at_last + problem.get_travel_time(last_node_obj.id, current_node_obj.id)
            
            # Thời gian bắt đầu phục vụ tại node hiện tại
            start_service_at_current = max(arrival_at_current, getattr(current_node_obj, 'ready_time', 0))

            # *** KIỂM TRA DUE TIME NGAY TẠI ĐÂY ***
            if start_service_at_current > getattr(current_node_obj, 'due_time', float('inf')) + 1e-6:
                return None # Vi phạm -> không khả thi

            # Cập nhật thời gian cho vòng lặp tiếp theo
            current_time = start_service_at_current
            last_node_id = current_node_id
        
        # --- 3. TÍNH TOÁN CHI PHÍ (Giữ nguyên) ---
        prev_node_id = route.nodes_id[pos_to_insert - 1]
        next_node_id = route.nodes_id[pos_to_insert]
        prev_obj = problem.node_objects[prev_node_id % problem.total_nodes]
        next_obj = problem.node_objects[next_node_id % problem.total_nodes]

        cost_increase = (problem.get_distance(prev_obj.id, customer.id) + 
                         problem.get_distance(customer.id, next_obj.id) - 
                         problem.get_distance(prev_obj.id, next_obj.id))
                         
        return cost_increase

    # <<< HÀM NÀY CŨNG CẦN CẬP NHẬT ĐỂ PHÙ HỢP >>>
    def find_best_insertion_for_se_route(self, route: SERoute, customer: "Customer") -> Optional[Dict]:
        best_candidate = {"pos": None, "cost_increase": float('inf')}
        if len(route.nodes_id) < 2:
            return None
        
        for i in range(len(route.nodes_id) - 1):
            pos_to_insert = i + 1
            
            # Gọi hàm kiểm tra đã được cập nhật
            cost_increase = self._calculate_insertion_delay_and_feasibility(
                route, customer, pos_to_insert
            )
            
            if cost_increase is None:
                continue

            if cost_increase < best_candidate["cost_increase"]:
                best_candidate["pos"] = pos_to_insert
                best_candidate["cost_increase"] = cost_increase
        
        if best_candidate["pos"] is None:
            return None
        return best_candidate

def _recalculate_fe_route_and_check_feasibility(fe_route: FERoute, problem: "ProblemInstance") -> Tuple[Optional[float], bool]:
    # (Nội dung hàm này không thay đổi, nó đã hoạt động tại chỗ)
    if not fe_route.serviced_se_routes:
        fe_route.total_dist, fe_route.schedule = 0.0, []
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
        se_routes_at_sat = [r for r in fe_route.serviced_se_routes if r.satellite == satellite]
        del_load_at_sat = sum(r.total_load_delivery for r in se_routes_at_sat)
        current_load -= del_load_at_sat
        schedule.append({'activity': 'UNLOAD_DELIV', 'node_id': satellite.id, 'load_change': -del_load_at_sat, 'load_after': current_load, 'arrival_time': arrival_at_sat, 'start_svc_time': arrival_at_sat, 'departure_time': arrival_at_sat})
        latest_se_finish = 0
        for se_route in se_routes_at_sat:
            se_route.service_start_times[se_route.nodes_id[0]] = arrival_at_sat
            se_route.calculate_full_schedule_and_slacks()
            for cust in se_route.get_customers():
                if hasattr(cust, 'due_time') and se_route.service_start_times.get(cust.id, float('inf')) > cust.due_time + 1e-6: return None, False
                if hasattr(cust, 'deadline'): route_deadlines.add(cust.deadline)
            latest_se_finish = max(latest_se_finish, se_route.service_start_times.get(se_route.nodes_id[-1], 0))
        pickup_load_at_sat = sum(r.total_load_pickup for r in se_routes_at_sat)
        departure_from_sat = latest_se_finish
        current_load += pickup_load_at_sat
        schedule.append({'activity': 'LOAD_PICKUP', 'node_id': satellite.id, 'load_change': pickup_load_at_sat, 'load_after': current_load, 'arrival_time': latest_se_finish, 'start_svc_time': latest_se_finish, 'departure_time': departure_from_sat})
        current_time, last_node_id = departure_from_sat, satellite.id
    arrival_at_depot = current_time + problem.get_travel_time(last_node_id, depot.id)
    schedule.append({'activity': 'ARRIVE_DEPOT', 'node_id': depot.id, 'load_change': -current_load, 'load_after': 0, 'arrival_time': arrival_at_depot, 'start_svc_time': arrival_at_depot, 'departure_time': arrival_at_depot})
    fe_route.schedule = schedule
    fe_route.calculate_route_properties()
    effective_deadline = min(route_deadlines) if route_deadlines else float('inf')
    if arrival_at_depot > effective_deadline + 1e-6: return None, False
    return fe_route.total_dist, True

def _calculate_route_proximity(customer: "Customer", se_route: SERoute, problem: "ProblemInstance") -> float:
    # (Hàm này không thay đổi)
    if not se_route.get_customers(): return problem.get_distance(customer.id, se_route.satellite.id)
    min_dist = min(problem.get_distance(customer.id, c.id) for c in se_route.get_customers())
    return min_dist

def find_k_best_global_insertion_options_combined(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor, k: int) -> List[Dict]:
    """
    Hàm tìm kiếm các lựa chọn chèn tốt nhất, đã được tái cấu trúc để sử dụng
    cơ chế backup/restore thay vì deepcopy và sửa lỗi kiểm tra tải trọng.
    """
    problem = solution.problem
    best_options_heap = []
    counter = itertools.count()

    def add_option_to_heap(cost_increase, option_details):
        """Hàm nội bộ để quản lý heap chứa k lựa chọn tốt nhất."""
        count = next(counter)
        if len(best_options_heap) < k:
            heapq.heappush(best_options_heap, (-cost_increase, count, option_details))
        elif cost_increase < -best_options_heap[0][0]:
            heapq.heapreplace(best_options_heap, (-cost_increase, count, option_details))

    # ==========================================================================
    # Kịch bản 1: Chèn vào một SE route hiện có
    # ==========================================================================
    # Tạo danh sách các ứng viên SE route dựa trên độ gần
    candidate_se_routes = [
        r for r in solution.se_routes if _calculate_route_proximity(customer, r, problem) < float('inf')
    ]
    candidate_se_routes.sort(key=lambda r: _calculate_route_proximity(customer, r, problem))

    # Chỉ xem xét N ứng viên hàng đầu để tăng tốc (pruning)
    for se_route in candidate_se_routes[:config.PRUNING_N_SE_ROUTE_CANDIDATES]:
        if not se_route.serving_fe_routes:
            continue
        
        best_local_insertion = insertion_processor.find_best_insertion_for_se_route(se_route, customer)
        
        if best_local_insertion:
            fe_route = list(se_route.serving_fe_routes)[0]
            original_global_cost = se_route.total_dist + fe_route.total_dist
            
            # Sử dụng cơ chế Backup/Restore để tạo sandbox an toàn và hiệu quả
            fe_memento = fe_route.backup()
            se_memento = se_route.backup()
            
            try:
                # Thực hiện thay đổi tạm thời trên các đối tượng thật
                se_route.insert_customer_at_pos(customer, best_local_insertion['pos'])
                new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(fe_route, problem)
                
                if is_feasible:
                    new_global_cost = se_route.total_dist + (new_fe_cost if new_fe_cost is not None else float('inf'))
                    total_increase = new_global_cost - original_global_cost
                    option = {
                        'total_cost_increase': total_increase,
                        'type': 'insert_into_existing_se',
                        'se_route': se_route,
                        'se_pos': best_local_insertion['pos']
                    }
                    add_option_to_heap(total_increase, option)
            finally:
                # Luôn luôn hoàn tác các thay đổi sau khi đã đánh giá xong
                fe_route.restore(fe_memento)
                se_route.restore(se_memento)

    # ==========================================================================
    # Kịch bản 2: Tạo một SE route mới (và có thể cả FE route mới)
    # ==========================================================================
    candidate_satellites = problem.satellite_neighbors.get(customer.id, problem.satellites)
    for satellite in candidate_satellites:
        # Tạo một SE route tạm thời cho khách hàng tại vệ tinh này
        temp_new_se = SERoute(satellite, problem)
        temp_new_se.insert_customer_at_pos(customer, 1)

        # Kiểm tra nhanh tính khả thi về time window của chính SE route này
        if not all(
            temp_new_se.service_start_times.get(c.id, float('inf')) <= c.due_time + 1e-6
            for c in temp_new_se.get_customers()
        ):
            continue
        
        se_cost = temp_new_se.total_dist

        # ---
        # 2b: Đánh giá việc tạo một FE route hoàn toàn mới
        # ---
        # Kiểm tra tải trọng của chính FE route mới này
        if temp_new_se.total_load_delivery <= problem.fe_vehicle_capacity + 1e-6:
            temp_fe_for_new = FERoute(problem)
            temp_fe_for_new.add_serviced_se_route(temp_new_se)
            new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_new, problem)
            if is_feasible:
                total_increase = se_cost + (new_fe_cost if new_fe_cost is not None else float('inf'))
                option = {'total_cost_increase': total_increase, 'type': 'create_new_se_new_fe', 'new_satellite': satellite}
                add_option_to_heap(total_increase, option)

        # ---
        # 2a: Đánh giá việc mở rộng một FE route hiện có
        # ---
        for fe_route in solution.fe_routes:
            # <<< SỬA LỖI KIỂM TRA TẢI TRỌNG >>>
            current_fe_delivery_load = sum(r.total_load_delivery for r in fe_route.serviced_se_routes)
            new_se_delivery_load = temp_new_se.total_load_delivery
            
            # Kiểm tra tải trọng trước khi thực hiện các tính toán tốn kém
            if current_fe_delivery_load + new_se_delivery_load > problem.fe_vehicle_capacity + 1e-6:
                continue

            # Nếu qua được, mới tiếp tục backup và đánh giá
            original_fe_cost = fe_route.total_dist
            fe_memento_expand = fe_route.backup()
            
            try:
                # Thực hiện thay đổi tạm thời
                fe_route.add_serviced_se_route(temp_new_se)
                
                new_fe_cost_expand, is_feasible_expand = _recalculate_fe_route_and_check_feasibility(fe_route, problem)
                
                if is_feasible_expand:
                    total_increase_expand = se_cost + ((new_fe_cost_expand if new_fe_cost_expand is not None else float('inf')) - original_fe_cost)
                    option = {'total_cost_increase': total_increase_expand, 'type': 'create_new_se_expand_fe', 'new_satellite': satellite, 'fe_route': fe_route}
                    add_option_to_heap(total_increase_expand, option)
            finally:
                # Luôn hoàn tác sau khi đánh giá để đưa fe_route về trạng thái ban đầu
                fe_route.restore(fe_memento_expand)

    # Trả về danh sách k lựa chọn tốt nhất đã được sắp xếp
    sorted_options = sorted([opt for cost, count, opt in best_options_heap], key=lambda x: x['total_cost_increase'])
    return sorted_options
# Các hàm find_best... và find_k_best... chỉ là wrapper
def find_best_global_insertion_option(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor) -> Dict:
    best_k_options = find_k_best_global_insertion_options_combined(customer, solution, insertion_processor, k=1)
    return best_k_options[0] if best_k_options else {'total_cost_increase': float('inf')}

def find_k_best_global_insertion_options(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor, k: int) -> List[Dict]:
    return find_k_best_global_insertion_options_combined(customer, solution, insertion_processor, k)