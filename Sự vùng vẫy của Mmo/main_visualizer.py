import random
import config
import time
from problem_parser import ProblemInstance, PickupCustomer # <<< THÊM PickupCustomer VÀO ĐÂY
from data_structures import Solution

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
from solution_generator import generate_initial_solution
from lns_algorithm import run_alns_phase

# <<< DÒNG IMPORT MỚI >>>
from visualizer import visualize_solution


def print_solution_details(solution: Solution):
    # (Hàm này giữ nguyên, không thay đổi)
    print("\n" + "="*60 + "\n--- DETAILED SOLUTION REPORT ---\n" + "="*60)
    print(f"\n[SUMMARY]\nTotal Cost: {solution.calculate_total_cost():.2f}")
    print(f"Number of FE Routes: {len(solution.fe_routes)}")
    print(f"Number of SE Routes: {len(solution.se_routes)}")
    print(f"Unserved Customers: {len(solution.unserved_customers)}")
    if solution.unserved_customers: print(f"  -> IDs: {[c.id for c in solution.unserved_customers]}")
    
    print("\n\n" + "-"*20 + " SECOND-ECHELON (SE) ROUTES " + "-"*20)
    if not solution.se_routes: 
        print("No SE routes in the solution.")
    else:
        fe_to_se_map = {}
        for fe_route in solution.fe_routes:
            fe_to_se_map[fe_route] = []
        unassigned_se = []
        for se_route in solution.se_routes:
            assigned = False
            for fe_route in se_route.serving_fe_routes:
                if fe_route in fe_to_se_map:
                    fe_to_se_map[fe_route].append(se_route)
                    assigned = True
            if not assigned:
                unassigned_se.append(se_route)

        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n--- SE Routes served by [FE Route #{i+1}] ---")
            se_routes_for_fe = sorted(fe_to_se_map.get(fe_route, []), key=lambda r: r.satellite.id)
            if not se_routes_for_fe:
                print("  (This FE route serves no SE routes)")
            for se_route in se_routes_for_fe:
                print(se_route)
        
        if unassigned_se:
            print("\n--- Unassigned SE Routes (Potential Error) ---")
            for se_route in unassigned_se:
                print(se_route)

    print("\n\n" + "-"*20 + " FIRST-ECHELON (FE) ROUTES " + "-"*20)
    if not solution.fe_routes: 
        print("No FE routes in the solution.")
    else:
        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n[FE Route #{i+1}]")
            serviced_sats = sorted([se.satellite.id for se in fe_route.serviced_se_routes])
            print(f"Servicing Satellites: {serviced_sats if serviced_sats else 'None'}")
            print(fe_route)


# <<< THAY THẾ TOÀN BỘ HÀM NÀY BẰNG PHIÊN BẢN MỚI >>>
def validate_solution_feasibility(solution: Solution):
    print("\n\n" + "="*60 + "\n--- COMPREHENSIVE SOLUTION FEASIBILITY VALIDATION ---\n" + "="*60)
    errors = []
    warnings = [] # Dùng cho các vấn đề không nghiêm trọng bằng
    problem = solution.problem

    # ==========================================================
    # 1. KIỂM TRA TÍNH TOÀN VẸN CẤP SOLUTION
    # ==========================================================
    all_served_ids = set(solution.customer_to_se_route_map.keys())
    all_problem_ids = {c.id for c in problem.customers}
    total_customers_in_routes = sum(len(r.get_customers()) for r in solution.se_routes)
    
    # Validation 11 (Map Consistency)
    if len(all_served_ids) != total_customers_in_routes:
        errors.append(f"STRUCTURAL: customer_map size ({len(all_served_ids)}) != customers in routes ({total_customers_in_routes})")
    if len(all_served_ids) + len(solution.unserved_customers) != len(all_problem_ids):
        errors.append(f"STRUCTURAL: Served ({len(all_served_ids)}) + Unserved ({len(solution.unserved_customers)}) != Total problem customers ({len(all_problem_ids)})")

    # ==========================================================
    # 2. KIỂM TRA CHI TIẾT TỪNG SE ROUTE
    # ==========================================================
    for i, se_route in enumerate(solution.se_routes):
        # Validation 10 (No Empty Routes)
        if not se_route.get_customers():
            errors.append(f"SE Route (Sat {se_route.satellite.id}): Route is empty but exists in solution.")
            continue
            
        # Validation 8 (Load Consistency) & Capacity
        running_load = se_route.total_load_delivery
        if running_load > problem.se_vehicle_capacity + 1e-6:
            errors.append(f"SE Route (Sat {se_route.satellite.id}): Initial delivery load ({running_load:.2f}) exceeds capacity ({problem.se_vehicle_capacity:.2f})")
        for cust_id in se_route.nodes_id[1:-1]:
            cust = problem.node_objects[cust_id]
            if cust.type == 'DeliveryCustomer': running_load -= cust.demand
            else: running_load += cust.demand
            if running_load < -1e-6 or running_load > problem.se_vehicle_capacity + 1e-6:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Load violation at customer {cust.id}. Load: {running_load:.2f}")

        # Validation Time Windows & Schedule Logic (6)
        last_node_id = se_route.nodes_id[0]
        last_departure_time = se_route.service_start_times[last_node_id]
        
        for node_id in se_route.nodes_id[1:]:
            node_obj = problem.node_objects[node_id % problem.total_nodes]
            start_time = se_route.service_start_times.get(node_id)
            
            # Check time window
            if start_time < getattr(node_obj, 'ready_time', 0) - 1e-6:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Node {node_obj.id} served too early (Start: {start_time:.2f} < Ready: {getattr(node_obj, 'ready_time', 0):.2f})")
            if start_time > getattr(node_obj, 'due_time', float('inf')) + 1e-6:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Node {node_obj.id} served too late (Start: {start_time:.2f} > Due: {getattr(node_obj, 'due_time', float('inf')):.2f})")

            # Check schedule logic
            last_node_obj = problem.node_objects[last_node_id % problem.total_nodes]
            st_last = last_node_obj.service_time if last_node_obj.type != 'Satellite' else 0.0
            expected_arrival = last_departure_time + problem.get_travel_time(last_node_obj.id, node_obj.id)
            actual_arrival = start_time - se_route.waiting_times.get(node_id, 0.0)
            if abs(expected_arrival - actual_arrival) > 1e-6:
                errors.append(f"SE Route (Sat {se_route.satellite.id}): Time inconsistency between node {last_node_obj.id} and {node_obj.id}. Expected arrival {expected_arrival:.2f}, got {actual_arrival:.2f}")

            last_departure_time = start_time + (node_obj.service_time if node_obj.type != 'Satellite' else 0.0)
            last_node_id = node_id

    # ==========================================================
    # 3. KIỂM TRA CHI TIẾT TỪNG FE ROUTE & SYNCHRONIZATION
    # ==========================================================
    satellite_loads_from_fe = {} # {sat_id: {'delivery': load, 'pickup': load}}

    for i, fe_route in enumerate(solution.fe_routes):
        # Validation 10 & Link Consistency
        if not fe_route.serviced_se_routes:
            errors.append(f"FE Route #{i+1}: Is empty but exists in solution.")
            continue
        for se_route in fe_route.serviced_se_routes:
            if fe_route not in se_route.serving_fe_routes:
                errors.append(f"FE Route #{i+1} -> SE (Sat {se_route.satellite.id}): Link inconsistency (one-way link).")
        
        if not fe_route.schedule:
            errors.append(f"FE Route #{i+1}: Services routes but has no schedule.")
            continue

        # Validation 5 (Effective Deadline)
        arrival_at_depot = fe_route.schedule[-1]['arrival_time']
        all_deadlines = {cust.deadline for se in fe_route.serviced_se_routes for cust in se.get_customers() if isinstance(cust, PickupCustomer)}
        if all_deadlines and arrival_at_depot > min(all_deadlines) + 1e-6:
             errors.append(f"FE Route #{i+1}: Violates effective deadline (Arrival: {arrival_at_depot:.2f} > Deadline: {min(all_deadlines):.2f})")

        # Validation FE Capacity & Collect data for Load Sync
        for event in fe_route.schedule:
            if event['load_after'] > problem.fe_vehicle_capacity + 1e-6:
                errors.append(f"FE Route #{i+1}: Capacity violation. Load: {event['load_after']:.2f} > Cap: {problem.fe_vehicle_capacity:.2f}")
            
            sat_id = event['node_id']
            if sat_id not in satellite_loads_from_fe: satellite_loads_from_fe[sat_id] = {'delivery': 0.0, 'pickup': 0.0}
            if event['activity'] == 'UNLOAD_DELIV': satellite_loads_from_fe[sat_id]['delivery'] -= event['load_change'] # load_change is negative
            if event['activity'] == 'LOAD_PICKUP': satellite_loads_from_fe[sat_id]['pickup'] += event['load_change']

        # Validation 1 & 2 (Time Synchronization)
        for se_route in fe_route.serviced_se_routes:
            sat_id = se_route.satellite.id
            fe_arrival_at_sat = next((e['arrival_time'] for e in fe_route.schedule if e['node_id'] == sat_id and e['activity'] == 'UNLOAD_DELIV'), None)
            se_start_time = se_route.service_start_times[se_route.nodes_id[0]]
            if fe_arrival_at_sat is not None and se_start_time < fe_arrival_at_sat - 1e-6:
                errors.append(f"SYNC ERROR on FE->SE #{i+1} (Sat {sat_id}): SE starts ({se_start_time:.2f}) before FE arrives ({fe_arrival_at_sat:.2f}).")

            fe_pickup_start_at_sat = next((e['start_svc_time'] for e in fe_route.schedule if e['node_id'] == sat_id and e['activity'] == 'LOAD_PICKUP'), None)
            se_end_time = se_route.service_start_times[se_route.nodes_id[-1]]
            if fe_pickup_start_at_sat is not None and se_end_time > fe_pickup_start_at_sat + 1e-6:
                errors.append(f"SYNC ERROR on SE->FE #{i+1} (Sat {sat_id}): SE returns ({se_end_time:.2f}) after FE starts picking up ({fe_pickup_start_at_sat:.2f}).")

    # ==========================================================
    # 4. KIỂM TRA ĐỒNG BỘ TẢI TRỌNG TOÀN CỤC
    # ==========================================================
    satellite_loads_from_se = {} # {sat_id: {'delivery': load, 'pickup': load}}
    for se_route in solution.se_routes:
        sat_id = se_route.satellite.id
        if sat_id not in satellite_loads_from_se: satellite_loads_from_se[sat_id] = {'delivery': 0.0, 'pickup': 0.0}
        satellite_loads_from_se[sat_id]['delivery'] += se_route.total_load_delivery
        satellite_loads_from_se[sat_id]['pickup'] += se_route.total_load_pickup
    
    all_sats = set(satellite_loads_from_fe.keys()) | set(satellite_loads_from_se.keys())
    for sat_id in all_sats:
        load_fe = satellite_loads_from_fe.get(sat_id, {'delivery': 0.0, 'pickup': 0.0})
        load_se = satellite_loads_from_se.get(sat_id, {'delivery': 0.0, 'pickup': 0.0})
        # Validation 3 & 4
        if abs(load_fe['delivery'] - load_se['delivery']) > 1e-6:
            errors.append(f"LOAD SYNC ERROR (Delivery) at Sat {sat_id}: FE unloads {load_fe['delivery']:.2f}, but SEs need {load_se['delivery']:.2f}")
        if abs(load_fe['pickup'] - load_se['pickup']) > 1e-6:
            errors.append(f"LOAD SYNC ERROR (Pickup) at Sat {sat_id}: FE loads {load_fe['pickup']:.2f}, but SEs bring {load_se['pickup']:.2f}")


    # ==========================================================
    # 5. In kết quả
    # ==========================================================
    if not errors and not warnings:
        print("\n[VALIDATION SUCCESS] Solution is feasible and fully consistent.")
    else:
        if errors:
            print("\n[VALIDATION FAILED] Found the following critical issues:")
            for i, error in enumerate(errors):
                print(f"  ERR #{i+1}: {error}")
        if warnings:
            print("\n[VALIDATION WARNINGS] Found the following potential issues:")
            for i, warning in enumerate(warnings):
                print(f"  WARN #{i+1}: {warning}")
    print("="*60)


def main():
    start_time = time.time()
    random.seed(config.RANDOM_SEED)
    try:
        problem = ProblemInstance(file_path=config.FILE_PATH, vehicle_speed=config.VEHICLE_SPEED)
    except Exception as e:
        print(f"Error loading instance: {e}"); return

    # Cập nhật map với các toán tử mới
    destroy_operators_map = {
        "random_removal": random_removal, "shaw_removal": shaw_removal,
        "worst_slack_removal": worst_slack_removal, "worst_distance_removal": worst_distance_removal,
        "route_removal": route_removal, "satellite_removal": satellite_removal,
        "least_utilized_route_removal": least_utilized_route_removal,
    }
    repair_operators_map = {
        "greedy_repair": greedy_repair, "regret_insertion": regret_insertion,
        "earliest_deadline_first_insertion": earliest_deadline_first_insertion, "farthest_first_insertion": farthest_first_insertion,
        "largest_first_insertion": largest_first_insertion, "closest_first_insertion": closest_first_insertion,
        "earliest_time_window_insertion": earliest_time_window_insertion, "latest_time_window_insertion": latest_time_window_insertion,
        "latest_deadline_first_insertion": latest_deadline_first_insertion,
    }

    print("\n" + "#"*70 + "\n### STAGE 1: GENERATING INITIAL SOLUTION ###\n" + "#"*70)
    initial_state = generate_initial_solution(problem, lns_iterations=config.LNS_INITIAL_ITERATIONS, q_percentage=config.Q_PERCENTAGE_INITIAL)
    print(f"\n--- Stage 1 Complete. Initial Best Cost: {initial_state.cost:.2f} ---")

    print("\n" + "#"*70 + "\n### STAGE 2: ADAPTIVE LARGE NEIGHBORHOOD SEARCH ###\n" + "#"*70)
    best_alns_state, _ = run_alns_phase(initial_state=initial_state, iterations=config.ALNS_MAIN_ITERATIONS, destroy_operators=destroy_operators_map, repair_operators=repair_operators_map)

    final_solution = best_alns_state.solution
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n\n" + "#"*70 + "\n### FINAL OPTIMAL SOLUTION ###\n" + "#"*70)
    print(f"Total execution time: {total_time:.2f} seconds")
    print_solution_details(final_solution)
    validate_solution_feasibility(final_solution)
    
    # <<< CÁC DÒNG MỚI ĐỂ GỌI VISUALIZER >>>
    if final_solution:
        print("\nDisplaying solution visualization... (Close the plot window to exit)")
        visualize_solution(final_solution)


if __name__ == "__main__":
    main()