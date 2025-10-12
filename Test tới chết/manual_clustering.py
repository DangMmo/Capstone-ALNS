# --- START OF FILE manual_clustering.py (UPGRADED VERSION) ---

import numpy as np
import kmedoids
import math

def _find_best_satellite_for_pair(cust_i, cust_j, problem):
    """
    Hàm trợ giúp: Tìm vệ tinh tốt nhất cho một cặp khách hàng.
    "Tốt nhất" được định nghĩa là vệ tinh tối thiểu hóa tổng khoảng cách đến cả hai khách hàng.
    """
    best_satellite = None
    min_dist = float('inf')
    
    if not problem.satellites:
        return None

    for sat in problem.satellites:
        dist = problem.get_distance(sat.id, cust_i.id) + problem.get_distance(sat.id, cust_j.id)
        if dist < min_dist:
            min_dist = dist
            best_satellite = sat
            
    return best_satellite

def calculate_satellite_aware_std_dissimilarity(cust_i, cust_j, problem, alpha=0.5):
    """
    <<< NANG CAP >>>
    Tính toán độ khác biệt Spatial-Temporal-Demand (STD) có nhận thức về Vệ tinh.
    alpha: Trọng số. alpha=1.0 -> chỉ xét i-j (giống bản gốc). alpha=0.0 -> chỉ xét S-i, S-j.
    """
    # B1: Tim ve tinh chung tiem nang tot nhat cho cap (i, j)
    best_sat = _find_best_satellite_for_pair(cust_i, cust_j, problem)
    if best_sat is None:
        # Neu khong co ve tinh, quay ve cach tinh goc (hoac tra ve gia tri lon)
        return calculate_std_dissimilarity(cust_i, cust_j, problem) # Fallback to original

    # B2: Tinh toan thanh phan KHONG GIAN co nhan thuc ve Ve tinh
    dist_ij = problem.get_distance(cust_i.id, cust_j.id)
    dist_sat_path = problem.get_distance(best_sat.id, cust_i.id) + problem.get_distance(cust_i.id, cust_j.id)
    
    # Cong thuc ket hop: alpha dieu chinh su quan trong giua duong di truc tiep va duong di qua ve tinh
    # Cach tiep can khac: spatial_dist = alpha * dist_ij + (1 - alpha) * (problem.get_distance(best_sat.id, cust_i.id) + problem.get_distance(best_sat.id, cust_j.id))
    spatial_dist = dist_sat_path # Su dung duong di thuc te hon S->i->j

    # B3: Tinh toan thanh phan THOI GIAN co nhan thuc ve Ve tinh
    # Gia dinh xe bat dau tu ve tinh, den i, roi den j.
    time_sat_to_i = problem.get_travel_time(best_sat.id, cust_i.id)
    time_i_to_j = problem.get_travel_time(cust_i.id, cust_j.id)

    # Thoi gian bat dau phuc vu som nhat co the tai i (sau khi di tu ve tinh)
    earliest_start_i = max(time_sat_to_i, cust_i.ready_time)

    # Kiem tra tinh kha thi cua cua so thoi gian tai i
    if earliest_start_i > cust_i.due_time:
        return float('inf') # Bat kha thi ngay tu dau

    # Tinh toan f_ij va h_ij voi lich trinh thuc te hon
    # f_ij: Do linh hoat khi di S -> i -> j
    f_ij = cust_j.due_time - (earliest_start_i + cust_i.service_time + time_i_to_j)
    if f_ij < 0: 
        return float('inf')
    
    # h_ij: Thoi gian cho toi thieu tai j khi di S -> i -> j
    # Thoi gian den j = thoi gian bat dau tai i + phuc vu tai i + di chuyen i->j
    arrival_at_j = earliest_start_i + cust_i.service_time + time_i_to_j
    h_ij = max(0, cust_j.ready_time - arrival_at_j)

    # B4: Ghep noi cac thanh phan nhu cu
    scheduling_horizon = 900
    
    temporal_term = (f_ij - h_ij) / scheduling_horizon
    demand_term = (cust_i.demand + cust_j.demand) / problem.se_vehicle_capacity
    
    penalty_multiplier = max(0.1, 2.0 - temporal_term + demand_term)
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

    # <<< THAY DOI: Su dung ham tinh toan moi >>>
    print(f"  B1: Tao ma tran do khac biet STD co nhan thuc ve Ve tinh {num_customers}x{num_customers}...")
    dissimilarity_matrix = np.zeros((num_customers, num_customers))
    for i in range(num_customers):
        for j in range(i + 1, num_customers):
            # Tinh toan theo ca hai chieu i->j va j->i
            score_ij = calculate_satellite_aware_std_dissimilarity(all_customers[i], all_customers[j], problem)
            score_ji = calculate_satellite_aware_std_dissimilarity(all_customers[j], all_customers[i], problem)
            # Lay gia tri tot nhat (nho nhat)
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

# --- Dưới đây là hàm gốc để so sánh (không cần thiết cho hoạt động chính) ---
def calculate_std_dissimilarity(cust_i, cust_j, problem):
    """
    Hàm gốc để tham khảo.
    """
    spatial_dist = problem.get_distance(cust_i.id, cust_j.id)
    travel_time = problem.get_travel_time(cust_i.id, cust_j.id)
    
    f_ij = cust_j.due_time - (cust_i.ready_time + cust_i.service_time + travel_time)
    if f_ij < 0: 
        return float('inf')
    
    h_ij = max(0, cust_j.ready_time - (cust_i.due_time + cust_i.service_time + travel_time))
    
    scheduling_horizon = 900
    
    temporal_term = (f_ij - h_ij) / scheduling_horizon
    demand_term = (cust_i.demand + cust_j.demand) / problem.se_vehicle_capacity
    
    penalty_multiplier = max(0.1, 2.0 - temporal_term + demand_term)
    return spatial_dist * penalty_multiplier

# --- END OF FILE manual_clustering.py (UPGRADED VERSION) ---