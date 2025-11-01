import pandas as pd
import numpy as np

# Import các module nền tảng đã tạo ở Giai đoạn 1
import config
from utils import calculate_travel_time, get_coords

def load_and_parse_data():
    """
    Tai du lieu tu file CSV va phan loai thanh cac DataFrame rieng biet.
    
    Returns:
        tuple: Mot tuple chua 3 DataFrame: (hub_df, satellites_df, customers_df)
    """
    try:
        full_df = pd.read_csv(config.DATA_PATH)
    except FileNotFoundError:
        print(f"Loi: Khong tim thay file du lieu tai duong dan '{config.DATA_PATH}'")
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
    
    # Reset index cho cac DataFrame moi de de truy cap
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

    Doi voi cac khach hang lay hang (pickup), deadline tai hub se duoc quy doi
    thanh mot thoi diem den muon nhat (latest) hieu dung tai vi tri khach hang.
    
    Args:
        customers_df (pd.DataFrame): DataFrame chua thong tin khach hang.
        satellites_df (pd.DataFrame): DataFrame chua thong tin satellites.
        hub_df (pd.DataFrame): DataFrame chua thong tin hub.

    Returns:
        pd.DataFrame: DataFrame khach hang da duoc cap nhat voi cot 'effective_latest'.
    """
    print("\nBat dau tien xu ly du lieu khach hang...")
    
    # Tao cot 'effective_latest' va khoi tao bang gia tri 'Latest' goc
    customers_df['effective_latest'] = customers_df['Latest']
    
    # Lay toa do cua hub mot lan duy nhat
    hub_coords = get_coords(hub_df.iloc[0])

    # Loc ra cac khach hang can lay hang de xu ly
    pickup_customers = customers_df[customers_df['Type'] == config.PICKUP_TYPE]
    
    print(f"Tim thay {len(pickup_customers)} khach hang lay hang (pickup) can tinh toan deadline...")

    for index, customer in pickup_customers.iterrows():
        customer_coords = get_coords(customer)
        
        # --- Tim satellite gan nhat voi khach hang ---
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
        
        # --- Tinh toan nguoc thoi gian tu deadline tai Hub ---
        # 1. Thoi gian di chuyen tu satellite gan nhat ve hub (dung toc do xe FE)
        time_sat_to_hub = calculate_travel_time(nearest_satellite_coords, hub_coords, config.FE_VEHICLE_SPEED)
        
        # 2. Thoi diem muon nhat xe FE phai roi satellite
        latest_departure_from_sat = customer['Deadline'] - time_sat_to_hub
        
        # 3. Thoi diem muon nhat xe SE phai ve den satellite
        latest_arrival_at_sat = latest_departure_from_sat - nearest_satellite['Service Time']
        
        # 4. Thoi gian di chuyen tu khach hang den satellite gan nhat (dung toc do xe SE)
        time_cust_to_sat = calculate_travel_time(customer_coords, nearest_satellite_coords, config.SE_VEHICLE_SPEED)
        
        # 5. Thoi diem muon nhat xe SE phai roi khoi khach hang
        latest_departure_from_customer = latest_arrival_at_sat - time_cust_to_sat
        
        # 6. Thoi diem muon nhat xe SE co the den (bat dau phuc vu) khach hang
        latest_effective_arrival = latest_departure_from_customer - customer['Service Time']
        
        # --- Cap nhat gia tri 'effective_latest' ---
        # Lay gia tri nho hon giua deadline goc tai khach hang va deadline hieu dung vua tinh
        final_latest = min(customer['Latest'], latest_effective_arrival)
        
        # Cap nhat truc tiep vao DataFrame goc
        customers_df.at[index, 'effective_latest'] = final_latest

    print("Hoan thanh tien xu ly.")
    return customers_df