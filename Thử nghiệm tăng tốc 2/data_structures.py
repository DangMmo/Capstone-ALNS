# --- START OF FILE data_structures.py (OPTIMIZED WITH NUMBA) ---

from __future__ import annotations
import copy
from typing import Dict, List, Set, TYPE_CHECKING, Optional

# <<< BƯỚC 1: IMPORT THƯ VIỆN MỚI >>>
import numpy as np
import numba

if TYPE_CHECKING:
    from problem_parser import ProblemInstance, Customer, Satellite, PickupCustomer

# ... (Lớp FERoute không thay đổi, giữ nguyên) ...
class FERoute:
    def __init__(self, problem: "ProblemInstance"):
        self.problem = problem
        self.serviced_se_routes: Set[SERoute] = set()
        self.schedule: List[Dict] = []
        self.total_dist: float = 0.0
        self.total_time: float = 0.0
        self.route_deadline: float = float('inf')
    def __repr__(self) -> str:
        if not self.schedule: return "--- Empty FERoute ---"
        path_nodes = [self.schedule[0]['node_id']]
        for event in self.schedule[1:]:
            if event['node_id'] != path_nodes[-1]:
                path_nodes.append(event['node_id'])
        path_str = " -> ".join(map(str, path_nodes))
        deadline_str = f"Route Deadline: {self.route_deadline:.2f}" if self.route_deadline != float('inf') else "No Deadline"
        header_str = (f"--- FERoute (Cost: {self.total_dist:.2f}, Time: {self.total_time:.2f}) --- {deadline_str}")
        lines = [header_str, f"Path: {path_str}"]
        tbl_header = (f"  {'Activity':<15}| {'Node':<6}| {'Load After':>12}| {'Arrival':>9}| {'Departure':>11}")
        lines.append(tbl_header)
        lines.append("  " + "-" * len(tbl_header))
        for event in self.schedule:
            lines.append(f"  {event['activity']:<15}| {event['node_id']:<6}| {event['load_after']:>12.2f}| "
                         f"{event['arrival_time']:>9.2f}| {event['departure_time']:>11.2f}")
        return "\n".join(lines)
    def add_serviced_se_route(self, se_route: "SERoute"): self.serviced_se_routes.add(se_route)
    def remove_serviced_se_route(self, se_route: "SERoute"): self.serviced_se_routes.discard(se_route)
    def calculate_route_properties(self):
        if len(self.schedule) < 2: self.total_dist, self.total_time, self.route_deadline = 0.0, 0.0, float('inf'); return
        self.total_dist = 0.0; path_nodes = [self.schedule[0]['node_id']]; [path_nodes.append(e['node_id']) for e in self.schedule[1:] if e['node_id'] != path_nodes[-1]]
        for i in range(len(path_nodes) - 1): self.total_dist += self.problem.get_distance(path_nodes[i], path_nodes[i+1])
        self.total_time = self.schedule[-1]['arrival_time'] - self.schedule[0]['departure_time']
        deadlines = {c.deadline for se in self.serviced_se_routes for c in se.get_customers() if hasattr(c, 'deadline')}
        self.route_deadline = min(deadlines) if deadlines else float('inf')


# <<< BƯỚC 2: ĐỊNH NGHĨA HÀM LÕI NUMBA >>>
# Numba không thể truy cập các đối tượng phức tạp, vì vậy chúng ta truyền dữ liệu dưới dạng mảng
# <<< BƯỚC 1: SỬA LẠI HOÀN TOÀN HÀM LÕI NUMBA >>>
@numba.jit(nopython=True, cache=True)
def _core_calculate_se_properties_numba(
    temp_nodes_id: np.ndarray,
    node_data: np.ndarray,
    dist_matrix: np.ndarray,
    time_matrix: np.ndarray,
    initial_delivery_load: float,
    se_vehicle_capacity: float,
    fe_arrival_time: float,
    total_nodes: int
) -> np.ndarray:
    result = np.zeros(6 + len(temp_nodes_id), dtype=np.float64) 
    
    # --- 1. KIỂM TRA TẢI TRỌNG (Đã đúng, giữ nguyên) ---
    running_load = initial_delivery_load
    for i in range(1, len(temp_nodes_id) - 1):
        node_id = temp_nodes_id[i]
        demand = node_data[node_id, 0]
        is_pickup = node_data[node_id, 4]
        if is_pickup == 0: running_load -= demand
        else: running_load += demand
        if running_load < -1e-6 or running_load > se_vehicle_capacity + 1e-6:
            return result

    # --- 2. MÔ PHỎNG LỊCH TRÌNH (LOGIC MỚI, CHÍNH XÁC) ---
    temp_service_start_times = np.zeros(len(temp_nodes_id), dtype=np.float64)
    
    # Khởi tạo thời gian bắt đầu tại satellite
    first_node_in_route_id = temp_nodes_id[1]
    effective_start_time = max(fe_arrival_time, node_data[first_node_in_route_id, 2])
    temp_service_start_times[0] = effective_start_time

    # Lặp để tính toán lịch trình
    for i in range(len(temp_nodes_id) - 1):
        prev_id_in_route = temp_nodes_id[i]
        curr_id_in_route = temp_nodes_id[i+1]
        
        prev_idx = prev_id_in_route % total_nodes
        curr_idx = curr_id_in_route % total_nodes
        
        service_time_prev = node_data[prev_idx, 1]
        # Lấy thời gian bắt đầu phục vụ của node trước đó từ mảng
        start_service_prev = temp_service_start_times[i]
        
        departure_prev = start_service_prev + service_time_prev
        arrival_curr = departure_prev + time_matrix[prev_idx, curr_idx]
        start_service_curr = max(arrival_curr, node_data[curr_idx, 2])
        
        if start_service_curr > node_data[curr_idx, 3] + 1e-6:
            return result
        
        # Lưu thời gian bắt đầu phục vụ của node hiện tại vào mảng
        temp_service_start_times[i+1] = start_service_curr

    # --- 3. TÍNH TOÁN KẾT QUẢ (Đã đúng, giữ nguyên) ---
    new_total_dist = 0.0
    for i in range(len(temp_nodes_id) - 1):
        prev_idx = temp_nodes_id[i] % total_nodes
        curr_idx = temp_nodes_id[i+1] % total_nodes
        new_total_dist += dist_matrix[prev_idx, curr_idx]

    deadline_count = 0
    for node_id in temp_nodes_id:
        idx = node_id % total_nodes
        if node_data[idx, 4] == 1: # is_pickup
            deadline = node_data[idx, 5]
            if deadline < np.inf:
                result[6 + deadline_count] = deadline
                deadline_count += 1
    
    result[0] = 1.0
    result[1] = new_total_dist
    result[2] = initial_delivery_load
    result[4] = temp_service_start_times[-1] # schedule_end_time
    result[5] = deadline_count

    return result

class SERoute:
    def __init__(self, satellite: "Satellite", problem: "ProblemInstance", start_time: float = 0.0):
        self.problem = problem
        self.satellite = satellite
        self.nodes_id: List[int] = [satellite.dist_id, satellite.coll_id]
        self.serving_fe_routes: Set[FERoute] = set()
        self.service_start_times: Dict[int, float] = {satellite.dist_id: start_time}
        self.waiting_times: Dict[int, float] = {satellite.dist_id: 0.0}
        self.forward_time_slacks: Dict[int, float] = {satellite.dist_id: float('inf')}
        self.total_dist: float = 0.0
        self.total_load_pickup: float = 0.0
        self.total_load_delivery: float = 0.0
        self.calculate_full_schedule_and_slacks()
    def calculate_full_schedule_and_slacks(self):
        # ... (Nội dung hàm này giữ nguyên) ...
        for i in range(len(self.nodes_id) - 1):
            prev_id, curr_id = self.nodes_id[i], self.nodes_id[i+1]
            prev_obj = self.problem.node_objects[prev_id % self.problem.total_nodes]
            curr_obj = self.problem.node_objects[curr_id % self.problem.total_nodes]
            st_prev = prev_obj.service_time if prev_obj.type != 'Satellite' else 0.0
            departure_prev = self.service_start_times.get(prev_id, 0.0) + st_prev
            arrival_curr = departure_prev + self.problem.get_travel_time(prev_obj.id, curr_obj.id)
            start_service = max(arrival_curr, getattr(curr_obj, 'ready_time', 0))
            self.service_start_times[curr_id] = start_service
            self.waiting_times[curr_id] = start_service - arrival_curr
        n = len(self.nodes_id)
        if self.nodes_id: self.forward_time_slacks.setdefault(self.nodes_id[n-1], float('inf'))
        for i in range(n - 2, -1, -1):
            node_id, succ_id = self.nodes_id[i], self.nodes_id[i+1]
            node_obj = self.problem.node_objects[node_id % self.problem.total_nodes]
            due_time = getattr(node_obj, 'due_time', float('inf'))
            st_node = node_obj.service_time if node_obj.type != 'Satellite' else 0.0
            departure_node = self.service_start_times.get(node_id, 0.0) + st_node
            arrival_succ = self.service_start_times.get(succ_id, 0.0) - self.waiting_times.get(succ_id, 0.0)
            slack_between = arrival_succ - departure_node
            self.forward_time_slacks[node_id] = min(self.forward_time_slacks.get(succ_id, float('inf')) + slack_between, due_time - self.service_start_times.get(node_id, 0.0))
    def __repr__(self) -> str:
        # ... (Nội dung hàm này giữ nguyên) ...
        path_ids = [nid % self.problem.total_nodes for nid in self.nodes_id]
        path_str = " -> ".join(map(str, path_ids))
        start_time_val = self.service_start_times.get(self.nodes_id[0], 0.0)
        end_time_val = self.service_start_times.get(self.nodes_id[-1], 0.0)
        operating_time = end_time_val - start_time_val if len(self.nodes_id) > 1 else 0.0
        header_str = (f"--- SERoute for Satellite {self.satellite.id} (Cost: {self.total_dist:.2f}, Time: {operating_time:.2f}) ---")
        lines = [header_str, f"Path: {path_str}"]
        tbl_header = (f"  {'Node':<10}| {'Type':<18}| {'Demand':>8}| {'Load After':>12}| {'Arrival':>9}| {'Start Svc':>9}| {'Departure':>11}| {'Deadline':>10}")
        lines.append(tbl_header)
        lines.append("  " + "-" * len(tbl_header))
        current_load = self.total_load_delivery
        dep_start = start_time_val
        lines.append(f"  {str(self.satellite.id) + ' (Dist)':<10}| {'Satellite':<18}| {-self.total_load_delivery:>8.2f}| {current_load:>12.2f}| "
                     f"{start_time_val:>9.2f}| {start_time_val:>9.2f}| {dep_start:>11.2f}| {'N/A':>10}")
        for node_id in self.nodes_id[1:-1]:
            customer = self.problem.node_objects[node_id]
            demand_str, deadline_str = "", "N/A"
            if customer.type == 'DeliveryCustomer':
                current_load -= customer.demand
                demand_str = f"{-customer.demand:.2f}"
            else:
                current_load += customer.demand
                demand_str = f"+{customer.demand:.2f}"
                if hasattr(customer, 'deadline'):
                    deadline_str = f"{customer.deadline:.2f}"
            arrival = self.service_start_times.get(node_id, 0.0) - self.waiting_times.get(node_id, 0.0)
            start_svc = self.service_start_times.get(node_id, 0.0)
            departure = start_svc + customer.service_time
            lines.append(f"  {customer.id:<10}| {customer.type:<18}| {demand_str:>8}| {current_load:>12.2f}| "
                         f"{arrival:>9.2f}| {start_svc:>9.2f}| {departure:>11.2f}| {deadline_str:>10}")
        final_load = current_load
        arrival_end = self.service_start_times.get(self.nodes_id[-1], 0.0) - self.waiting_times.get(self.nodes_id[-1], 0.0)
        dep_end = end_time_val
        lines.append(f"  {str(self.satellite.id) + ' (Coll)':<10}| {'Satellite':<18}| {self.total_load_pickup:>+8.2f}| {final_load:>12.2f}| "
                     f"{arrival_end:>9.2f}| {end_time_val:>9.2f}| {dep_end:>11.2f}| {'N/A':>10}")
        return "\n".join(lines)
    def insert_customer_at_pos(self, customer: "Customer", pos: int):
        # ... (Nội dung hàm này giữ nguyên) ...
        prev_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]; succ_obj = self.problem.node_objects[self.nodes_id[pos] % self.problem.total_nodes]
        cost_inc = (self.problem.get_distance(prev_obj.id, customer.id) + self.problem.get_distance(customer.id, succ_obj.id) - self.problem.get_distance(prev_obj.id, succ_obj.id))
        self.nodes_id.insert(pos, customer.id); self.total_dist += cost_inc
        if customer.type == 'DeliveryCustomer': self.total_load_delivery += customer.demand
        else: self.total_load_pickup += customer.demand
        self.calculate_full_schedule_and_slacks()
    def remove_customer(self, customer: "Customer"):
        # ... (Nội dung hàm này giữ nguyên) ...
        if customer.id not in self.nodes_id: return
        pos = self.nodes_id.index(customer.id)
        prev_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]; succ_obj = self.problem.node_objects[self.nodes_id[pos+1] % self.problem.total_nodes]
        cost_dec = (self.problem.get_distance(prev_obj.id, customer.id) + self.problem.get_distance(customer.id, succ_obj.id) - self.problem.get_distance(prev_obj.id, succ_obj.id))
        self.total_dist -= cost_dec; self.nodes_id.pop(pos)
        if customer.type == 'DeliveryCustomer': self.total_load_delivery -= customer.demand
        else: self.total_load_pickup -= customer.demand
        self.calculate_full_schedule_and_slacks()
    def get_customers(self) -> List["Customer"]:
        # ... (Nội dung hàm này giữ nguyên) ...
        return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]

    # <<< BƯỚC 3: SỬA ĐỔI HÀM MÔ PHỎNG ĐỂ GỌI NUMBA >>>
    def calculate_insertion_properties(self, customer: "Customer", pos: int, fe_arrival_time: float) -> Optional[Dict]:
        problem = self.problem
        temp_nodes_id = np.array(self.nodes_id[:pos] + [customer.id] + self.nodes_id[pos:])
        new_delivery_load = self.total_load_delivery
        new_pickup_load = self.total_load_pickup
        if customer.type == 'DeliveryCustomer':
            new_delivery_load += customer.demand
        else:
            new_pickup_load += customer.demand
        if new_delivery_load > problem.se_vehicle_capacity + 1e-6:
            return None
        result_array = _core_calculate_se_properties_numba(
            temp_nodes_id,
            problem.node_data_for_numba,
            problem.dist_matrix_numba,
            problem.time_matrix_numba,
            new_delivery_load,
            problem.se_vehicle_capacity,
            fe_arrival_time,
            problem.total_nodes
        )
        if result_array[0] == 0:
            return None
        deadline_count = int(result_array[5])
        deadlines = set(result_array[6 : 6 + deadline_count])
        return {
            "new_total_dist": result_array[1],
            "new_delivery_load": new_delivery_load,
            "new_pickup_load": new_pickup_load,
            "new_schedule_end_time": result_array[4],
            "new_deadlines": deadlines
        }
# ... (Lớp Solution và VRP2E_State giữ nguyên) ...
class Solution:
    def __init__(self, problem: "ProblemInstance"):
        self.problem = problem
        self.fe_routes: List[FERoute] = []
        self.se_routes: List[SERoute] = []
        self.customer_to_se_route_map: Dict[int, SERoute] = {}
        self.unserved_customers: List["Customer"] = []
    def add_fe_route(self, fe_route: FERoute): self.fe_routes.append(fe_route)
    def add_se_route(self, se_route: SERoute): self.se_routes.append(se_route); self.update_customer_map()
    def remove_fe_route(self, fe_route: FERoute):
        if fe_route in self.fe_routes: self.fe_routes.remove(fe_route)
    def remove_se_route(self, se_route: SERoute):
        if se_route in self.se_routes: self.se_routes.remove(se_route)
        self.update_customer_map()
    def link_routes(self, fe_route: FERoute, se_route: SERoute): fe_route.add_serviced_se_route(se_route); se_route.serving_fe_routes.add(fe_route)
    def unlink_routes(self, fe_route: FERoute, se_route: SERoute): fe_route.remove_serviced_se_route(se_route); se_route.serving_fe_routes.discard(fe_route)
    def update_customer_map(self): self.customer_to_se_route_map = {c.id: r for r in self.se_routes for c in r.get_customers()}
    def calculate_total_cost(self) -> float: return sum(r.total_dist for r in self.fe_routes) + sum(r.total_dist for r in self.se_routes)

class VRP2E_State:
    def __init__(self, solution: Solution): self.solution = solution
    def copy(self): return copy.deepcopy(self)
    @property
    def cost(self) -> float: return self.solution.calculate_total_cost()


# --- END OF FILE data_structures.py ---