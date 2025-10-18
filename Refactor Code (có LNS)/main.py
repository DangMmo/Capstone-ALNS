# --- START OF FILE main.py (UPDATED with Full Validation) ---

from problem_parser import ProblemInstance, Customer, PickupCustomer
from solution_generator import create_refined_initial_solution
from data_structures import Solution

def print_solution_details(solution: Solution):
    """
    In ra bản tóm tắt và chi tiết toàn bộ các tuyến đường trong lời giải.
    """
    print("\n" + "="*60)
    print("--- DETAILED SOLUTION REPORT ---")
    print("="*60)

    print("\n[SUMMARY]")
    print(f"Total Cost: {solution.calculate_total_cost():.2f}")
    print(f"Number of FE Routes: {len(solution.fe_routes)}")
    print(f"Number of SE Routes: {len(solution.se_routes)}")
    print(f"Unserved Customers: {len(solution.unserved_customers)}")
    if solution.unserved_customers:
        print(f"  -> IDs: {[c.id for c in solution.unserved_customers]}")

    print("\n\n" + "-"*20 + " SECOND-ECHELON (SE) ROUTES " + "-"*20)
    if not solution.se_routes:
        print("No SE routes in the solution.")
    else:
        for i, se_route in enumerate(sorted(solution.se_routes, key=lambda r: r.satellite.id)):
            print(f"\n[SE Route #{i+1}]")
            print(se_route)

    print("\n\n" + "-"*20 + " FIRST-ECHELON (FE) ROUTES " + "-"*20)
    if not solution.fe_routes:
        print("No FE routes in the solution.")
    else:
        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n[FE Route #{i+1}]")
            print(fe_route)


def validate_solution_feasibility(solution: Solution):
    """
    [HÀM MỚI] Thực hiện các kiểm tra sâu về tính khả thi của lời giải.
    """
    print("\n\n" + "="*60)
    print("--- SOLUTION FEASIBILITY VALIDATION ---")
    print("="*60)
    
    errors = []
    
    # 1. Kiểm tra tất cả khách hàng đã được phục vụ
    all_served_ids = set(solution.customer_to_se_route_map.keys())
    all_problem_ids = {c.id for c in solution.problem.customers}
    if len(all_served_ids) + len(solution.unserved_customers) != len(all_problem_ids):
        errors.append("MISMATCH in served/unserved customer count!")
    
    # 2. Kiểm tra từng SE Route
    for se_route in solution.se_routes:
        for cust in se_route.get_customers():
            start_time = se_route.service_start_times.get(cust.id)
            if start_time is None:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Customer {cust.id} is in route but has no start time.")
                continue
            if start_time > cust.due_time + 1e-6:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Customer {cust.id} violates due time (Start: {start_time:.2f} > Due: {cust.due_time:.2f}).")

    # 3. Kiểm tra từng FE Route
    for fe_route in solution.fe_routes:
        if not fe_route.schedule:
            errors.append(f"FE Route has no schedule but services {len(fe_route.serviced_se_routes)} SE routes.")
            continue
        
        arrival_at_depot = fe_route.schedule[-1]['arrival_time']
        
        # Kiểm tra deadline
        all_deadlines = {cust.deadline for se in fe_route.serviced_se_routes for cust in se.get_customers() if isinstance(cust, PickupCustomer)}
        if arrival_at_depot > fe_route.route_deadline + 1e-6:
             errors.append(f"FE Route violates its effective deadline (Arrival: {arrival_at_depot:.2f} > Deadline: {fe_route.route_deadline:.2f}).")
        
        for deadline in all_deadlines:
            if arrival_at_depot > deadline + 1e-6:
                errors.append(f"FE Route violates a specific customer deadline (Arrival: {arrival_at_depot:.2f} > Deadline: {deadline:.2f}).")

    # 4. In kết quả Validation
    if not errors:
        print("\n[VALIDATION SUCCESS] Solution appears to be feasible.")
    else:
        print("\n[VALIDATION FAILED] Found the following potential issues:")
        for i, error in enumerate(errors):
            print(f"  {i+1}. {error}")
    print("="*60)


def main():
    file_path = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\C_100_7_TD.csv"
    LNS_ITERATIONS = 10
    Q_PERCENTAGE = 0.2

    try:
        problem = ProblemInstance(file_path=file_path)
    except Exception as e:
        print(f"Error loading instance: {e}"); return

    final_state = create_refined_initial_solution(problem, LNS_ITERATIONS, Q_PERCENTAGE)
    solution = final_state.solution
    
    print_solution_details(solution)
    
    validate_solution_feasibility(solution)

if __name__ == "__main__":
    main()

# --- END OF FILE main.py ---