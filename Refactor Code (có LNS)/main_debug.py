# --- START OF FILE main_debug.py (FIXED AttributeError) ---

import pandas as pd
import math
import copy
import random
from typing import Dict, List, Set, Optional, Tuple

# ==============================================================================
# PHẦN 1: PARSER & DATA STRUCTURES
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
    def __init__(self, problem: ProblemInstance): self.problem, self.serviced_se_routes, self.schedule, self.total_dist = problem, set(), [], 0.0
    def add_serviced_se_route(self, se_route): self.serviced_se_routes.add(se_route)

class SERoute:
    def __init__(self, satellite: Satellite, problem: ProblemInstance, start_time: float = 0.0):
        self.problem, self.satellite = problem, satellite
        self.nodes_id: List[int] = [satellite.dist_id, satellite.coll_id]
        self.service_start_times: Dict[int, float] = {satellite.dist_id: start_time, satellite.coll_id: float('inf')}
        self.total_dist, self.total_load_pickup, self.total_load_delivery = 0.0, 0.0, 0.0
        self.calculate_full_schedule()
        
    def calculate_full_schedule(self):
        for i in range(len(self.nodes_id) - 1):
            prev_id, curr_id = self.nodes_id[i], self.nodes_id[i+1]
            # --- FIX: self.total_nodes -> self.problem.total_nodes ---
            prev_obj = self.problem.node_objects[prev_id % self.problem.total_nodes]
            curr_obj = self.problem.node_objects[curr_id % self.problem.total_nodes]
            st_prev = prev_obj.service_time if prev_obj.type != 'Satellite' else 0.0
            departure_prev = self.service_start_times[prev_id] + st_prev
            arrival_curr = departure_prev + self.problem.get_travel_time(prev_obj.id, curr_obj.id)
            self.service_start_times[curr_id] = max(arrival_curr, getattr(curr_obj, 'ready_time', 0))

    def insert_customer_at_pos(self, customer: Customer, pos: int):
        # --- FIX: self.total_nodes -> self.problem.total_nodes ---
        prev_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]
        succ_obj = self.problem.node_objects[self.nodes_id[pos] % self.problem.total_nodes]
        cost_inc = (self.problem.get_distance(prev_obj.id, customer.id) + 
                    self.problem.get_distance(customer.id, succ_obj.id) - 
                    self.problem.get_distance(prev_obj.id, succ_obj.id))
        self.nodes_id.insert(pos, customer.id)
        self.total_dist += cost_inc
        if customer.type == 'DeliveryCustomer': self.total_load_delivery += customer.demand
        else: self.total_load_pickup += customer.demand
        self.calculate_full_schedule()
        
    def get_customers(self) -> List[Customer]: 
        return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]

class Solution:
    def __init__(self, problem: ProblemInstance):
        self.problem, self.fe_routes, self.se_routes = problem, [], []
        self.unserved_customers: List[Customer] = []
    def add_fe_route(self, fe_route): self.fe_routes.append(fe_route)
    def add_se_route(self, se_route): self.se_routes.append(se_route)
    def calculate_total_cost(self): return sum(r.total_dist for r in self.fe_routes) + sum(r.total_dist for r in self.se_routes)

# ==============================================================================
# PHẦN 2: LOGIC THUẬT TOÁN
# ==============================================================================

def _recalculate_fe_route_and_check_feasibility_simple(fe_route: FERoute, problem: ProblemInstance) -> bool:
    if not fe_route.serviced_se_routes: return True
    depot = problem.depot
    # Sắp xếp theo ID để đảm bảo thứ tự ổn định
    sat_sequence = sorted(list(fe_route.serviced_se_routes), key=lambda se: se.satellite.id)
    
    current_time, last_node_id = 0.0, depot.id
    all_deadlines = set()

    for se_route in sat_sequence:
        satellite = se_route.satellite
        arrival_at_sat = current_time + problem.get_travel_time(last_node_id, satellite.id)
        
        se_route.service_start_times[se_route.nodes_id[0]] = arrival_at_sat
        se_route.calculate_full_schedule()
        
        for cust in se_route.get_customers():
            if se_route.service_start_times[cust.id] > cust.due_time + 1e-6:
                return False # Vi phạm Time Window
            if hasattr(cust, 'deadline'):
                all_deadlines.add(cust.deadline)
        
        latest_se_finish_time = se_route.service_start_times.get(se_route.nodes_id[-1], 0)
        current_time = latest_se_finish_time + satellite.service_time
        last_node_id = satellite.id

    arrival_at_depot = current_time + problem.get_travel_time(last_node_id, depot.id)
    for deadline in all_deadlines:
        if arrival_at_depot > deadline + 1e-6:
            return False # Vi phạm Deadline

    return True

def create_initial_solution(problem: ProblemInstance):
    solution = Solution(problem)
    customers_to_serve = list(problem.customers)
    random.shuffle(customers_to_serve)

    for i, customer in enumerate(customers_to_serve):
        print(f"  -> Processing customer {i+1}/{len(customers_to_serve)} (ID: {customer.id})...", end='\r')
        
        best_option = {'cost': float('inf'), 'action': None}

        # Kịch bản: Tạo một SE và FE route mới cho khách hàng này
        for satellite in problem.satellites:
            # 1. Thử tạo SERoute
            temp_se = SERoute(satellite, problem, start_time=0) # Bắt đầu từ 0 để kiểm tra
            temp_se.insert_customer_at_pos(customer, 1)

            # 2. Kiểm tra Time Window của SERoute này
            is_se_feasible = True
            for cust in temp_se.get_customers():
                if temp_se.service_start_times[cust.id] > cust.due_time + 1e-6:
                    is_se_feasible = False; break
            if not is_se_feasible: continue

            # 3. Thử tạo FERoute và kiểm tra
            temp_fe = FERoute(problem)
            temp_fe.add_serviced_se_route(temp_se)
            is_fe_feasible = _recalculate_fe_route_and_check_feasibility_simple(temp_fe, problem)
            
            if is_fe_feasible:
                cost = temp_se.total_dist # Chỉ tính chi phí SE cho đơn giản
                if cost < best_option['cost']:
                    best_option['cost'] = cost
                    best_option['action'] = ('NEW', satellite, temp_se)
        
        # Thực hiện hành động tốt nhất (nếu có)
        if best_option['action']:
            action_type, satellite, new_se_route = best_option['action']
            if action_type == 'NEW':
                new_fe_route = FERoute(problem)
                new_fe_route.add_serviced_se_route(new_se_route)
                # Tính toán lại lần cuối để đảm bảo lịch trình đúng
                _recalculate_fe_route_and_check_feasibility_simple(new_fe_route, problem)
                solution.add_se_route(new_se_route)
                solution.add_fe_route(new_fe_route)
        else:
            solution.unserved_customers.append(customer)
            print(f"\nWarning: Could not serve customer {customer.id}")

    return solution

# ==============================================================================
# PHẦN 3: HÀM MAIN ĐỂ CHẠY
# ==============================================================================

def main():
    file_path = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_7_TD.csv"
    
    try:
        problem = ProblemInstance(file_path=file_path)
    except Exception as e:
        print(f"Error loading instance: {e}"); return

    print("\n--- Starting Initial Solution Construction (Simplified Debug Version) ---")
    solution = create_initial_solution(problem)
    
    print("\n\n--- Initial Solution Results ---")
    print(f"Total Cost: {solution.calculate_total_cost():.2f}")
    print(f"Number of FE Routes: {len(solution.fe_routes)}")
    print(f"Number of SE Routes: {len(solution.se_routes)}")
    print(f"Unserved Customers: {len(solution.unserved_customers)}")
    if solution.unserved_customers:
        print(f"  -> IDs: {[c.id for c in solution.unserved_customers]}")

if __name__ == "__main__":
    main()

# --- END OF FILE main_debug.py ---