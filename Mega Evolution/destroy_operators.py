# --- START OF FILE destroy_operators.py (UPDATED FOR PHASE 1) ---

import random
from typing import List, Tuple, TYPE_CHECKING, Set

if TYPE_CHECKING:
    from data_structures import VRP2E_State, SERoute, FERoute
    from problem_parser import ProblemInstance, Customer

# Import _recalculate... để cập nhật FE route sau khi xóa
from insertion_logic import _recalculate_fe_route_and_check_feasibility


# ==============================================================================
# HÀM TRỢ GIÚP NỘI BỘ CHO VIỆC XÓA
# ==============================================================================
def _perform_removal(state: "VRP2E_State", to_remove_ids: Set[int]) -> Tuple["VRP2E_State", List["Customer"]]:
    """
    Hàm nội bộ để thực hiện việc xóa một tập hợp khách hàng khỏi một state.
    """
    solution = state.solution
    removed_objs = []
    affected_fes = set()

    cust_map_snapshot = dict(solution.customer_to_se_route_map)

    for cust_id in to_remove_ids:
        if cust_id not in cust_map_snapshot:
            continue
            
        se_route = cust_map_snapshot[cust_id]
        customer_obj = solution.problem.node_objects[cust_id]
        
        removed_objs.append(customer_obj)
        # Tìm fe_route tương ứng từ se_route
        if se_route.serving_fe_routes:
            fe_route = list(se_route.serving_fe_routes)[0]
            affected_fes.add(fe_route)
        
        se_route.remove_customer(customer_obj)

    solution.update_customer_map()
    
    for fe_route in list(affected_fes):
        for se_route_in_fe in list(fe_route.serviced_se_routes):
            if not se_route_in_fe.get_customers():
                solution.unlink_routes(fe_route, se_route_in_fe)
                solution.remove_se_route(se_route_in_fe)
        
        if not fe_route.serviced_se_routes:
             solution.remove_fe_route(fe_route)
        else:
             _recalculate_fe_route_and_check_feasibility(fe_route, solution.problem)
             
    return state, removed_objs


# ==============================================================================
# CÁC TOÁN TỬ PHÁ HỦY (DESTROY OPERATORS)
# ==============================================================================
def random_removal(state: "VRP2E_State", q: int) -> Tuple["VRP2E_State", List["Customer"]]:
    new_state = state.copy()
    
    served_ids = list(new_state.solution.customer_to_se_route_map.keys())
    if not served_ids:
        return new_state, []

    q = min(q, len(served_ids))
    to_remove_ids = set(random.sample(served_ids, q))
    
    return _perform_removal(new_state, to_remove_ids)


# --- Các hằng số và hàm _calculate_relatedness cho Shaw Removal ---
W_DIST = 9
W_TIME = 3
W_DEMAND = 2
W_ROUTE = 5

def _calculate_relatedness(cust1: "Customer", cust2: "Customer", state: "VRP2E_State") -> float:
    # ... (Nội dung hàm này giữ nguyên như trước) ...
    problem = state.solution.problem
    solution = state.solution
    dist = problem.get_distance(cust1.id, cust2.id)
    norm_dist = dist / problem._max_dist if problem._max_dist > 0 else 0
    se_route1 = solution.customer_to_se_route_map.get(cust1.id)
    se_route2 = solution.customer_to_se_route_map.get(cust2.id)
    if not se_route1 or not se_route2: return float('inf')
    start_time1 = se_route1.service_start_times.get(cust1.id, 0.0)
    start_time2 = se_route2.service_start_times.get(cust2.id, 0.0)
    time_diff = abs(start_time1 - start_time2)
    norm_time = time_diff / problem._max_due_time if problem._max_due_time > 0 else 0
    demand_diff = abs(cust1.demand - cust2.demand)
    norm_demand = demand_diff / problem._max_demand if problem._max_demand > 0 else 0
    same_route_flag = 0 if se_route1 is se_route2 else 1
    relatedness = (W_DIST * norm_dist + W_TIME * norm_time + W_DEMAND * norm_demand + W_ROUTE * same_route_flag)
    return relatedness


def shaw_removal(state: "VRP2E_State", q: int, p: int = 6) -> Tuple["VRP2E_State", List["Customer"]]:
    new_state = state.copy()
    
    all_served_cust_ids = list(new_state.solution.customer_to_se_route_map.keys())
    if not all_served_cust_ids:
        return new_state, []

    q = min(q, len(all_served_cust_ids))
    to_remove_ids = set()

    seed_id = random.choice(all_served_cust_ids)
    to_remove_ids.add(seed_id)
    
    while len(to_remove_ids) < q:
        bait_id = random.choice(list(to_remove_ids))
        bait_obj = new_state.solution.problem.node_objects[bait_id]
        unselected_cust_ids = [cid for cid in all_served_cust_ids if cid not in to_remove_ids]
        candidates = []
        for cand_id in unselected_cust_ids:
            cand_obj = new_state.solution.problem.node_objects[cand_id]
            relatedness = _calculate_relatedness(bait_obj, cand_obj, new_state)
            candidates.append((cand_id, relatedness))
        candidates.sort(key=lambda x: x[1])
        rand_val = random.random()
        index = int(pow(rand_val, p) * len(candidates))
        chosen_id = candidates[index][0]
        to_remove_ids.add(chosen_id)

    return _perform_removal(new_state, to_remove_ids)


def worst_slack_removal(state: "VRP2E_State", q: int, p: int = 3) -> Tuple["VRP2E_State", List["Customer"]]:
    new_state = state.copy()
    solution = new_state.solution

    candidates = []
    for cust_id, se_route in solution.customer_to_se_route_map.items():
        slack = se_route.forward_time_slacks.get(cust_id, 0.0)
        candidates.append((cust_id, slack))

    if not candidates:
        return new_state, []
        
    # Sắp xếp theo slack TĂNG DẦN (ít slack nhất lên đầu)
    candidates.sort(key=lambda x: x[1])

    to_remove_ids = set()
    q = min(q, len(candidates))

    while len(to_remove_ids) < q and candidates:
        rand_val = random.random()
        index = int(pow(rand_val, p) * len(candidates))
        chosen_id = candidates[index][0]
        
        if chosen_id not in to_remove_ids:
            to_remove_ids.add(chosen_id)
            del candidates[index] 

    return _perform_removal(new_state, to_remove_ids)


### --- START: TOÁN TỬ MỚI CỦA GIAI ĐOẠN 1 --- ###
def worst_distance_removal(state: "VRP2E_State", q: int, p: int = 3) -> Tuple["VRP2E_State", List["Customer"]]:
    """
    Xóa các khách hàng có chi phí tiết kiệm được (cost saving) cao nhất.
    """
    new_state = state.copy()
    solution = new_state.solution
    problem = solution.problem

    candidates = []
    cust_map = solution.customer_to_se_route_map
    
    for cust_id, se_route in cust_map.items():
        if cust_id not in se_route.nodes_id: continue
        
        pos = se_route.nodes_id.index(cust_id)
        # Bỏ qua nếu khách hàng là node đầu hoặc cuối (không thể xảy ra trong logic hiện tại nhưng để an toàn)
        if pos == 0 or pos == len(se_route.nodes_id) - 1:
            continue
            
        customer = problem.node_objects[cust_id]
        prev_node_id = se_route.nodes_id[pos - 1]
        next_node_id = se_route.nodes_id[pos + 1]

        # Lấy đối tượng node để tính khoảng cách
        prev_obj = problem.node_objects[prev_node_id % problem.total_nodes]
        next_obj = problem.node_objects[next_node_id % problem.total_nodes]

        dist_prev_cust = problem.get_distance(prev_obj.id, customer.id)
        dist_cust_next = problem.get_distance(customer.id, next_obj.id)
        dist_prev_next = problem.get_distance(prev_obj.id, next_obj.id)
        
        cost_saving = dist_prev_cust + dist_cust_next - dist_prev_next
        candidates.append((cust_id, cost_saving))

    if not candidates:
        return new_state, []

    # Sắp xếp theo cost_saving GIẢM DẦN (tiết kiệm nhiều nhất lên đầu)
    candidates.sort(key=lambda x: x[1], reverse=True)

    to_remove_ids = set()
    q = min(q, len(candidates))

    # Chọn q khách hàng để xóa bằng phương pháp chọn ngẫu nhiên lũy thừa
    while len(to_remove_ids) < q and candidates:
        rand_val = random.random()
        index = int(pow(rand_val, p) * len(candidates))
        chosen_id = candidates[index][0]

        if chosen_id not in to_remove_ids:
            to_remove_ids.add(chosen_id)
            # Xóa ứng viên đã chọn khỏi danh sách để tránh chọn lại
            del candidates[index]
            
    return _perform_removal(new_state, to_remove_ids)
### --- END: TOÁN TỬ MỚI CỦA GIAI ĐOẠN 1 --- ###
def route_removal(state: "VRP2E_State", q: int) -> Tuple["VRP2E_State", List["Customer"]]:
    """
    Xóa tất cả khách hàng thuộc một hoặc nhiều tuyến đường SE được chọn ngẫu nhiên.
    """
    new_state = state.copy()
    solution = new_state.solution
    
    se_routes = list(solution.se_routes)
    if not se_routes:
        return new_state, []
        
    to_remove_ids = set()
    
    # Tiếp tục chọn tuyến đường cho đến khi số khách hàng cần xóa đạt gần q
    # hoặc không còn tuyến nào để chọn
    while len(to_remove_ids) < q and se_routes:
        route_to_remove = random.choice(se_routes)
        
        customer_ids_in_route = {c.id for c in route_to_remove.get_customers()}
        to_remove_ids.update(customer_ids_in_route)
        
        se_routes.remove(route_to_remove) # Không chọn lại tuyến này
        
    return _perform_removal(new_state, to_remove_ids)

def satellite_removal(state: "VRP2E_State", q: int) -> Tuple["VRP2E_State", List["Customer"]]:
    """
    Xóa tất cả khách hàng thuộc về một satellite được chọn ngẫu nhiên.
    """
    new_state = state.copy()
    solution = new_state.solution

    # Lấy danh sách các satellite đang được sử dụng
    if not solution.se_routes:
        return new_state, []
    active_satellites = list({se_route.satellite for se_route in solution.se_routes})
    
    # Chọn ngẫu nhiên một satellite
    satellite_to_clear = random.choice(active_satellites)
    
    to_remove_ids = set()
    # Tìm tất cả khách hàng thuộc satellite đã chọn
    for se_route in solution.se_routes:
        if se_route.satellite.id == satellite_to_clear.id:
            customer_ids_in_route = {c.id for c in se_route.get_customers()}
            to_remove_ids.update(customer_ids_in_route)
            
    return _perform_removal(new_state, to_remove_ids)
### --- START: TOÁN TỬ MỚI CỦA GIAI ĐOẠN HOÀN THIỆN --- ###
def least_utilized_route_removal(state: "VRP2E_State", q: int) -> Tuple["VRP2E_State", List["Customer"]]:
    """
    Xóa khách hàng từ các tuyến đường SE kém hiệu quả nhất (ít khách hàng nhất).
    """
    new_state = state.copy()
    solution = new_state.solution
    
    if not solution.se_routes:
        return new_state, []

    # Sắp xếp các tuyến theo số lượng khách hàng tăng dần
    sorted_routes = sorted(solution.se_routes, key=lambda r: len(r.get_customers()))
    
    # Tạo một bể chứa các ứng viên (25% các tuyến yếu nhất, tối thiểu 1)
    pool_size = max(1, int(len(sorted_routes) * 0.25))
    candidate_pool = sorted_routes[:pool_size]

    to_remove_ids = set()
    # Chọn ngẫu nhiên từ bể ứng viên để xóa
    while len(to_remove_ids) < q and candidate_pool:
        route_to_remove = random.choice(candidate_pool)
        to_remove_ids.update({c.id for c in route_to_remove.get_customers()})
        candidate_pool.remove(route_to_remove)
        
    return _perform_removal(new_state, to_remove_ids)
### --- END: TOÁN TỬ MỚI CỦA GIAI ĐOẠN HOÀN THIỆN --- ###
# --- END OF FILE destroy_operators.py ---