# --- START OF FILE manual_clustering.py ---

import numpy as np
import kmedoids
import math

def calculate_std_dissimilarity(cust_i, cust_j, problem):
    """
    Tính toán độ khác biệt Spatial-Temporal-Demand (STD) giữa hai khách hàng.
    (Hàm này được giữ nguyên, không thay đổi so với file gốc)
    """
    spatial_dist = problem.get_distance(cust_i.id, cust_j.id)
    travel_time = spatial_dist
    
    # f_ij: Tính linh hoạt về lịch trình. Giá trị âm nghĩa là không khả thi.
    f_ij = cust_j.due_time - (cust_i.ready_time + cust_i.service_time + travel_time)
    if f_ij < 0: 
        return float('inf')  # Trả về vô cực nếu không thể đi từ i đến j
    
    # h_ij: Thời gian chờ đợi lãng phí tối thiểu
    h_ij = max(0, cust_j.ready_time - (cust_i.due_time + cust_i.service_time + travel_time))
    
    # scheduling_horizon: Khung thời gian hoạt động để chuẩn hóa
    scheduling_horizon = max(1, problem.depot.due_time if hasattr(problem.depot, 'due_time') else 900)
    
    # Tính các thành phần của hệ số phạt
    temporal_term = (f_ij - h_ij) / scheduling_horizon
    demand_term = (cust_i.demand + cust_j.demand) / problem.se_vehicle_capacity
    
    penalty_multiplier = max(0.1, 2.0 - temporal_term + demand_term)
    return spatial_dist * penalty_multiplier

def perform_manual_clustering(problem, num_clusters):
    """
    Thực hiện phân cụm khách hàng với số lượng cụm K do người dùng chỉ định.

    Args:
        problem (ProblemInstance): Đối tượng bài toán chứa danh sách khách hàng.
        num_clusters (int): Số lượng cụm (K) mong muốn.

    Returns:
        Một danh sách các cụm, mỗi cụm là một danh sách các đối tượng khách hàng.
        Trả về None nếu đầu vào không hợp lệ.
    """
    all_customers = problem.customers
    num_customers = len(all_customers)
    
    print(f"--- BAT DAU QUA TRINH PHAN CUM THU CONG VOI K = {num_clusters} ---")
    
    # --- 1. KIỂM TRA TÍNH HỢP LỆ CỦA ĐẦU VÀO ---
    if not isinstance(num_clusters, int) or num_clusters <= 0:
        print(f"Lỗi: Số cụm ({num_clusters}) phải là một số nguyên dương.")
        return None
    if num_customers == 0:
        print("Không có khách hàng nào để phân cụm.")
        return []
    if num_clusters > num_customers:
        print(f"Lỗi: Số cụm ({num_clusters}) không thể lớn hơn số khách hàng ({num_customers}).")
        return None
    if num_clusters == 1:
        print("Số cụm là 1, trả về tất cả khách hàng trong một cụm duy nhất.")
        return [all_customers]

    # --- 2. TÍNH TOÁN MA TRẬN DỊ BIỆT (Giữ nguyên) ---
    print(f"  2a: Tao ma tran di biet STD {num_customers}x{num_customers}...")
    dissimilarity_matrix = np.zeros((num_customers, num_customers))
    for i in range(num_customers):
        for j in range(i + 1, num_customers):
            score_ij = calculate_std_dissimilarity(all_customers[i], all_customers[j], problem)
            score_ji = calculate_std_dissimilarity(all_customers[j], all_customers[i], problem)
            dissimilarity_matrix[i, j] = dissimilarity_matrix[j, i] = min(score_ij, score_ji)

    # Xử lý các giá trị vô cực
    if np.any(np.isinf(dissimilarity_matrix)):
        max_finite_val = np.max(dissimilarity_matrix[np.isfinite(dissimilarity_matrix)], initial=1000)
        dissimilarity_matrix[np.isinf(dissimilarity_matrix)] = max_finite_val * 10
    
    np.fill_diagonal(dissimilarity_matrix, 0)

    # --- 3. THỰC HIỆN PHÂN CỤM VỚI K ĐÃ CHO ---
    # <<< THAY ĐỔI CHÍNH: Bỏ hoàn toàn phần tìm K tối ưu bằng Silhouette Score >>>
    print(f"  2b: Phan cum {num_customers} KH vao {num_clusters} cum su dung K-Medoids...")
    
    # Sử dụng trực tiếp giá trị `num_clusters` từ input
    clusterer = kmedoids.KMedoids(n_clusters=num_clusters, method='fasterpam', random_state=42)
    labels = clusterer.fit_predict(dissimilarity_matrix)
    
    # --- 4. TẠO DANH SÁCH CÁC CỤM (Giữ nguyên) ---
    clusters = [[] for _ in range(num_clusters)]
    for i, label in enumerate(labels):
        clusters[label].append(all_customers[i])
        
    print("  Phan cum hoan tat.")
    return clusters

# --- END OF FILE manual_clustering.py ---