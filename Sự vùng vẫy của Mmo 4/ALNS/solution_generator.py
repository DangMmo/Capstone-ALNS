# --- START OF FILE solution_generator.py (UPDATED) ---

# --- Phần import của file alns/solution_generator.py ---

import random
from typing import TYPE_CHECKING

# Import từ package 'core'
from core.data_structures import VRP2E_State, Solution, SERoute, FERoute

# Import từ cùng package 'alns'
from .insertion_logic import InsertionProcessor, find_best_global_insertion_option, _recalculate_fe_route_and_check_feasibility
from .lns_algorithm import run_local_search_phase 
from .destroy_operators import random_removal
from .repair_operators import greedy_repair

if TYPE_CHECKING:
    from core.problem_parser import ProblemInstance

def create_integrated_initial_solution(problem: "ProblemInstance", random_customers: bool = True, verbose: bool = True) -> VRP2E_State:
    solution = Solution(problem)
    insertion_processor = InsertionProcessor(problem)
    customers_to_serve = list(problem.customers)
    if random_customers: random.shuffle(customers_to_serve)
    solution.unserved_customers = []
    if verbose: print("--- Phase 1a: Greedy Insertion Construction ---")
    for i, customer in enumerate(customers_to_serve):
        if verbose: print(f"  -> Processing customer {i+1}/{len(customers_to_serve)} (ID: {customer.id})...", end='\r')
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        option_type = best_option.get('type')
        if option_type == 'insert_into_existing_se':
            se_route, pos = best_option['se_route'], best_option['se_pos']
            fe_route = list(se_route.serving_fe_routes)[0]
            se_route.insert_customer_at_pos(customer, pos)
            solution.update_customer_map()
            _recalculate_fe_route_and_check_feasibility(fe_route, problem)
        elif option_type == 'create_new_se_new_fe':
            satellite = best_option['new_satellite']
            new_se = SERoute(satellite, solution.problem)
            new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se)
            new_fe = FERoute(solution.problem)
            solution.add_fe_route(new_fe)
            solution.link_routes(new_fe, new_se)
            _recalculate_fe_route_and_check_feasibility(new_fe, problem)
        elif option_type == 'create_new_se_expand_fe':
            satellite, fe_route = best_option['new_satellite'], best_option['fe_route']
            new_se = SERoute(satellite, solution.problem)
            new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se)
            solution.link_routes(fe_route, new_se)
            _recalculate_fe_route_and_check_feasibility(fe_route, problem)
        else: 
            solution.unserved_customers.append(customer)
            if verbose: print(f"\nWarning: Could not serve customer {customer.id}")
    if verbose: print("\n\n>>> Greedy construction complete!")
    return VRP2E_State(solution)

def generate_initial_solution(problem: "ProblemInstance", lns_iterations: int, q_percentage: float, verbose: bool = True) -> VRP2E_State:
    initial_state = create_integrated_initial_solution(problem, verbose=verbose)
    initial_cost = initial_state.cost
    if verbose: print(f"--- Phase 1a Complete. Pre-LNS Cost: {initial_cost:.2f} ---")
    if lns_iterations > 0:
        if verbose: print("\n--- Phase 1b: Local Search Refinement (Restrictive LNS) ---")
        final_state = run_local_search_phase(
            initial_state=initial_state, iterations=lns_iterations,
            q_percentage=q_percentage, destroy_op=random_removal,
            repair_op=greedy_repair, verbose=verbose
        )
    else:
        final_state = initial_state
    return final_state