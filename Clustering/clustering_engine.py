from kmedoids import KMedoids
from sklearn.metrics import silhouette_score
import numpy as np
import time

# Import cac module da tao
import config

def analyze_k_and_suggest_optimal(dissimilarity_matrix):
    """
    Phan tich diem Silhouette cho mot khoang k va goi y gia tri toi uu.
    
    Args:
        dissimilarity_matrix (np.ndarray): Ma tran khac biet.

    Returns:
        tuple: (k_suggested, scores_by_k) trong do k_suggested la so nguyen,
               scores_by_k la mot dictionary luu diem so cua moi k.
    """
    print("\nBat dau phan tich Silhouette Score de tim k goi y...")
    start_time = time.time()
    scores_by_k = {}
    
    for k in config.K_CLUSTERS_RANGE:
        print(f"  - Dang thu nghiem voi k = {k}...")
        
        # Su dung init='build' theo khuyen nghi va de tuong thich
        kmedoids = KMedoids(n_clusters=k, metric='precomputed', method='pam', init='build')
        
        labels = kmedoids.fit_predict(dissimilarity_matrix)
        
        # Kiem tra de tranh loi neu chi co 1 cum duoc tao ra
        if len(np.unique(labels)) > 1:
            score = silhouette_score(dissimilarity_matrix, labels, metric='precomputed')
            scores_by_k[k] = score
            print(f"    -> Silhouette Score: {score:.4f}")
        else:
            scores_by_k[k] = -1.0 # Gan diem so am neu khong the tinh
            print(f"    -> Khong the tinh Silhouette Score (chi co 1 cum).")

    if not scores_by_k:
        print("Khong co diem so nao de tim k toi uu.")
        return None, {}
        
    k_suggested = max(scores_by_k, key=scores_by_k.get)
    
    end_time = time.time()
    print(f"\nHoan thanh phan tich trong {end_time - start_time:.2f} giay.")
    print(f"==> K toi uu duoc goi y la: {k_suggested} (voi Silhouette Score = {scores_by_k[k_suggested]:.4f})")
    
    return k_suggested, scores_by_k

def run_clustering(dissimilarity_matrix, n_clusters):
    """
    Chay thuat toan K-Medoids voi mot so cum n_clusters cho truoc.
    
    Args:
        dissimilarity_matrix (np.ndarray): Ma tran khac biet.
        n_clusters (int): So cum mong muon.

    Returns:
        np.ndarray: Mot mang cac nhan (labels) cho moi khach hang.
    """
    print(f"\nChay gom cum cuoi cung voi k = {n_clusters}...")
    start_time = time.time()

    # Su dung init='build'
    kmedoids = KMedoids(n_clusters=n_clusters, metric='precomputed', method='pam', init='build')
    
    labels = kmedoids.fit_predict(dissimilarity_matrix)
    
    end_time = time.time()
    print(f"Hoan thanh gom cum trong {end_time - start_time:.2f} giay.")
    return labels