# --- START OF FILE repair_operators.py ---

import random
from typing import List, TYPE_CHECKING

# Import các công cụ
from data_structures import SERoute, FERoute
from insertion_logic import InsertionProcessor, find_best_global_insertion_option, _recalculate_fe_route_and_check_feasibility

if TYPE_CHECKING:
    from data_structures import VRP2E_State
    from problem_parser import Customer

def greedy_repair(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)
    
    random.shuffle(customers_to_insert)

    for customer in customers_to_insert:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        option_type = best_option.get('type')

        if option_type == 'insert_into_existing_se':
            se_route, pos = best_option['se_route'], best_option['se_pos']
            fe_route = list(se_route.serving_fe_routes)[0]
            se_route.insert_customer_at_pos(customer, pos)
            solution.update_customer_map()
            _recalculate_fe_route_and_check_feasibility(fe_route, solution.problem)
        elif option_type == 'create_new_se_new_fe':
            satellite = best_option['new_satellite']
            new_se = SERoute(satellite, solution.problem)
            new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se)
            new_fe = FERoute(solution.problem)
            solution.add_fe_route(new_fe)
            solution.link_routes(new_fe, new_se)
            _recalculate_fe_route_and_check_feasibility(new_fe, solution.problem)
        elif option_type == 'create_new_se_expand_fe':
            satellite, fe_route = best_option['new_satellite'], best_option['fe_route']
            new_se = SERoute(satellite, solution.problem)
            new_se.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se)
            solution.link_routes(fe_route, new_se)
            _recalculate_fe_route_and_check_feasibility(fe_route, solution.problem)
        else:
            if customer not in solution.unserved_customers:
                solution.unserved_customers.append(customer)
                
    return new_state

# --- END OF FILE repair_operators.py ---