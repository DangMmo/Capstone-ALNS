# --- START OF FILE utils/clustering_plots.py ---

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

def plot_silhouette_scores(k_scores, save_dir=None):
    if not k_scores: return
    plt.figure(figsize=(10, 6))
    plt.plot(list(k_scores.keys()), list(k_scores.values()), marker='o', linestyle='--')
    plt.title('Bieu do Silhouette Score cho cac gia tri k')
    plt.xlabel('So Cum (k)')
    plt.ylabel('Silhouette Score')
    plt.xticks(list(k_scores.keys()))
    plt.grid(True)
    if save_dir:
        plt.savefig(os.path.join(save_dir, "A_silhouette_scores.png"))
        plt.close()

def plot_clusters_map(customers_df, satellites_df, hub_df, save_dir=None):
    plt.figure(figsize=(12, 10))
    sns.scatterplot(data=customers_df, x='X', y='Y', hue='cluster_id', palette='viridis', s=30, alpha=0.8, legend='full')
    plt.scatter(satellites_df['X'], satellites_df['Y'], s=150, c='red', marker='^', edgecolor='black', label='Satellites')
    plt.scatter(hub_df['X'], hub_df['Y'], s=300, c='gold', marker='*', edgecolor='black', label='Hub')
    plt.title('Phan Cum Khach Hang')
    plt.xlabel('Toa do X'); plt.ylabel('Toa do Y')
    plt.legend(title='Legend'); plt.axis('equal'); plt.grid(True)
    if save_dir:
        plt.savefig(os.path.join(save_dir, "B_clusters_map.png"))
        plt.close()
# --- END OF FILE utils/clustering_plots.py ---