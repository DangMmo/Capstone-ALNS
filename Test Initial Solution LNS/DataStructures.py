# --- START OF FILE DataStructures.py ---

import sys
from Parser import ProblemInstance 

class SERoute:
    def __init__(self, satellite, problem):
        self.problem = problem
        self.satellite = satellite
        self.nodes_id = [satellite.dist_id, satellite.coll_id]
        self.service_start_times = {satellite.dist_id: 0.0, satellite.coll_id: float('inf')}
        self.waiting_times = {satellite.dist_id: 0.0, satellite.coll_id: 0.0}
        self.forward_time_slacks = {satellite.dist_id: float('inf'), satellite.coll_id: float('inf')}
        
        self.total_dist = 0.0
        self.total_time = 0.0
        
        self.total_load_pickup = 0.0
        self.total_load_delivery = 0.0

    def __repr__(self):
        path_ids = [nid % self.problem.total_nodes for nid in self.nodes_id]
        path_str = " -> ".join(map(str, path_ids))
        deadlines = [c.deadline for c in self.get_customers() if hasattr(c, 'deadline')]
        route_deadline_str = f"Route Deadline: {min(deadlines):.2f}" if deadlines else ""
        
        header_str = f"--- SERoute for Satellite {self.satellite.id} (Cost: {self.total_dist:.2f} m, Time: {self.total_time:.2f} min) --- {route_deadline_str}"
        
        s = [header_str, f"Path: {path_str}"]
        header = (f"  {'Node':<10}| {'Type':<18}| {'Demand':>8}| {'Load After':>12}| {'Arrival':>9}| {'Start Svc':>9}| "
                  f"{'Latest Arr':>10}| {'Deadline':>8}")
        s.append(header)
        s.append("  " + "-" * len(header))
        current_load = self.total_load_delivery
        start_node_obj = self.problem.node_objects[self.satellite.id]
        start_time = self.service_start_times.get(self.satellite.dist_id, 0.0)
        latest_arrival_start = start_time + self.forward_time_slacks.get(self.satellite.dist_id, 0.0)
        s.append(f"  {str(start_node_obj.id) + ' (Dist)':<10}| {'Satellite':<18}| {-self.total_load_delivery:>8.2f}| {current_load:>12.2f}| "
                 f"{start_time:>9.2f}| {start_time:>9.2f}| {latest_arrival_start:>10.2f}| {'N/A':>8}")
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
        end_time = self.service_start_times.get(self.satellite.coll_id, 0.0)
        final_load = current_load
        s.append(f"  {str(end_node_obj.id) + ' (Coll)':<10}| {'Satellite':<18}| {self.total_load_pickup:>+8.2f}| {final_load:>12.2f}| "
                 f"{end_time:>9.2f}| {end_time:>9.2f}| {'inf':>10}| {'N/A':>8}")
        return "\n".join(s)

    def calculate_full_schedule_and_slacks(self):
        self.total_time = 0.0
        
        prev_node_id = self.nodes_id[0]
        prev_node_obj = self.problem.node_objects[prev_node_id % self.problem.total_nodes]
        for i in range(1, len(self.nodes_id)):
            curr_node_id, curr_node_obj = self.nodes_id[i], self.problem.node_objects[self.nodes_id[i] % self.problem.total_nodes]
            
            travel_time = self.problem.get_travel_time(prev_node_obj.id, curr_node_obj.id)
            self.total_time += travel_time
            
            arrival_time = self.service_start_times.get(prev_node_id, 0) + prev_node_obj.service_time + travel_time
            start_service_time = max(arrival_time, getattr(curr_node_obj, 'ready_time', 0))
            self.service_start_times[curr_node_id], self.waiting_times[curr_node_id] = start_service_time, start_service_time - arrival_time
            prev_node_id, prev_node_obj = curr_node_id, curr_node_obj
            
        n = len(self.nodes_id)
        self.forward_time_slacks[self.nodes_id[n-1]] = float('inf')
        for i in range(n - 2, -1, -1):
            node_id, succ_node_id = self.nodes_id[i], self.nodes_id[i+1]
            node_obj = self.problem.node_objects[node_id % self.problem.total_nodes]
            succ_node_obj_lookup = self.problem.node_objects.get(succ_node_id % self.problem.total_nodes)
            due_time = getattr(node_obj, 'due_time', float('inf'))
            travel_time_between = self.problem.get_travel_time(node_obj.id, succ_node_obj_lookup.id) if succ_node_obj_lookup else 0
            slack_between = (self.service_start_times.get(succ_node_id, float('inf')) - (self.service_start_times.get(node_id, 0) + node_obj.service_time) - travel_time_between)
            self.forward_time_slacks[node_id] = min(self.forward_time_slacks.get(succ_node_id, float('inf')) + slack_between, due_time - self.service_start_times.get(node_id, 0))

    def insert_customer_at_pos(self, customer, pos):
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
        if customer.id not in self.nodes_id:
            return
        
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
    
    def find_best_insertion_pos(self, customer):
        best_pos, min_cost_increase = None, float('inf')
        capacity = self.problem.se_vehicle_capacity
        for i in range(1, len(self.nodes_id)):
            # Capacity check
            temp_nodes_id = self.nodes_id[:i] + [customer.id] + self.nodes_id[i:]
            temp_total_delivery, temp_total_pickup = self.total_load_delivery, self.total_load_pickup
            if customer.type == 'DeliveryCustomer': temp_total_delivery += customer.demand
            else: temp_total_pickup += customer.demand
            if temp_total_delivery > capacity: continue
            is_capacity_feasible = True
            current_load = temp_total_delivery
            for node_idx in range(1, len(temp_nodes_id) - 1):
                cust_obj = self.problem.node_objects[temp_nodes_id[node_idx]]
                if cust_obj.type == 'DeliveryCustomer': current_load -= cust_obj.demand
                else: current_load += cust_obj.demand
                if current_load > capacity: is_capacity_feasible = False; break
            if not is_capacity_feasible: continue
            
            # Time window check
            prev_node_obj = self.problem.node_objects[self.nodes_id[i-1] % self.problem.total_nodes]
            succ_node_obj = self.problem.node_objects[self.nodes_id[i] % self.problem.total_nodes]
            start_time_prev = self.service_start_times[self.nodes_id[i-1]]
            travel_to_cust = self.problem.get_travel_time(prev_node_obj.id, customer.id)
            arrival_at_cust = start_time_prev + prev_node_obj.service_time + travel_to_cust
            start_service_cust = max(arrival_at_cust, customer.ready_time)
            if start_service_cust > customer.due_time: continue
            departure_from_cust = start_service_cust + customer.service_time
            travel_to_succ = self.problem.get_travel_time(customer.id, succ_node_obj.id)
            arrival_at_succ = departure_from_cust + travel_to_succ
            time_shift = arrival_at_succ - (self.service_start_times.get(self.nodes_id[i], 0) - self.waiting_times.get(self.nodes_id[i], 0))
            if time_shift > self.forward_time_slacks.get(self.nodes_id[i], float('inf')): continue

            cost_increase = (self.problem.get_distance(prev_node_obj.id, customer.id) + 
                             self.problem.get_distance(customer.id, succ_node_obj.id) - 
                             self.problem.get_distance(prev_node_obj.id, succ_node_obj.id))
            if cost_increase < min_cost_increase:
                min_cost_increase, best_pos = cost_increase, i
        return best_pos, min_cost_increase
        
    def get_customers(self): 
        return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]

class FERoute:
    def __init__(self, problem):
        self.problem = problem
        self.nodes_id = [problem.depot.id, problem.depot.id]
        self.satellite_loads = {}
        self.satellite_deadlines = {}
        self.schedule = {}
        self.total_dist = 0.0
        self.total_time = 0.0
        
    def __repr__(self):
        path_str = " -> ".join(map(str, self.nodes_id))
        total_pickup = sum(d['pickup_load'] for d in self.satellite_loads.values())
        route_deadline = min(self.satellite_deadlines.values()) if self.satellite_deadlines else float('inf')
        
        header_str = f"--- FERoute (Cost: {self.total_dist:.2f} m, Time: {self.total_time:.2f} min, Total Pickup: {total_pickup:.2f}, Route Deadline: {route_deadline:.2f}) ---"
        
        s = [header_str, f"Path: {path_str}"]
        header = (f"  {'Node':<10}| {'Type':<10}| {'Unload (-)':>12}| {'Load (+)':>10}| {'Load After':>12}| "
                  f"{'Arrival':>9}| {'Departure':>9}| {'Deadline':>8}")
        s.append(header)
        s.append("  " + "-" * len(header))
        start_load = sum(d['delivery_load'] for d in self.satellite_loads.values())
        current_load = start_load
        depot_schedule = self.schedule.get(self.problem.depot.id, {'arrival': 0.0, 'departure': 0.0})
        s.append(f"  {self.problem.depot.id:<10}| {'Depot':<10}| {'0.00':>12}| {start_load:>+10.2f}| {current_load:>12.2f}| "
                 f"{depot_schedule['arrival']:>9.2f}| {depot_schedule['departure']:>9.2f}| {'N/A':>8}")
        for sat_id in self.nodes_id[1:-1]:
            loads = self.satellite_loads.get(sat_id, {'delivery_load': 0, 'pickup_load': 0})
            delivery, pickup = loads['delivery_load'], loads['pickup_load']
            current_load -= delivery
            current_load += pickup
            sat_schedule = self.schedule.get(sat_id, {'arrival': 0.0, 'departure': 0.0})
            deadline = self.satellite_deadlines.get(sat_id, float('inf'))
            deadline_str = f"{deadline:.2f}" if deadline != float('inf') else "N/A"
            s.append(f"  {sat_id:<10}| {'Satellite':<10}| {-delivery:>12.2f}| {pickup:>+10.2f}| {current_load:>12.2f}| "
                     f"{sat_schedule['arrival']:>9.2f}| {sat_schedule['departure']:>9.2f}| {deadline_str:>8}")
        final_pickup = sum(d['pickup_load'] for d in self.satellite_loads.values())
        final_arrival_time = self.schedule.get('final_arrival', 0.0)
        s.append(f"  {self.problem.depot.id:<10}| {'Depot':<10}| {-final_pickup:>12.2f}| {'0.00':>10}| {0.0:>12.2f}| "
                 f"{final_arrival_time:>9.2f}| {'-':>9}| {'N/A':>8}")
        return "\n".join(s)
        
    def add_satellite(self, satellite, delivery_load, pickup_load, deadline=float('inf')):
        if satellite.id not in self.nodes_id: self.nodes_id.insert(-1, satellite.id)
        if satellite.id not in self.satellite_loads: self.satellite_loads[satellite.id] = {'delivery_load': 0, 'pickup_load': 0}
        self.satellite_loads[satellite.id]['delivery_load'] += delivery_load
        self.satellite_loads[satellite.id]['pickup_load'] += pickup_load
        if satellite.id not in self.satellite_deadlines: self.satellite_deadlines[satellite.id] = deadline
        else: self.satellite_deadlines[satellite.id] = min(self.satellite_deadlines[satellite.id], deadline)

    def update_route_info(self):
        self.total_dist = 0.0
        self.total_time = 0.0
        
        current_time = 0.0
        self.schedule[self.problem.depot.id] = {'arrival': 0.0, 'departure': 0.0}
        
        for i in range(len(self.nodes_id) - 1):
            prev_node_id, curr_node_id = self.nodes_id[i], self.nodes_id[i+1]
            
            self.total_dist += self.problem.get_distance(prev_node_id, curr_node_id)
            travel_time = self.problem.get_travel_time(prev_node_id, curr_node_id)
            self.total_time += travel_time
            
            if curr_node_id != self.problem.depot.id:
                arrival_time = current_time + travel_time
                departure_time = self.schedule.get(curr_node_id, {}).get('departure', arrival_time)
                self.schedule[curr_node_id] = {'arrival': arrival_time, 'departure': departure_time}
                current_time = departure_time
                
        if len(self.nodes_id) > 2:
             self.schedule['final_arrival'] = current_time + self.problem.get_travel_time(self.nodes_id[-2], self.nodes_id[-1])
        else:
             self.schedule['final_arrival'] = 0.0

    def get_satellites_visited(self):
        return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]

class Solution:
    def __init__(self, problem):
        self.problem = problem
        self.fe_routes, self.se_routes = [], []
        self.unserved_customers = list(problem.customers)
        self.total_cost = 0.0
        self.total_time = 0.0

    def calculate_total_cost_and_time(self):
        fe_cost = sum(r.total_dist for r in self.fe_routes)
        se_cost = sum(r.total_dist for r in self.se_routes)
        self.total_cost = fe_cost + se_cost
        
        fe_time = sum(r.total_time for r in self.fe_routes)
        se_time = sum(r.total_time for r in self.se_routes)
        self.total_time = fe_time + se_time

# --- END OF FILE DataStructures.py ---