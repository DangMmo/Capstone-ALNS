# --- START OF FILE main_flexible.py ---

from Parser import ProblemInstance
from manual_clustering import perform_manual_clustering
from SolutionBuilder import construct_solution

def main():
    # Chọn file dữ liệu
    # file_name = "CS_1_D.csv"
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\C_100_5_TD.csv"
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_2_D.csv"

    try:
        problem = ProblemInstance(file_name)
    except FileNotFoundError:
        print(f"LOI: Khong tim thay file '{file_name}'. Vui long dat file CSV vao cung thu muc.")
        return
    
    # ==========================================================
    # ==            BẢNG ĐIỀU KHIỂN CỦA BẠN                  ==
    # ==========================================================
    
    # 1. Nhập số cụm mong muốn
    K_VALUE = 7  # <-- Thay đổi số cụm mong muốn ở đây
    
    # 2. Số vòng lặp LNS để tối ưu các tuyến SE trong mỗi cụm.
    #    Đặt bằng 0 để chạy thuật toán xây dựng đơn giản (không có LNS).
    #    Giá trị đề xuất: 100-1000 để thấy sự cải thiện.
    LNS_ITERATIONS_PER_CLUSTER = 5 # <-- Thay đổi số vòng lặp LNS ở đây

    # 3. Quyết định có sử dụng deadline như ràng buộc cứng hay không
    CONSIDER_DEADLINE = True
    
    # ==========================================================

    print(f"\n--- GIAI DOAN 1: THUC HIEN PHAN CUM VOI K = {K_VALUE} ---")
    clusters = perform_manual_clustering(problem, K_VALUE)
    
    if clusters is None:
        print("\nQua trinh phan cum that bai. Dung chuong trinh.")
        return
        
    print("\n--- CHI TIET CAC CUM DA TAO ---")
    for i, cluster in enumerate(clusters):
        print(f"  Cum {i+1}: {len(cluster)} khach hang")

    # Gọi hàm xây dựng giải pháp với tham số LNS
    final_solution = construct_solution(problem, clusters, 
                                        use_deadline=CONSIDER_DEADLINE,
                                        lns_iterations=LNS_ITERATIONS_PER_CLUSTER)
    
    deadline_status_str = "CO XET DEADLINE (RANG BUOC CUNG)" if CONSIDER_DEADLINE else "KHONG XET DEADLINE"
    print(f"\n\n--- KET QUA LOI GIAI HOAN CHINH ({deadline_status_str}) ---")
    
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

# --- END OF FILE main_flexible.py ---