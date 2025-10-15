# --- START OF FILE InstanceVisualizer.py (LEGEND POSITION FIXED) ---

import pandas as pd
import matplotlib.pyplot as plt

class InstanceVisualizer:
    """
    Lop nay dung de doc, tom tat va truc quan hoa du lieu dau vao
    cua bai toan 2E-VRP-PDD tu mot file CSV.
    """
    # ... (Phuong thuc __init__ va summarize giu nguyen, khong can chep lai)
    def __init__(self, file_path: str):
        print(f">>> Dang doc file instance: {file_path}")
        try:
            self.df = pd.read_csv(file_path)
            self.df.columns = self.df.columns.str.strip()
            self.file_path = file_path
            
            self.fe_cap = self.df['FE Cap'].dropna().iloc[0]
            self.se_cap = self.df['SE Cap'].dropna().iloc[0]

            self.depot = self.df[self.df['Type'] == 0]
            self.satellites = self.df[self.df['Type'] == 1]
            self.delivery_customers = self.df[self.df['Type'] == 2]
            self.pickup_customers = self.df[self.df['Type'] == 3]
            print(">>> Doc file thanh cong!")

        except FileNotFoundError:
            print(f"!!! LOI: Khong tim thay file tai duong dan: {file_path}")
            self.df = None
        except Exception as e:
            print(f"!!! LOI: Co van de khi doc file: {e}")
            self.df = None

    def summarize(self):
        if self.df is None:
            print(">>> Khong co du lieu de tom tat do loi doc file.")
            return
            
        print("\n" + "="*70)
        print("--- TOM TAT DU LIEU DAU VAO ---")
        print("="*70)
        print(f"\n[THONG SO CHUNG]")
        print(f"- Dung tich xe cap 1 (FE Vehicle Capacity): {self.fe_cap}")
        print(f"- Dung tich xe cap 2 (SE Vehicle Capacity): {self.se_cap}")
        
        total_customers = len(self.delivery_customers) + len(self.pickup_customers)
        print(f"\n[THONG KE SO LUONG]")
        print(f"- Kho tong (Depot):         {len(self.depot)}")
        print(f"- Tram trung chuyen (Satellites): {len(self.satellites)}")
        print(f"- Khach hang nhan (Delivery): {len(self.delivery_customers)}")
        print(f"- Khach hang gui (Pickup):    {len(self.pickup_customers)}")
        print(f"------------------------------------")
        print(f"- TONG SO KHACH HANG:     {total_customers}")
        
        total_delivery_demand = self.delivery_customers['Demand'].sum()
        total_pickup_demand = self.pickup_customers['Demand'].sum()
        print(f"\n[THONG KE NHU CAU (DEMAND)]")
        print(f"- Tong nhu cau can giao: {total_delivery_demand:.2f}")
        print(f"- Tong nhu cau can lay: {total_pickup_demand:.2f}")

        if not self.pickup_customers.empty:
            print(f"\n[THONG KE DEADLINE CUA KHACH GUI HANG (ID)]")
            deadline_groups = self.pickup_customers.groupby('Deadline')
            sorted_deadlines = sorted(deadline_groups.groups.keys())
            
            for deadline in sorted_deadlines:
                group = deadline_groups.get_group(deadline)
                customer_ids = list(group.index)
                ids_str = ", ".join(map(str, customer_ids))
                print(f"- Deadline {int(deadline):<5}: {len(customer_ids)} khach hang (IDs: {ids_str})")

        print("\n" + "="*70)


    def plot(self):
        """
        Ve bieu do truc quan hoa, duoc toi uu hoa cho cac instance lon
        voi nhieu diem chong cheo.
        """
        if self.df is None:
            print(">>> Khong co du lieu de ve do loi doc file.")
            return

        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(12, 12)) 

        # --- LOGIC PHAN LOAI KHÁCH HÀNG (giu nguyen) ---
        delivery_coords = set(zip(self.delivery_customers['X'], self.delivery_customers['Y']))
        pickup_coords = set(zip(self.pickup_customers['X'], self.pickup_customers['Y']))
        both_coords = delivery_coords.intersection(pickup_coords)

        delivery_only_cust = self.delivery_customers[
            self.delivery_customers.apply(lambda row: (row['X'], row['Y']) not in both_coords, axis=1)
        ]
        pickup_only_cust = self.pickup_customers[
            self.pickup_customers.apply(lambda row: (row['X'], row['Y']) not in both_coords, axis=1)
        ]
        both_cust_locations = self.delivery_customers[
            self.delivery_customers.apply(lambda row: (row['X'], row['Y']) in both_coords, axis=1)
        ].drop_duplicates(subset=['X', 'Y'])

        # --- VE BIEU DO VOI CAC THUOC TINH DUOC CAI TIEN ---
        ax.scatter(delivery_only_cust['X'], delivery_only_cust['Y'], 
                   c='blue', marker='o', s=15, zorder=1,
                   label=f'Delivery Only Customers ({len(delivery_only_cust)})', 
                   alpha=0.4)

        ax.scatter(pickup_only_cust['X'], pickup_only_cust['Y'], 
                   c='darkorange', marker='+', s=40, zorder=2,
                   label=f'Pickup Only Customers ({len(pickup_only_cust)})', 
                   alpha=0.8)

        if not both_cust_locations.empty:
            ax.scatter(both_cust_locations['X'], both_cust_locations['Y'], 
                       c='purple', marker='D', s=50, zorder=3,
                       label=f'Delivery & Pickup Customers ({len(both_cust_locations)})',
                       edgecolors='black', alpha=0.9)

        ax.scatter(self.satellites['X'], self.satellites['Y'], 
                   c='yellow', marker='^', s=150, zorder=4, 
                   label='Satellites (Tram trung chuyen)', 
                   edgecolors='black')
                   
        ax.scatter(self.depot['X'], self.depot['Y'], 
                   c='red', marker='s', s=250, zorder=5, 
                   label='Depot (Kho tong)', 
                   edgecolors='black')

        for index, row in pd.concat([self.depot, self.satellites]).iterrows():
            ax.text(row['X'], row['Y'] + 150, str(index), 
                    fontsize=10, weight='bold', color='black', 
                    ha='center', va='bottom')

        ax.set_title(f'Truc quan hoa Instance: {self.file_path.split("/")[-1].split("\\")[-1]}', fontsize=16)
        ax.set_xlabel('X', fontsize=12)
        ax.set_ylabel('Y', fontsize=12)
        ax.set_aspect('equal', adjustable='box')
        
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0., fontsize=12)
        
        # <<< THAY DOI: Su dung subplots_adjust thay cho tight_layout >>>
        plt.subplots_adjust(left=0.08, right=0.80, top=0.95, bottom=0.08)
        
        plt.show()
if __name__ == '__main__':
    
    # file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_2_D.csv"
    file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_5_TD.csv"
    # file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\C_100_5_TD.csv"
    # file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-without-deadline\\100 customer WD\\C_100_10.csv"
    # file_name = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_2_D.csv"
    
    visualizer = InstanceVisualizer(file_path=file_name)
    
    if visualizer.df is not None:
        visualizer.summarize()
        visualizer.plot()

# --- END OF FILE InstanceVisualizer.py (FINAL VERSION) ---