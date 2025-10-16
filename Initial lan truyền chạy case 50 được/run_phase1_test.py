# --- START OF FILE run_phase1_test.py (UPDATED) ---

from Parser import ProblemInstance
from Heuristics import create_integrated_initial_solution

def main():
    """
    Ham chinh de tai instance, xay dung loi giai ban dau,
    va in ra ket qua chi tiet.
    """
    # Thay doi duong dan file cua ban o day
    file_path = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\C_100_10_TD.csv"
    
    try:
        problem = ProblemInstance(file_path=file_path)
    except FileNotFoundError:
        print(f"LOI: Khong tim thay file '{file_path}'. Vui long kiem tra lai duong dan.")
        return

    # Goi ham de xay dung loi giai ban dau
    initial_state = create_integrated_initial_solution(problem)
    
    # In ra ket qua tom tat
    solution = initial_state.solution
    print("\n" + "="*50)
    print("--- KET QUA LOI GIAI BAN DAU ---")
    print("="*50)
    
    num_fe_routes = len(solution.fe_routes)
    num_se_routes = len(solution.se_routes)
    total_cost = solution.calculate_total_cost()
    
    print(f"- Tong so tuyen FE (cap 1): {num_fe_routes}")
    print(f"- Tong so tuyen SE (cap 2): {num_se_routes}")
    print(f"- Tong chi phi (quang duong): {total_cost:.2f}")
    
    # --- CAI TIEN: In ra toan bo cac tuyen de theo doi ---
    
    print("\n" + "-"*20 + " DANH SACH CAC TUYEN SE (CAP 2) " + "-"*20)
    if not solution.se_routes:
        print("Khong co tuyen SE nao.")
    else:
        for i, se_route in enumerate(solution.se_routes):
            print(f"\n[SE Route #{i+1}]")
            print(se_route)
            serving_fes = list(se_route.serving_fe_routes)
            if serving_fes:
                # Tim index cua FE route trong danh sach tong the
                fe_route_index = solution.fe_routes.index(serving_fes[0])
                print(f"  -> Duoc phuc vu boi: FE Route #{fe_route_index + 1}")
            else:
                print("  -> CANH BAO: Tuyen SE nay chua duoc FE route nao phuc vu!")

    print("\n" + "-"*20 + " DANH SACH CAC TUYEN FE (CAP 1) " + "-"*20)
    if not solution.fe_routes:
        print("Khong co tuyen FE nao.")
    else:
        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n[FE Route #{i+1}]")
            print(fe_route)
            if fe_route.serviced_se_routes:
                # Tim index cua cac SE route duoc phuc vu
                serviced_indices = [solution.se_routes.index(se) + 1 for se in fe_route.serviced_se_routes]
                print(f"  -> Dang phuc vu cac SE Routes: {serviced_indices}")
            else:
                print("  -> Tuyen FE nay khong phuc vu tuyen SE nao.")

    print("\n" + "="*50)


if __name__ == "__main__":
    main()

# --- END OF FILE run_phase1_test.py (UPDATED) ---