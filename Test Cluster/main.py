# --- START OF FILE main_flexible.py ---
from Parser import ProblemInstance
from manual_clustering import perform_manual_clustering
# <<< THAY ĐỔI: Import hàm hợp nhất >>>
from SolutionBuilder import construct_solution

def main():
    # Chọn file dữ liệu
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\B_100_10_TD.csv"
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_2_D.csv"

    problem = ProblemInstance(file_name)
    
    # ==========================================================
    # ==            BẢNG ĐIỀU KHIỂN CỦA BẠN                  ==
    # ==========================================================
    
    # 1. Nhập số cụm mong muốn
    K_VALUE = 7 # <-- THAY ĐỔI Ở ĐÂY 
    
    # 2. Quyết định có sử dụng deadline hay không (True hoặc False)
    CONSIDER_DEADLINE = True # <-- THAY ĐỔI Ở ĐÂY
    
    # ==========================================================

    # --- BƯỚC 1: PHÂN CỤM THỦ CÔNG ---
    print(f"\n--- GIAI DOAN 1: THUC HIEN PHAN CUM VOI K = {K_VALUE} ---")
    clusters = perform_manual_clustering(problem, K_VALUE)
    
    if clusters is None:
        print("\nQua trinh phan cum that bai. Dung chuong trinh.")
        return
        
    print("\n--- CHI TIET CAC CUM DA TAO ---")
    for i, cluster in enumerate(clusters):
        print(f"  Cum {i+1}: {len(cluster)} khach hang")

    # --- BƯỚC 2: XÂY DỰNG LỜI GIẢI THEO LỰA CHỌN ---
    # <<< THAY ĐỔI: Truyền biến CONSIDER_DEADLINE vào hàm >>>
    final_solution = construct_solution(problem, clusters, use_deadline=CONSIDER_DEADLINE)
    
    # --- BƯỚC 3: IN KẾT QUẢ CUỐI CÙNG ---
    deadline_status_str = "CO XET DEADLINE" if CONSIDER_DEADLINE else "KHONG XET DEADLINE"
    print(f"\n\n--- KET QUA LOI GIAI HOAN CHINH ({deadline_status_str}) ---")
    print(f"Tong chi phi: {final_solution.total_cost:.2f}")
    print(f"So tuyen FE: {len(final_solution.fe_routes)}")
    print(f"So tuyen SE: {len(final_solution.se_routes)}")
    
    num_unserved = len(final_solution.unserved_customers)
    if num_unserved > 0:
        print(f"So khach hang khong the phuc vu: {num_unserved}")
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

# --- END OF FILE main_flexible.py ---