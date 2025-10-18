# --- START OF FILE main_single_file.py (WITH LNS REFINEMENT) ---

import pandas as pd
import math
import copy
import random
from typing import Dict, List, Set, Optional, Tuple, Callable

# ==============================================================================
# PHẦN 1: PARSER & DATA STRUCTURES (Đã hoạt động tốt)
# ==============================================================================
class Node:
    def __init__(self, node_id, x, y): self.id, self.x, self.y, self.service_time = int(node_id), int(x), int(y), 0.0
class Depot(Node):
    def __init__(self, node_id, x, y): super().__init__(node_id, x, y); self.type = 'Depot'
class Satellite(Node):
    def __init__(self, node_id, x, y, st): super().__init__(node_id, x, y); self.type, self.service_time, self.dist_id = 'Satellite', float(st), self.id
class Customer(Node):
    def __init__(self, node_id, x, y, d, st, et, lt): super().__init__(node_id, x, y); self.demand, self.service_time, self.ready_time, self.due_time = float(d), float(st), float(et), float(lt)
class DeliveryCustomer(Customer):
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.type = 'DeliveryCustomer'
class PickupCustomer(Customer):
    def __init__(self, node_id, x, y, d, st, et, lt, deadline): super().__init__(node_id, x, y, d, st, et, lt); self.type, self.deadline = 'PickupCustomer', float(deadline)

class ProblemInstance:
    def __init__(self, file_path, vehicle_speed=1.0):
        df = pd.read_csv(file_path); df.columns = df.columns.str.strip()
        self.depot, self.satellites, self.customers, node_objects = None, [], [], {}
        for i, row in df.iterrows():
            node = None
            if row['Type'] == 0: node = Depot(i, row['X'], row['Y']); self.depot = node
            elif row['Type'] == 1: node = Satellite(i, row['X'], row['Y'], row['Service Time']); self.satellites.append(node)
            elif row['Type'] == 2: node = DeliveryCustomer(i, row['X'], row['Y'], row['Demand'], row['Service Time'], row['Early'], row['Latest']); self.customers.append(node)
            elif row['Type'] == 3: node = PickupCustomer(i, row['X'], row['Y'], row['Demand'], row['Service Time'], row['Early'], row['Latest'], row['Deadline']); self.customers.append(node)
            if node: node_objects[i] = node
        self.node_objects, self.total_nodes = node_objects, len(node_objects)
        for sat in self.satellites: sat.coll_id = sat.id + self.total_nodes
        self.fe_vehicle_capacity, self.se_vehicle_capacity, self.vehicle_speed = df.iloc[0]['FE Cap'], df.iloc[0]['SE Cap'], vehicle_speed
        nodes = [self.depot] + self.satellites + self.customers; self.dist_matrix = {n1.id: {n2.id: math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2) for n2 in nodes} for n1 in nodes}
    def get_distance(self, n1, n2): return self.dist_matrix.get(n1, {}).get(n2, float('inf'))
    def get_travel_time(self, n1, n2): return self.get_distance(n1, n2) / self.vehicle_speed if self.vehicle_speed > 0 else float('inf')

class FERoute:
    def __init__(self, problem: ProblemInstance): self.problem, self.serviced_se_routes, self.schedule, self.total_dist, self.total_time, self.route_deadline = problem, set(), [], 0.0, 0.0, float('inf')
    def add_serviced_se_route(self, se_route): self.serviced_se_routes.add(se_route)
    def remove_serviced_se_route(self, se_route): self.serviced_se_routes.discard(se_route)
    def calculate_route_properties(self):
        if len(self.schedule) < 2: self.total_dist, self.total_time, self.route_deadline = 0.0, 0.0, float('inf'); return
        self.total_dist = 0; path_nodes = [self.schedule[0]['node_id']]; [path_nodes.append(e['node_id']) for e in self.schedule[1:] if e['node_id'] != path_nodes[-1]]
        for i in range(len(path_nodes) - 1): self.total_dist += self.problem.get_distance(path_nodes[i], path_nodes[i+1])
        self.total_time = self.schedule[-1]['arrival_time'] - self.schedule[0]['departure_time']
        deadlines = {c.deadline for se in self.serviced_se_routes for c in se.get_customers() if hasattr(c, 'deadline')}
        self.route_deadline = min(deadlines) if deadlines else float('inf')

class SERoute:
    def __init__(self, satellite: "Satellite", problem: "ProblemInstance", start_time: float = 0.0):
        self.problem, self.satellite = problem, satellite; self.nodes_id: List[int] = [satellite.dist_id, satellite.coll_id]
        self.serving_fe_routes: Set[FERoute] = set(); self.service_start_times: Dict[int, float] = {satellite.dist_id: start_time}
        self.waiting_times: Dict[int, float] = {satellite.dist_id: 0.0}; self.forward_time_slacks: Dict[int, float] = {satellite.dist_id: float('inf')}
        self.total_dist, self.total_load_pickup, self.total_load_delivery = 0.0, 0.0, 0.0
        self.calculate_full_schedule_and_slacks()
    def calculate_full_schedule_and_slacks(self):
        # ... (Nội dung hàm này giữ nguyên như code gốc) ...
        for i in range(len(self.nodes_id) - 1):
            prev_id, curr_id = self.nodes_id[i], self.nodes_id[i+1]; prev_obj = self.problem.node_objects[prev_id % self.problem.total_nodes]; curr_obj = self.problem.node_objects[curr_id % self.problem.total_nodes]
            st_prev = prev_obj.service_time if prev_obj.type != 'Satellite' else 0.0
            departure_prev = self.service_start_times[prev_id] + st_prev
            arrival_curr = departure_prev + self.problem.get_travel_time(prev_obj.id, curr_obj.id)
            start_service = max(arrival_curr, getattr(curr_obj, 'ready_time', 0))
            self.service_start_times[curr_id] = start_service; self.waiting_times[curr_id] = start_service - arrival_curr
        n = len(self.nodes_id); self.forward_time_slacks[self.nodes_id[n-1]] = float('inf')
        for i in range(n - 2, -1, -1):
            node_id, succ_id = self.nodes_id[i], self.nodes_id[i+1]; node_obj = self.problem.node_objects[node_id % self.problem.total_nodes]; due_time = getattr(node_obj, 'due_time', float('inf'))
            st_node = node_obj.service_time if node_obj.type != 'Satellite' else 0.0
            departure_node = self.service_start_times[node_id] + st_node
            arrival_succ = self.service_start_times[succ_id] - self.waiting_times[succ_id]
            slack_between = arrival_succ - departure_node
            self.forward_time_slacks[node_id] = min(self.forward_time_slacks.get(succ_id, float('inf')) + slack_between, due_time - self.service_start_times[node_id])
    def insert_customer_at_pos(self, customer, pos):
        # ... (Nội dung hàm này giữ nguyên như code gốc) ...
        prev_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]; succ_obj = self.problem.node_objects[self.nodes_id[pos] % self.problem.total_nodes]
        cost_inc = (self.problem.get_distance(prev_obj.id, customer.id) + self.problem.get_distance(customer.id, succ_obj.id) - self.problem.get_distance(prev_obj.id, succ_obj.id))
        self.nodes_id.insert(pos, customer.id); self.total_dist += cost_inc
        if customer.type == 'DeliveryCustomer': self.total_load_delivery += customer.demand
        else: self.total_load_pickup += customer.demand
        self.calculate_full_schedule_and_slacks()
    def remove_customer(self, customer):
        if customer.id not in self.nodes_id: return
        pos = self.nodes_id.index(customer.id)
        prev_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]; succ_obj = self.problem.node_objects[self.nodes_id[pos+1] % self.problem.total_nodes]
        cost_dec = (self.problem.get_distance(prev_obj.id, customer.id) + self.problem.get_distance(customer.id, succ_obj.id) - self.problem.get_distance(prev_obj.id, succ_obj.id))
        self.total_dist -= cost_dec; self.nodes_id.pop(pos)
        if customer.type == 'DeliveryCustomer': self.total_load_delivery -= customer.demand
        else: self.total_load_pickup -= customer.demand
        self.calculate_full_schedule_and_slacks()
    def get_customers(self): return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]

class Solution:
    def __init__(self, problem: ProblemInstance):
        self.problem, self.fe_routes, self.se_routes, self.customer_to_se_route_map = problem, [], [], {}
        self.unserved_customers: List[Customer] = []
    def add_fe_route(self, fe_route): self.fe_routes.append(fe_route)
    def add_se_route(self, se_route): self.se_routes.append(se_route); self.update_customer_map()
    def remove_fe_route(self, fe_route): self.fe_routes.remove(fe_route) if fe_route in self.fe_routes else None
    def remove_se_route(self, se_route): self.se_routes.remove(se_route) if se_route in self.se_routes else None; self.update_customer_map()
    def link_routes(self, fe_route, se_route): fe_route.add_serviced_se_route(se_route); se_route.serving_fe_routes.add(fe_route)
    def unlink_routes(self, fe_route, se_route): fe_route.remove_serviced_se_route(se_route); se_route.serving_fe_routes.discard(fe_route)
    def update_customer_map(self): self.customer_to_se_route_map = {c.id: r for r in self.se_routes for c in r.get_customers()}
    def calculate_total_cost(self): return sum(r.total_dist for r in self.fe_routes) + sum(r.total_dist for r in self.se_routes)

class VRP2E_State:
    def __init__(self, solution: Solution): self.solution = solution
    def copy(self): return copy.deepcopy(self)
    @property
    def cost(self): return self.solution.calculate_total_cost()

# ==============================================================================
# PHẦN 2: LOGIC THUẬT TOÁN (Lấy từ Heuristics.py gốc)
# ==============================================================================
class InsertionProcessor:
    def __init__(self, problem: ProblemInstance): self.problem = problem
    def find_best_insertion_for_se_route(self, route: SERoute, customer: Customer) -> Optional[Dict]:
        best_candidate = {"pos": None, "cost_increase": float('inf')}
        if len(route.nodes_id) < 2: return None
        for i in range(len(route.nodes_id) - 1):
            pos_to_insert = i + 1
            is_cap_ok = True; temp_del_load = route.total_load_delivery
            if customer.type == 'DeliveryCustomer': temp_del_load += customer.demand
            if temp_del_load > self.problem.se_vehicle_capacity: continue
            temp_nodes_cap = route.nodes_id[:pos_to_insert] + [customer.id] + route.nodes_id[pos_to_insert:]
            running_load = temp_del_load
            for node_id in temp_nodes_cap[1:-1]:
                cust_obj = self.problem.node_objects[node_id]
                if cust_obj.type == 'DeliveryCustomer': running_load -= cust_obj.demand
                else: running_load += cust_obj.demand
                if running_load < 0 or running_load > self.problem.se_vehicle_capacity: is_cap_ok = False; break
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

def _recalculate_fe_route_and_check_feasibility(fe_route: FERoute, problem: ProblemInstance) -> Tuple[Optional[float], bool]:
    # ... (Hàm này giữ nguyên như code gốc) ...
    if not fe_route.serviced_se_routes: fe_route.total_dist, fe_route.schedule = 0.0, []; return 0.0, True
    depot = problem.depot; sats_to_visit = {se.satellite for se in fe_route.serviced_se_routes}; current_loc = depot
    sat_sequence: List[Satellite] = []
    while sats_to_visit:
        nearest_sat = min(sats_to_visit, key=lambda s: problem.get_distance(current_loc.id, s.id))
        sat_sequence.append(nearest_sat); sats_to_visit.remove(nearest_sat); current_loc = nearest_sat
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
            se_route.service_start_times[se_route.nodes_id[0]] = arrival_at_sat; se_route.calculate_full_schedule_and_slacks()
            for cust in se_route.get_customers():
                if se_route.service_start_times.get(cust.id, float('inf')) > cust.due_time + 1e-6: return None, False
                if hasattr(cust, 'deadline'): route_deadlines.add(cust.deadline)
            latest_se_finish = max(latest_se_finish, se_route.service_start_times.get(se_route.nodes_id[-1], 0))
        pickup_load_at_sat = sum(r.total_load_pickup for r in se_routes)
        departure_from_sat = latest_se_finish + satellite.service_time
        schedule.append({'activity': 'LOAD_PICKUP', 'node_id': satellite.id, 'load_change': pickup_load_at_sat, 'load_after': current_load - del_load_at_sat + pickup_load_at_sat, 'arrival_time': latest_se_finish, 'start_svc_time': latest_se_finish, 'departure_time': departure_from_sat})
        current_time, current_load, last_node_id = departure_from_sat, current_load - del_load_at_sat + pickup_load_at_sat, satellite.id
    arrival_at_depot = current_time + problem.get_travel_time(last_node_id, depot.id)
    schedule.append({'activity': 'ARRIVE_DEPOT', 'node_id': depot.id, 'load_change': -current_load, 'load_after': 0, 'arrival_time': arrival_at_depot, 'start_svc_time': arrival_at_depot, 'departure_time': arrival_at_depot})
    fe_route.schedule = schedule; fe_route.calculate_route_properties()
    effective_deadline = min(route_deadlines) if route_deadlines else float('inf')
    if arrival_at_depot > effective_deadline + 1e-6: return None, False
    return fe_route.total_dist, True

def find_best_global_insertion_option(customer: Customer, solution: Solution, insertion_processor: InsertionProcessor) -> Dict:
    problem = solution.problem; best_option = {'total_cost_increase': float('inf')}
    for se_route in solution.se_routes:
        insertion_result = insertion_processor.find_best_insertion_for_se_route(se_route, customer)
        if not (insertion_result and se_route.serving_fe_routes): continue
        fe_route = list(se_route.serving_fe_routes)[0]; original_global_cost = se_route.total_dist + fe_route.total_dist
        temp_fe_route = copy.deepcopy(fe_route)
        try: temp_se_ref = next(r for r in temp_fe_route.serviced_se_routes if r.nodes_id == se_route.nodes_id and r.satellite.id == se_route.satellite.id)
        except StopIteration: continue
        temp_se_ref.insert_customer_at_pos(customer, insertion_result['pos'])
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
        if is_feasible:
            total_increase = (temp_se_ref.total_dist + new_fe_cost) - original_global_cost
            if total_increase < best_option['total_cost_increase']:
                best_option.update({'total_cost_increase': total_increase, 'type': 'insert_into_existing_se', 'se_route': se_route, 'se_pos': insertion_result['pos']})
    for satellite in problem.satellites:
        temp_new_se = SERoute(satellite, problem); temp_new_se.insert_customer_at_pos(customer, 1); se_cost = temp_new_se.total_dist
        temp_fe_for_new = FERoute(problem); temp_fe_for_new.add_serviced_se_route(temp_new_se)
        new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_new, problem)
        if is_feasible and (se_cost + new_fe_cost) < best_option['total_cost_increase']:
            best_option.update({'total_cost_increase': se_cost + new_fe_cost, 'type': 'create_new_se_new_fe', 'new_satellite': satellite})
        for fe_route in solution.fe_routes:
            if sum(r.total_load_delivery for r in fe_route.serviced_se_routes) + temp_new_se.total_load_delivery > problem.fe_vehicle_capacity: continue
            original_fe_cost = fe_route.total_dist; temp_fe_route = copy.deepcopy(fe_route); temp_fe_route.add_serviced_se_route(temp_new_se)
            new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
            if is_feasible:
                total_increase = se_cost + (new_fe_cost - original_fe_cost)
                if total_increase < best_option['total_cost_increase']:
                    best_option.update({'total_cost_increase': total_increase, 'type': 'create_new_se_expand_fe', 'new_satellite': satellite, 'fe_route': fe_route})
    return best_option

def create_integrated_initial_solution(problem: ProblemInstance, random_customers: bool = True) -> VRP2E_State:
    solution = Solution(problem)
    insertion_processor = InsertionProcessor(problem)
    customers_to_serve = list(problem.customers)
    if random_customers: random.shuffle(customers_to_serve)
    
    solution.unserved_customers = [] # Bắt đầu với ds rỗng, thêm vào nếu thất bại

    for i, customer in enumerate(customers_to_serve):
        print(f"  -> Processing customer {i+1}/{len(customers_to_serve)} (ID: {customer.id})...", end='\r')
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        option_type = best_option.get('type')

        if option_type == 'insert_into_existing_se':
            se_route, pos = best_option['se_route'], best_option['se_pos']
            fe_route = list(se_route.serving_fe_routes)[0]
            se_route.insert_customer_at_pos(customer, pos); solution.update_customer_map()
            _recalculate_fe_route_and_check_feasibility(fe_route, problem)
        elif option_type == 'create_new_se_new_fe':
            satellite = best_option['new_satellite']
            new_se = SERoute(satellite, problem); new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se)
            new_fe = FERoute(problem); solution.add_fe_route(new_fe)
            solution.link_routes(new_fe, new_se)
            _recalculate_fe_route_and_check_feasibility(new_fe, problem)
        elif option_type == 'create_new_se_expand_fe':
            satellite, fe_route = best_option['new_satellite'], best_option['fe_route']
            new_se = SERoute(satellite, problem); new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se)
            solution.link_routes(fe_route, new_se)
            _recalculate_fe_route_and_check_feasibility(fe_route, problem)
        else: 
            solution.unserved_customers.append(customer)
            print(f"\nWarning: Could not serve customer {customer.id}")

    print("\n\n>>> Initial solution construction complete!")
    return VRP2E_State(solution)

# ==============================================================================
# PHẦN 3: CÁC THÀNH PHẦN MỚI CHO LNS
# ==============================================================================
DestroyOperator = Callable[['VRP2E_State', int], Tuple['VRP2E_State', List['Customer']]]
RepairOperator = Callable[['VRP2E_State', List['Customer']], 'VRP2E_State']

def random_removal(state: VRP2E_State, q: int) -> Tuple[VRP2E_State, List[Customer]]:
    new_state = state.copy(); solution = new_state.solution
    served_ids = list(solution.customer_to_se_route_map.keys())
    if not served_ids: return new_state, []
    q = min(q, len(served_ids))
    to_remove_ids = random.sample(served_ids, q)
    removed_objs, affected_fes = [], set()

    for cust_id in to_remove_ids:
        se_route = solution.customer_to_se_route_map[cust_id]
        customer_obj = solution.problem.node_objects[cust_id]
        removed_objs.append(customer_obj)
        if se_route.serving_fe_routes:
            affected_fes.add(list(se_route.serving_fe_routes)[0])
        se_route.remove_customer(customer_obj)
    
    solution.update_customer_map()
    
    for fe_route in list(affected_fes):
        for se_route in list(fe_route.serviced_se_routes):
            if not se_route.get_customers():
                solution.unlink_routes(fe_route, se_route)
                solution.remove_se_route(se_route)
        if not fe_route.serviced_se_routes:
             solution.remove_fe_route(fe_route)
        else:
             _recalculate_fe_route_and_check_feasibility(fe_route, solution.problem)
    return new_state, removed_objs

def greedy_repair(state: VRP2E_State, customers_to_insert: List[Customer]) -> VRP2E_State:
    new_state = state.copy(); solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)
    random.shuffle(customers_to_insert)

    for customer in customers_to_insert:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        option_type = best_option.get('type')
        # ... (Logic chèn giống hệt trong create_integrated_initial_solution) ...
        if option_type == 'insert_into_existing_se':
            se_route, pos = best_option['se_route'], best_option['se_pos']; fe_route = list(se_route.serving_fe_routes)[0]
            se_route.insert_customer_at_pos(customer, pos); solution.update_customer_map(); _recalculate_fe_route_and_check_feasibility(fe_route, solution.problem)
        elif option_type == 'create_new_se_new_fe':
            satellite = best_option['new_satellite']; new_se = SERoute(satellite, solution.problem); new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se); new_fe = FERoute(solution.problem); solution.add_fe_route(new_fe); solution.link_routes(new_fe, new_se); _recalculate_fe_route_and_check_feasibility(new_fe, solution.problem)
        elif option_type == 'create_new_se_expand_fe':
            satellite, fe_route = best_option['new_satellite'], best_option['fe_route']; new_se = SERoute(satellite, solution.problem); new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se); solution.link_routes(fe_route, new_se); _recalculate_fe_route_and_check_feasibility(fe_route, solution.problem)
        else:
            if customer not in solution.unserved_customers: solution.unserved_customers.append(customer)
    return new_state

def run_lns_loop(initial_state: VRP2E_State, iterations: int, q_percentage: float, destroy_op: DestroyOperator, repair_op: RepairOperator) -> VRP2E_State:
    current_state, best_state = initial_state.copy(), initial_state.copy()
    print("\n--- Starting LNS Refinement ---")
    for i in range(iterations):
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0: print("No customers to optimize. Stopping LNS."); break
        q = max(2, int(num_cust * q_percentage))
        destroyed_state, removed_customers = destroy_op(current_state, q)
        repaired_state = repair_op(destroyed_state, removed_customers)
        
        current_cost, new_cost, best_cost = current_state.cost, repaired_state.cost, best_state.cost
        log_str = f"  LNS Iter {i+1:>4}/{iterations} | Current: {current_cost:>10.2f}, New: {new_cost:>10.2f}, Best: {best_cost:>10.2f}"
        if new_cost < current_cost:
            current_state = repaired_state.copy(); log_str += " -> ACCEPTED"
            if new_cost < best_cost:
                best_state = repaired_state.copy(); log_str += " (NEW BEST!)"
        print(log_str)
    print(f"\n--- LNS complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state

# ==============================================================================
# PHẦN 4: HÀM MAIN ĐỂ CHẠY
# ==============================================================================
def main():
    file_path = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_7_TD.csv"
    LNS_ITERATIONS = 250
    Q_PERCENTAGE = 0.2

    try: problem = ProblemInstance(file_path=file_path)
    except Exception as e: print(f"Error loading instance: {e}"); return

    print("\n--- Phase 1: Initial Solution Construction ---")
    initial_state = create_integrated_initial_solution(problem)
    initial_cost = initial_state.cost
    print(f"\n--- Phase 1 Complete. Initial Cost: {initial_cost:.2f} ---")

    if LNS_ITERATIONS > 0:
        final_state = run_lns_loop(initial_state, LNS_ITERATIONS, Q_PERCENTAGE, random_removal, greedy_repair)
    else:
        final_state = initial_state
    
    solution = final_state.solution
    print("\n--- FINAL RESULTS ---")
    print(f"Total Cost: {solution.calculate_total_cost():.2f}")
    print(f"Number of FE Routes: {len(solution.fe_routes)}")
    print(f"Number of SE Routes: {len(solution.se_routes)}")
    print(f"Unserved Customers: {len(solution.unserved_customers)}")
    if solution.unserved_customers: print(f"  -> IDs: {[c.id for c in solution.unserved_customers]}")

    all_served_ids = set(solution.customer_to_se_route_map.keys())
    all_problem_ids = {c.id for c in problem.customers}
    if len(all_served_ids) + len(solution.unserved_customers) != len(all_problem_ids):
        print("\n[VALIDATION WARNING] Mismatch in served/unserved customer count!")

if __name__ == "__main__":
    main()

# --- END OF FILE main_single_file.py ---