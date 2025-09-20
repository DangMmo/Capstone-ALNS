from Parser import ProblemInstance
from InitialSolution import construct_initial_solution

def main():
    # Chọn file dữ liệu bạn muốn chạy
    # file_name = r"C:\path\to\your\data\CS_1_D.csv"
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\C_100_1_TD.csv" # Sử dụng file A_100_1_LD.csv
    
    # 1. Tải và phân tích dữ liệu
    problem = ProblemInstance(file_name)
    
    # 2. Xây dựng lời giải ban đầu
    initial_solution = construct_initial_solution(problem)
    
    # 3. In kết quả để kiểm tra
    print("\n--- KET QUA LOI GIAI BAN DAU ---")
    print(f"Tong chi phi: {initial_solution.total_cost:.2f}")
    print(f"So tuyen FE: {len(initial_solution.fe_routes)}")
    print(f"So tuyen SE: {len(initial_solution.se_routes)}")
    
    print("\nChi tiet cac tuyen FE:")
    for i, route in enumerate(initial_solution.fe_routes):
        print(f"  FE Route {i+1}: {route}")
        
    print("\nChi tiet cac tuyen SE (5 tuyen dau tien):")
    for i, route in enumerate(initial_solution.se_routes[:5]):
        print(f"  SE Route {i+1}: {route}")

if __name__ == "__main__":
    main()