# --- START OF FILE insertion_logic.py ---

import copy
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

# Import from other modules
from data_structures import SERoute, FERoute, Solution

if TYPE_CHECKING:
    from problem_parser import ProblemInstance, Customer, Satellite

class InsertionProcessor:
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
    if not fe_route.serviced_se_routes:
        fe_route.total_dist = 0.0
        fe_route.schedule = []
        return 0.0, True

    depot = problem.depot
    sats_to_visit = {se.satellite for se in fe_route.serviced_se_routes}
    current_loc = depot
    
    sat_sequence: List["Satellite"] = []
    while sats_to_visit:
        nearest_sat = min(sats_to_visit, key=lambda s: problem.get_distance(current_loc.id, s.id))
        sat_sequence.append(nearest_sat)
        sats_to_visit.remove(nearest_sat)
        current_loc = nearest_sat

    schedule, current_time, current_load = [], 0.0, sum(se.total_load_delivery for se in fe_route.serviced_se_routes)
    schedule.append({'activity': 'DEPART_DEPOT', 'node_id': depot.id, 'load_change': current_load, 'load_after': current_load, 'arrival_time': 0.0, 'start_svc_time': 0.0, 'departure_time': 0.0})
    last_node_id, route_deadlines = depot.id, set()

    for satellite in sat_sequence:
        arrival_at_sat = current_time + problem.get_travel_time(last_node_id, satellite.id)
        
        se_routes = [r for r in fe_route.serviced_se_routes if r.satellite == satellite]
        del_load_at_sat = sum(r.total_load_delivery for r in se_routes)
        schedule.append({'activity': 'UNLOAD_DELIV', 'node_id': satellite.id, 'load_change': -del_load_at_sat, 'load_after': current_load - del_load_at_sat, 'arrival_time': arrival_at_sat, 'start_svc_time': arrival_at_sat, 'departure_time': arrival_at_sat})
        
        latest_se_finish = 0
        for se_route in se_routes:
            se_route.service_start_times[se_route.nodes_id[0]] = arrival_at_sat
            se_route.calculate_full_schedule_and_slacks()
            for cust in se_route.get_customers():
                if se_route.service_start_times.get(cust.id, float('inf')) > cust.due_time + 1e-6:
                    return None, False
                if hasattr(cust, 'deadline'):
                    route_deadlines.add(cust.deadline)
            latest_se_finish = max(latest_se_finish, se_route.service_start_times.get(se_route.nodes_id[-1], 0))
        
        pickup_load_at_sat = sum(r.total_load_pickup for r in se_routes)
        departure_from_sat = latest_se_finish + satellite.service_time
        schedule.append({'activity': 'LOAD_PICKUP', 'node_id': satellite.id, 'load_change': pickup_load_at_sat, 'load_after': current_load - del_load_at_sat + pickup_load_at_sat, 'arrival_time': latest_se_finish, 'start_svc_time': latest_se_finish, 'departure_time': departure_from_sat})
        current_time, current_load, last_node_id = departure_from_sat, current_load - del_load_at_sat + pickup_load_at_sat, satellite.id

    arrival_at_depot = current_time + problem.get_travel_time(last_node_id, depot.id)
    schedule.append({'activity': 'ARRIVE_DEPOT', 'node_id': depot.id, 'load_change': -current_load, 'load_after': 0, 'arrival_time': arrival_at_depot, 'start_svc_time': arrival_at_depot, 'departure_time': arrival_at_depot})
    
    fe_route.schedule = schedule
    fe_route.calculate_route_properties()
    
    effective_deadline = min(route_deadlines) if route_deadlines else float('inf')
    if arrival_at_depot > effective_deadline + 1e-6:
        return None, False

    return fe_route.total_dist, True

def find_best_global_insertion_option(customer: "Customer", solution: Solution, insertion_processor: InsertionProcessor) -> Dict:
    problem = solution.problem
    best_option = {'total_cost_increase': float('inf')}

    for se_route in solution.se_routes:
        insertion_result = insertion_processor.find_best_insertion_for_se_route(se_route, customer)
        if not (insertion_result and se_route.serving_fe_routes):
            continue
        
        fe_route = list(se_route.serving_fe_routes)[0]
        original_global_cost = se_route.total_dist + fe_route.total_dist
        temp_fe_route = copy.deepcopy(fe_route)
        try:
            temp_se_ref = next(r for r in temp_fe_route.serviced_se_routes if r.nodes_id == se_route.nodes_id and r.satellite.id == se_route.satellite.id)
        except StopIteration:
            continue
            
        temp_se_ref.insert_customer_at_pos(customer, insertion_result['pos'])
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
        
        if is_feasible:
            total_increase = (temp_se_ref.total_dist + new_fe_cost) - original_global_cost
            if total_increase < best_option['total_cost_increase']:
                best_option.update({
                    'total_cost_increase': total_increase,
                    'type': 'insert_into_existing_se',
                    'se_route': se_route,
                    'se_pos': insertion_result['pos']
                })

    for satellite in problem.satellites:
        temp_new_se = SERoute(satellite, problem)
        temp_new_se.insert_customer_at_pos(customer, 1)
        se_cost = temp_new_se.total_dist

        # Kịch bản 2b
        temp_fe_for_new = FERoute(problem)
        temp_fe_for_new.add_serviced_se_route(temp_new_se)
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_new, problem)
        if is_feasible and (se_cost + new_fe_cost) < best_option['total_cost_increase']:
            best_option.update({
                'total_cost_increase': se_cost + new_fe_cost,
                'type': 'create_new_se_new_fe',
                'new_satellite': satellite
            })

        # Kịch bản 2a
        for fe_route in solution.fe_routes:
            if sum(r.total_load_delivery for r in fe_route.serviced_se_routes) + temp_new_se.total_load_delivery > problem.fe_vehicle_capacity:
                continue
            
            original_fe_cost = fe_route.total_dist
            temp_fe_route = copy.deepcopy(fe_route)
            temp_fe_route.add_serviced_se_route(temp_new_se)
            new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
            
            if is_feasible:
                total_increase = se_cost + (new_fe_cost - original_fe_cost)
                if total_increase < best_option['total_cost_increase']:
                    best_option.update({
                        'total_cost_increase': total_increase,
                        'type': 'create_new_se_expand_fe',
                        'new_satellite': satellite,
                        'fe_route': fe_route
                    })
    return best_option

# --- END OF FILE insertion_logic.py ---