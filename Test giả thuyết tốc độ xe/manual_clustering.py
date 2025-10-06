# --- START OF FILE manual_clustering.py ---

import numpy as np
import kmedoids
import math

def calculate_std_dissimilarity(cust_i, cust_j, problem):
    """
    Tính toán độ khác biệt Spatial-Temporal-Demand (STD) giữa hai khách hàng.
    *** PHIÊN BẢN ĐÃ CẬP NHẬT SỬ DỤNG TỐC ĐỘ XE ***
    """
    spatial_dist = problem.get_distance(cust_i.id, cust_j.id)
    # <<< THAY ĐỔI: travel_time được tính từ tốc độ >>>
    travel_time = problem.get_travel_time(cust_i.id, cust_j.id)
    
    f_ij = cust_j.due_time - (cust_i.ready_time + cust_i.service_time + travel_time)
    if f_ij < 0: 
        return float('inf')
    
    h_ij = max(0, cust_j.ready_time - (cust_i.due_time + cust_i.service_time + travel_time))
    
    # scheduling_horizon: Khung thời gian hoạt động (ví dụ 900 phút ~ 15 giờ)
    scheduling_horizon = 900
    
    temporal_term = (f_ij - h_ij) / scheduling_horizon
    demand_term = (cust_i.demand + cust_j.demand) / problem.se_vehicle_capacity
    
    penalty_multiplier = max(0.1, 2.0 - temporal_term + demand_term)
    # Chi phí vẫn dựa trên khoảng cách, nhưng penalty bị ảnh hưởng bởi thời gian
    return spatial_dist * penalty_multiplier

def perform_manual_clustering(problem, num_clusters):
    all_customers = problem.customers
    num_customers = len(all_customers)
    
    print(f"--- BAT DAU QUA TRINH PHAN CUM THU CONG VOI K = {num_clusters} ---")
    
    if not isinstance(num_clusters, int) or num_clusters <= 0:
        print(f"Loi: So cum ({num_clusters}) phai la mot so nguyen duong.")
        return None
    if num_customers == 0:
        print("Khong co khach hang nao de phan cum.")
        return []
    if num_clusters > num_customers:
        print(f"Loi: So cum ({num_clusters}) khong the lon hon so khach hang ({num_customers}).")
        return None
    if num_clusters == 1:
        print("So cum la 1, tra ve tat ca khach hang trong mot cum duy nhat.")
        return [all_customers]

    print(f"  B1: Tao ma tran di biet STD {num_customers}x{num_customers}...")
    dissimilarity_matrix = np.zeros((num_customers, num_customers))
    for i in range(num_customers):
        for j in range(i + 1, num_customers):
            score_ij = calculate_std_dissimilarity(all_customers[i], all_customers[j], problem)
            score_ji = calculate_std_dissimilarity(all_customers[j], all_customers[i], problem)
            dissimilarity_matrix[i, j] = dissimilarity_matrix[j, i] = min(score_ij, score_ji)

    if np.any(np.isinf(dissimilarity_matrix)):
        max_finite_val = np.max(dissimilarity_matrix[np.isfinite(dissimilarity_matrix)], initial=1000)
        dissimilarity_matrix[np.isinf(dissimilarity_matrix)] = max_finite_val * 10
    
    np.fill_diagonal(dissimilarity_matrix, 0)

    print(f"  B2: Phan cum {num_customers} KH vao {num_clusters} cum su dung K-Medoids...")
    clusterer = kmedoids.KMedoids(n_clusters=num_clusters, method='fasterpam', random_state=42)
    labels = clusterer.fit_predict(dissimilarity_matrix)
    
    clusters = [[] for _ in range(num_clusters)]
    for i, label in enumerate(labels):
        clusters[label].append(all_customers[i])
        
    print("  Phan cum hoan tat.")
    return clusters

# --- END OF FILE manual_clustering.py ---