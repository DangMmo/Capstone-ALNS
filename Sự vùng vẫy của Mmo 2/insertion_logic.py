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

    def find_all_feasible_insertions_for_se_route(self, route: SERoute, customer: "Customer") -> List[Dict]:
        """
        Tìm tất cả các vị trí chèn khả thi về mặt cục bộ (tải trọng) trong một SE route.
        Hàm này KHÔNG kiểm tra time window, vì time window phụ thuộc vào FE.
        Nó trả về một danh sách các lựa chọn, mỗi lựa chọn là một dict.
        """
        feasible_options = []
        problem = route.problem
        
        for i in range(len(route.nodes_id) - 1):
            pos_to_insert = i + 1
            
            # --- 1. KIỂM TRA TẢI TRỌNG (Kiểm tra duy nhất ở đây) ---
            temp_nodes_id = route.nodes_id[:pos_to_insert] + [customer.id] + route.nodes_id[pos_to_insert:]
            
            new_delivery_load = route.total_load_delivery
            if customer.type == 'DeliveryCustomer':
                new_delivery_load += customer.demand
            if new_delivery_load > problem.se_vehicle_capacity + 1e-6:
                # Nếu tải trọng ban đầu đã vượt quá, không cần thử các vị trí khác trên tuyến này
                break 

            running_load = new_delivery_load
            is_load_feasible = True
            for node_id in temp_nodes_id[1:-1]:
                cust_obj = problem.node_objects[node_id]
                if cust_obj.type == 'DeliveryCustomer': running_load -= cust_obj.demand
                else: running_load += cust_obj.demand
                if running_load < -1e-6 or running_load > problem.se_vehicle_capacity + 1e-6:
                    is_load_feasible = False
                    break
            
            if not is_load_feasible:
                continue # Bỏ qua vị trí này

            # --- 2. TÍNH TOÁN CHI PHÍ CỤC BỘ ---
            prev_node_id = route.nodes_id[pos_to_insert - 1]
            next_node_id = route.nodes_id[pos_to_insert]
            prev_obj = problem.node_objects[prev_node_id % problem.total_nodes]
            next_obj = problem.node_objects[next_node_id % problem.total_nodes]

            cost_increase = (problem.get_distance(prev_obj.id, customer.id) + 
                             problem.get_distance(customer.id, next_obj.id) - 
                             problem.get_distance(prev_obj.id, next_obj.id))
            
            feasible_options.append({
                "pos": pos_to_insert,
                "cost_increase": cost_increase
            })

        return feasible_options


def _recalculate_fe_route_and_check_feasibility(fe_route: FERoute, problem: "ProblemInstance") -> Tuple[Optional[float], bool]:
    # (Hàm này giữ nguyên vai trò tính toán lại lịch trình FE và kiểm tra tất cả ràng buộc)
    if not fe_route.serviced_se_routes:
        fe_route.total_dist = 0.0
        fe_route.schedule = []
        fe_route.calculate_route_properties()
        return 0.0, True
        
    depot = problem.depot
    sats_to_visit = {se.satellite for se in fe_route.serviced_se_routes}
    # Sắp xếp các vệ tinh để có lịch trình FE tất định
    sats_list = sorted(list(sats_to_visit), key=lambda s: problem.get_distance(depot.id, s.id))
    
    schedule = []
    current_time = 0.0
    current_load = sum(se.total_load_delivery for se in fe_route.serviced_se_routes)
    
    schedule.append({'activity': 'DEPART_DEPOT', 'node_id': depot.id, 'load_change': current_load, 'load_after': current_load, 'arrival_time': 0.0, 'start_svc_time': 0.0, 'departure_time': 0.0})
    
    last_node_id = depot.id
    route_deadlines = set()

    for satellite in sats_list:
        arrival_at_sat = current_time + problem.get_travel_time(last_node_id, satellite.id)
        
        se_routes_at_sat = [r for r in fe_route.serviced_se_routes if r.satellite == satellite]
        
        del_load_at_sat = sum(r.total_load_delivery for r in se_routes_at_sat)
        current_load -= del_load_at_sat
        schedule.append({'activity': 'UNLOAD_DELIV', 'node_id': satellite.id, 'load_change': -del_load_at_sat, 'load_after': current_load, 'arrival_time': arrival_at_sat, 'start_svc_time': arrival_at_sat, 'departure_time': arrival_at_sat})
        
        latest_se_finish = 0
        for se_route in se_routes_at_sat:
            # Cập nhật thời gian bắt đầu của SE route và tính lại toàn bộ lịch trình của nó
            se_route.service_start_times[se_route.nodes_id[0]] = arrival_at_sat
            se_route.calculate_full_schedule_and_slacks()
            
            # KIỂM TRA TIME WINDOW CỦA SE ROUTE NGAY SAU KHI TÍNH LẠI
            for cust in se_route.get_customers():
                if hasattr(cust, 'due_time') and se_route.service_start_times.get(cust.id, float('inf')) > cust.due_time + 1e-6:
                    return None, False # Báo cáo không khả thi ngay lập tức
                if hasattr(cust, 'deadline'):
                    route_deadlines.add(cust.deadline)
            
            latest_se_finish = max(latest_se_finish, se_route.service_start_times.get(se_route.nodes_id[-1], 0))

        pickup_load_at_sat = sum(r.total_load_pickup for r in se_routes_at_sat)
        departure_from_sat = latest_se_finish
        current_load += pickup_load_at_sat
        schedule.append({'activity': 'LOAD_PICKUP', 'node_id': satellite.id, 'load_change': pickup_load_at_sat, 'load_after': current_load, 'arrival_time': latest_se_finish, 'start_svc_time': latest_se_finish, 'departure_time': departure_from_sat})
        
        current_time = departure_from_sat
        last_node_id = satellite.id

    arrival_at_depot = current_time + problem.get_travel_time(last_node_id, depot.id)
    schedule.append({'activity': 'ARRIVE_DEPOT', 'node_id': depot.id, 'load_change': -current_load, 'load_after': 0, 'arrival_time': arrival_at_depot, 'start_svc_time': arrival_at_depot, 'departure_time': arrival_at_depot})
    
    fe_route.schedule = schedule
    fe_route.calculate_route_properties()
    
    effective_deadline = min(route_deadlines) if route_deadlines else float('inf')
    if arrival_at_depot > effective_deadline + 1e-6:
        return None, False
        
    return fe_route.total_dist, True

def _calculate_route_proximity(customer: "Customer", se_route: SERoute, problem: "ProblemInstance") -> float:
    if not se_route.get_customers():
        return problem.get_distance(customer.id, se_route.satellite.id)
    min_dist = min(problem.get_distance(customer.id, c.id) for c in se_route.get_customers())
    return min_dist
def find_k_best_global_insertion_options_combined(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor, k: int) -> List[Dict]:
    problem = solution.problem
    best_options_heap = []
    counter = itertools.count()

    def add_option_to_heap(cost_increase, option_details):
        # (Hàm này giữ nguyên)
        count = next(counter)
        if len(best_options_heap) < k:
            heapq.heappush(best_options_heap, (-cost_increase, count, option_details))
        elif cost_increase < -best_options_heap[0][0]:
            heapq.heapreplace(best_options_heap, (-cost_increase, count, option_details))

    # ==========================================================================
    # Kịch bản 1: Chèn vào một SE route hiện có
    # ==========================================================================
    candidate_se_routes = [r for r in solution.se_routes]
    candidate_se_routes.sort(key=lambda r: _calculate_route_proximity(customer, r, problem))

    for se_route in candidate_se_routes[:config.PRUNING_N_SE_ROUTE_CANDIDATES]:
        if not se_route.serving_fe_routes: continue
        
        local_insertions = insertion_processor.find_all_feasible_insertions_for_se_route(se_route, customer)
        if not local_insertions: continue

        for local_option in local_insertions:
            fe_route = list(se_route.serving_fe_routes)[0]
            original_global_cost = se_route.total_dist + fe_route.total_dist
            
            # <<< CẢI TIẾN: BACKUP CẢ CÁC SERoute LÂN CẬN >>>
            # Backup FE route và tất cả các SE route con của nó
            fe_memento = fe_route.backup()
            se_mementos = {se: se.backup() for se in fe_route.serviced_se_routes}

            try:
                # Tìm đúng đối tượng se_route trong số các route đang được quản lý bởi fe_route
                se_route_to_modify = next(se for se in fe_route.serviced_se_routes if se is se_route)
                se_route_to_modify.insert_customer_at_pos(customer, local_option['pos'])
                
                new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(fe_route, problem)
                
                if is_feasible:
                    # Chú ý: se_route_to_modify đã bị thay đổi, nên total_dist của nó cũng thay đổi
                    new_global_cost = se_route_to_modify.total_dist + (new_fe_cost if new_fe_cost is not None else float('inf'))
                    total_increase = new_global_cost - (se_mementos[se_route_to_modify].total_dist + fe_memento.total_dist)

                    option = {'total_cost_increase': total_increase, 'type': 'insert_into_existing_se', 'se_route': se_route, 'se_pos': local_option['pos']}
                    add_option_to_heap(total_increase, option)
            finally:
                # Hoàn tác tất cả
                fe_route.restore(fe_memento)
                for se, memento in se_mementos.items():
                    se.restore(memento)

    # ==========================================================================
    # Kịch bản 2: Tạo một SE route mới 
    # ==========================================================================
    candidate_satellites = problem.satellite_neighbors.get(customer.id, problem.satellites)
    for satellite in candidate_satellites:
        temp_new_se = SERoute(satellite, problem)
        temp_new_se.insert_customer_at_pos(customer, 1)

        # 2b: Tạo FE route mới (Logic này an toàn, không sửa đổi state hiện tại)
        if temp_new_se.total_load_delivery <= problem.fe_vehicle_capacity + 1e-6:
            temp_fe_for_new = FERoute(problem)
            temp_fe_for_new.add_serviced_se_route(temp_new_se)
            new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_new, problem)
            if is_feasible:
                total_increase = temp_new_se.total_dist + (new_fe_cost if new_fe_cost is not None else float('inf'))
                option = {'total_cost_increase': total_increase, 'type': 'create_new_se_new_fe', 'new_satellite': satellite}
                add_option_to_heap(total_increase, option)

        # 2a: Mở rộng FE route hiện có
        for fe_route in solution.fe_routes:
            if sum(r.total_load_delivery for r in fe_route.serviced_se_routes) + temp_new_se.total_load_delivery > problem.fe_vehicle_capacity + 1e-6:
                continue
            
            original_fe_cost = fe_route.total_dist

            # <<< CẢI TIẾN TƯƠNG TỰ: BACKUP CẢ CÁC SERoute CON >>>
            fe_memento_expand = fe_route.backup()
            se_mementos_expand = {se: se.backup() for se in fe_route.serviced_se_routes}
            
            try:
                # temp_new_se là đối tượng mới, không cần backup
                fe_route.add_serviced_se_route(temp_new_se)
                new_fe_cost_expand, is_feasible_expand = _recalculate_fe_route_and_check_feasibility(fe_route, problem)
                
                if is_feasible_expand:
                    total_increase_expand = temp_new_se.total_dist + ((new_fe_cost_expand if new_fe_cost_expand is not None else float('inf')) - original_fe_cost)
                    option = {'total_cost_increase': total_increase_expand, 'type': 'create_new_se_expand_fe', 'new_satellite': satellite, 'fe_route': fe_route}
                    add_option_to_heap(total_increase_expand, option)
            finally:
                # Hoàn tác tất cả
                fe_route.restore(fe_memento_expand)
                for se, memento in se_mementos_expand.items():
                    se.restore(memento)

    sorted_options = sorted([opt for cost, count, opt in best_options_heap], key=lambda x: x['total_cost_increase'])
    return sorted_options


def find_best_global_insertion_option(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor) -> Dict:
    best_k_options = find_k_best_global_insertion_options_combined(customer, solution, insertion_processor, k=1)
    return best_k_options[0] if best_k_options else {'total_cost_increase': float('inf')}

def find_k_best_global_insertion_options(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor, k: int) -> List[Dict]:
    return find_k_best_global_insertion_options_combined(customer, solution, insertion_processor, k)