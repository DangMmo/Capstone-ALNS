# --- START OF FILE main.py (FINAL VERSION WITH CLEANUP LOGIC) ---

import copy
from Parser import ProblemInstance
from DataStructures import Solution
from manual_clustering import perform_manual_clustering
from SolutionBuilder import (
    build_and_optimize_routes_for_cluster,
    _find_cluster_satellite,
    build_fe_routes_with_sequential_insertion
)

def validate_solution_flows(all_se_routes, all_fe_routes):
    """Kiểm tra xem luồng hàng hóa giữa FE và SE có cân bằng không."""
    satellite_demands = {}
    for se_route in all_se_routes:
        sat_id = se_route.satellite.id
        if sat_id not in satellite_demands:
            satellite_demands[sat_id] = {'required_delivery': 0, 'required_pickup': 0}
        satellite_demands[sat_id]['required_delivery'] += se_route.total_load_delivery
        satellite_demands[sat_id]['required_pickup'] += se_route.total_load_pickup

    fe_service = {}
    for fe_route in all_fe_routes:
        for event in fe_route.schedule:
            if event['activity'] in ['UNLOAD_DELIV', 'LOAD_PICKUP']:
                sat_id = event['node_id']
                if sat_id not in fe_service:
                    fe_service[sat_id] = {'serviced_delivery': 0, 'serviced_pickup': 0}
                if event['activity'] == 'UNLOAD_DELIV':
                    fe_service[sat_id]['serviced_delivery'] += -event['load_change']
                elif event['activity'] == 'LOAD_PICKUP':
                    fe_service[sat_id]['serviced_pickup'] += event['load_change']

    is_valid = True
    print("\n\n--- SOLUTION FLOW VALIDATION ---")
    all_sat_ids = sorted(list(set(satellite_demands.keys()) | set(fe_service.keys())))
    for sat_id in all_sat_ids:
        req_del = satellite_demands.get(sat_id, {}).get('required_delivery', 0)
        req_pick = satellite_demands.get(sat_id, {}).get('required_pickup', 0)
        serv_del = fe_service.get(sat_id, {}).get('serviced_delivery', 0)
        serv_pick = fe_service.get(sat_id, {}).get('serviced_pickup', 0)
        del_gap = req_del - serv_del
        pick_gap = req_pick - serv_pick
        if abs(del_gap) > 1e-6 or abs(pick_gap) > 1e-6:
            is_valid = False
            print(f"[ERROR] Satellite {sat_id}: Flow Mismatch!")
            if abs(del_gap) > 1e-6: print(f"  - Delivery: Required={req_del:.2f}, Serviced={serv_del:.2f} -> GAP={del_gap:.2f}")
            if abs(pick_gap) > 1e-6: print(f"  - Pickup:   Required={req_pick:.2f}, Serviced={serv_pick:.2f} -> GAP={pick_gap:.2f}")
    if is_valid: print("All satellite flows are balanced. Solution is valid.")
    else: print("!!! SOLUTION IS INVALID DUE TO FLOW MISMATCHES !!!")
    print("--------------------------------\n")
    return is_valid

def main():
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_5_TD.csv"
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\C_100_5_TD.csv"
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-without-deadline\\100 customer WD\\C_100_10.csv"
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_2_D.csv"
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_5_TD.csv"

    # ==========================================================
    # ==            BẢNG ĐIỀU KHIỂN CỦA BẠN                  ==
    # ========================================================== 
    K_VALUE = 4
    LNS_ITERATIONS_PER_CLUSTER = 5
    CONSIDER_DEADLINE = True    
    VEHICLE_SPEED_METERS_PER_MINUTE = 1.0
    # ==========================================================

    try:
        problem = ProblemInstance(file_name, vehicle_speed=VEHICLE_SPEED_METERS_PER_MINUTE)
    except FileNotFoundError:
        print(f"LOI: Khong tim thay file '{file_name}'."); return
    
    # --- GIAI ĐOAN 1: PHAN CUM ---
    print(f"\n--- GIAI DOAN 1: THUC HIEN PHAN CUM VOI K = {K_VALUE} ---")
    clusters = perform_manual_clustering(problem, K_VALUE)
    if clusters is None: print("\nQua trinh phan cum that bai. Dung chuong trinh."); return
    print("\n--- CHI TIET CAC CUM DA TAO ---")
    for i, cluster in enumerate(clusters): print(f"  Cum {i+1}: {len(cluster)} khach hang")

    # --- GIAI ĐOAN 2: XÂY DỰNG LỜI GIẢI THÔ (RAW SOLUTION) ---
    print("\n--- GIAI DOAN 2: XAY DUNG LOI GIAI THO ---")
    
    # 1. Giải quyết tất cả các cụm để có được một tập hợp lớn các tuyến SE
    all_se_routes = []
    unserved_customers = []
    for i, cluster in enumerate(clusters):
        print(f"\n--- Dang xu ly Cum {i+1}/{len(clusters)} ({len(cluster)} khach hang) ---")
        if not cluster: continue
        
        home_satellite = _find_cluster_satellite(cluster, problem)
        if not home_satellite:
            unserved_customers.extend(cluster)
            continue

        se_routes, unserved_in_cluster = build_and_optimize_routes_for_cluster(
            home_satellite, cluster, problem, lns_iterations=LNS_ITERATIONS_PER_CLUSTER
        )
        all_se_routes.extend(se_routes)
        unserved_customers.extend(unserved_in_cluster)
        
    # 2. Từ tập hợp tất cả các tuyến SE, xây dựng hệ thống FE tốt nhất có thể
    temp_fe_solution = Solution(problem)
    
    if all_se_routes:
        # Tổng hợp yêu cầu từ tất cả các tuyến SE đã tạo
        final_reqs = {}
        for sat in {r.satellite for r in all_se_routes}:
            routes_for_sat = [r for r in all_se_routes if r.satellite == sat]
            if not routes_for_sat: continue
            req = {'latest_se_pickup_arrival': max(r.service_start_times.get(r.satellite.coll_id, float('-inf')) for r in routes_for_sat),
                   'delivery_load': sum(r.total_load_delivery for r in routes_for_sat),
                   'pickup_load': sum(r.total_load_pickup for r in routes_for_sat), 'obj': sat}
            if CONSIDER_DEADLINE:
                deadlines = [c.deadline for r in routes_for_sat for c in r.get_customers() if hasattr(c, 'deadline') and c.deadline != float('inf')]
                req['deadline'] = min(deadlines) if deadlines else float('inf')
            final_reqs[sat.id] = req
        
        # Gọi hàm xây dựng FE
        build_fe_routes_with_sequential_insertion(temp_fe_solution, final_reqs, problem, CONSIDER_DEADLINE)
        
    # --- GIAI ĐOAN 3: DỌN DẸP VÀ HOÀN THIỆN LỜI GIẢI ---
    print("\n--- GIAI DOAN 3: DON DEP VA HOAN THIEN LOI GIAI ---")
    final_solution = Solution(problem)

    # 1. Xác định các tuyến SE không khả thi và loại bỏ chúng
    unserviced_sat_ids = set(temp_fe_solution.unserviced_satellite_reqs.keys())
    
    if unserviced_sat_ids:
        print(f"[POST-PROCESSING] Phat hien cac ve tinh khong duoc FE phuc vu: {unserviced_sat_ids}")
        
        # Lọc ra các tuyến SE hợp lệ
        valid_se_routes = [r for r in all_se_routes if r.satellite.id not in unserviced_sat_ids]
        invalid_se_routes = [r for r in all_se_routes if r.satellite.id in unserviced_sat_ids]
        
        # Cập nhật danh sách khách hàng không được phục vụ
        for r in invalid_se_routes:
            for c in r.get_customers():
                if c not in unserved_customers:
                    unserved_customers.append(c)
        
        final_solution.se_routes = valid_se_routes
        # Xây dựng lại FE CHỈ với các tuyến SE hợp lệ
        if valid_se_routes:
            valid_reqs = {}
            for sat in {r.satellite for r in valid_se_routes}:
                # ... (copy logic tổng hợp reqs từ trên) ...
                routes_for_sat = [r for r in valid_se_routes if r.satellite == sat]
                if not routes_for_sat: continue
                req = {'latest_se_pickup_arrival': max(r.service_start_times.get(r.satellite.coll_id, float('-inf')) for r in routes_for_sat),
                       'delivery_load': sum(r.total_load_delivery for r in routes_for_sat),
                       'pickup_load': sum(r.total_load_pickup for r in routes_for_sat), 'obj': sat}
                if CONSIDER_DEADLINE:
                    deadlines = [c.deadline for r in routes_for_sat for c in r.get_customers() if hasattr(c, 'deadline') and c.deadline != float('inf')]
                    req['deadline'] = min(deadlines) if deadlines else float('inf')
                valid_reqs[sat.id] = req
            
            build_fe_routes_with_sequential_insertion(final_solution, valid_reqs, problem, CONSIDER_DEADLINE)
    else:
        # Nếu tất cả vệ tinh đều được phục vụ, chỉ cần sao chép kết quả
        final_solution.se_routes = all_se_routes
        final_solution.fe_routes = temp_fe_solution.fe_routes

    # 2. Đồng bộ hóa, tính toán và kiểm tra cuối cùng
    for fe_route in final_solution.fe_routes:
        for event in fe_route.schedule:
            if event['activity'] == 'UNLOAD_DELIV':
                sat_id, se_start_time = event['node_id'], event['departure_time']
                for se_route in final_solution.se_routes:
                    if se_route.satellite.id == sat_id:
                        se_route.service_start_times[se_route.satellite.dist_id] = se_start_time
                        se_route.calculate_full_schedule_and_slacks()
    
    final_solution.unserved_customers = unserved_customers
    final_solution.calculate_total_cost_and_time()
    
    validate_solution_flows(final_solution.se_routes, final_solution.fe_routes)

    # 4. IN KẾT QUẢ CUỐI CÙNG
    deadline_status_str = "CO XET DEADLINE" if CONSIDER_DEADLINE else "KHONG XET DEADLINE"
    fe_strategy_str = "FE Giao-Lay dong thoi (CPD)"
    print(f"--- KET QUA LOI GIAI HOAN CHINH ({deadline_status_str}, {fe_strategy_str}) ---")
    print(f"Tong chi phi (quang duong): {final_solution.total_cost:.2f} m")
    print(f"Tong thoi gian hoat dong: {final_solution.total_time:.2f} min")
    print(f"So tuyen FE: {len(final_solution.fe_routes)}")
    print(f"So tuyen SE: {len(final_solution.se_routes)}")
    if final_solution.unserved_customers:
        print(f"So khach hang khong the phuc vu: {len(final_solution.unserved_customers)}")
        unserved_ids = sorted([c.id for c in final_solution.unserved_customers])
        print(f"  Danh sach ID: {unserved_ids}")
    else:
        print("Trang thai: Da phuc vu tat ca khach hang.")
    
    print("\nChi tiet cac tuyen FE:")
    for i, route in enumerate(final_solution.fe_routes): print(f"\n[FE Route {i+1}] \n{route}")
    print("\nChi tiet cac tuyen SE:")
    for i, route in enumerate(final_solution.se_routes): print(f"\n[SE Route {i+1}] \n{route}")

if __name__ == "__main__":
    main()

# --- END OF FILE main.py (FINAL VERSION WITH CLEANUP LOGIC) ---