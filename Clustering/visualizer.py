import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def plot_silhouette_scores(k_scores):
    """
    Ve bieu do duong the hien gia tri Silhouette Score cho moi gia tri k.
    
    Args:
        k_scores (dict): Dictionary co key la so cum (k) va value la diem so.
    """
    if not k_scores:
        print("Khong co du lieu diem so de ve bieu do.")
        return

    k_values = list(k_scores.keys())
    scores = list(k_scores.values())

    plt.figure(figsize=(10, 6))
    plt.plot(k_values, scores, marker='o', linestyle='--')
    
    plt.title('Bieu do Silhouette Score cho cac gia tri k')
    plt.xlabel('So Cum (k)')
    plt.ylabel('Silhouette Score')
    plt.xticks(k_values) # Dam bao hien thi tat ca cac gia tri k tren truc x
    plt.grid(True)
    # plt.show() se duoc goi o file main de hien thi tat ca bieu do cung luc

def plot_clusters(customers_df, satellites_df, hub_df):
    """
    Ve bieu do phan tan de hien thi cac cum khach hang tren ban do.
    
    Args:
        customers_df (pd.DataFrame): DataFrame khach hang da co cot 'cluster_id'.
        satellites_df (pd.DataFrame): DataFrame cac satellite.
        hub_df (pd.DataFrame): DataFrame hub.
    """
    plt.figure(figsize=(12, 10))
    
    # Su dung seaborn de ve cac cum khach hang voi mau sac tu dong
    sns.scatterplot(
        data=customers_df,
        x='X',
        y='Y',
        hue='cluster_id',
        palette='viridis', # Chon mot bang mau dep mat
        s=30,             # Kich thuoc diem khach hang
        alpha=0.8,
        legend='full'
    )
    
    # Ve cac satellite len tren
    plt.scatter(
        satellites_df['X'],
        satellites_df['Y'],
        s=150,             # Kich thuoc lon hon
        c='red',
        marker='^',        # Hinh tam giac
        edgecolor='black',
        label='Satellites'
    )
    
    # Ve hub len tren cung
    plt.scatter(
        hub_df['X'],
        hub_df['Y'],
        s=300,             # Kich thuoc rat lon
        c='gold',
        marker='*',        # Hinh ngoi sao
        edgecolor='black',
        label='Hub'
    )

    plt.title('Phan Cum Khach Hang')
    plt.xlabel('Toa do X')
    plt.ylabel('Toa do Y')
    plt.legend(title='Legend')
    plt.axis('equal') # Dam bao ti le truc X va Y la 1:1 de khong bop meo khong gian
    plt.grid(True)
    # plt.show() se duoc goi o file main