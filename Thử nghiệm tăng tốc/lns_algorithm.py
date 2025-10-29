# --- START OF FILE lns_algorithm.py (UPDATED FOR PHASE 3) ---

import math
import random
from typing import Callable, List, Tuple, Dict, TYPE_CHECKING
import config

from adaptive_mechanism import AdaptiveOperatorSelector

# ... (Type hints và hàm run_local_search_phase giữ nguyên) ...
if TYPE_CHECKING:
    from data_structures import VRP2E_State
    from problem_parser import Customer

DestroyOperator = Callable[['VRP2E_State', int], Tuple['VRP2E_State', List['Customer']]]
RepairOperator = Callable[['VRP2E_State', List['Customer']], 'VRP2E_State']

def run_local_search_phase(initial_state: "VRP2E_State", iterations: int, q_percentage: float, 
                           destroy_op: DestroyOperator, repair_op: RepairOperator) -> "VRP2E_State":
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
        print(log_str)
    print(f"--- Local Search complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state

def run_alns_phase(initial_state: "VRP2E_State", iterations: int, 
                   destroy_operators: Dict[str, Callable], 
                   repair_operators: Dict[str, Callable]) -> Tuple["VRP2E_State", Tuple[List, List]]:
    current_state, best_state = initial_state.copy(), initial_state.copy()
    operator_selector = AdaptiveOperatorSelector(destroy_operators, repair_operators, config.REACTION_FACTOR)
    T_start = -(config.START_TEMP_WORSENING_PCT * current_state.cost) / math.log(config.START_TEMP_ACCEPT_PROB)
    T = T_start
    fe_route_pool, se_route_pool = [], []
    print(f"\n--- Starting ALNS Phase ---")
    print(f"  Iterations: {iterations}, Initial Temp: {T:.2f}, Initial Cost: {current_state.cost:.2f}")

    small_destroy_counter = 0
    iterations_without_improvement = 0

    for i in range(1, iterations + 1):
        destroy_op_obj = operator_selector.select_destroy_operator()
        repair_op_obj = operator_selector.select_repair_operator()
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0: break

        is_large_destroy = False
        if small_destroy_counter < config.SMALL_DESTROY_SEGMENT_LENGTH:
            q_percentage = random.uniform(*config.Q_SMALL_RANGE)
            small_destroy_counter += 1
            current_state_for_destroy = current_state
        else:
            is_large_destroy = True
            q_percentage = random.uniform(*config.Q_LARGE_RANGE)
            small_destroy_counter = 0
            print(f"  >>> Large destroy/diversification triggered at iter {i} <<<")
            current_state_for_destroy = best_state.copy()
        
        q = max(2, int(num_cust * q_percentage))
        destroyed_state, removed_customers = destroy_op_obj.function(current_state_for_destroy, q)
        repaired_state = repair_op_obj.function(destroyed_state, removed_customers)

        source_cost = current_state_for_destroy.cost
        new_cost = repaired_state.cost
        sigma_update = 0
        log_msg = ""
        
        if is_large_destroy:
            current_state = repaired_state
            log_msg = f"(Large destroy accepted: {new_cost:.2f})"
            if new_cost < best_state.cost:
                 best_state = repaired_state.copy()
                 sigma_update = config.SIGMA_1_NEW_BEST
                 log_msg += f" (NEW BEST!)"
            else:
                 sigma_update = config.SIGMA_3_ACCEPTED
        else:
            if new_cost < source_cost:
                current_state = repaired_state
                if new_cost < best_state.cost:
                    best_state = repaired_state.copy()
                    sigma_update = config.SIGMA_1_NEW_BEST
                    log_msg = f"(NEW BEST: {new_cost:.2f})"
                else:
                    sigma_update = config.SIGMA_2_BETTER
                    log_msg = f"(Accepted: {new_cost:.2f})"
            else:
                delta = new_cost - source_cost
                if T > 1e-6 and random.random() < math.exp(-delta / T):
                    current_state = repaired_state
                    sigma_update = config.SIGMA_3_ACCEPTED
                    log_msg = f"(SA Accepted: {new_cost:.2f})"
        
        if sigma_update > 0:
            operator_selector.update_scores(destroy_op_obj, repair_op_obj, sigma_update)
            fe_route_pool.extend(current_state.solution.fe_routes)
            se_route_pool.extend(current_state.solution.se_routes)
        
        # --- LOGIC KHỞI ĐỘNG LẠI (TINH CHỈNH) ---
        if sigma_update == config.SIGMA_1_NEW_BEST:
            iterations_without_improvement = 0
        else:
            iterations_without_improvement += 1
        
        if iterations_without_improvement >= config.RESTART_THRESHOLD:
            print(f"  >>> Restart triggered at iter {i}. No improvement for {config.RESTART_THRESHOLD} iters. <<<")
            current_state = best_state.copy()
            # T = T_start * 0.8  # <<< DÒNG NÀY ĐÃ BỊ XÓA/VÔ HIỆU HÓA
            iterations_without_improvement = 0
        
        T *= config.COOLING_RATE
        
        if i % config.SEGMENT_LENGTH == 0:
            operator_selector.update_weights()
            
        if i % 100 == 0 or log_msg:
            print(f"  Iter {i:>5}/{iterations} | Best: {best_state.cost:<10.2f} | Current: {current_state.cost:<10.2f} | Temp: {T:<8.2f} | Ops: {destroy_op_obj.name}/{repair_op_obj.name} | {log_msg}")
    
    print(f"\n--- ALNS phase complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state, (fe_route_pool, se_route_pool)

# --- END OF FILE lns_algorithm.py ---