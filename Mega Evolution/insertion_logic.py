# --- START OF FILE insertion_logic.py (FIXED) ---

import copy
import heapq
import itertools # THÊM IMPORT MỚI
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

# Import from other modules
from data_structures import SERoute, FERoute, Solution

if TYPE_CHECKING:
    from problem_parser import ProblemInstance, Customer, Satellite

class InsertionProcessor:
    # ... (Nội dung lớp này giữ nguyên) ...
    def __init__(self, problem: "ProblemInstance"):
        self.problem = problem

    def find_best_insertion_for_se_route(self, route: SERoute, customer: "Customer") -> Optional[Dict]:
        best_candidate = {"pos": None, "cost_increase": float('inf')}
        if len(route.nodes_id) < 2: return None

        for i in range(len(route.nodes_id) - 1):
            pos_to_insert = i + 1
            
            is_cap_ok = True
            temp_del_load = route.total_load_delivery
            if customer.type == 'DeliveryCustomer':
                temp_del_load += customer.demand
            if temp_del_load > self.problem.se_vehicle_capacity:
                continue

            temp_nodes_cap = route.nodes_id[:pos_to_insert] + [customer.id] + route.nodes_id[pos_to_insert:]
            running_load = temp_del_load
            for node_id in temp_nodes_cap[1:-1]:
                cust_obj = self.problem.node_objects[node_id]
                if cust_obj.type == 'DeliveryCustomer': running_load -= cust_obj.demand
                else: running_load += cust_obj.demand
                if running_load < 0 or running_load > self.problem.se_vehicle_capacity:
                    is_cap_ok = False; break
            if not is_cap_ok: continue
            
            temp_route = copy.deepcopy(route)
            temp_route.insert_customer_at_pos(customer, pos_to_insert)
            
            is_feasible = all(
                temp_route.service_start_times.get(node_id, float('inf')) <= self.problem.node_objects[node_id].due_time + 1e-6
                for node_id in temp_route.nodes_id[1:-1]
            )
            if not is_feasible: continue
            
            cost_increase = temp_route.total_dist - route.total_dist
            if cost_increase < best_candidate["cost_increase"]:
                best_candidate["pos"] = pos_to_insert
                best_candidate["cost_increase"] = cost_increase
        
        if best_candidate["pos"] is None: return None
        return best_candidate


def _recalculate_fe_route_and_check_feasibility(fe_route: FERoute, problem: "ProblemInstance") -> Tuple[Optional[float], bool]:
    # ... (Nội dung hàm này giữ nguyên) ...
    if not fe_route.serviced_se_routes:
        fe_route.total_dist = 0.0
        fe_route.schedule = []
        fe_route.calculate_route_properties()
        return 0.0, True

    depot = problem.depot
    sats_to_visit = {se.satellite for se in fe_route.serviced_se_routes}
    current_loc = depot
    
    sat_sequence: List["Satellite"] = []
    # Sort satellites by distance from current location to make the path deterministic
    sats_list = sorted(list(sats_to_visit), key=lambda s: problem.get_distance(current_loc.id, s.id))

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
        departure_from_sat = latest_se_finish # Service time for satellite is now part of SE route time
        
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
    # ... (Nội dung hàm này giữ nguyên) ...
    # This function is now a special case of the k-best function
    best_k_options = find_k_best_global_insertion_options(customer, solution, insertion_processor, k=1)
    if best_k_options:
        return best_k_options[0]
    return {'total_cost_increase': float('inf')}


def find_k_best_global_insertion_options(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor, k: int) -> List[Dict]:
    """
    Tìm k lựa chọn chèn tốt nhất trên toàn bộ lời giải cho một khách hàng.
    """
    problem = solution.problem
    best_options_heap = []
    
    # SỬA LỖI: Thêm bộ đếm để phá vỡ thế hòa
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
        
        insertion_result = insertion_processor.find_best_insertion_for_se_route(se_route, customer)
        if not insertion_result:
            continue
        
        fe_route = list(se_route.serving_fe_routes)[0]
        original_global_cost = se_route.total_dist + fe_route.total_dist
        
        temp_fe_route = copy.deepcopy(fe_route)
        try:
            # A more robust way to find the corresponding SE route in the copied FE route
            temp_se_ref = next(r for r in temp_fe_route.serviced_se_routes if r.satellite.id == se_route.satellite.id and r.nodes_id == se_route.nodes_id)
        except StopIteration:
            continue
            
        temp_se_ref.insert_customer_at_pos(customer, insertion_result['pos'])
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
        
        if is_feasible:
            total_increase = (temp_se_ref.total_dist + (new_fe_cost if new_fe_cost is not None else float('inf'))) - original_global_cost
            option = {
                'total_cost_increase': total_increase,
                'type': 'insert_into_existing_se',
                'se_route': se_route,
                'se_pos': insertion_result['pos']
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
            if sum(r.total_load_delivery for r in fe_route.serviced_se_routes) + temp_new_se.total_load_delivery > problem.fe_vehicle_capacity:
                continue
            
            original_fe_cost = fe_route.total_dist
            temp_fe_route = copy.deepcopy(fe_route)
            temp_fe_route.add_serviced_se_route(temp_new_se)
            new_fe_cost_expand, is_feasible_expand = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
            
            if is_feasible_expand:
                total_increase_expand = se_cost + ((new_fe_cost_expand if new_fe_cost_expand is not None else float('inf')) - original_fe_cost)
                option = {
                    'total_cost_increase': total_increase_expand,
                    'type': 'create_new_se_expand_fe',
                    'new_satellite': satellite,
                    'fe_route': fe_route
                }
                add_option_to_heap(total_increase_expand, option)

    # Chuyển từ heap sang danh sách đã sắp xếp
    sorted_options = sorted([opt for cost, count, opt in best_options_heap], key=lambda x: x['total_cost_increase'])
    return sorted_options

# --- END OF FILE insertion_logic.py ---