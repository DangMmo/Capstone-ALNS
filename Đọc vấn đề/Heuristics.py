# --- START OF FILE Heuristics.py ---

import copy
from Parser import ProblemInstance, Customer
from DataStructures import SERoute

class InsertionProcessor:
    """
    Lớp này chứa logic thuật toán liên quan đến việc chèn khách hàng vào các tuyến đường.
    Nó tách biệt logic "quyết định" ra khỏi các lớp cấu trúc dữ liệu.
    """
    def __init__(self, problem: ProblemInstance):
        self.problem = problem

    def find_best_insertion_for_se_route(self, route: SERoute, customer: Customer):
        """
        Tìm vị trí và chi phí tốt nhất để chèn một khách hàng vào một SERoute cụ thể.
        Đây là logic đã được chuyển từ lớp SERoute ra ngoài.

        Args:
            route (SERoute): Tuyến đường cấp 2 đang được xem xét.
            customer (Customer): Khách hàng cần chèn.

        Returns:
            dict: Một dictionary chứa 'pos' và 'cost_increase' của vị trí tốt nhất,
                  hoặc None nếu không tìm thấy vị trí khả thi.
        """
        best_candidate = {"pos": None, "cost_increase": float('inf')}
        
        # Lặp qua tất cả các vị trí chèn khả thi (từ sau điểm bắt đầu đến trước điểm kết thúc)
        for i in range(1, len(route.nodes_id)):
            temp_route = copy.deepcopy(route)
            
            # --- KIỂM TRA TẢI TRỌNG (CAPACITY CHECK) ---
            is_cap_ok = True
            # Tải trọng ban đầu để giao hàng
            temp_del_load = route.total_load_delivery
            if customer.type == 'DeliveryCustomer':
                temp_del_load += customer.demand
            if temp_del_load > self.problem.se_vehicle_capacity:
                continue # Tải ban đầu đã vượt quá, không cần kiểm tra thêm

            # Kiểm tra tải trọng dọc tuyến
            temp_nodes_for_cap_check = route.nodes_id[:i] + [customer.id] + route.nodes_id[i:]
            running_load = temp_del_load
            for node_id in temp_nodes_for_cap_check[1:-1]:
                cust_obj = self.problem.node_objects[node_id]
                if cust_obj.type == 'DeliveryCustomer':
                    running_load -= cust_obj.demand
                else:
                    running_load += cust_obj.demand
                if running_load > self.problem.se_vehicle_capacity:
                    is_cap_ok = False
                    break
            if not is_cap_ok: continue
            
            # --- KIỂM TRA THỜI GIAN (TIME WINDOW & DEADLINE CHECK) ---
            # Thử chèn và kiểm tra tính khả thi
            temp_route.insert_customer_at_pos(customer, i)
            
            is_feasible = True
            # Chỉ cần kiểm tra từ vị trí chèn trở đi
            for node_idx in range(i, len(temp_route.nodes_id)):
                node_id = temp_route.nodes_id[node_idx]
                node_obj = self.problem.node_objects[node_id % self.problem.total_nodes]
                if hasattr(node_obj, 'due_time'):
                    # service_start_times đã được cập nhật bên trong insert_customer_at_pos
                    if temp_route.service_start_times[node_id] > node_obj.due_time:
                        is_feasible = False
                        break
            if not is_feasible: continue
            
            # Kiểm tra ràng buộc deadline liên cấp
            if not temp_route.is_feasible_under_proxy_deadline():
                continue

            # --- CẬP NHẬT ỨNG VIÊN TỐT NHẤT ---
            cost_increase = temp_route.total_dist - route.total_dist
            if cost_increase < best_candidate["cost_increase"]:
                best_candidate["pos"] = i
                best_candidate["cost_increase"] = cost_increase
        
        if best_candidate["pos"] is None:
            return None # Không tìm thấy vị trí chèn khả thi
        return best_candidate

# --- END OF FILE Heuristics.py ---