from __future__ import annotations
import copy
from typing import Dict, List, Set, TYPE_CHECKING

# <<< DÒNG IMPORT MỚI >>>
# Import RouteMemento từ file transaction.py mà chúng ta đã tạo.
# Giả sử file đó nằm cùng cấp.
from transaction import RouteMemento

if TYPE_CHECKING:
    from problem_parser import ProblemInstance, Customer, Satellite, PickupCustomer

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

    # <<< CÁC PHƯƠNG THỨC MỚI CHO CƠ CHẾ MEMENTO >>>
    def backup(self) -> RouteMemento:
        """Tạo một memento chứa trạng thái hiện tại của route."""
        return RouteMemento(self)

    def restore(self, memento: RouteMemento):
        """Khôi phục trạng thái của route từ một memento."""
        self.serviced_se_routes = memento.serviced_se_routes
        self.schedule = memento.schedule
        self.total_dist = memento.total_dist
        self.total_time = memento.total_time
        self.route_deadline = memento.route_deadline


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
        # Tái tính toán lịch trình và các thông số thời gian cho SE route.
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
        
        # Tái tính toán độ trễ (slack) ngược từ cuối tuyến
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
        # (Nội dung hàm này giữ nguyên)
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
        prev_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]; succ_obj = self.problem.node_objects[self.nodes_id[pos] % self.problem.total_nodes]
        cost_inc = (self.problem.get_distance(prev_obj.id, customer.id) + self.problem.get_distance(customer.id, succ_obj.id) - self.problem.get_distance(prev_obj.id, succ_obj.id))
        self.nodes_id.insert(pos, customer.id); self.total_dist += cost_inc
        if customer.type == 'DeliveryCustomer': self.total_load_delivery += customer.demand
        else: self.total_load_pickup += customer.demand
        self.calculate_full_schedule_and_slacks()
        
    def remove_customer(self, customer: "Customer"):
        if customer.id not in self.nodes_id: return
        pos = self.nodes_id.index(customer.id)
        prev_obj = self.problem.node_objects[self.nodes_id[pos-1] % self.problem.total_nodes]; succ_obj = self.problem.node_objects[self.nodes_id[pos+1] % self.problem.total_nodes]
        cost_dec = (self.problem.get_distance(prev_obj.id, customer.id) + self.problem.get_distance(customer.id, succ_obj.id) - self.problem.get_distance(prev_obj.id, succ_obj.id))
        self.total_dist -= cost_dec; self.nodes_id.pop(pos)
        if customer.type == 'DeliveryCustomer': self.total_load_delivery -= customer.demand
        else: self.total_load_pickup -= customer.demand
        self.calculate_full_schedule_and_slacks()
        
    def get_customers(self) -> List["Customer"]:
        return [self.problem.node_objects[nid] for nid in self.nodes_id[1:-1]]
        
    # <<< CÁC PHƯƠNG THỨC MỚI CHO CƠ CHẾ MEMENTO >>>
    def backup(self) -> RouteMemento:
        """Tạo một memento chứa trạng thái hiện tại của route."""
        return RouteMemento(self)

    def restore(self, memento: RouteMemento):
        """Khôi phục trạng thái của route từ một memento."""
        self.nodes_id = memento.nodes_id
        self.total_dist = memento.total_dist
        self.total_load_pickup = memento.total_load_pickup
        self.total_load_delivery = memento.total_load_delivery
        self.service_start_times = memento.service_start_times
        self.waiting_times = memento.waiting_times
        self.forward_time_slacks = memento.forward_time_slacks
        self.serving_fe_routes = memento.serving_fe_routes


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
    def __init__(self, solution: Solution): 
        self.solution = solution
    
    # <<< PHƯƠNG THỨC COPY ĐƯỢC CẬP NHẬT >>>
    def copy(self): 
        """
        Tạo một bản sao sâu (deepcopy) hoàn chỉnh của state.
        LƯU Ý QUAN TRỌNG: Hàm này rất tốn kém về mặt hiệu năng.
        Chỉ nên sử dụng nó để lưu trữ trạng thái tốt nhất (best_state)
        hoặc khi cần một bản sao độc lập hoàn toàn, không dùng trong mỗi vòng lặp ALNS.
        """
        return copy.deepcopy(self)
    
    @property
    def cost(self) -> float: 
        return self.solution.calculate_total_cost()