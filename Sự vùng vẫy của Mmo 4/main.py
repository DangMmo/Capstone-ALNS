# --- START OF FILE main.py (PHAN HOI CUOI CUNG - DAY DU NHAT) ---

import os
import sys
import shutil
import datetime
import time
import random
import pandas as pd
import matplotlib.pyplot as plt

# --- Import tu cac package ---
import config
from core.problem_parser import ProblemInstance, PickupCustomer
from core.data_structures import Solution
from ALNS.solution_generator import generate_initial_solution
from ALNS.lns_algorithm import run_alns_phase
from ALNS.destroy_operators import (
    random_removal, shaw_removal, worst_slack_removal,
    worst_cost_removal, route_removal, satellite_removal,
    least_utilized_route_removal
)
from ALNS.repair_operators import (
    greedy_repair, regret_insertion, earliest_deadline_first_insertion,
    farthest_first_insertion, largest_first_insertion, closest_first_insertion,
    earliest_time_window_insertion, latest_time_window_insertion,
    latest_deadline_first_insertion
)
from clustering.data_handler import load_and_parse_data, preprocess_customers
from clustering.dissimilarity_calculator import create_dissimilarity_matrix
from clustering.clustering_engine import analyze_k_and_suggest_optimal, run_clustering
from utils.visualizer import visualize_solution
from utils import analytics_plots, clustering_plots

# --- Lop Logger duoc nang cap ---
class Logger(object):
    def __init__(self, filename="log.txt", stream=sys.stdout):
        self.terminal = stream
        self.log_file = open(filename, 'a', encoding='utf-8')
        # Thuộc tính mới để kiểm tra xem stream có phải là terminal không
        self.is_terminal = stream.isatty() if hasattr(stream, 'isatty') else False

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.flush()

    def write_to_log_only(self, message):
        self.log_file.write(message + "\n")
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

# ==============================================================================
# QUY TRINH CLUSTERING
# ==============================================================================
def run_clustering_phase(run_dir):
    """Chay toan bo quy trinh clustering va tao ra cac file CSV con."""
    print("\n" + "#"*70 + "\n### ORCHESTRATOR - GIAI DOAN 1: GOM CUM ###\n" + "#"*70)
    hub_df, satellites_df, customers_df = load_and_parse_data()
    if customers_df is None or customers_df.empty:
        print("Khong co du lieu khach hang de gom cum. Dung chuong trinh."); return None
    customers_processed_df = preprocess_customers(customers_df, satellites_df, hub_df)
    dissimilarity_matrix = create_dissimilarity_matrix(customers_processed_df)
    k_suggested, scores_by_k = analyze_k_and_suggest_optimal(dissimilarity_matrix)
    if k_suggested is None: print("Loi khi phan tich k. Dung chuong trinh."); return None
    k_final = k_suggested
    if config.INTERACTIVE_K_SELECTION:
        try:
            prompt = f"\nNhap so cum (k) de giai (Enter de dung k goi y={k_suggested}): "
            user_input = input(prompt)
            if user_input.strip() and int(user_input) in config.K_CLUSTERS_RANGE:
                k_final = int(user_input)
                print(f"Ban da chon k = {k_final}")
            else:
                print(f"Su dung gia tri goi y k = {k_suggested}")
        except (ValueError, TypeError):
            print(f"Dau vao khong hop le, su dung gia tri goi y k = {k_suggested}")
    print(f"\nSe tien hanh giai cho {k_final} cum.")
    final_labels = run_clustering(dissimilarity_matrix, k_final)
    customers_processed_df['cluster_id'] = final_labels
    print("\nDang tao va luu bieu do phan tich clustering...")
    clustering_plots.plot_silhouette_scores(scores_by_k, save_dir=run_dir)
    clustering_plots.plot_clusters_map(customers_processed_df, satellites_df, hub_df, save_dir=run_dir)
    os.makedirs(config.CLUSTER_DATA_DIR, exist_ok=True)
    cluster_file_paths = []
    for cluster_id in range(k_final):
        cluster_customers_df = customers_processed_df[customers_processed_df['cluster_id'] == cluster_id]
        if cluster_customers_df.empty: continue
        output_df = pd.concat([hub_df, satellites_df, cluster_customers_df], ignore_index=True)
        file_path = os.path.join(config.CLUSTER_DATA_DIR, f"cluster_{cluster_id}_data.csv")
        output_df.to_csv(file_path, index=False)
        cluster_file_paths.append(file_path)
    return cluster_file_paths

# ==============================================================================
# QUY TRINH GIAI BANG ALNS
# ==============================================================================
def run_solver_for_file(file_path: str, is_sub_problem: bool):
    """Chay bo giai ALNS cho mot file du lieu cu the."""
    verbose = not is_sub_problem
    destroy_operators_map = {
        "random_removal": random_removal, "shaw_removal": shaw_removal, "worst_slack_removal": worst_slack_removal,
        "worst_cost_removal": worst_cost_removal, "route_removal": route_removal, "satellite_removal": satellite_removal,
        "least_utilized_route_removal": least_utilized_route_removal,
    }
    repair_operators_map = {
        "greedy_repair": greedy_repair, "regret_insertion": regret_insertion, "earliest_deadline_first_insertion": earliest_deadline_first_insertion,
        "farthest_first_insertion": farthest_first_insertion, "largest_first_insertion": largest_first_insertion, "closest_first_insertion": closest_first_insertion,
        "earliest_time_window_insertion": earliest_time_window_insertion, "latest_time_window_insertion": latest_time_window_insertion,
        "latest_deadline_first_insertion": latest_deadline_first_insertion
    }
    try:
        problem = ProblemInstance(file_path=file_path, vehicle_speed=config.VEHICLE_SPEED, verbose=verbose)
    except Exception as e:
        print(f"Loi khi tai file {file_path}: {e}"); return None, (None, None)
    initial_state = generate_initial_solution(problem, lns_iterations=config.LNS_INITIAL_ITERATIONS, q_percentage=config.Q_PERCENTAGE_INITIAL, verbose=verbose)
    best_state, (run_history, op_history) = run_alns_phase(
        initial_state=initial_state, iterations=config.ALNS_MAIN_ITERATIONS,
        destroy_operators=destroy_operators_map, repair_operators=repair_operators_map,
        verbose=verbose, track_history=True
    )
    return best_state, (run_history, op_history)

# ==============================================================================
# QUY TRINH HOP NHAT KET QUA VA BAO CAO
# ==============================================================================
def merge_solutions(sub_solutions_states: list, master_problem: ProblemInstance) -> Solution:
    """Hop nhat cac loi giai con va cap nhat lai problem instance cho cac route."""
    print("Bat dau hop nhat cac loi giai con...")
    master_solution = Solution(master_problem)
    
    for state in sub_solutions_states:
        if state:
            sub_solution = state.solution
            
            # <<< BƯỚC SỬA LỖI: GÁN LẠI PROBLEM CHO TỪNG ROUTE >>>
            for fe_route in sub_solution.fe_routes:
                fe_route.problem = master_problem
                master_solution.fe_routes.append(fe_route)
            
            for se_route in sub_solution.se_routes:
                se_route.problem = master_problem
                master_solution.se_routes.append(se_route)
            
            master_solution.unserved_customers.extend(sub_solution.unserved_customers)

    master_solution.update_customer_map()
    print(f"Hop nhat hoan tat. Tong cong co {len(master_solution.fe_routes)} FE routes va {len(master_solution.se_routes)} SE routes.")
    return master_solution

def print_solution_details(solution: Solution, title: str):
    """In ra bao cao tom tat ve loi giai ra console."""
    print(f"\n" + "="*80 + f"\n--- {title} ---\n" + "="*80)
    print(f"\n[TONG QUAN]")
    print(f"Chi phi muc tieu (tu config): {solution.get_objective_cost():.2f}")
    total_dist = sum(r.total_dist for r in solution.fe_routes) + sum(r.total_dist for r in solution.se_routes)
    total_time = sum(r.total_travel_time for r in solution.fe_routes) + sum(r.total_travel_time for r in solution.se_routes)
    print(f"  -> Tong quang duong: {total_dist:.2f}")
    print(f"  -> Tong thoi gian di chuyen: {total_time:.2f}")
    print(f"So luong tuyen FE: {len(solution.fe_routes)}")
    print(f"So luong tuyen SE: {len(solution.se_routes)}")

def log_full_solution_details(solution: Solution, logger: Logger):
    """Ghi bao cao chi tiet toan bo cac tuyen duong vao file log."""
    report_lines = []
    report_lines.append("\n" + "="*80 + "\n--- CHI TIET TOAN BO TUYEN DUONG (LOG FILE) ---\n" + "="*80)
    fe_to_se_map = {fe: [] for fe in solution.fe_routes}
    unassigned_se = []
    for se_route in solution.se_routes:
        assigned = False
        for fe_route in se_route.serving_fe_routes:
            if fe_route in fe_to_se_map: fe_to_se_map[fe_route].append(se_route); assigned = True
        if not assigned: unassigned_se.append(se_route)
    report_lines.append("\n\n" + "-"*20 + " SECOND-ECHELON (SE) ROUTES " + "-"*20)
    if not solution.se_routes: 
        report_lines.append("Khong co tuyen SE nao trong loi giai.")
    else:
        for i, fe_route in enumerate(solution.fe_routes):
            report_lines.append(f"\n--- Cac tuyen SE duoc phuc vu boi [FE Route #{i+1}] ---")
            se_routes_for_fe = sorted(fe_to_se_map.get(fe_route, []), key=lambda r: r.satellite.id)
            if not se_routes_for_fe: report_lines.append("  (Tuyen FE nay khong phuc vu tuyen SE nao)")
            for se_route in se_routes_for_fe: report_lines.append(str(se_route))
        if unassigned_se:
            report_lines.append("\n--- Cac tuyen SE khong duoc phuc vu (Co the la loi) ---")
            for se_route in unassigned_se: report_lines.append(str(se_route))
    report_lines.append("\n\n" + "-"*20 + " FIRST-ECHELON (FE) ROUTES " + "-"*20)
    if not solution.fe_routes: 
        report_lines.append("Khong co tuyen FE nao trong loi giai.")
    else:
        for i, fe_route in enumerate(solution.fe_routes):
            report_lines.append(f"\n[FE Route #{i+1}]")
            serviced_sats = sorted([se.satellite.id for se in fe_route.serviced_se_routes])
            report_lines.append(f"Phuc vu cac ve tinh: {serviced_sats if serviced_sats else 'None'}")
            report_lines.append(str(fe_route))
    report_lines.append("\n" + "="*80)
    logger.write_to_log_only("\n".join(report_lines))

def validate_solution_feasibility(solution: Solution):
    """Kiem tra chi tiet tinh hop le cua loi giai."""
    print("\n\n" + "="*80 + "\n--- KIEM TRA TINH HOP LE CUA LOI GIAI ---\n" + "="*80)
    errors = []; problem = solution.problem
    all_served_ids = set(solution.customer_to_se_route_map.keys())
    all_problem_ids = {c.id for c in problem.customers}
    total_customers_in_routes = sum(len(r.get_customers()) for r in solution.se_routes)
    if len(all_served_ids) != total_customers_in_routes: errors.append(f"SAI LECH MAP: customer_map ({len(all_served_ids)}) vs. customers_in_routes ({total_customers_in_routes})")
    if len(all_served_ids) + len(solution.unserved_customers) != len(all_problem_ids): errors.append(f"SAI LECH TONG SO: Da phuc vu ({len(all_served_ids)}) + Chua phuc vu ({len(solution.unserved_customers)}) != Tong so khach hang ({len(all_problem_ids)})")
    for se_route in solution.se_routes:
        if se_route.total_load_delivery > problem.se_vehicle_capacity + 1e-6: errors.append(f"SE Route (Sat {se_route.satellite.id}): Tai trong giao hang ban dau ({se_route.total_load_delivery:.2f}) vuot qua suc chua ({problem.se_vehicle_capacity:.2f})")
        for cust in se_route.get_customers():
            start_time = se_route.service_start_times.get(cust.id)
            if start_time is None: errors.append(f"SE Route (Sat {se_route.satellite.id}): Khach hang {cust.id} co trong tuyen nhung khong co thoi gian bat dau."); continue
            if start_time > cust.due_time + 1e-6: errors.append(f"SE Route (Sat {se_route.satellite.id}): Khach hang {cust.id} phuc vu tre (Bat dau: {start_time:.2f} > Due: {cust.due_time:.2f})")
        if not se_route.serving_fe_routes: errors.append(f"SE Route (Sat {se_route.satellite.id}): Khong duoc phuc vu boi bat ky tuyen FE nao.")
    for i, fe_route in enumerate(solution.fe_routes):
        if not fe_route.schedule and fe_route.serviced_se_routes: errors.append(f"FE Route #{i+1}: Khong co lich trinh nhung van phuc vu {len(fe_route.serviced_se_routes)} tuyen SE."); continue
        if not fe_route.schedule: continue
        for event in fe_route.schedule:
            if event['load_after'] < -1e-6 or event['load_after'] > problem.fe_vehicle_capacity + 1e-6: errors.append(f"FE Route #{i+1}: Vi pham suc chua. Tai trong: {event['load_after']:.2f}, Suc chua: {problem.fe_vehicle_capacity:.2f}")
        arrival_at_depot = fe_route.schedule[-1]['arrival_time']
        all_deadlines = {cust.deadline for se in fe_route.serviced_se_routes for cust in se.get_customers() if isinstance(cust, PickupCustomer)}
        if all_deadlines and arrival_at_depot > min(all_deadlines) + 1e-6: errors.append(f"FE Route #{i+1}: Vi pham deadline hieu dung (Ve depot: {arrival_at_depot:.2f} > Deadline: {min(all_deadlines):.2f})")
    if not errors: print("\n[KIEM TRA THANH CONG] Solution appears to be feasible.")
    else:
        print("\n[KIEM TRA THAT BAI] Phat hien cac van de sau:"); [print(f"  - {e}") for e in errors]
    print("="*80)

# ==============================================================================
# HAM MAIN CHINH
# ==============================================================================
def main():
    base_output_dir = config.BASE_RESULTS_DIR
    if config.CLEAR_OLD_RESULTS_ON_START and os.path.exists(base_output_dir): shutil.rmtree(base_output_dir)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    instance_name = os.path.splitext(os.path.basename(config.FILE_PATH))[0]
    run_dir = os.path.join(base_output_dir, f"{instance_name}_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    log_instance = Logger(os.path.join(run_dir, "log.txt"), sys.stdout)
    sys.stdout = log_instance; sys.stderr = log_instance
    shutil.copy('config.py', os.path.join(run_dir, 'config_snapshot.py'))
    start_time_total = time.time()
    random.seed(config.RANDOM_SEED)
    print("="*70 + "\n   MASTER ORCHESTRATOR FOR 2E-VRP-PDD SOLVER\n" + f"   Run ID: {instance_name}_{timestamp}\n" + "="*70)
    
    final_solution, run_history, op_history = None, {}, {}

    if config.ENABLE_CLUSTER_PIPELINE:
        cluster_files = run_clustering_phase(run_dir)
        if cluster_files:
            sub_solution_states, cluster_summary = [], []
            master_problem = ProblemInstance(file_path=config.FILE_PATH, vehicle_speed=config.VEHICLE_SPEED, verbose=False)
            total_iterations = len(cluster_files) * config.ALNS_MAIN_ITERATIONS
            
            print("\n" + "#"*70 + "\n### ORCHESTRATOR - GIAI DOAN 2: GIAI CAC BAI TOAN CON ###\n" + "#"*70)
            for i, file_path in enumerate(cluster_files):
                sub_problem_start_time = time.time()
                print(f"\n--- [{i+1}/{len(cluster_files)}] Dang giai: {os.path.basename(file_path)} ---")
                state, (run_hist, op_hist) = run_solver_for_file(file_path, is_sub_problem=True)
                sub_problem_end_time = time.time()
                if state:
                    sub_solution_states.append(state)
                    print_solution_details(state.solution, f"KET QUA CHO CUM {i}")
                    solve_time = sub_problem_end_time - sub_problem_start_time
                    summary_item = {
                        "Cluster ID": i, "Customers": len(state.solution.customer_to_se_route_map),
                        "Objective Cost": state.cost,
                        "Total Distance": sum(r.total_dist for r in state.solution.fe_routes) + sum(r.total_dist for r in state.solution.se_routes),
                        "Total Travel Time": sum(r.total_travel_time for r in state.solution.fe_routes) + sum(r.total_travel_time for r in state.solution.se_routes),
                        "FE Routes": len(state.solution.fe_routes), "SE Routes": len(state.solution.se_routes),
                        "Solve Time (s)": solve_time}
                    cluster_summary.append(summary_item)
                    if i == len(cluster_files) - 1: run_history, op_history = run_hist, op_hist

            print("\n" + "#"*70 + "\n### ORCHESTRATOR - GIAI DOAN 3: HOP NHAT LOI GIAI ###\n" + "#"*70)
            final_solution = merge_solutions(sub_solution_states, master_problem)
            if cluster_summary:
                print("\n\n" + "="*120 + "\n--- TOM TAT KET QUA GIAI THEO TUNG CUM ---\n" + "="*120)
                summary_df = pd.DataFrame(cluster_summary)
                for col in ['Objective Cost', 'Total Distance', 'Total Travel Time', 'Solve Time (s)']:
                    summary_df[col] = summary_df[col].map('{:,.2f}'.format)
                print(summary_df.to_string(index=False))
                summary_df.to_csv(os.path.join(run_dir, "C_cluster_summary.csv"), index=False)
            print(f"\nTong so vong lap ALNS da chay (gan dung): {total_iterations}")
            if os.path.exists(config.CLUSTER_DATA_DIR): shutil.rmtree(config.CLUSTER_DATA_DIR)
    else:
        print("\n" + "#"*70 + "\n### ORCHESTRATOR - CHE DO GIAI TRUC TIEP ###\n" + "#"*70)
        best_state, (run_history, op_history) = run_solver_for_file(config.FILE_PATH, is_sub_problem=False)
        if best_state: final_solution = best_state.solution

    if final_solution:
        end_time_total = time.time()
        print("\n\n" + "#"*70 + "\n### ORCHESTRATOR - KET QUA CUOI CUNG ###\n" + "#"*70)
        print(f"Tong thoi gian thuc thi: {end_time_total - start_time_total:.2f} giay")
        print_solution_details(final_solution, "BAO CAO LOI GIAI TONG HOP")
        validate_solution_feasibility(final_solution)
        log_full_solution_details(final_solution, log_instance)
        
        print("\nDang tao va luu cac bieu do...")
        visualize_solution(final_solution, save_dir=run_dir, filename_prefix="D_")
        
        if run_history and run_history.get('iteration'):
            prefix = "E_" if config.ENABLE_CLUSTER_PIPELINE else ""
            analytics_plots.plot_convergence(run_history, save_dir=run_dir, filename_prefix=prefix)
            analytics_plots.plot_acceptance_criteria(run_history, save_dir=run_dir, filename_prefix=prefix)
            analytics_plots.plot_destroy_impact(run_history, save_dir=run_dir, filename_prefix=prefix)
        if op_history and op_history.get('iteration'):
            prefix = "F_" if config.ENABLE_CLUSTER_PIPELINE else ""
            analytics_plots.plot_operator_weights(op_history, save_dir=run_dir, filename_prefix=prefix)
        
        print(f"\nHoan tat! Tat ca log va ket qua da duoc luu tai: {run_dir}")
    else:
        print("\nKhong tim thay loi giai nao.")

if __name__ == "__main__":
    main()