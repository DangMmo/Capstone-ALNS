
from __future__ import annotations
import sys
import math
from typing import Dict, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from Parser import ProblemInstance, Customer, Satellite, Depot

class SERoute:
    def __init__(self, satellite: Satellite, problem: ProblemInstance, start_time: float = 0.0):
        self.problem = problem
        self.satellite = satellite
        self.nodes_id: List[int] = [satellite.dist_id, satellite.coll_id]
        self.serving_fe_routes: Set[FERoute] = set()
        self.service_start_times: Dict[int, float] = {satellite.dist_id: start_time, satellite.coll_id: float('inf')}
        self.waiting_times: Dict[int, float] = {satellite.dist_id: 0.0, satellite.coll_id: 0.0}
        self.forward_time_slacks: Dict[int, float] = {satellite.dist_id: float('inf'), satellite.coll_id: float('inf')}
        self.total_dist: float = 0.0
        self.total_load_pickup: float = 0.0
        self.total_load_delivery: float = 0.0
        self.calculate_full_schedule_and_slacks()
        
    def calculate_full_schedule_and_slacks(self):
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
            due_time = getattr(node_obj, 'due_time', float('inf'))
            service_time_node = node_obj.service_time
            if node_obj.type == 'Satellite': service_time_node = 0.0
            
            departure_time_node = self.service_start_times[node_id] + service_time_node
            arrival_time_succ = self.service_start_times[succ_node_id] - self.waiting_times[succ_node_id]
            slack_between = arrival_time_succ - departure_time_node
            
            self.forward_time_slacks[node_id] = min(self.forward_time_slacks.get(succ_node_id, float('inf')) + slack_between,
                                                  due_time - self.service_start_times[node_id])

    def __repr__(self):
        path_ids = [nid % self.problem.total_nodes for nid in self.nodes_id]
        path_str = " -> ".join(map(str, path_ids))
        deadlines = [c.deadline for c in self.get_customers() if hasattr(c, 'deadline')]
        route_deadline_str = f"Route Deadline: {min(deadlines):.2f}" if deadlines else "No Deadline"
        
        start_time_val = self.service_start_times.get(self.nodes_id[0], 0.0)
        end_time_val = self.service_start_times.get(self.nodes_id[-1], 0.0)
        operating_time = end_time_val - start_time_val if len(self.nodes_id) > 2 else 0.0

        header_str = (f"--- SERoute for Satellite {self.satellite.id} (Cost: {self.total_dist:.2f}, "
                      f"Time: {operating_time:.2f}) --- {route_deadline_str}")
        
        lines = [header_str, f"Path: {path_str}"]
        tbl_header = (f"  {'Node':<10}| {'Type':<18}| {'Demand':>8}| {'Load After':>12}| {'Arrival':>9}| {'Start Svc':>9}| "
                      f"{'Latest Arr':>10}| {'Deadline':>8}")
        lines.append(tbl_header)
        lines.append("  " + "-" * len(tbl_header))
        
        current_load = self.total_load_delivery
        latest_arrival_start = start_time_val + self.forward_time_slacks.get(self.satellite.dist_id, 0.0)
        
        lines.append(f"  {str(self.satellite.id) + ' (Dist)':<10}| {'Satellite':<18}| {-self.total_load_delivery:>8.2f}| {current_load:>12.2f}| "
                     f"{start_time_val:>9.2f}| {start_time_val:>9.2f}| {latest_arrival_start:>10.2f}| {'N/A':>8}")

        for node_id in self.nodes_id[1:-1]:
            customer = self.problem.node_objects[node_id]
            demand_str, deadline_str = "", "N/A"
            if customer.type == 'DeliveryCustomer':
                current_load -= customer.demand
                demand_str = f"{-customer.demand:.2f}"
            else:
                current_load += customer.demand
                demand_str = f"+{customer.demand:.2f}"
                deadline_str = f"{customer.deadline:.2f}"
            
            arrival = self.service_start_times.get(node_id, 0.0) - self.waiting_times.get(node_id, 0.0)
            start_svc = self.service_start_times.get(node_id, 0.0)
            latest_arrival = arrival + self.forward_time_slacks.get(node_id, 0.0)
            lines.append(f"  {customer.id:<10}| {customer.type:<18}| {demand_str:>8}| {current_load:>12.2f}| "
                         f"{arrival:>9.2f}| {start_svc:>9.2f}| {latest_arrival:>10.2f}| {deadline_str:>8}")

        final_load = current_load
        lines.append(f"  {str(self.satellite.id) + ' (Coll)':<10}| {'Satellite':<18}| {self.total_load_pickup:>+8.2f}| {final_load:>12.2f}| "
                     f"{end_time_val:>9.2f}| {end_time_val:>9.2f}| {'inf':>10}| {'N/A':>8}")
        return "\n".join(lines)

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

    def get_customers(self): 
        return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]

class FERoute:
    def __init__(self, problem: ProblemInstance):
        self.problem = problem
        self.serviced_se_routes: Set[SERoute] = set()
        self.served_customers: Set[int] = set()
        self.schedule: List[Dict] = [] 
        self.total_dist: float = 0.0
        self.total_time: float = 0.0
        self.route_deadline: float = float('inf')

    def __repr__(self):
        if not self.schedule: return "--- Empty FERoute ---"
        path_nodes = [self.schedule[0]['node_id']]
        for event in self.schedule[1:]:
            if event['node_id'] != path_nodes[-1]:
                path_nodes.append(event['node_id'])
        path_str = " -> ".join(map(str, path_nodes))
        deadline_str = f"Route Deadline: {self.route_deadline:.2f}" if self.route_deadline != float('inf') else "No Deadline"
        header_str = (f"--- FERoute (Cost: {self.total_dist:.2f}, Time: {self.total_time:.2f}) --- {deadline_str}")
        lines = [header_str, f"Path: {path_str}"]
        tbl_header = (f"  {'Node':<6}| {'Activity':<15}| {'Load Change':>12}| {'Load After':>12}| {'Arrival':>9}| {'Start Svc':>9}| {'Departure':>11}")
        lines.append(tbl_header)
        lines.append("  " + "-" * len(tbl_header))
        for event in self.schedule:
            lines.append(f"  {event['node_id']:<6}| {event['activity']:<15}| {event['load_change']:>+12.2f}| {event['load_after']:>12.2f}| "
                         f"{event['arrival_time']:>9.2f}| {event['start_svc_time']:>9.2f}| {event['departure_time']:>11.2f}")
        return "\n".join(lines)
    
    def calculate_route_properties(self):
        """
        Cap nhat cac thuoc tinh tong hop (total_dist, total_time, route_deadline)
        dua tren thuoc tinh 'schedule' hien tai.
        """
        if len(self.schedule) < 2:
            self.total_dist = 0.0
            self.total_time = 0.0
            self.route_deadline = float('inf')
            return

        # Tinh toan tong quang duong
        self.total_dist = 0
        path_nodes = [self.schedule[0]['node_id']]
        for event in self.schedule[1:]:
            if event['node_id'] != path_nodes[-1]:
                path_nodes.append(event['node_id'])
        
        for i in range(len(path_nodes) - 1):
            self.total_dist += self.problem.get_distance(path_nodes[i], path_nodes[i+1])
        
        # Tinh toan tong thoi gian
        start_time = self.schedule[0]['departure_time']
        end_time = self.schedule[-1]['arrival_time']
        self.total_time = end_time - start_time
        
        # Tinh toan deadline hieu luc cua tuyen
        deadlines = {cust.deadline for se in self.serviced_se_routes for cust in se.get_customers() if hasattr(cust, 'deadline')}
        self.route_deadline = min(deadlines) if deadlines else float('inf')

    def _rebuild_served_customers(self):
        self.served_customers.clear()
        for se_route in self.serviced_se_routes:
            for customer in se_route.get_customers():
                self.served_customers.add(customer.id)
    
    def add_serviced_se_route(self, se_route: SERoute):
        if se_route in self.serviced_se_routes: return
        self.serviced_se_routes.add(se_route)
        for customer in se_route.get_customers():
            self.served_customers.add(customer.id)

    def remove_serviced_se_route(self, se_route: SERoute):
        self.serviced_se_routes.discard(se_route)
        self._rebuild_served_customers()

    def get_satellites_visited(self) -> Set[Satellite]:
        return {self.problem.node_objects[event['node_id']] for event in self.schedule if event['activity'] in ['UNLOAD_DELIV', 'LOAD_PICKUP']}
class Solution:
    def __init__(self, problem: ProblemInstance):
        self.problem = problem
        self.fe_routes: List[FERoute] = []
        self.se_routes: List[SERoute] = []
        self.se_routes_by_satellite: Dict[int, List[SERoute]] = {}
        self.customer_to_se_route_map: Dict[int, SERoute] = {}
        self.fe_routes_by_satellite: Dict[int, List[FERoute]] = {}
        self.unserved_customers: List[Customer] = list(problem.customers)
        self.total_cost: float = 0.0

    def add_se_route(self, se_route: SERoute):
        if se_route in self.se_routes: return
        self.se_routes.append(se_route)
        sat_id = se_route.satellite.id
        self.se_routes_by_satellite.setdefault(sat_id, []).append(se_route)
        for customer in se_route.get_customers():
            self.customer_to_se_route_map[customer.id] = se_route

    def remove_se_route(self, se_route: SERoute):
        if se_route not in self.se_routes: return
        self.se_routes.remove(se_route)
        sat_id = se_route.satellite.id
        if sat_id in self.se_routes_by_satellite and se_route in self.se_routes_by_satellite[sat_id]:
            self.se_routes_by_satellite[sat_id].remove(se_route)
            if not self.se_routes_by_satellite[sat_id]:
                del self.se_routes_by_satellite[sat_id]
        for customer in se_route.get_customers():
            if customer.id in self.customer_to_se_route_map:
                del self.customer_to_se_route_map[customer.id]
        for fe_route in list(se_route.serving_fe_routes):
            self.unlink_routes(fe_route, se_route)

    def add_fe_route(self, fe_route: FERoute):
        if fe_route not in self.fe_routes:
            self.fe_routes.append(fe_route)

    def remove_fe_route(self, fe_route: FERoute):
        if fe_route not in self.fe_routes: return
        self.fe_routes.remove(fe_route)
        for se_route in list(fe_route.serviced_se_routes):
            self.unlink_routes(fe_route, se_route)

    def link_routes(self, fe_route: FERoute, se_route: SERoute):
        fe_route.add_serviced_se_route(se_route)
        se_route.serving_fe_routes.add(fe_route)

    def unlink_routes(self, fe_route: FERoute, se_route: SERoute):
        fe_route.remove_serviced_se_route(se_route)
        se_route.serving_fe_routes.discard(fe_route)
        
    def calculate_total_cost(self):
        fe_cost = sum(r.total_dist for r in self.fe_routes)
        se_cost = sum(r.total_dist for r in self.se_routes)
        self.total_cost = fe_cost + se_cost
        return self.total_cost
    
# --- END OF FILE DataStructures.py (ADVANCED & COMPATIBLE VERSION) ---
# --- END OF FILE DataStructures.py (PHASE 1 VERSION - FULL) ---