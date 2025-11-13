# --- START OF FILE clustering/dissimilarity_calculator.py ---

import pandas as pd
import numpy as np
import time

import config
from utils.utils import calculate_travel_time, get_coords

def _calculate_std_pdd_for_pair(customer_i, customer_j):
    """
    Ham noi bo de tinh gia tri khac biet STD-PDD cho mot cap khach hang.
    """
    coords_i = get_coords(customer_i)
    coords_j = get_coords(customer_j)

    # --- 1. Thanh phan Khong gian (Spatial) ---
    spatial_component = np.sqrt((coords_i[0] - coords_j[0])**2 + (coords_i[1] - coords_j[1])**2)

    # --- 2. Thanh phan Thoi gian (Temporal) ---
    
    # <<< SỬA LỖI TẠI ĐÂY: SE_VEHICLE_SPEED -> VEHICLE_SPEED >>>
    travel_time_ij = calculate_travel_time(coords_i, coords_j, config.VEHICLE_SPEED)

    f_ij = customer_j['effective_latest'] - (customer_i['Early'] + customer_i['Service Time'] + travel_time_ij)
    h_ij = max(0, customer_j['Early'] - (customer_i['effective_latest'] + customer_i['Service Time'] + travel_time_ij))
    
    temporal_penalty = (f_ij - h_ij) / config.MAX_SCHEDULING_FLEXIBILITY
    
    # --- 3. Thanh phan Nhu cau (Demand) ---
    demand_penalty = (abs(customer_i['Demand']) + abs(customer_j['Demand'])) / config.SE_VEHICLE_CAPACITY

    # --- Ket hop theo cong thuc ---
    # (Loại bỏ các trọng số W_* không còn trong config mới để đơn giản hóa)
    dissimilarity = spatial_component * (2 - temporal_penalty + demand_penalty)
    
    return dissimilarity


def create_dissimilarity_matrix(customers_df):
    """
    Tao ma tran khac biet NxN cho tat ca cac khach hang.
    """
    print("\nBat dau tinh toan ma tran khac biet...")
    start_time = time.time()
    
    num_customers = len(customers_df)
    dissimilarity_matrix = np.zeros((num_customers, num_customers))

    customers_list = customers_df.to_dict('records')

    for i in range(num_customers):
        for j in range(i, num_customers):
            if i == j:
                dissimilarity_matrix[i, j] = 0
            else:
                customer_i = customers_list[i]
                customer_j = customers_list[j]

                std_ij = _calculate_std_pdd_for_pair(customer_i, customer_j)
                std_ji = _calculate_std_pdd_for_pair(customer_j, customer_i)
                
                value = min(std_ij, std_ji)
                dissimilarity_matrix[i, j] = value
                dissimilarity_matrix[j, i] = value
    
    end_time = time.time()
    print(f"Hoan thanh tinh toan ma tran trong {end_time - start_time:.2f} giay.")
    
    return dissimilarity_matrix
# --- END OF FILE clustering/dissimilarity_calculator.py ---