# --- START OF FILE main.py (UPDATED FOR FULL ALNS RUN) ---

from problem_parser import ProblemInstance
from data_structures import Solution
from solution_generator import generate_initial_solution
from lns_algorithm import run_alns_phase

# Import tất cả các toán tử đã xây dựng
from destroy_operators import (
    random_removal, 
    shaw_removal, 
    worst_slack_removal
)
from repair_operators import (
    greedy_repair, 
    regret_insertion, 
    earliest_deadline_first_insertion
)


def print_solution_details(solution: Solution):
    """
    In ra bản tóm tắt và chi tiết toàn bộ các tuyến đường trong lời giải.
    """
    # ... (Nội dung hàm này giữ nguyên) ...
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
    Thực hiện các kiểm tra sâu về tính khả thi của lời giải.
    """
    # ... (Nội dung hàm này giữ nguyên) ...
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
            if hasattr(cust, 'due_time') and start_time > cust.due_time + 1e-6:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Customer {cust.id} violates due time (Start: {start_time:.2f} > Due: {cust.due_time:.2f}).")

    # 3. Kiểm tra từng FE Route
    from problem_parser import PickupCustomer # Cần import để kiểm tra
    for fe_route in solution.fe_routes:
        if not fe_route.schedule:
            if fe_route.serviced_se_routes:
                errors.append(f"FE Route has no schedule but services {len(fe_route.serviced_se_routes)} SE routes.")
            continue
        
        arrival_at_depot = fe_route.schedule[-1]['arrival_time']
        
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
    file_path = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\A_100_10_TD.csv"
    
    # --- CẤU HÌNH THUẬT TOÁN ---
    # Giai đoạn 1: LNS hạn chế để tạo lời giải ban đầu
    LNS_INITIAL_ITERATIONS = 10
    Q_PERCENTAGE_INITIAL = 0.4
    
    # Giai đoạn 2: ALNS đầy đủ để tối ưu hóa
    ALNS_MAIN_ITERATIONS = 20 # Bắt đầu với số lần lặp vừa phải để test

    try:
        problem = ProblemInstance(file_path=file_path)
    except Exception as e:
        print(f"Error loading instance: {e}"); return

    # --- TẬP HỢP CÁC TOÁN TỬ ---
    destroy_operators_map = {
        "random_removal": random_removal,
        "shaw_removal": shaw_removal,
        "worst_slack_removal": worst_slack_removal,
    }
    repair_operators_map = {
        "greedy_repair": greedy_repair,
        "regret_insertion": regret_insertion,
        "earliest_deadline_first_insertion": earliest_deadline_first_insertion
    }

    # --- GIAI ĐOẠN 1: TẠO LỜI GIẢI BAN ĐẦU ---
    print("\n" + "#"*70)
    print("### STAGE 1: GENERATING INITIAL SOLUTION ###")
    print("#"*70)
    initial_state = generate_initial_solution(
        problem, 
        lns_iterations=LNS_INITIAL_ITERATIONS, 
        q_percentage=Q_PERCENTAGE_INITIAL
    )
    print(f"\n--- Stage 1 Complete. Initial Best Cost: {initial_state.cost:.2f} ---")


    # --- GIAI ĐOẠN 2: TỐI ƯU HÓA BẰNG ALNS ---
    print("\n" + "#"*70)
    print("### STAGE 2: ADAPTIVE LARGE NEIGHBORHOOD SEARCH ###")
    print("#"*70)
    
    # Chạy ALNS. route_pools sẽ được dùng ở Bước 5, tạm thời bỏ qua
    best_alns_state, route_pools = run_alns_phase(
        initial_state=initial_state,
        iterations=ALNS_MAIN_ITERATIONS,
        destroy_operators=destroy_operators_map,
        repair_operators=repair_operators_map
    )

    final_solution = best_alns_state.solution
    
    # --- KẾT QUẢ CUỐI CÙNG ---
    print("\n\n" + "#"*70)
    print("### FINAL OPTIMAL SOLUTION ###")
    print("#"*70)
    print_solution_details(final_solution)
    validate_solution_feasibility(final_solution)

if __name__ == "__main__":
    main()

# --- END OF FILE main.py ---