# --- START OF FILE destroy_operators.py ---

import random
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from data_structures import VRP2E_State, FERoute
    from problem_parser import Customer

# Import _recalculate... để cập nhật FE route sau khi xóa
from insertion_logic import _recalculate_fe_route_and_check_feasibility

def random_removal(state: "VRP2E_State", q: int) -> Tuple["VRP2E_State", List["Customer"]]:
    new_state = state.copy()
    solution = new_state.solution
    
    served_ids = list(solution.customer_to_se_route_map.keys())
    if not served_ids:
        return new_state, []

    q = min(q, len(served_ids))
    to_remove_ids = random.sample(served_ids, q)
    
    removed_objs = []
    affected_fes = set()

    for cust_id in to_remove_ids:
        se_route = solution.customer_to_se_route_map[cust_id]
        customer_obj = solution.problem.node_objects[cust_id]
        
        removed_objs.append(customer_obj)
        if se_route.serving_fe_routes:
            affected_fes.add(list(se_route.serving_fe_routes)[0])
        
        se_route.remove_customer(customer_obj)
    
    solution.update_customer_map()
    
    for fe_route in list(affected_fes):
        # Dọn dẹp các SE route rỗng
        for se_route in list(fe_route.serviced_se_routes):
            if not se_route.get_customers():
                solution.unlink_routes(fe_route, se_route)
                solution.remove_se_route(se_route)
        
        # Dọn dẹp các FE route rỗng
        if not fe_route.serviced_se_routes:
             solution.remove_fe_route(fe_route)
        else:
             # Cập nhật lại lịch trình FE
             _recalculate_fe_route_and_check_feasibility(fe_route, solution.problem)
             
    return new_state, removed_objs

# --- END OF FILE destroy_operators.py ---