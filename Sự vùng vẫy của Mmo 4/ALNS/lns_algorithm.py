# --- START OF FILE alns/lns_algorithm.py ---

import math
import random
from typing import Callable, List, Tuple, Dict, TYPE_CHECKING
import config
from tqdm import tqdm
import sys
# Import từ các package khác
from core.transaction import ChangeContext

# Import từ cùng package 'alns'
from .adaptive_mechanism import AdaptiveOperatorSelector

if TYPE_CHECKING:
    from core.data_structures import VRP2E_State, Solution
    from core.problem_parser import Customer

DestroyOperatorFunc = Callable[['Solution', 'ChangeContext', int], List['Customer']]
RepairOperatorFunc = Callable[['Solution', 'ChangeContext', List['Customer']], None]


# <<< THÊM verbose=True VÀO ĐỊNH NGHĨA HÀM >>>
def run_local_search_phase(initial_state: "VRP2E_State", iterations: int, q_percentage: float, 
                           destroy_op: Callable, repair_op: Callable, verbose: bool = True) -> "VRP2E_State":
    current_state = initial_state
    best_state = initial_state.copy()
    if verbose: print("--- Starting Local Search Refinement ---")
    
    # Sử dụng tqdm cho local search luôn cho gọn
    progress_bar = tqdm(range(iterations), disable=not verbose, desc="LNS Refinement", unit="iter")
    for i in progress_bar:
        context = ChangeContext(current_state.solution)
        cost_before = current_state.cost
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0:
            if verbose: tqdm.write("No customers to optimize. Stopping.")
            break
        q = max(2, int(num_cust * q_percentage))
        removed_customers = destroy_op(current_state.solution, context, q)
        repair_op(current_state.solution, context, removed_customers)
        cost_after = current_state.cost
        
        log_msg = ""
        if cost_after < cost_before:
            if cost_after < best_state.cost:
                best_state = current_state.copy()
                log_msg = "(NEW BEST!)"
        else:
            context.rollback()
        
        progress_bar.set_postfix(best=f"{best_state.cost:.2f}", current=f"{current_state.cost:.2f}", msg=log_msg)
        
    if verbose: print(f"--- Local Search complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state

def run_alns_phase(initial_state: "VRP2E_State", iterations: int, 
                   destroy_operators: Dict[str, DestroyOperatorFunc], 
                   repair_operators: Dict[str, RepairOperatorFunc],
                   verbose: bool = True, track_history: bool = True) -> Tuple["VRP2E_State", Tuple[Dict, Dict]]:
    current_state, best_state = initial_state, initial_state.copy()
    operator_selector = AdaptiveOperatorSelector(destroy_operators, repair_operators, config.REACTION_FACTOR)
    T_start, primary_cost = 0, initial_state.solution.get_primary_objective_cost()
    if config.START_TEMP_ACCEPT_PROB > 0 and primary_cost > 0:
        delta = config.START_TEMP_WORSENING_PCT * primary_cost
        T_start = -delta / math.log(config.START_TEMP_ACCEPT_PROB)
    T = T_start if T_start > 0 else 1.0
    history, operator_history = {"iteration": [], "best_cost": [], "current_cost": [], "temperature": [], "accepted_move_type": [], "q_removed": [], "is_large_destroy": []}, {"iteration": [], "destroy_weights": [], "repair_weights": []}
    
    if verbose: print(f"\n--- Starting ALNS Phase ---\n  Iterations: {iterations}, Initial Temp: {T:.2f}, Initial Cost: {current_state.cost:.2f}")
    
    use_tqdm = verbose and hasattr(sys.stdout, 'is_terminal') and sys.stdout.is_terminal
    iterations_range = tqdm(range(1, iterations + 1), disable=not use_tqdm, desc="ALNS Progress  ", unit="iter", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
    
    small_destroy_counter, iterations_without_improvement = 0, 0
    
    for i in iterations_range:
        context = ChangeContext(current_state.solution)
        cost_before_change = current_state.cost
        destroy_op_obj, repair_op_obj = operator_selector.select_destroy_operator(), operator_selector.select_repair_operator()
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0: break
        is_large_destroy = (small_destroy_counter >= config.SMALL_DESTROY_SEGMENT_LENGTH)
        q_percentage = random.uniform(*(config.Q_LARGE_RANGE if is_large_destroy else config.Q_SMALL_RANGE))
        if is_large_destroy: small_destroy_counter = 0
        else: small_destroy_counter += 1
        q = max(2, int(num_cust * q_percentage))
        removed_customers = destroy_op_obj.function(current_state.solution, context, q)
        repair_op_obj.function(current_state.solution, context, removed_customers)
        cost_after_change = current_state.cost
        sigma_update, log_msg, accepted = 0, "", False
        if cost_after_change < cost_before_change:
            accepted = True
            if cost_after_change < best_state.cost: sigma_update, log_msg = config.SIGMA_1_NEW_BEST, f"(NEW BEST: {cost_after_change:,.2f})"
            else: sigma_update = config.SIGMA_2_BETTER
        elif T > 1e-6 and random.random() < math.exp(-(cost_after_change - cost_before_change) / T):
            accepted, sigma_update = True, config.SIGMA_3_ACCEPTED
        if accepted:
            operator_selector.update_scores(destroy_op_obj, repair_op_obj, sigma_update)
            if cost_after_change < best_state.cost: best_state = current_state.copy()
        else: context.rollback()
        if sigma_update == config.SIGMA_1_NEW_BEST: iterations_without_improvement = 0
        else: iterations_without_improvement += 1
        if iterations_without_improvement >= config.RESTART_THRESHOLD:
            if verbose: tqdm.write(f"  Iter {i}: >> Restart triggered. <<")
            current_state = best_state.copy(); iterations_without_improvement = 0
        T *= config.COOLING_RATE
        
        if use_tqdm:
            iterations_range.set_postfix(best=f"{best_state.cost:,.2f}", current=f"{current_state.cost:,.2f}")
        
        if verbose:
            log_str = (f"  Iter {i:>5}/{iterations} | Best: {best_state.cost:<12.2f} | Current: {current_state.cost:<12.2f} | "
                       f"Temp: {T:<8.2f} | Ops: {destroy_op_obj.name}/{repair_op_obj.name} | {log_msg}")
            if hasattr(sys.stdout, 'write_to_log_only'): sys.stdout.write_to_log_only(log_str)
            elif not use_tqdm and log_msg: print(log_str)

        if track_history:
            history["q_removed"].append(q); history["is_large_destroy"].append(is_large_destroy)
            if i % config.SEGMENT_LENGTH == 0:
                operator_selector.update_weights()
                operator_history["iteration"].append(i)
                operator_history["destroy_weights"].append({op.name: op.weight for op in operator_selector.destroy_ops})
                operator_history["repair_weights"].append({op.name: op.weight for op in operator_selector.repair_ops})
            history["iteration"].append(i); history["best_cost"].append(best_state.cost); history["current_cost"].append(current_state.cost)
            history["temperature"].append(T)
            log_move_type = 'rejected'
            if sigma_update == config.SIGMA_1_NEW_BEST: log_move_type = 'new_best'
            elif sigma_update == config.SIGMA_2_BETTER: log_move_type = 'better'
            elif accepted: log_move_type = 'sa_accepted'
            history["accepted_move_type"].append(log_move_type)
        else:
             if i % config.SEGMENT_LENGTH == 0: operator_selector.update_weights()
    if verbose: print(f"\n--- ALNS phase complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state, (history, operator_history)