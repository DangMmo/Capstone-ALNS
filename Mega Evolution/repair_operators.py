# --- START OF FILE repair_operators.py (UPDATED FOR PHASE 1) ---

import random
from typing import List, TYPE_CHECKING, Dict

# Import các công cụ
from data_structures import SERoute, FERoute, Solution
from insertion_logic import InsertionProcessor, find_best_global_insertion_option, find_k_best_global_insertion_options, _recalculate_fe_route_and_check_feasibility
from problem_parser import PickupCustomer

if TYPE_CHECKING:
    from data_structures import VRP2E_State
    from problem_parser import Customer, ProblemInstance, Depot


# ==============================================================================
# HÀM TRỢ GIÚP NỘI BỘ CHO VIỆC CHÈN
# ==============================================================================
def _perform_insertion(solution: "Solution", customer_to_insert: "Customer", best_option: Dict):
    """
    Hàm nội bộ để thực hiện việc chèn một khách hàng vào lời giải
    dựa trên dictionary 'best_option' đã được quyết định.
    """
    problem = solution.problem
    option_type = best_option.get('type')

    if option_type == 'insert_into_existing_se':
        se_route = best_option['se_route']
        pos = best_option['se_pos']
        # Cẩn thận: fe_route có thể không tồn tại nếu se_route bị rỗng sau khi xóa
        if se_route.serving_fe_routes:
            fe_route = list(se_route.serving_fe_routes)[0]
            se_route.insert_customer_at_pos(customer_to_insert, pos)
            _recalculate_fe_route_and_check_feasibility(fe_route, problem)
        else: # Trường hợp đặc biệt: SE route không còn được phục vụ
             if customer_to_insert not in solution.unserved_customers:
                solution.unserved_customers.append(customer_to_insert)

    elif option_type == 'create_new_se_new_fe':
        satellite = best_option['new_satellite']
        new_se = SERoute(satellite, problem)
        new_se.insert_customer_at_pos(customer_to_insert, 1)
        solution.add_se_route(new_se)
        new_fe = FERoute(problem)
        solution.add_fe_route(new_fe)
        solution.link_routes(new_fe, new_se)
        _recalculate_fe_route_and_check_feasibility(new_fe, problem)

    elif option_type == 'create_new_se_expand_fe':
        satellite = best_option['new_satellite']
        fe_route = best_option['fe_route']
        new_se = SERoute(satellite, problem)
        new_se.insert_customer_at_pos(customer_to_insert, 1)
        solution.add_se_route(new_se)
        solution.link_routes(fe_route, new_se)
        _recalculate_fe_route_and_check_feasibility(fe_route, problem)
        
    else: 
        if customer_to_insert not in solution.unserved_customers:
            solution.unserved_customers.append(customer_to_insert)
    
    solution.update_customer_map()


# ==============================================================================
# CÁC TOÁN TỬ SỬA CHỮA (REPAIR OPERATORS)
# ==============================================================================
def greedy_repair(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)
    
    random.shuffle(customers_to_insert)

    for customer in customers_to_insert:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
                
    return new_state


def earliest_deadline_first_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)

    def get_deadline(customer):
        if isinstance(customer, PickupCustomer):
            return customer.deadline
        return float('inf')

    sorted_customers = sorted(customers_to_insert, key=get_deadline)

    for customer in sorted_customers:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
    
    return new_state


def regret_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"], k: int = 4) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)
    
    remaining_customers = list(customers_to_insert)

    while remaining_customers:
        best_customer_to_insert = None
        max_regret = -float('inf')
        best_option_for_max_regret_customer = None

        for customer in remaining_customers:
            best_options = find_k_best_global_insertion_options(customer, solution, insertion_processor, k)
            
            if not best_options:
                continue

            best_insertion_cost = best_options[0]['total_cost_increase']
            regret_value = 0
            # Tính toán hối tiếc
            for i in range(1, len(best_options)):
                regret_value += (best_options[i]['total_cost_increase'] - best_insertion_cost)
            
            if regret_value > max_regret:
                max_regret = regret_value
                best_customer_to_insert = customer
                best_option_for_max_regret_customer = best_options[0]

        if best_customer_to_insert is None:
            # Nếu không thể chèn bất kỳ khách hàng nào còn lại, dừng lại
            solution.unserved_customers.extend(remaining_customers)
            break

        _perform_insertion(solution, best_customer_to_insert, best_option_for_max_regret_customer)
        
        remaining_customers.remove(best_customer_to_insert)
                
    return new_state

### --- START: TOÁN TỬ MỚI CỦA GIAI ĐOẠN 1 --- ###
def farthest_first_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    """
    Sửa chữa lời giải bằng cách ưu tiên chèn những khách hàng ở xa depot nhất trước.
    """
    new_state = state.copy()
    solution = new_state.solution
    problem = solution.problem
    insertion_processor = InsertionProcessor(problem)

    def get_distance_from_depot(customer: "Customer"):
        # Tính khoảng cách từ khách hàng đến depot
        return problem.get_distance(customer.id, problem.depot.id)

    # Sắp xếp khách hàng theo khoảng cách đến depot GIẢM DẦN (xa nhất trước)
    sorted_customers = sorted(customers_to_insert, key=get_distance_from_depot, reverse=True)

    for customer in sorted_customers:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
    
    return new_state
### --- END: TOÁN TỬ MỚI CỦA GIAI ĐOẠN 1 --- ###
def largest_first_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    """
    Sửa chữa lời giải bằng cách ưu tiên chèn những khách hàng có nhu cầu (demand) lớn nhất trước.
    """
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)

    # Sắp xếp khách hàng theo demand GIẢM DẦN
    sorted_customers = sorted(customers_to_insert, key=lambda c: c.demand, reverse=True)

    for customer in sorted_customers:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
    
    return new_state
### --- START: TOÁN TỬ MỚI CỦA GIAI ĐOẠN HOÀN THIỆN --- ###
def closest_first_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    problem = solution.problem
    insertion_processor = InsertionProcessor(problem)
    def get_distance_from_depot(customer: "Customer"):
        return problem.get_distance(customer.id, problem.depot.id)
    # Sắp xếp theo khoảng cách tăng dần (gần nhất trước)
    sorted_customers = sorted(customers_to_insert, key=get_distance_from_depot)
    for customer in sorted_customers:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
    return new_state

def earliest_time_window_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)
    # Sắp xếp theo ready_time tăng dần
    sorted_customers = sorted(customers_to_insert, key=lambda c: c.ready_time)
    for customer in sorted_customers:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
    return new_state

def latest_time_window_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)
    # Sắp xếp theo due_time giảm dần
    sorted_customers = sorted(customers_to_insert, key=lambda c: c.due_time, reverse=True)
    for customer in sorted_customers:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
    return new_state

def latest_deadline_first_insertion(state: "VRP2E_State", customers_to_insert: List["Customer"]) -> "VRP2E_State":
    new_state = state.copy()
    solution = new_state.solution
    insertion_processor = InsertionProcessor(solution.problem)
    def get_deadline_for_sorting(customer: "Customer"):
        # Gán giá trị âm vô cùng cho khách hàng không có deadline để họ bị xếp cuối
        return getattr(customer, 'deadline', float('-inf'))
    # Sắp xếp theo deadline giảm dần
    sorted_customers = sorted(customers_to_insert, key=get_deadline_for_sorting, reverse=True)
    for customer in sorted_customers:
        best_option = find_best_global_insertion_option(customer, solution, insertion_processor)
        _perform_insertion(solution, customer, best_option)
    return new_state
### --- END: TOÁN TỬ MỚI CỦA GIAI ĐOẠN HOÀN THIỆN --- ###
# --- END OF FILE repair_operators.py ---