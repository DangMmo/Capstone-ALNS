# --- START OF FILE clustering/data_handler.py ---

import pandas as pd
import numpy as np

import config
from utils.utils import calculate_travel_time, get_coords

def load_and_parse_data():
    """
    Tai du lieu tu file CSV va phan loai thanh cac DataFrame rieng biet.
    
    Returns:
        tuple: Mot tuple chua 3 DataFrame: (hub_df, satellites_df, customers_df)
    """
    try:
        # <<< SỬA LỖI TẠI ĐÂY: DATA_PATH -> FILE_PATH >>>
        full_df = pd.read_csv(config.FILE_PATH)
    except FileNotFoundError:
        print(f"Loi: Khong tim thay file du lieu tai duong dan '{config.FILE_PATH}'")
        return None, None, None

    # Lay thong tin Hub (Type 0)
    hub_df = full_df[full_df['Type'] == config.HUB_TYPE].copy()
    
    # Lay thong tin cac Satellites (Type 1)
    satellites_df = full_df[full_df['Type'] == config.SATELLITE_TYPE].copy()
    
    # Lay thong tin tat ca khach hang (Type 2 va 3)
    customers_df = full_df[
        (full_df['Type'] == config.DELIVERY_TYPE) | 
        (full_df['Type'] == config.PICKUP_TYPE)
    ].copy()
    
    hub_df.reset_index(drop=True, inplace=True)
    satellites_df.reset_index(drop=True, inplace=True)
    customers_df.reset_index(drop=True, inplace=True)
    
    print("Tai du lieu thanh cong:")
    print(f"- Hub: {len(hub_df)} diem")
    print(f"- Satellites: {len(satellites_df)} diem")
    print(f"- Customers: {len(customers_df)} diem")
    
    return hub_df, satellites_df, customers_df

def preprocess_customers(customers_df, satellites_df, hub_df):
    """
    Tien xu ly DataFrame khach hang de tinh toan 'cua so thoi gian hieu dung'.
    """
    print("\nBat dau tien xu ly du lieu khach hang...")
    
    customers_df['effective_latest'] = customers_df['Latest']
    
    hub_coords = get_coords(hub_df.iloc[0])

    pickup_customers = customers_df[customers_df['Type'] == config.PICKUP_TYPE]
    
    print(f"Tim thay {len(pickup_customers)} khach hang lay hang (pickup) can tinh toan deadline...")

    for index, customer in pickup_customers.iterrows():
        customer_coords = get_coords(customer)
        
        min_dist = float('inf')
        nearest_satellite = None
        for _, satellite in satellites_df.iterrows():
            dist = np.sqrt((customer_coords[0] - satellite['X'])**2 + (customer_coords[1] - satellite['Y'])**2)
            if dist < min_dist:
                min_dist = dist
                nearest_satellite = satellite
        
        if nearest_satellite is None:
            continue
            
        nearest_satellite_coords = get_coords(nearest_satellite)
        
        # <<< SỬA LỖI TẠI ĐÂY: FE/SE_VEHICLE_SPEED -> VEHICLE_SPEED >>>
        # Giả định tốc độ FE và SE là như nhau theo config mới
        time_sat_to_hub = calculate_travel_time(nearest_satellite_coords, hub_coords, config.VEHICLE_SPEED)
        latest_departure_from_sat = customer['Deadline'] - time_sat_to_hub
        latest_arrival_at_sat = latest_departure_from_sat - nearest_satellite['Service Time']
        time_cust_to_sat = calculate_travel_time(customer_coords, nearest_satellite_coords, config.VEHICLE_SPEED)
        latest_departure_from_customer = latest_arrival_at_sat - time_cust_to_sat
        latest_effective_arrival = latest_departure_from_customer - customer['Service Time']
        
        final_latest = min(customer['Latest'], latest_effective_arrival)
        
        customers_df.at[index, 'effective_latest'] = final_latest

    print("Hoan thanh tien xu ly.")
    return customers_df

# --- END OF FILE clustering/data_handler.py ---