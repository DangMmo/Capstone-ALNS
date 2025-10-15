# --- START OF FILE DataStructures.py (REFACTORED VERSION) ---

import sys
# import copy # Dòng này không còn cần thiết trong file này nữa
from Parser import ProblemInstance 

class SERoute:
    def __init__(self, satellite, problem, start_time=0.0):
        self.problem = problem
        self.satellite = satellite
        self.nodes_id = [satellite.dist_id, satellite.coll_id]
        
        self.service_start_times = {satellite.dist_id: start_time, satellite.coll_id: float('inf')}
        self.waiting_times = {satellite.dist_id: 0.0, satellite.coll_id: 0.0}
        self.forward_time_slacks = {satellite.dist_id: float('inf'), satellite.coll_id: float('inf')}
        
        self.total_dist = 0.0
        self.total_load_pickup = 0.0
        self.total_load_delivery = 0.0
        
        self.calculate_full_schedule_and_slacks()

    def __repr__(self):
        # ... (nội dung của __repr__ giữ nguyên, không thay đổi)
        path_ids = [nid % self.problem.total_nodes for nid in self.nodes_id]
        path_str = " -> ".join(map(str, path_ids))
        deadlines = [c.deadline for c in self.get_customers() if hasattr(c, 'deadline')]
        route_deadline_str = f"Route Deadline: {min(deadlines):.2f}" if deadlines else "No Deadline"
        
        if len(self.nodes_id) > 2:
            start_time = self.service_start_times.get(self.nodes_id[0], 0.0)
            end_time = self.service_start_times.get(self.nodes_id[-1], 0.0)
            operating_time = end_time - start_time
        else:
            operating_time = 0.0

        header_str = (f"--- SERoute for Satellite {self.satellite.id} (Cost: {self.total_dist:.2f} m, "
                      f"Time: {operating_time:.2f} min) --- {route_deadline_str}")
        
        s = [header_str, f"Path: {path_str}"]
        header = (f"  {'Node':<10}| {'Type':<18}| {'Demand':>8}| {'Load After':>12}| {'Arrival':>9}| {'Start Svc':>9}| "
                  f"{'Latest Arr':>10}| {'Deadline':>8}")
        s.append(header)
        s.append("  " + "-" * len(header))
        
        current_load = self.total_load_delivery
        start_node_obj = self.problem.node_objects[self.satellite.id]
        start_time_val = self.service_start_times.get(self.satellite.dist_id, 0.0)
        latest_arrival_start = start_time_val + self.forward_time_slacks.get(self.satellite.dist_id, 0.0)
        
        s.append(f"  {str(start_node_obj.id) + ' (Dist)':<10}| {'Satellite':<18}| {-self.total_load_delivery:>8.2f}| {current_load:>12.2f}| "
                 f"{start_time_val:>9.2f}| {start_time_val:>9.2f}| {latest_arrival_start:>10.2f}| {'N/A':>8}")

        for node_id in self.nodes_id[1:-1]:
            customer = self.problem.node_objects[node_id]
            if customer.type == 'DeliveryCustomer':
                current_load -= customer.demand
                demand_str = f"{-customer.demand:.2f}"
                deadline_str = "N/A"
            else:
                current_load += customer.demand
                demand_str = f"+{customer.demand:.2f}"
                deadline_str = f"{customer.deadline:.2f}"
            arrival = self.service_start_times.get(node_id, 0.0) - self.waiting_times.get(node_id, 0.0)
            start_svc = self.service_start_times.get(node_id, 0.0)
            latest_arrival = arrival + self.forward_time_slacks.get(node_id, 0.0)
            s.append(f"  {customer.id:<10}| {customer.type:<18}| {demand_str:>8}| {current_load:>12.2f}| "
                     f"{arrival:>9.2f}| {start_svc:>9.2f}| {latest_arrival:>10.2f}| {deadline_str:>8}")

        end_node_obj = self.problem.node_objects[self.satellite.id]
        end_time_val = self.service_start_times.get(self.satellite.coll_id, 0.0)
        final_load = current_load
        s.append(f"  {str(end_node_obj.id) + ' (Coll)':<10}| {'Satellite':<18}| {self.total_load_pickup:>+8.2f}| {final_load:>12.2f}| "
                 f"{end_time_val:>9.2f}| {end_time_val:>9.2f}| {'inf':>10}| {'N/A':>8}")
        return "\n".join(s)

    def calculate_full_schedule_and_slacks(self):
        # ... (nội dung giữ nguyên, không thay đổi)
        current_time = self.service_start_times[self.nodes_id[0]]
        
        for i in range(len(self.nodes_id) - 1):
            prev_node_id = self.nodes_id[i]
            curr_node_id = self.nodes_id[i+1]
            
            prev_node_obj = self.problem.node_objects[prev_node_id % self.problem.total_nodes]
            curr_node_obj = self.problem.node_objects[curr_node_id % self.problem.total_nodes]
            
            service_time_prev = prev_node_obj.service_time
            if prev_node_obj.type == 'Satellite':
                service_time_prev = 0.0

            travel_time = self.problem.get_travel_time(prev_node_obj.id, curr_node_obj.id)
            
            departure_time_prev = self.service_start_times[prev_node_id] + service_time_prev
            
            arrival_time = departure_time_prev + travel_time
            start_service_time = max(arrival_time, getattr(curr_node_obj, 'ready_time', 0))
            
            self.service_start_times[curr_node_id] = start_service_time
            self.waiting_times[curr_node_id] = start_service_time - arrival_time
            
        n = len(self.nodes_id)
        self.forward_time_slacks[self.nodes_id[n-1]] = float('inf')
        for i in range(n - 2, -1, -1):
            node_id = self.nodes_id[i]
            succ_node_id = self.nodes_id[i+1]
            node_obj = self.problem.node_objects[node_id % self.problem.total_nodes]
            succ_node_obj_lookup = self.problem.node_objects.get(succ_node_id % self.problem.total_nodes)
            due_time = getattr(node_obj, 'due_time', float('inf'))
            service_time_node = node_obj.service_time
            if node_obj.type == 'Satellite': service_time_node = 0.0
            
            departure_time_node = self.service_start_times[node_id] + service_time_node
            arrival_time_succ = self.service_start_times[succ_node_id] - self.waiting_times[succ_node_id]
            
            slack_between = arrival_time_succ - departure_time_node
            
            self.forward_time_slacks[node_id] = min(self.forward_time_slacks.get(succ_node_id, float('inf')) + slack_between,
                                                  due_time - self.service_start_times[node_id])
        
    def insert_customer_at_pos(self, customer, pos):
        # ... (nội dung giữ nguyên, không thay đổi)
        self.nodes_id.insert(pos, customer.id)
        if customer.type == 'DeliveryCustomer': self.total_load_delivery += customer.demand
        else: self.total_load_pickup += customer.demand
        
        prev_node_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]
        succ_node_obj = self.problem.node_objects[self.nodes_id[pos+1] % self.problem.total_nodes]
        
        cost_increase = (self.problem.get_distance(prev_node_obj.id, customer.id) + 
                         self.problem.get_distance(customer.id, succ_node_obj.id) - 
                         self.problem.get_distance(prev_node_obj.id, succ_node_obj.id))
        self.total_dist += cost_increase
        
        self.calculate_full_schedule_and_slacks()
        
    def remove_customer(self, customer):
        # ... (nội dung giữ nguyên, không thay đổi)
        if customer.id not in self.nodes_id: return
        
        pos = self.nodes_id.index(customer.id)
        prev_node_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]
        succ_node_obj = self.problem.node_objects[self.nodes_id[pos+1] % self.problem.total_nodes]
        
        cost_decrease = (self.problem.get_distance(prev_node_obj.id, customer.id) + 
                         self.problem.get_distance(customer.id, succ_node_obj.id) - 
                         self.problem.get_distance(prev_node_obj.id, succ_node_obj.id))
        self.total_dist -= cost_decrease

        self.nodes_id.pop(pos)
        if customer.type == 'DeliveryCustomer': self.total_load_delivery -= customer.demand
        else: self.total_load_pickup -= customer.demand
        
        self.calculate_full_schedule_and_slacks()

    # <<< PHƯƠNG THỨC find_best_insertion_pos ĐÃ ĐƯỢC XÓA KHỎI ĐÂY >>>

    def is_feasible_under_proxy_deadline(self):
        # ... (nội dung giữ nguyên, không thay đổi)
        all_customers_on_route = self.get_customers()
        pickup_customers = [c for c in all_customers_on_route if c.type == 'PickupCustomer']
        if not pickup_customers: return True

        effective_route_deadline = min(c.deadline for c in pickup_customers)
        arrival_at_collection_satellite = self.service_start_times.get(self.nodes_id[-1], float('inf'))
        
        proxy_arrival_at_hub = (arrival_at_collection_satellite + 0.0 + 
                                self.problem.get_travel_time(self.satellite.id, self.problem.depot.id))
        
        return proxy_arrival_at_hub <= effective_route_deadline

    def get_customers(self): 
        # ... (nội dung giữ nguyên, không thay đổi)
        return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]

# ... (Các lớp FERoute và Solution giữ nguyên, không thay đổi)
class FERoute:
    # ... (giữ nguyên)
    def __init__(self, problem):
        self.problem = problem
        self.schedule = [] 
        self.total_dist = 0.0
        self.total_time = 0.0
        self.route_deadline = float('inf')

    def __repr__(self):
        if not self.schedule:
            return "--- Empty FERoute ---"
        path_nodes = []
        for event in self.schedule:
            node_id = event['node_id']
            if not path_nodes or path_nodes[-1] != node_id:
                path_nodes.append(node_id)
        path_str = " -> ".join(map(str, path_nodes))
        deadline_str = f"Route Deadline: {self.route_deadline:.2f}" if self.route_deadline != float('inf') else "No Deadline"
        header_str = (f"--- FERoute (Cost: {self.total_dist:.2f} m, Time: {self.total_time:.2f} min) "
                      f"--- {deadline_str}")
        s = [header_str, f"Path: {path_str}"]
        header = (f"  {'Node':<6}| {'Activity':<15}| {'Load Change':>12}| {'Load After':>12}| "
                  f"{'Arrival':>9}| {'Start Svc':>9}| {'Departure':>11}")
        s.append(header)
        s.append("  " + "-" * len(header))
        for event in self.schedule:
            s.append(f"  {event['node_id']:<6}| {event['activity']:<15}| {event['load_change']:>+12.2f}| {event['load_after']:>12.2f}| "
                     f"{event['arrival_time']:>9.2f}| {event['start_svc_time']:>9.2f}| {event['departure_time']:>11.2f}")
        return "\n".join(s)

    def calculate_route_properties(self):
        if len(self.schedule) < 2:
            self.total_dist = 0; self.total_time = 0; return
        self.total_dist = 0
        path_nodes = []
        for event in self.schedule:
            node_id = event['node_id']
            if not path_nodes or path_nodes[-1] != node_id:
                path_nodes.append(node_id)
        for i in range(len(path_nodes) - 1):
            self.total_dist += self.problem.get_distance(path_nodes[i], path_nodes[i+1])
        start_time = self.schedule[0]['departure_time']
        end_time = self.schedule[-1]['arrival_time']
        self.total_time = end_time - start_time
        deadlines = [event.get('deadline') for event in self.schedule if event.get('deadline') and event.get('deadline') != float('inf')]
        self.route_deadline = min(deadlines) if deadlines else float('inf')

    def get_satellites_visited(self):
        visited_ids = set()
        for event in self.schedule:
            if event['activity'] in ['UNLOAD_DELIV', 'LOAD_PICKUP']:
                visited_ids.add(event['node_id'])
        return [self.problem.node_objects[sat_id] for sat_id in visited_ids]

class Solution:
    # ... (giữ nguyên)
    def __init__(self, problem):
        self.problem = problem
        self.fe_routes, self.se_routes = [], []
        self.unserved_customers = list(problem.customers)
        self.total_cost = 0.0
        self.total_time = 0.0
        self.unserviced_satellite_reqs = {}

    def calculate_total_cost_and_time(self):
        fe_cost = sum(r.total_dist for r in self.fe_routes)
        se_cost = sum(r.total_dist for r in self.se_routes)
        self.total_cost = fe_cost + se_cost
        
        if not self.fe_routes:
            self.total_time = 0
        else:
            self.total_time = max(r.schedule[-1]['arrival_time'] for r in self.fe_routes if r.schedule)

# --- END OF FILE DataStructures.py (REFACTORED VERSION) ---