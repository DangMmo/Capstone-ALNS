# --- START OF FILE insertion_logic.py (FIXED NameError) ---

import copy
import heapq
import itertools
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

from data_structures import SERoute, FERoute, Solution

# <<< SỬA LỖI NẰM Ở ĐÂY >>>
# Thêm các import cần thiết cho Type Hinting vào khối này
if TYPE_CHECKING:
    from problem_parser import ProblemInstance, Customer, Satellite
# <<< KẾT THÚC SỬA LỖI >>>


def _recalculate_fe_route_and_check_feasibility(fe_route: FERoute, problem: "ProblemInstance") -> Tuple[Optional[float], bool]:
    # ... (Nội dung hàm này giữ nguyên) ...
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
                if hasattr(cust, 'due_time') and se_route.service_start_times.get(cust.id, float('inf')) > cust.due_time + 1e-6: return None, False
                if hasattr(cust, 'deadline'): route_deadlines.add(cust.deadline)
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
    if arrival_at_depot > effective_deadline + 1e-6: return None, False
    return fe_route.total_dist, True

def simulate_fe_recalculation_with_se_update(fe_route: "FERoute", problem: "ProblemInstance", se_route_to_update: "SERoute", update_info: Dict) -> Tuple[Optional[float], bool]:
    depot = problem.depot
    sats_to_visit = {se.satellite for se in fe_route.serviced_se_routes}
    sats_list = sorted(list(sats_to_visit), key=lambda s: problem.get_distance(depot.id, s.id))
    current_time, last_node_id = 0.0, depot.id
    route_deadlines = set()
    path_nodes = [depot.id]
    for satellite in sats_list:
        arrival_at_sat = current_time + problem.get_travel_time(last_node_id, satellite.id)
        path_nodes.append(satellite.id)
        se_routes_at_this_sat = [r for r in fe_route.serviced_se_routes if r.satellite == satellite]
        latest_se_finish = 0
        for se_route in se_routes_at_this_sat:
            if se_route is se_route_to_update:
                latest_se_finish = max(latest_se_finish, update_info['new_schedule_end_time'])
                route_deadlines.update(update_info['new_deadlines'])
            else:
                start_se_time = se_route.service_start_times.get(se_route.nodes_id[0], 0.0)
                end_se_time = se_route.service_start_times.get(se_route.nodes_id[-1], 0.0)
                duration = end_se_time - start_se_time
                first_cust_ready = 0.0
                if se_route.get_customers(): first_cust_ready = getattr(se_route.get_customers()[0], 'ready_time', 0.0)
                effective_start = max(arrival_at_sat, first_cust_ready)
                latest_se_finish = max(latest_se_finish, effective_start + duration)
                deadlines = {c.deadline for c in se_route.get_customers() if hasattr(c, 'deadline')}
                route_deadlines.update(deadlines)
        current_time, last_node_id = latest_se_finish, satellite.id
    arrival_at_depot = current_time + problem.get_travel_time(last_node_id, depot.id)
    path_nodes.append(depot.id)
    new_total_dist = sum(problem.get_distance(path_nodes[i], path_nodes[i+1]) for i in range(len(path_nodes) - 1))
    effective_deadline = min(route_deadlines) if route_deadlines else float('inf')
    if arrival_at_depot > effective_deadline + 1e-6: return None, False
    return new_total_dist, True

def find_best_global_insertion_option(customer: "Customer", solution: "Solution") -> Dict:
    best_k_options = find_k_best_global_insertion_options(customer, solution, k=1)
    if best_k_options: return best_k_options[0]
    return {'total_cost_increase': float('inf')}

def find_k_best_global_insertion_options(customer: "Customer", solution: "Solution", k: int) -> List[Dict]:
    problem = solution.problem
    best_options_heap = []
    counter = itertools.count()
    def add_option_to_heap(cost_increase, option_details):
        count = next(counter)
        if len(best_options_heap) < k: heapq.heappush(best_options_heap, (-cost_increase, count, option_details))
        elif cost_increase < -best_options_heap[0][0]: heapq.heapreplace(best_options_heap, (-cost_increase, count, option_details))

    # Kịch bản 1: Chèn vào SE route hiện có (KHÔNG DÙNG DEEPCOPY)
    for se_route in solution.se_routes:
        if not se_route.serving_fe_routes: continue
        fe_route = list(se_route.serving_fe_routes)[0]
        fe_arrival_time = se_route.service_start_times.get(se_route.nodes_id[0], 0.0)
        for i in range(len(se_route.nodes_id) - 1):
            pos_to_insert = i + 1
            se_update_info = se_route.calculate_insertion_properties(customer, pos_to_insert, fe_arrival_time)
            if not se_update_info: continue
            new_fe_cost, is_fe_feasible = simulate_fe_recalculation_with_se_update(fe_route, problem, se_route, se_update_info)
            if is_fe_feasible:
                original_global_cost = se_route.total_dist + fe_route.total_dist
                new_global_cost = se_update_info['new_total_dist'] + new_fe_cost
                total_increase = new_global_cost - original_global_cost
                option = {'total_cost_increase': total_increase, 'type': 'insert_into_existing_se', 'se_route': se_route, 'se_pos': pos_to_insert}
                add_option_to_heap(total_increase, option)

    # Kịch bản 2: Tạo SE route mới (Vẫn giữ deepcopy ở đây vì ít tốn kém hơn)
    for satellite in problem.satellites:
        # 2a: Mở rộng FE route hiện có
        for fe_route in solution.fe_routes:
            temp_se = SERoute(satellite, problem)
            temp_se.insert_customer_at_pos(customer, 1)
            if sum(r.total_load_delivery for r in fe_route.serviced_se_routes) + temp_se.total_load_delivery > problem.fe_vehicle_capacity: continue
            original_fe_cost = fe_route.total_dist
            temp_fe_for_sim = copy.deepcopy(fe_route)
            temp_fe_for_sim.add_serviced_se_route(temp_se)
            new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_sim, problem)
            if is_feasible:
                total_increase = temp_se.total_dist + (new_fe_cost - original_fe_cost)
                option = {'total_cost_increase': total_increase, 'type': 'create_new_se_expand_fe', 'new_satellite': satellite, 'fe_route': fe_route}
                add_option_to_heap(total_increase, option)
        
        # 2b: Tạo FE route mới
        temp_se_for_new_fe = SERoute(satellite, problem)
        temp_se_for_new_fe.insert_customer_at_pos(customer, 1)
        temp_fe_for_new_fe = FERoute(problem)
        temp_fe_for_new_fe.add_serviced_se_route(temp_se_for_new_fe)
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_new_fe, problem)
        if is_feasible:
            total_increase = temp_se_for_new_fe.total_dist + new_fe_cost
            option = {'total_cost_increase': total_increase, 'type': 'create_new_se_new_fe', 'new_satellite': satellite}
            add_option_to_heap(total_increase, option)

    sorted_options = sorted([opt for cost, count, opt in best_options_heap], key=lambda x: x['total_cost_increase'])
    return sorted_options

# --- END OF FILE insertion_logic.py ---