# --- START OF FILE utils/utils.py ---

import numpy as np  # <<< THÊM DÒNG NÀY >>>
import pandas as pd

def calculate_euclidean_distance(point1_coords, point2_coords):
    """
    Tính khoảng cách Euclid giữa hai điểm.
    Mỗi điểm là một tuple, list hoặc numpy array dạng (x, y).
    """
    return np.sqrt((point1_coords[0] - point2_coords[0])**2 + (point1_coords[1] - point2_coords[1])**2)

def calculate_travel_time(point1_coords, point2_coords, speed):
    """
    Tính thời gian di chuyển giữa hai điểm dựa trên khoảng cách và tốc độ.
    Trả về thời gian (cùng đơn vị với speed, ví dụ: phút).
    """
    if speed <= 0:
        return float('inf')
        
    distance = calculate_euclidean_distance(point1_coords, point2_coords)
    return distance / speed

def get_coords(node_series):
    """
    Hàm tiện ích để lấy tọa độ (x, y) từ một dòng dữ liệu (pandas Series).
    """
    return (node_series['X'], node_series['Y'])

# --- END OF FILE utils/utils.py ---