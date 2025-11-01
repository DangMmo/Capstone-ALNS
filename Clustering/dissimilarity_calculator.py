import pandas as pd
import numpy as np
import time

# Import cac module da tao
import config
from utils import calculate_travel_time, get_coords

def _calculate_std_pdd_for_pair(customer_i, customer_j):
    """
    Ham noi bo de tinh gia tri khac biet STD-PDD cho mot cap khach hang.
    
    Args:
        customer_i (pd.Series): Dong du lieu cua khach hang i.
        customer_j (pd.Series): Dong du lieu cua khach hang j.

    Returns:
        float: Gia tri khac biet.
    """
    coords_i = get_coords(customer_i)
    coords_j = get_coords(customer_j)

    # --- 1. Thanh phan Khong gian (Spatial) ---
    spatial_component = np.sqrt((coords_i[0] - coords_j[0])**2 + (coords_i[1] - coords_j[1])**2)

    # --- 2. Thanh phan Thoi gian (Temporal) ---
    # Thoi gian di chuyen giua hai khach hang (su dung xe SE)
    travel_time_ij = calculate_travel_time(coords_i, coords_j, config.SE_VEHICLE_SPEED)

    # f_ij: Do linh hoat toi da ve thoi gian khi di tu i -> j
    f_ij = customer_j['effective_latest'] - (customer_i['Early'] + customer_i['Service Time'] + travel_time_ij)
    
    # h_ij: Thoi gian cho doi toi thieu khi di tu i -> j
    # Luu y: effective_latest cua i duoc su dung de tinh thoi gian cho
    h_ij = max(0, customer_j['Early'] - (customer_i['effective_latest'] + customer_i['Service Time'] + travel_time_ij))
    
    # Tinh toan muc phat thoi gian
    temporal_penalty = (f_ij - h_ij) / config.MAX_SCHEDULING_FLEXIBILITY
    
    # --- 3. Thanh phan Nhu cau (Demand) ---
    demand_penalty = (abs(customer_i['Demand']) + abs(customer_j['Demand'])) / config.SE_VEHICLE_CAPACITY

    # --- Ket hop theo cong thuc cua Kerscher & Minner ---
    # Dissimilarity = S * (2 - Temporal_Flexibility + Relative_Demand)
    # Temporal_Flexibility duoc chuan hoa, Relative_Demand duoc chuan hoa
    # So 2 la mot he so de dam bao gia tri luon duong
    dissimilarity = spatial_component * (2 - temporal_penalty + demand_penalty)
    
    return dissimilarity


def create_dissimilarity_matrix(customers_df):
    """
    Tao ma tran khac biet NxN cho tat ca cac khach hang.
    
    Args:
        customers_df (pd.DataFrame): DataFrame khach hang da duoc tien xu ly.

    Returns:
        np.ndarray: Ma tran khac biet doi xung.
    """
    print("\nBat dau tinh toan ma tran khac biet...")
    start_time = time.time()
    
    num_customers = len(customers_df)
    dissimilarity_matrix = np.zeros((num_customers, num_customers))

    # Chuyen DataFrame sang list of dicts de truy cap nhanh hon trong vong lap
    customers_list = customers_df.to_dict('records')

    for i in range(num_customers):
        for j in range(i, num_customers): # Chi tinh toan nua tren cua ma tran
            if i == j:
                dissimilarity_matrix[i, j] = 0
            else:
                customer_i = customers_list[i]
                customer_j = customers_list[j]

                # Tinh toan theo hai chieu i->j va j->i
                std_ij = _calculate_std_pdd_for_pair(customer_i, customer_j)
                std_ji = _calculate_std_pdd_for_pair(customer_j, customer_i)
                
                # Doi xung hoa ma tran bang cach lay gia tri nho hon
                value = min(std_ij, std_ji)
                dissimilarity_matrix[i, j] = value
                dissimilarity_matrix[j, i] = value
    
    end_time = time.time()
    print(f"Hoan thanh tinh toan ma tran trong {end_time - start_time:.2f} giay.")
    
    return dissimilarity_matrix