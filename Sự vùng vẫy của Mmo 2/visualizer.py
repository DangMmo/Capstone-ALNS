# --- START OF FILE visualizer.py ---

import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
from data_structures import Solution, SERoute

def _get_unique_nodes_from_fe_schedule(schedule: List[Dict]) -> List[int]:
    """Trích xuất danh sách các ID node duy nhất theo đúng thứ tự từ lịch trình FE."""
    if not schedule:
        return []
    path_nodes = [schedule[0]['node_id']]
    for event in schedule[1:]:
        if event['node_id'] != path_nodes[-1]:
            path_nodes.append(event['node_id'])
    return path_nodes

def visualize_solution(solution: Solution):
    """
    Trực quan hóa lời giải 2E-VRP bằng Matplotlib.
    - Depot: Ngôi sao đen
    - Satellites: Hình vuông xanh lá
    - Customers: Hình tròn xanh dương
    - FE Routes: Nét đứt, dày, mỗi route một màu riêng.
    - SE Routes: Nét liền, mỏng, có màu giống với FE route phục vụ nó.
    """
    problem = solution.problem
    fig, ax = plt.subplots(figsize=(20, 16))

    # --- 1. Chuẩn bị màu sắc ---
    # Sử dụng colormap 'tab20' có nhiều màu sắc phân biệt
    num_fe_routes = len(solution.fe_routes)
    fe_route_colors = plt.cm.get_cmap('tab20', num_fe_routes if num_fe_routes > 0 else 1)
    
    # Tạo map ánh xạ từ Vệ tinh -> Màu của FE route phục vụ nó
    satellite_to_color_map: Dict[int, any] = {}
    for i, fe_route in enumerate(solution.fe_routes):
        color = fe_route_colors(i)
        for se_route in fe_route.serviced_se_routes:
            satellite_to_color_map[se_route.satellite.id] = color

    # --- 2. Vẽ các điểm (Nodes) ---
    all_nodes = problem.node_objects.values()
    ax.scatter(
        [c.x for c in problem.customers], [c.y for c in problem.customers],
        c='cornflowerblue', marker='o', s=50, label='Customer'
    )
    ax.scatter(
        [s.x for s in problem.satellites], [s.y for s in problem.satellites],
        c='limegreen', marker='s', s=150, label='Satellite', edgecolors='black'
    )
    ax.scatter(
        problem.depot.x, problem.depot.y,
        c='black', marker='*', s=500, label='Depot', edgecolors='white'
    )
    
    # Thêm nhãn ID cho từng điểm
    for node in all_nodes:
        ax.text(node.x, node.y + 1, str(node.id), fontsize=9, ha='center')

    # --- 3. Vẽ các tuyến đường SE (Cấp 2) ---
    for se_route in solution.se_routes:
        color = satellite_to_color_map.get(se_route.satellite.id, 'gray') # Màu xám nếu không được phục vụ
        
        # Lấy ID node thực tế (loại bỏ dist_id/coll_id)
        path_node_ids = [nid % problem.total_nodes for nid in se_route.nodes_id]
        
        # Lấy tọa độ
        path_coords = [(problem.node_objects[nid].x, problem.node_objects[nid].y) for nid in path_node_ids]
        
        x_coords, y_coords = zip(*path_coords)
        ax.plot(x_coords, y_coords, color=color, linestyle='-', linewidth=1.2, alpha=0.8)

    # --- 4. Vẽ các tuyến đường FE (Cấp 1) ---
    for i, fe_route in enumerate(solution.fe_routes):
        color = fe_route_colors(i)
        
        path_node_ids = _get_unique_nodes_from_fe_schedule(fe_route.schedule)
        if not path_node_ids:
            continue

        path_coords = [(problem.node_objects[nid].x, problem.node_objects[nid].y) for nid in path_node_ids]
        
        x_coords, y_coords = zip(*path_coords)
        ax.plot(x_coords, y_coords, color=color, linestyle='--', linewidth=3, alpha=0.9)
    
    # --- 5. Hoàn thiện biểu đồ ---
    ax.set_title(f"2E-VRP Solution Visualization (Total Cost: {solution.calculate_total_cost():.2f})", fontsize=18)
    ax.set_xlabel("X Coordinate", fontsize=12)
    ax.set_ylabel("Y Coordinate", fontsize=12)
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)
    
    # Đảm bảo các trục có cùng tỉ lệ
    ax.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()
    plt.show()

# --- END OF FILE visualizer.py ---