# --- START OF FILE main_manual_k.py ---

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from Parser import ProblemInstance, DeliveryCustomer, PickupCustomer
from manual_clustering import perform_manual_clustering 

def plot_clusters(problem, clusters):
    """Vẽ biểu đồ các cụm khách hàng, vệ tinh và kho."""
    if not clusters:
        print("Không có cụm nào để vẽ.")
        return
        
    plt.figure(figsize=(14, 12))
    colors = plt.get_cmap('tab10', len(clusters))

    # Vẽ khách hàng theo từng cụm
    for i, cluster in enumerate(clusters):
        delivery_custs = [c for c in cluster if isinstance(c, DeliveryCustomer)]
        pickup_custs = [c for c in cluster if isinstance(c, PickupCustomer)]

        if delivery_custs:
            del_x = [c.x for c in delivery_custs]
            del_y = [c.y for c in delivery_custs]
            plt.scatter(del_x, del_y, color=colors(i), marker='o', s=50, alpha=0.8, 
                        label=f'Cụm {i+1}')
        
        if pickup_custs:
            pick_x = [c.x for c in pickup_custs]
            pick_y = [c.y for c in pickup_custs]
            plt.scatter(pick_x, pick_y, color=colors(i), marker='^', s=60, alpha=0.8, 
                        edgecolors='black')
    
    # Vẽ các vệ tinh
    sat_x = [s.x for s in problem.satellites]
    sat_y = [s.y for s in problem.satellites]
    plt.scatter(sat_x, sat_y, color='red', marker='s', s=150, label='Vệ tinh', edgecolors='black', zorder=10)
    for s in problem.satellites:
        plt.text(s.x, s.y, f'S{s.id}', fontsize=12, color='white', ha='center', va='center', zorder=11)

    # Vẽ kho
    plt.scatter(problem.depot.x, problem.depot.y, color='black', marker='*', s=300, label='Kho', edgecolors='white', zorder=10)
    plt.text(problem.depot.x, problem.depot.y + 5, 'Depot', fontsize=12, color='black', ha='center', va='bottom')

    plt.title('Kết quả phân cụm khách hàng', fontsize=16)
    plt.xlabel('Tọa độ X')
    plt.ylabel('Tọa độ Y')
    
    # Tạo legend tùy chỉnh
    legend_elements = [
        Line2D([0], [0], marker='o', color='gray', label='Khách giao hàng', linestyle='None', markersize=8),
        Line2D([0], [0], marker='^', color='gray', label='Khách lấy hàng', linestyle='None', markersize=9, markeredgecolor='black')
    ]
    
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.legend(handles=handles + legend_elements, bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
    
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.show()

def main():
    # Vui lòng thay đổi đường dẫn file dữ liệu
    file_name ="C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_1_D.csv"
    
    problem = ProblemInstance(file_name)
    
    # ==========================================================
    # ==            ĐÂY LÀ NƠI BẠN NHẬP SỐ CỤM K             ==
    # ==========================================================
    K_VALUE = 5  # <-- Thay đổi số cụm mong muốn ở đây
    
    # Gọi hàm phân cụm thủ công
    clusters = perform_manual_clustering(problem, K_VALUE)
    
    if clusters is None or not clusters:
        print("\nQuá trình phân cụm không tạo ra kết quả. Dừng chương trình.")
        return
    
    # ==========================================================
    # PHẦN TRÌNH BÀY KẾT QUẢ - GIỮ NGUYÊN GIỐNG FILE VISUALIZE.PY
    # ==========================================================
    
    print("\n\n--- CHI TIET CAC CUM DA TAO ---")
    total_delivery_demand = 0
    total_pickup_demand = 0
    
    for i, cluster in enumerate(clusters):
        cluster_delivery_demand = sum(c.demand for c in cluster if c.type == 'DeliveryCustomer')
        cluster_pickup_demand = sum(c.demand for c in cluster if c.type == 'PickupCustomer')
        total_delivery_demand += cluster_delivery_demand
        total_pickup_demand += cluster_pickup_demand
        
        print("\n" + "="*50)
        print(f" CUM {i+1} - {len(cluster)} KH "
              f"| Tong Giao: {cluster_delivery_demand:.2f} | Tong Lay: {cluster_pickup_demand:.2f}")
        print("="*50)
        
        # Sắp xếp khách hàng trong cụm theo ID để dễ theo dõi
        cluster.sort(key=lambda c: c.id)

        header = f"  {'ID':<5} | {'Loai':<18} | {'Demand':>8} | {'Ready Time':>12} | {'Due Time':>10} | {'Deadline':>10}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        
        for c in cluster:
            deadline_str = f"{c.deadline:.2f}" if hasattr(c, 'deadline') else "N/A"
            print(f"  {c.id:<5} | {c.type:<18} | {c.demand:>8.2f} | {c.ready_time:>12.2f} | {c.due_time:>10.2f} | {deadline_str:>10}")
            
    print("\n" + "="*50)
    print("TONG KET TOAN BAI TOAN:")
    print(f"  - Tong so khach hang: {len(problem.customers)}")
    print(f"  - Tong nhu cau giao (delivery): {total_delivery_demand:.2f}")
    print(f"  - Tong nhu cau lay (pickup): {total_pickup_demand:.2f}")
    print("="*50)

    # Vẽ biểu đồ kết quả
    plot_clusters(problem, clusters)

if __name__ == "__main__":
    main()

# --- END OF FILE main_manual_k.py ---