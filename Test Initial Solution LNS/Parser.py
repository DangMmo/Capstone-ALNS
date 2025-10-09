# --- START OF FILE Parser.py ---

import pandas as pd
import math

class Node:
    """Lớp cơ sở cho tất cả các điểm trên bản đồ."""
    def __init__(self, node_id, x, y):
        self.id = int(node_id)
        self.x = int(x)
        self.y = int(y)
        self.service_time = 0.0

class Depot(Node):
    """Đại diện cho kho tổng (Set 0)."""
    def __init__(self, node_id, x, y):
        super().__init__(node_id, x, y)
        self.type = 'Depot'
    def __repr__(self):
        return f"Depot(id={self.id})"

class Satellite(Node):
    """Đại diện cho trạm trung chuyển (Set S)."""
    def __init__(self, node_id, x, y, service_time):
        super().__init__(node_id, x, y)
        self.type = 'Satellite'
        self.service_time = float(service_time)
        self.dist_id = self.id
        self.coll_id = -1
    def __repr__(self):
        return f"Satellite(id={self.id})"
        
class Customer(Node):
    """Lớp cơ sở cho khách hàng."""
    def __init__(self, node_id, x, y, demand, service_time, early_tw, late_tw):
        super().__init__(node_id, x, y)
        self.demand = float(demand)
        self.service_time = float(service_time)
        self.ready_time = float(early_tw)
        self.due_time = float(late_tw)

class DeliveryCustomer(Customer):
    """Đại diện cho khách nhận hàng (Set Z_L)."""
    def __init__(self, node_id, x, y, demand, service_time, early_tw, late_tw):
        super().__init__(node_id, x, y, demand, service_time, early_tw, late_tw)
        self.type = 'DeliveryCustomer'
    def __repr__(self):
        return f"DeliveryCustomer(id={self.id}, demand={self.demand})"

class PickupCustomer(Customer):
    """Đại diện cho khách gửi hàng (Set Z_F)."""
    def __init__(self, node_id, x, y, demand, service_time, early_tw, late_tw, deadline):
        super().__init__(node_id, x, y, demand, service_time, early_tw, late_tw)
        self.type = 'PickupCustomer'
        self.deadline = float(deadline)
    def __repr__(self):
        return f"PickupCustomer(id={self.id}, demand={self.demand}, deadline={self.deadline})"

class ProblemInstance:
    def __init__(self, file_path):
        print(f"Dang doc va khoi tao bai toan tu file: {file_path}...")
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()

        # A. KHỞI TẠO CÁC SETS
        self.depot = None
        self.satellites = []
        self.customers = []
        node_objects = {}
        for index, row in df.iterrows():
            node = None
            node_id = index 
            if row['Type'] == 0:
                node = Depot(node_id, row['X'], row['Y'])
                self.depot = node
            elif row['Type'] == 1:
                node = Satellite(node_id, row['X'], row['Y'], row['Service Time'])
                self.satellites.append(node)
            elif row['Type'] == 2:
                node = DeliveryCustomer(node_id, row['X'], row['Y'], row['Demand'], row['Service Time'], row['Early'], row['Latest'])
                self.customers.append(node)
            elif row['Type'] == 3:
                node = PickupCustomer(node_id, row['X'], row['Y'], row['Demand'], row['Service Time'], row['Early'], row['Latest'], row['Deadline'])
                self.customers.append(node)
            if node:
                node_objects[node_id] = node
        self.node_objects = node_objects
        self.total_nodes = len(node_objects)
        for sat in self.satellites:
            sat.coll_id = sat.id + self.total_nodes

        # B. KHỞI TẠO CÁC PARAMETERS
        self.fe_vehicle_capacity = df.iloc[0]['FE Cap']
        self.se_vehicle_capacity = df.iloc[0]['SE Cap']
        
        self.vehicle_speed = 1.0 # mét/phút
        
        all_physical_nodes = [self.depot] + self.satellites + self.customers
        self.dist_matrix = {}
        for n1 in all_physical_nodes:
            self.dist_matrix[n1.id] = {}
            for n2 in all_physical_nodes:
                dist = math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2)
                self.dist_matrix[n1.id][n2.id] = dist
        
        print("Khoi tao bai toan thanh cong!")

    def get_distance(self, node_id1, node_id2):
        return self.dist_matrix.get(node_id1, {}).get(node_id2, float('inf'))

    def get_travel_time(self, node_id1, node_id2):
        distance = self.get_distance(node_id1, node_id2)
        if self.vehicle_speed > 0:
            return distance / self.vehicle_speed
        return float('inf')

# --- END OF FILE Parser.py ---