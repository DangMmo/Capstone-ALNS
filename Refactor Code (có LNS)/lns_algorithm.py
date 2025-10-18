# --- START OF FILE lns_algorithm.py ---

from typing import Callable, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from data_structures import VRP2E_State
    from problem_parser import Customer

DestroyOperator = Callable[['VRP2E_State', int], Tuple['VRP2E_State', List['Customer']]]
RepairOperator = Callable[['VRP2E_State', List['Customer']], 'VRP2E_State']

def run_lns_loop(initial_state: "VRP2E_State", iterations: int, q_percentage: float, 
                 destroy_op: DestroyOperator, repair_op: RepairOperator) -> "VRP2E_State":
                 
    current_state, best_state = initial_state.copy(), initial_state.copy()
    print("\n--- Starting LNS Refinement ---")

    for i in range(iterations):
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0:
            print("No customers to optimize. Stopping LNS.")
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
        
    print(f"\n--- LNS complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state

# --- END OF FILE lns_algorithm.py ---