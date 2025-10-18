# --- START OF FILE debug_single_insertion.py ---

# Import các thành phần cần thiết
from problem_parser import ProblemInstance
from data_structures import SERoute, FERoute
from insertion_logic import _recalculate_fe_route_and_check_feasibility

def main():
    # --- CẤU HÌNH ---
    file_path = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_10_TD.csv"
    
    # Lấy khách hàng đầu tiên để thử
    CUSTOMER_ID_TO_TEST = 61 # ID từ log của bạn
    
    # --- THỰC THI ---
    print("--- Bat dau kich ban debug don gian ---")
    try:
        problem = ProblemInstance(file_path=file_path)
    except Exception as e:
        print(f"Loi khi tai instance: {e}"); return

    customer = problem.node_objects.get(CUSTOMER_ID_TO_TEST)
    if not customer:
        print(f"Khong tim thay khach hang voi ID {CUSTOMER_ID_TO_TEST}"); return
        
    print(f"Dang thu nghiem chen khach hang: {customer}")
    print(f"  -> Ready Time: {customer.ready_time}, Due Time: {customer.due_time}")
    if hasattr(customer, 'deadline'):
        print(f"  -> Deadline: {customer.deadline}")

    found_feasible_option = False

    # Lặp qua tất cả các satellite để thử tạo tuyến mới
    for satellite in problem.satellites:
        print(f"\n--- Dang thu voi Satellite {satellite.id} ---")

        # 1. Tạo một SERoute mới chỉ chứa khách hàng này
        temp_se = SERoute(satellite, problem)
        
        # In trạng thái SERoute trước khi chèn
        # print("  SERoute truoc khi chen:")
        # print(temp_se)

        is_se_insert_ok = temp_se.insert_customer_at_pos(customer, 1)
        
        if not is_se_insert_ok:
            print("  [KET QUA] -> THAT BAI: insert_customer_at_pos tra ve False.")
            print("     Ly do: Khach hang vi pham time window ngay trong tuyen SE don le.")
            print("     Thoi gian bat dau cua SE route:", temp_se.service_start_times[temp_se.nodes_id[0]])
            print("     Chi tiet tuyen SE sau khi chen (that bai):")
            print(temp_se)
            continue
        
        print("  -> Chen vao SERoute thanh cong. Tinh toan FE route...")
        
        # 2. Tạo một FERoute mới chỉ phục vụ SERoute này
        temp_fe = FERoute(problem)
        temp_fe.add_serviced_se_route(temp_se)
        
        # 3. Gọi hàm kiểm tra khả thi
        new_fe_cost, is_fe_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe, problem)
        
        if is_fe_feasible:
            print(f"  [KET QUA] -> THANH CONG! Tinh kha thi la TRUE.")
            print(f"     FE Cost: {new_fe_cost:.2f}, SE Cost: {temp_se.total_dist:.2f}")
            print("     Chi tiet tuyen FE:")
            print(temp_fe)
            found_feasible_option = True
            # break # Thoát ngay khi tìm thấy phương án khả thi đầu tiên
        else:
            print(f"  [KET QUA] -> THAT BAI: _recalculate_fe_route_and_check_feasibility tra ve False.")

    print("\n--- TONG KET DEBUG ---")
    if found_feasible_option:
        print("Co it nhat mot phuong an kha thi duoc tim thay.")
    else:
        print("KHONG TIM THAY PHUONG AN KHA THI NAO. Day la nguyen nhan loi chi phi 0.00.")

if __name__ == "__main__":
    main()

# --- END OF FILE debug_single_insertion.py ---