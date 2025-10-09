# --- START OF FILE verify_feasibility.py ---

import math
from Parser import ProblemInstance 

def verify_customer_feasibility(problem):
    print("\n--- Bat dau kiem tra tinh kha thi cua khach hang (DA XET TOC DO) ---")
    impossible_customers = []
    delivery_customers = [c for c in problem.customers if c.type == 'DeliveryCustomer']
    
    if not delivery_customers:
        print("Khong tim thay DeliveryCustomer nao de kiem tra.")
        return

    print(f"Tim thay {len(delivery_customers)} khach hang giao hang. Dang kiem tra...")

    for customer in delivery_customers:
        if not problem.satellites:
            print("Loi: Khong co ve tinh nao trong file du lieu.")
            return

        closest_satellite = min(problem.satellites, key=lambda s: problem.get_distance(s.id, customer.id))
        
        # <<< THAY ĐỔI: Tính thời gian di chuyển thay vì khoảng cách >>>
        time_depot_to_sat = problem.get_travel_time(problem.depot.id, closest_satellite.id)
        time_sat_to_cust = problem.get_travel_time(closest_satellite.id, customer.id)
        
        min_travel_time = time_depot_to_sat + time_sat_to_cust
        
        if min_travel_time > customer.due_time:
            impossible_customers.append({
                "id": customer.id,
                "due_time": customer.due_time,
                "min_travel_time": min_travel_time,
                "closest_satellite": closest_satellite.id
            })

    if impossible_customers:
        print("\n--- KET QUA: Phat hien cac khach hang BAT KHA THI ve mat thoi gian ---")
        print(f"Tong so: {len(impossible_customers)} / {len(delivery_customers)} khach hang giao hang.")
        print("-" * 70)
        header = f"{'Customer ID':<15} | {'Due Time (phut)':<16} | {'Min Travel Time (phut)':<24} | {'Closest Sat ID':<15}"
        print(header)
        print("-" * 70)
        for c in impossible_customers:
            print(f"{c['id']:<15} | {c['due_time']:<16.2f} | {c['min_travel_time']:<24.2f} | {c['closest_satellite']:<15}")
        print("-" * 70)
    else:
        print("\n--- KET QUA: Tat ca khach hang giao hang deu kha thi ve mat thoi gian di chuyen toi thieu. ---")

def main():
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_2_D.csv"
    problem = ProblemInstance(file_name)
    verify_customer_feasibility(problem)

if __name__ == "__main__":
    main()
# --- END OF FILE verify_feasibility.py ---