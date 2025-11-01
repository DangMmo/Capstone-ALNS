import pandas as pd
import numpy as np
import os # Thu vien de tuong tac voi he thong (tao thu muc)

# Import tat ca cac module chuc nang
import config
from data_handler import load_and_parse_data, preprocess_customers
from dissimilarity_calculator import create_dissimilarity_matrix
from clustering_engine import analyze_k_and_suggest_optimal, run_clustering

def main():
    """Ham chinh de chay luong gom cum va xuat file CSV."""
    
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
    print("VUI LONG CHON SO CUM (K) DE XUAT FILE")
    print("="*50)
    
    k_final = k_suggested  # Gia tri mac dinh
    try:
        prompt = f"\nNhap so cum ban muon su dung de xuat file (an Enter de chap nhan gia tri goi y: {k_suggested}): "
        user_input = input(prompt)
        
        if user_input.strip() == "": # Nguoi dung an Enter
            print(f"Da chap nhan gia tri goi y k = {k_suggested}")
            k_final = k_suggested
        else:
            chosen_k = int(user_input)
            if chosen_k in config.K_CLUSTERS_RANGE:
                k_final = chosen_k
                print(f"Ban da chon k = {k_final} de xuat file.")
            else:
                print(f"Gia tri '{chosen_k}' nam ngoai pham vi. Su dung gia tri goi y k = {k_suggested}")
                k_final = k_suggested
    except ValueError:
        print(f"Du lieu nhap vao khong hop le. Su dung gia tri goi y k = {k_suggested}")
        k_final = k_suggested
    
    # 3. Chay gom cum lan cuoi voi k_final
    final_labels = run_clustering(dissimilarity_matrix, k_final)
    customers_processed_df['cluster_id'] = final_labels

    # --- PHAN XUAT FILE CSV ---
    print("\n" + "="*50)
    print(f"BAT DAU XUAT {k_final} FILE CSV")
    print("="*50)

    # Tao thu muc output neu no chua ton tai
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    print(f"Cac file se duoc luu vao thu muc: '{config.OUTPUT_DIR}/'")

    for cluster_id in range(k_final):
        # Loc ra nhung khach hang thuoc cum hien tai
        cluster_customers_df = customers_processed_df[
            customers_processed_df['cluster_id'] == cluster_id
        ].copy()
        
        # Tao DataFrame hoan chinh cho bai toan con
        # Ghep: hub + tat ca satellites + cac khach hang cua cum
        output_df = pd.concat([hub_df, satellites_df, cluster_customers_df], ignore_index=True)
        
        # Tao duong dan file
        output_filename = f"cluster_{cluster_id}_data.csv"
        output_path = os.path.join(config.OUTPUT_DIR, output_filename)
        
        # Luu file CSV, khong bao gom cot index cua DataFrame
        output_df.to_csv(output_path, index=False)
        print(f"  - Da luu file: {output_path} ({len(cluster_customers_df)} khach hang)")
        
    print("\nHoan thanh xuat tat ca cac file.")

if __name__ == "__main__":
    main()