# --- START OF FILE main.py (UPDATED FOR COMPLETION PHASE) ---

import random
import config
from problem_parser import ProblemInstance
from data_structures import Solution
from solution_generator import generate_initial_solution
from lns_algorithm import run_alns_phase

# Import TẤT CẢ các toán tử, bao gồm cả các toán tử mới
from destroy_operators import (
    random_removal, 
    shaw_removal, 
    worst_slack_removal,
    worst_distance_removal,
    route_removal,
    satellite_removal,
    least_utilized_route_removal 
)
from repair_operators import (
    greedy_repair, 
    regret_insertion, 
    earliest_deadline_first_insertion,
    farthest_first_insertion,
    largest_first_insertion,
    closest_first_insertion,        
    earliest_time_window_insertion, 
    latest_time_window_insertion,   
    latest_deadline_first_insertion 
)

# ... (Các hàm print_solution_details và validate_solution_feasibility giữ nguyên) ...
def print_solution_details(solution: Solution):
    print("\n" + "="*60 + "\n--- DETAILED SOLUTION REPORT ---\n" + "="*60)
    print(f"\n[SUMMARY]\nTotal Cost: {solution.calculate_total_cost():.2f}")
    print(f"Number of FE Routes: {len(solution.fe_routes)}")
    print(f"Number of SE Routes: {len(solution.se_routes)}")
    print(f"Unserved Customers: {len(solution.unserved_customers)}")
    if solution.unserved_customers: print(f"  -> IDs: {[c.id for c in solution.unserved_customers]}")
    print("\n\n" + "-"*20 + " SECOND-ECHELON (SE) ROUTES " + "-"*20)
    if not solution.se_routes: print("No SE routes in the solution.")
    else:
        for i, se_route in enumerate(sorted(solution.se_routes, key=lambda r: r.satellite.id)): print(f"\n[SE Route #{i+1}]\n{se_route}")
    print("\n\n" + "-"*20 + " FIRST-ECHELON (FE) ROUTES " + "-"*20)
    if not solution.fe_routes: print("No FE routes in the solution.")
    else:
        for i, fe_route in enumerate(solution.fe_routes): print(f"\n[FE Route #{i+1}]\n{fe_route}")

def validate_solution_feasibility(solution: Solution):
    print("\n\n" + "="*60 + "\n--- SOLUTION FEASIBILITY VALIDATION ---\n" + "="*60)
    errors = []
    all_served_ids = set(solution.customer_to_se_route_map.keys())
    all_problem_ids = {c.id for c in solution.problem.customers}
    if len(all_served_ids) + len(solution.unserved_customers) != len(all_problem_ids): errors.append("MISMATCH in served/unserved customer count!")
    for se_route in solution.se_routes:
        for cust in se_route.get_customers():
            start_time = se_route.service_start_times.get(cust.id)
            if start_time is None:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Customer {cust.id} is in route but has no start time.")
                continue
            if hasattr(cust, 'due_time') and start_time > cust.due_time + 1e-6: errors.append(f"SE Route (Sat {se_route.satellite.id}): Customer {cust.id} violates due time (Start: {start_time:.2f} > Due: {cust.due_time:.2f}).")
    from problem_parser import PickupCustomer
    for fe_route in solution.fe_routes:
        if not fe_route.schedule:
            if fe_route.serviced_se_routes: errors.append(f"FE Route has no schedule but services {len(fe_route.serviced_se_routes)} SE routes.")
            continue
        arrival_at_depot = fe_route.schedule[-1]['arrival_time']
        all_deadlines = {cust.deadline for se in fe_route.serviced_se_routes for cust in se.get_customers() if isinstance(cust, PickupCustomer)}
        if arrival_at_depot > fe_route.route_deadline + 1e-6: errors.append(f"FE Route violates its effective deadline (Arrival: {arrival_at_depot:.2f} > Deadline: {fe_route.route_deadline:.2f}).")
        for deadline in all_deadlines:
            if arrival_at_depot > deadline + 1e-6: errors.append(f"FE Route violates a specific customer deadline (Arrival: {arrival_at_depot:.2f} > Deadline: {deadline:.2f}).")
    if not errors: print("\n[VALIDATION SUCCESS] Solution appears to be feasible.")
    else:
        print("\n[VALIDATION FAILED] Found the following potential issues:")
        for i, error in enumerate(errors): print(f"  {i+1}. {error}")
    print("="*60)

def main():
    random.seed(config.RANDOM_SEED)
    try:
        problem = ProblemInstance(file_path=config.FILE_PATH, vehicle_speed=config.VEHICLE_SPEED)
    except Exception as e:
        print(f"Error loading instance: {e}"); return

    # Cập nhật map với các toán tử mới
    destroy_operators_map = {
        "random_removal": random_removal,
        "shaw_removal": shaw_removal,
        "worst_slack_removal": worst_slack_removal,
        "worst_distance_removal": worst_distance_removal,
        "route_removal": route_removal,
        "satellite_removal": satellite_removal,
        "least_utilized_route_removal": least_utilized_route_removal, # <<< THÊM MỚI
    }
    repair_operators_map = {
        "greedy_repair": greedy_repair,
        "regret_insertion": regret_insertion,
        "earliest_deadline_first_insertion": earliest_deadline_first_insertion,
        "farthest_first_insertion": farthest_first_insertion,
        "largest_first_insertion": largest_first_insertion,
        "closest_first_insertion": closest_first_insertion,           # <<< THÊM MỚI
        "earliest_time_window_insertion": earliest_time_window_insertion, # <<< THÊM MỚI
        "latest_time_window_insertion": latest_time_window_insertion,     # <<< THÊM MỚI
        "latest_deadline_first_insertion": latest_deadline_first_insertion, # <<< THÊM MỚI
    }

    print("\n" + "#"*70 + "\n### STAGE 1: GENERATING INITIAL SOLUTION ###\n" + "#"*70)
    initial_state = generate_initial_solution(problem, lns_iterations=config.LNS_INITIAL_ITERATIONS, q_percentage=config.Q_PERCENTAGE_INITIAL)
    print(f"\n--- Stage 1 Complete. Initial Best Cost: {initial_state.cost:.2f} ---")

    print("\n" + "#"*70 + "\n### STAGE 2: ADAPTIVE LARGE NEIGHBORHOOD SEARCH ###\n" + "#"*70)
    best_alns_state, _ = run_alns_phase(initial_state=initial_state, iterations=config.ALNS_MAIN_ITERATIONS, destroy_operators=destroy_operators_map, repair_operators=repair_operators_map)

    final_solution = best_alns_state.solution
    
    print("\n\n" + "#"*70 + "\n### FINAL OPTIMAL SOLUTION ###\n" + "#"*70)
    print_solution_details(final_solution)
    validate_solution_feasibility(final_solution)

if __name__ == "__main__":
    main()

# --- END OF FILE main.py ---