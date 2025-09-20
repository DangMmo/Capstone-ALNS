# File: DataStructures.py (PHIÊN BẢN NÂNG CẤP HIỂN THỊ)

import sys

class SERoute:
    def __init__(self, satellite, problem):
        self.problem = problem
        self.satellite = satellite
        self.nodes_id = [satellite.dist_id, satellite.coll_id]
        
        self.service_start_times = {satellite.dist_id: 0.0, satellite.coll_id: float('inf')}
        self.waiting_times = {satellite.dist_id: 0.0, satellite.coll_id: 0.0}
        self.forward_time_slacks = {satellite.dist_id: float('inf'), satellite.coll_id: float('inf')}
        
        self.total_dist = 0.0
        self.total_load_pickup = 0.0
        self.total_load_delivery = 0.0

    def __repr__(self):
        """
        Tạo ra một chuỗi hiển thị chi tiết nhật ký hành trình của tuyến SE.
        """
        s = []
        path_ids = [nid % self.problem.total_nodes for nid in self.nodes_id]
        path_str = " -> ".join(map(str, path_ids))
        
        s.append(f"--- SERoute for Satellite {self.satellite.id} (Cost: {self.total_dist:.2f}) ---")
        s.append(f"Path: {path_str}")
        s.append(f"  {'Node':<10}| {'Type':<18}| {'Demand':>8}| {'Load After':>12}| {'Arrival':>9}| {'Start Svc':>9}")
        s.append("  " + "-"*78)

        # Bắt đầu tại bưu cục phân phối
        # Tải trọng ban đầu là toàn bộ hàng cần giao
        current_load = self.total_load_delivery
        
        start_node_obj = self.problem.node_objects[self.satellite.id]
        start_time = self.service_start_times.get(self.satellite.dist_id, 0.0)
        s.append(f"  {str(start_node_obj.id) + ' (Dist)':<10}| {'Satellite':<18}| {-self.total_load_delivery:>8.2f}| {current_load:>12.2f}| {start_time:>9.2f}| {start_time:>9.2f}")
        
        # Duyệt qua các khách hàng
        for node_id in self.nodes_id[1:-1]:
            customer = self.problem.node_objects[node_id]
            
            if customer.type == 'DeliveryCustomer':
                current_load -= customer.demand # Giảm tải
                demand_str = f"{-customer.demand:.2f}"
            else: # PickupCustomer
                current_load += customer.demand # Tăng tải
                demand_str = f"+{customer.demand:.2f}"

            arrival = self.service_start_times[node_id] - self.waiting_times[node_id]
            start_svc = self.service_start_times[node_id]
            
            s.append(f"  {customer.id:<10}| {customer.type:<18}| {demand_str:>8}| {current_load:>12.2f}| {arrival:>9.2f}| {start_svc:>9.2f}")
            
        # Kết thúc tại bưu cục thu gom
        end_node_obj = self.problem.node_objects[self.satellite.id]
        end_time = self.service_start_times.get(self.satellite.coll_id, 0.0)
        final_load = current_load - self.total_load_pickup # Bỏ hết hàng pickup lên xe FE
        s.append(f"  {str(end_node_obj.id) + ' (Coll)':<10}| {'Satellite':<18}| {self.total_load_pickup:>+8.2f}| {final_load:>12.2f}| {end_time:>9.2f}| {end_time:>9.2f}")
        
        return "\n".join(s)

    # Các hàm còn lại giữ nguyên...
    def calculate_full_schedule_and_slacks(self):
        # ... (Không đổi)
        prev_node_id = self.nodes_id[0]
        prev_node_obj = self.problem.node_objects[prev_node_id % self.problem.total_nodes]
        for i in range(1, len(self.nodes_id)):
            curr_node_id = self.nodes_id[i]
            curr_node_obj = self.problem.node_objects[curr_node_id % self.problem.total_nodes]
            travel_time = self.problem.get_distance(prev_node_obj.id, curr_node_obj.id)
            arrival_time = self.service_start_times[prev_node_id] + prev_node_obj.service_time + travel_time
            start_service_time = max(arrival_time, getattr(curr_node_obj, 'ready_time', 0))
            self.service_start_times[curr_node_id] = start_service_time
            self.waiting_times[curr_node_id] = start_service_time - arrival_time
            prev_node_id = curr_node_id
            prev_node_obj = curr_node_obj
        n = len(self.nodes_id)
        self.forward_time_slacks[self.nodes_id[n-1]] = float('inf')
        for i in range(n - 2, -1, -1):
            node_id, succ_node_id = self.nodes_id[i], self.nodes_id[i+1]
            node_obj = self.problem.node_objects[node_id % self.problem.total_nodes]
            due_time = getattr(node_obj, 'due_time', float('inf'))
            slack_between_nodes = (self.service_start_times[succ_node_id] 
                                  - (self.service_start_times[node_id] + node_obj.service_time)
                                  - self.problem.get_distance(node_obj.id, self.problem.node_objects[succ_node_id % self.problem.total_nodes].id))
            self.forward_time_slacks[node_id] = min(
                self.forward_time_slacks.get(succ_node_id, float('inf')) + slack_between_nodes,
                due_time - self.service_start_times[node_id])
    def find_best_insertion_pos(self, customer):
        # ... (Không đổi)
        best_pos, min_cost_increase = None, float('inf')
        for i in range(1, len(self.nodes_id)):
            prev_node_id, succ_node_id = self.nodes_id[i-1], self.nodes_id[i]
            prev_node_obj = self.problem.node_objects[prev_node_id % self.problem.total_nodes]
            succ_node_obj = self.problem.node_objects[succ_node_id % self.problem.total_nodes]
            if customer.type == 'DeliveryCustomer':
                if self.total_load_delivery + customer.demand > self.problem.se_vehicle_capacity: continue
            else:
                if self.total_load_pickup + customer.demand > self.problem.se_vehicle_capacity: continue
            start_time_prev = self.service_start_times[prev_node_id]
            travel_to_cust = self.problem.get_distance(prev_node_obj.id, customer.id)
            arrival_at_cust = start_time_prev + prev_node_obj.service_time + travel_to_cust
            start_service_cust = max(arrival_at_cust, customer.ready_time)
            if start_service_cust > customer.due_time: continue
            departure_from_cust = start_service_cust + customer.service_time
            travel_to_succ = self.problem.get_distance(customer.id, succ_node_obj.id)
            arrival_at_succ = departure_from_cust + travel_to_succ
            time_shift = arrival_at_succ - self.service_start_times[succ_node_id]
            if time_shift > self.forward_time_slacks[succ_node_id]: continue
            cost_increase = (self.problem.get_distance(prev_node_obj.id, customer.id) +
                             self.problem.get_distance(customer.id, succ_node_obj.id) -
                             self.problem.get_distance(prev_node_obj.id, succ_node_obj.id))
            if cost_increase < min_cost_increase:
                min_cost_increase, best_pos = cost_increase, i
        return best_pos, min_cost_increase
    def insert_customer_at_pos(self, customer, pos):
        # ... (Không đổi)
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

class FERoute:
    def __init__(self, problem):
        self.problem = problem
        self.nodes_id = [problem.depot.id, problem.depot.id]
        # **THÊM MỚI**: Lưu lại thông tin tải trọng tại mỗi bưu cục
        self.satellite_loads = {} # {sat_id: {'delivery_load': X, 'pickup_load': Y}}
        self.total_dist = 0.0

    def __repr__(self):
        """
        Tạo ra một chuỗi hiển thị chi tiết nhật ký hành trình của tuyến FE.
        """
        s = []
        path_str = " -> ".join(map(str, self.nodes_id))
        
        s.append(f"--- FERoute (Cost: {self.total_dist:.2f}) ---")
        s.append(f"Path: {path_str}")
        s.append(f"  {'Node':<10}| {'Type':<10}| {'Unload (-)':>12}| {'Load (+)':>10}| {'Load After':>12}")
        s.append("  " + "-"*65)
        
        # Bắt đầu tại kho tổng
        start_load = sum(d['delivery_load'] for d in self.satellite_loads.values())
        current_load = start_load
        s.append(f"  {self.problem.depot.id:<10}| {'Depot':<10}| {'0.00':>12}| {start_load:>+10.2f}| {current_load:>12.2f}")
        
        # Duyệt qua các bưu cục
        for sat_id in self.nodes_id[1:-1]:
            loads = self.satellite_loads.get(sat_id, {'delivery_load': 0, 'pickup_load': 0})
            delivery = loads['delivery_load']
            pickup = loads['pickup_load']
            
            current_load -= delivery # Dỡ hàng giao
            current_load += pickup   # Lấy hàng gom
            
            s.append(f"  {sat_id:<10}| {'Satellite':<10}| {-delivery:>12.2f}| {pickup:>+10.2f}| {current_load:>12.2f}")
            
        # Kết thúc tại kho tổng
        final_pickup = sum(d['pickup_load'] for d in self.satellite_loads.values())
        s.append(f"  {self.problem.depot.id:<10}| {'Depot':<10}| {-final_pickup:>12.2f}| {'0.00':>10}| {0.0:>12.2f}")

        return "\n".join(s)

    def update_route_info(self):
        self.total_dist = 0
        for i in range(len(self.nodes_id) - 1):
            self.total_dist += self.problem.get_distance(self.nodes_id[i], self.nodes_id[i+1])

class Solution:
    # ... (Không đổi)
    def __init__(self, problem):
        self.problem = problem
        self.fe_routes = []
        self.se_routes = []
        self.unserved_customers = [c.id for c in problem.customers]
        self.total_cost = float('inf')

    def calculate_total_cost(self):
        fe_cost = sum(r.total_dist for r in self.fe_routes)
        se_cost = sum(r.total_dist for r in self.se_routes)
        self.total_cost = fe_cost + se_cost
        return self.total_cost