# --- START OF FILE main_cluster_first.py ---

from Parser import ProblemInstance
from DataStructures import Solution
from manual_clustering import perform_manual_clustering
# <<< THAY DOI: Import cac ham moi/duoc tai cau truc tu SolutionBuilder
from SolutionBuilder import solve_sub_problem, _rescue_unserved_customers_globally

def main():
    # Chon file du lieu
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_5_TD.csv"
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_2_D.csv"

    # ==========================================================
    # ==            BANG DIEU KHIEN CUA BAN                  ==
    # ==========================================================
    
    # 1. Nhập số cụm mong muốn
    K_VALUE = 6

    # 2. Cấu hình các tham số cho quá trình giải quyết từng cụm
    LNS_ITERATIONS_PER_CLUSTER = 50

    # 3. Quyết định có sử dụng deadline như ràng buộc cứng hay không
    CONSIDER_DEADLINE = True
    # 4. Tốc độ xe (mét/phút)    
    VEHICLE_SPEED_METERS_PER_MINUTE = 1.0
        
    # 5. <<< MỚI: Chiến lược vận hành của xe FE >>>
    # True: Xe FE có thể vừa giao hàng, vừa lấy hàng trong cùng 1 chuyến (CPD).
    # False: Tách biệt, xe FE chỉ đi giao hoặc chỉ đi lấy hàng (SPD).
    SIMULTANEOUS_FE_PU_DEL = True
        
    # True: Nhu cầu của 1 vệ tinh có thể được phục vụ bởi nhiều xe FE.
    # False: Nhu cầu của 1 vệ tinh phải được phục vụ bởi duy nhất 1 xe FE.
    # LƯU Ý: Logic hiện tại chỉ hỗ trợ ALLOW_FE_SPLIT = False.
    ALLOW_FE_SPLIT = False # Logic hien tai chi ho tro False
    # ==========================================================

    try:
        problem = ProblemInstance(file_name, vehicle_speed=VEHICLE_SPEED_METERS_PER_MINUTE)
    except FileNotFoundError:
        print(f"LOI: Khong tim thay file '{file_name}'.")
        return
    
    # --- GIAI DOAN 1: PHAN CUM KHACH HANG ---
    print(f"\n--- GIAI DOAN 1: THUC HIEN PHAN CUM VOI K = {K_VALUE} ---")
    clusters = perform_manual_clustering(problem, K_VALUE)
    
    if clusters is None:
        print("\nQua trinh phan cum that bai. Dung chuong trinh.")
        return
        
    print("\n--- CHI TIET CAC CUM DA TAO ---")
    for i, cluster in enumerate(clusters):
        print(f"  Cum {i+1}: {len(cluster)} khach hang")

    # --- GIAI DOAN 2: GIAI QUYET TUNG CUM MOT CACH DOC LAP ---
    print("\n--- GIAI DOAN 2: GIAI QUYET TUNG BAI TOAN CON (CUM) ---")
    
    final_solution = Solution(problem)
    # Tao mot danh sach de thu thap tat ca KH khong duoc phuc vu tu cac cum
    global_unserved_customers = []

    for i, cluster in enumerate(clusters):
        print(f"\n--- Dang xu ly Cum {i+1}/{len(clusters)} ---")
        if not cluster:
            print("  Cum rong, bo qua.")
            continue

        # Goi ham giai quyet bai toan con cho cum hien tai
        sub_fe_routes, sub_se_routes, sub_unserved = solve_sub_problem(
            problem, 
            cluster, 
            lns_iterations=LNS_ITERATIONS_PER_CLUSTER,
            use_deadline=CONSIDER_DEADLINE,
            simultaneous_fe_pu_del=SIMULTANEOUS_FE_PU_DEL,
            allow_fe_split=ALLOW_FE_SPLIT
        )
        
        # Tong hop ket qua cua bai toan con vao giai phap cuoi cung
        final_solution.fe_routes.extend(sub_fe_routes)
        final_solution.se_routes.extend(sub_se_routes)
        global_unserved_customers.extend(sub_unserved)
        
        print(f"  => Cum {i+1} hoan tat: Tao {len(sub_fe_routes)} tuyen FE, {len(sub_se_routes)} tuyen SE. Co {len(sub_unserved)} KH chua duoc phuc vu.")

    # --- GIAI DOAN 3: GIAI CUU LIEN CUM (GLOBAL RESCUE) ---
    print(f"\n--- GIAI DOAN 3: GIAI CUU {len(global_unserved_customers)} KH CHUA DUOC PHUC VU TREN TOAN BAI TOAN ---")
    # Thu chen nhung KH con sot vao BAT KY tuyen SE nao da duoc tao ra
    _rescue_unserved_customers_globally(global_unserved_customers, final_solution.se_routes)

    # Cap nhat danh sach KH khong duoc phuc vu cuoi cung
    final_solution.unserved_customers = global_unserved_customers
    
    # Tinh toan chi phi tong the
    final_solution.calculate_total_cost_and_time()
    
    # --- KET QUA ---
    deadline_status_str = "CO XET DEADLINE (RANG BUOC CUNG)" if CONSIDER_DEADLINE else "KHONG XET DEADLINE"
    fe_strategy_str = "FE Giao-Lay dong thoi (CPD)" if SIMULTANEOUS_FE_PU_DEL else "FE Giao-Lay tach biet (SPD)"
    
    print(f"\n\n--- KET QUA LOI GIAI HOAN CHINH ({deadline_status_str}, {fe_strategy_str}) ---")
    
    print(f"Tong chi phi (quang duong): {final_solution.total_cost:.2f} m")
    print(f"Tong thoi gian hoat dong: {final_solution.total_time:.2f} min")
    
    print(f"So tuyen FE: {len(final_solution.fe_routes)}")
    print(f"So tuyen SE: {len(final_solution.se_routes)}")
    
    num_unserved = len(final_solution.unserved_customers)
    if num_unserved > 0:
        print(f"So khach hang khong the phuc vu: {num_unserved}")
        print(f"  Danh sach ID: {[c.id for c in final_solution.unserved_customers]}")
    else:
        print("Trang thai: Da phuc vu tat ca khach hang.")
    
    print("\nChi tiet cac tuyen FE:")
    for i, route in enumerate(final_solution.fe_routes):
        print(f"\n[FE Route {i+1}]")
        print(route)
        
    print("\nChi tiet cac tuyen SE:")
    for i, route in enumerate(final_solution.se_routes):
        print(f"\n[SE Route {i+1}]")
        print(route)

if __name__ == "__main__":
    main()
# --- END OF FILE main_cluster_first.py ---