import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Import tat ca cac module chuc nang
import config
from data_handler import load_and_parse_data, preprocess_customers
from dissimilarity_calculator import create_dissimilarity_matrix
from clustering_engine import analyze_k_and_suggest_optimal, run_clustering
from visualizer import plot_silhouette_scores, plot_clusters

def main():
    """Ham chinh de chay toan bo luong phan tich gom cum."""
    
    # --- Giai doan 2: Tai va xu ly du lieu ---
    hub_df, satellites_df, customers_df = load_and_parse_data()
    if customers_df is None:
        return

    customers_processed_df = preprocess_customers(customers_df, satellites_df, hub_df)

    # --- Giai doan 3: Tinh toan ma tran va gom cum ---
    dissimilarity_matrix = create_dissimilarity_matrix(customers_processed_df)
    
    # 1. Phan tich va lay k goi y
    k_suggested, scores_by_k = analyze_k_and_suggest_optimal(dissimilarity_matrix)
    
    if k_suggested is None:
        print("Da xay ra loi trong qua trinh phan tich k. Dung chuong trinh.")
        return

    # 2. TUONG TAC VOI NGUOI DUNG DE CHON K CUOI CUNG
    print("\n" + "="*50)
    print("VUI LONG CHON SO CUM (K)")
    print("="*50)
    print("Bang diem Silhouette:")
    for k, score in sorted(scores_by_k.items()):
        print(f"  - k = {k}: Score = {score:.4f}")
    
    k_final = k_suggested  # Gia tri mac dinh
    try:
        prompt = f"\nNhap so cum ban muon su dung (an Enter de chap nhan gia tri goi y: {k_suggested}): "
        user_input = input(prompt)
        
        if user_input.strip() == "": # Nguoi dung an Enter
            print(f"Da chap nhan gia tri goi y k = {k_suggested}")
            k_final = k_suggested
        else:
            chosen_k = int(user_input)
            if chosen_k in config.K_CLUSTERS_RANGE:
                k_final = chosen_k
                print(f"Ban da chon k = {k_final}")
            else:
                print(f"Gia tri '{chosen_k}' nam ngoai pham vi thu nghiem. Su dung gia tri goi y k = {k_suggested}")
                k_final = k_suggested
    except ValueError:
        print(f"Du lieu nhap vao khong hop le. Su dung gia tri goi y k = {k_suggested}")
        k_final = k_suggested
    
    # 3. Chay gom cum lan cuoi voi k_final
    final_labels = run_clustering(dissimilarity_matrix, k_final)
    customers_processed_df['cluster_id'] = final_labels

    # --- In ket qua phan tich ra console ---
    print("\n" + "="*50)
    print(f"KET QUA PHAN TICH GOM CUM (CHO K = {k_final})")
    print("="*50)
    
    for cluster_id in range(k_final):
        cluster_data = customers_processed_df[customers_processed_df['cluster_id'] == cluster_id]
        print(f"\n--- Thong tin Cum {cluster_id} ---")
        print(f"So luong khach hang: {len(cluster_data)}")
        
        # Thong ke theo loai khach hang
        type_counts = cluster_data['Type'].value_counts().to_dict()
        print(f"  - Giao hang (Type 2): {type_counts.get(config.DELIVERY_TYPE, 0)}")
        print(f"  - Lay hang (Type 3): {type_counts.get(config.PICKUP_TYPE, 0)}")

    # --- Giai doan 4: Truc quan hoa ket qua ---
    print("\nDang chuan bi hien thi bieu do... (Vui long dong cua so bieu do de ket thuc chuong trinh)")
    plot_silhouette_scores(scores_by_k)
    plot_clusters(customers_processed_df, satellites_df, hub_df)
    
    # Dong lenh quan trong de hien thi tat ca cac cua so bieu do da ve
    plt.show()

if __name__ == "__main__":
    main()