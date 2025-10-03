# --- START OF FILE verify_feasibility.py ---

import math
from Parser import ProblemInstance 

def verify_customer_feasibility(problem):
    """
    Duyệt qua tất cả khách hàng để kiểm tra xem họ có khả thi về mặt vật lý hay không.
    Một khách hàng được coi là "bất khả thi" nếu thời gian di chuyển tối thiểu từ
    kho đến tay họ đã lớn hơn thời gian muộn nhất họ yêu cầu (due_time).
    """
    print("\n--- Bat dau kiem tra tinh kha thi cua khach hang ---")
    
    impossible_customers = []
    
    # Chỉ cần kiểm tra DeliveryCustomers, vì chỉ họ mới có hàng đi từ kho
    delivery_customers = [c for c in problem.customers if c.type == 'DeliveryCustomer']
    
    if not delivery_customers:
        print("Khong tim thay DeliveryCustomer nao de kiem tra.")
        return

    print(f"Tim thay {len(delivery_customers)} khach hang giao hang. Dang kiem tra...")

    for customer in delivery_customers:
        # Với mỗi khách hàng, tìm vệ tinh gần họ nhất
        if not problem.satellites:
            print("Loi: Khong co ve tinh nao trong file du lieu.")
            return

        closest_satellite = min(problem.satellites, 
                                key=lambda s: problem.get_distance(s.id, customer.id))
        
        # Tính thời gian di chuyển tối thiểu (bỏ qua mọi service time và waiting time)
        # T = T(depot -> satellite) + T(satellite -> customer)
        time_depot_to_sat = problem.get_distance(problem.depot.id, closest_satellite.id)
        time_sat_to_cust = problem.get_distance(closest_satellite.id, customer.id)
        
        min_travel_time = time_depot_to_sat + time_sat_to_cust
        
        # So sánh với due_time của khách hàng
        if min_travel_time > customer.due_time:
            impossible_customers.append({
                "id": customer.id,
                "due_time": customer.due_time,
                "min_travel_time": min_travel_time,
                "closest_satellite": closest_satellite.id
            })

    # In kết quả
    if impossible_customers:
        print("\n--- KET QUA: Phat hien cac khach hang BAT KHA THI ve mat thoi gian ---")
        print(f"Tong so: {len(impossible_customers)} / {len(delivery_customers)} khach hang giao hang.")
        print("-" * 70)
        header = f"{'Customer ID':<15} | {'Due Time':<12} | {'Min Travel Time':<20} | {'Closest Sat ID':<15}"
        print(header)
        print("-" * 70)
        for c in impossible_customers:
            print(f"{c['id']:<15} | {c['due_time']:<12.2f} | {c['min_travel_time']:<20.2f} | {c['closest_satellite']:<15}")
        print("-" * 70)
    else:
        print("\n--- KET QUA: Tat ca khach hang giao hang deu kha thi ve mat thoi gian di chuyen toi thieu. ---")


def main():
    # Sử dụng file dữ liệu lớn của bạn
    #file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_1_D.csv"
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_10_TD.csv"

    problem = ProblemInstance(file_name)
    verify_customer_feasibility(problem)


if __name__ == "__main__":
    main()