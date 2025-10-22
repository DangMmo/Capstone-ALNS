# --- START OF FILE lns_algorithm.py (UPDATED with full logging) ---

import math
import random
from typing import Callable, List, Tuple, Dict, TYPE_CHECKING

# Import các thành phần mới
from adaptive_mechanism import AdaptiveOperatorSelector

if TYPE_CHECKING:
    from data_structures import VRP2E_State
    from problem_parser import Customer

DestroyOperator = Callable[['VRP2E_State', int], Tuple['VRP2E_State', List['Customer']]]
RepairOperator = Callable[['VRP2E_State', List['Customer']], 'VRP2E_State']

# ĐỔI TÊN HÀM NÀY
def run_local_search_phase(initial_state: "VRP2E_State", iterations: int, q_percentage: float, 
                           destroy_op: DestroyOperator, repair_op: RepairOperator) -> "VRP2E_State":
    """
    Chạy một pha LNS hạn chế (chỉ chấp nhận lời giải tốt hơn) để tinh chỉnh lời giải ban đầu.
    """         
    current_state, best_state = initial_state.copy(), initial_state.copy()
    print("--- Starting Local Search Refinement ---")

    for i in range(iterations):
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0:
            print("No customers to optimize. Stopping.")
            break
        
        q = max(2, int(num_cust * q_percentage))
        
        destroyed_state, removed_customers = destroy_op(current_state, q)
        repaired_state = repair_op(destroyed_state, removed_customers)
        
        current_cost, new_cost, best_cost = current_state.cost, repaired_state.cost, best_state.cost
        
        log_str = f"  LNS Iter {i+1:>4}/{iterations} | Current: {current_cost:>10.2f}, New: {new_cost:>10.2f}, Best: {best_cost:>10.2f}"
        
        if new_cost < current_cost:
            current_state = repaired_state.copy()
            log_str += " -> ACCEPTED"
            if new_cost < best_cost:
                best_state = repaired_state.copy()
                log_str += " (NEW BEST!)"
        
        # GIỮ LẠI DÒNG PRINT NÀY THEO YÊU CẦU
        print(log_str)
        
    print(f"--- Local Search complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state
### --- NEW ALNS PHASE FUNCTION STARTS HERE --- ###

### --- ALNS PHASE FUNCTION --- ###

# Các hằng số cho cơ chế thích ứng và SA
SIGMA_1_NEW_BEST = 9
SIGMA_2_BETTER = 5
SIGMA_3_ACCEPTED = 2
REACTION_FACTOR = 0.5
SEGMENT_LENGTH = 100
COOLING_RATE = 0.99975
START_TEMP_ACCEPT_PROB = 0.5
START_TEMP_WORSENING_PCT = 0.05

def run_alns_phase(initial_state: "VRP2E_State", iterations: int, 
                   destroy_operators: Dict[str, Callable], 
                   repair_operators: Dict[str, Callable]) -> Tuple["VRP2E_State", Tuple[List, List]]:
    """
    Chạy pha ALNS chính với cơ chế thích ứng và Simulated Annealing.
    """
    current_state, best_state = initial_state.copy(), initial_state.copy()
    operator_selector = AdaptiveOperatorSelector(destroy_operators, repair_operators, REACTION_FACTOR)
    T_start = -(START_TEMP_WORSENING_PCT * current_state.cost) / math.log(START_TEMP_ACCEPT_PROB)
    T = T_start
    fe_route_pool, se_route_pool = [], []

    print(f"\n--- Starting ALNS Phase ---")
    print(f"  Iterations: {iterations}, Initial Temp: {T:.2f}, Initial Cost: {current_state.cost:.2f}")

    for i in range(1, iterations + 1):
        
        destroy_op_obj = operator_selector.select_destroy_operator()
        repair_op_obj = operator_selector.select_repair_operator()
        
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0: break
        q = max(2, int(num_cust * random.uniform(0.1, 0.4)))

        destroyed_state, removed_customers = destroy_op_obj.function(current_state, q)
        repaired_state = repair_op_obj.function(destroyed_state, removed_customers)

        current_cost = current_state.cost
        new_cost = repaired_state.cost
        sigma_update = 0
        log_msg = ""

        if new_cost < current_cost:
            current_state = repaired_state
            if new_cost < best_state.cost:
                best_state = repaired_state.copy()
                sigma_update = SIGMA_1_NEW_BEST
                log_msg = f"(NEW BEST: {new_cost:.2f})"
            else:
                sigma_update = SIGMA_2_BETTER
                log_msg = f"(Accepted: {new_cost:.2f})"
        else:
            delta = new_cost - current_cost
            if T > 1e-6 and random.random() < math.exp(-delta / T):
                current_state = repaired_state
                sigma_update = SIGMA_3_ACCEPTED
                log_msg = f"(SA Accepted: {new_cost:.2f})"
        
        if sigma_update > 0:
            operator_selector.update_scores(destroy_op_obj, repair_op_obj, sigma_update)
            fe_route_pool.extend(current_state.solution.fe_routes)
            se_route_pool.extend(current_state.solution.se_routes)
            
        T *= COOLING_RATE
        
        # CẬP NHẬT TRỌNG SỐ SAU MỖI SEGMENT_LENGTH LẦN LẶP
        if i % SEGMENT_LENGTH == 0:
            operator_selector.update_weights()
            
        # IN LOG SAU MỖI 5 LẦN LẶP HOẶC KHI CÓ THAY ĐỔI QUAN TRỌNG
        if i % 5 == 0 or log_msg:
            print(f"  Iter {i:>5}/{iterations} | Best: {best_state.cost:<10.2f} | Current: {current_state.cost:<10.2f} | Temp: {T:<8.2f} | Ops: {destroy_op_obj.name}/{repair_op_obj.name} | {log_msg}")
    
    print(f"\n--- ALNS phase complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state, (fe_route_pool, se_route_pool)