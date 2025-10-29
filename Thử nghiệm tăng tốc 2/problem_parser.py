# --- START OF FILE problem_parser.py (UPDATED FOR NUMBA) ---

import pandas as pd
import math
import numpy as np # <<< IMPORT NUMPY >>>

class Node:
    def __init__(self, node_id, x, y): self.id, self.x, self.y, self.service_time = int(node_id), int(x), int(y), 0.0
class Depot(Node):
    def __init__(self, node_id, x, y): super().__init__(node_id, x, y); self.type = 'Depot'
class Satellite(Node):
    def __init__(self, node_id, x, y, st): super().__init__(node_id, x, y); self.type, self.service_time, self.dist_id = 'Satellite', float(st), self.id
class Customer(Node):
    def __init__(self, node_id, x, y, d, st, et, lt): super().__init__(node_id, x, y); self.demand, self.service_time, self.ready_time, self.due_time = float(d), float(st), float(et), float(lt)
class DeliveryCustomer(Customer):
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.type = 'DeliveryCustomer'
class PickupCustomer(Customer):
    def __init__(self, node_id, x, y, d, st, et, lt, deadline): super().__init__(node_id, x, y, d, st, et, lt); self.type, self.deadline = 'PickupCustomer', float(deadline)


class ProblemInstance:
    def __init__(self, file_path, vehicle_speed=1.0):
        df = pd.read_csv(file_path); df.columns = df.columns.str.strip()
        self.depot, self.satellites, self.customers, node_objects = None, [], [], {}
        for i, row in df.iterrows():
            node = None
            if row['Type'] == 0: node = Depot(i, row['X'], row['Y']); self.depot = node
            elif row['Type'] == 1: node = Satellite(i, row['X'], row['Y'], row['Service Time']); self.satellites.append(node)
            elif row['Type'] == 2: node = DeliveryCustomer(i, row['X'], row['Y'], row['Demand'], row['Service Time'], row['Early'], row['Latest']); self.customers.append(node)
            elif row['Type'] == 3: node = PickupCustomer(i, row['X'], row['Y'], row['Demand'], row['Service Time'], row['Early'], row['Latest'], row['Deadline']); self.customers.append(node)
            if node: node_objects[i] = node
        self.node_objects, self.total_nodes = node_objects, len(node_objects)
        for sat in self.satellites: sat.coll_id = sat.id + self.total_nodes
        self.fe_vehicle_capacity, self.se_vehicle_capacity = df.iloc[0]['FE Cap'], df.iloc[0]['SE Cap']
        self.vehicle_speed = vehicle_speed
        nodes = [self.depot] + self.satellites + self.customers
        self.dist_matrix = {n1.id: {n2.id: math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2) for n2 in nodes} for n1 in nodes}
        
        self._max_dist = 0.0
        for row in self.dist_matrix.values():
            if not row: continue
            max_row = max(row.values())
            if max_row > self._max_dist: self._max_dist = max_row
        
        self._max_due_time = 0.0
        self._max_demand = 0.0
        for cust in self.customers:
            if cust.due_time > self._max_due_time: self._max_due_time = cust.due_time
            if cust.demand > self._max_demand: self._max_demand = cust.demand
        
        # <<< BƯỚC 4: TẠO CÁC MẢNG DỮ LIỆU CHO NUMBA >>>
        self._prepare_numba_data()

    def _prepare_numba_data(self):
        """Tạo các mảng NumPy để truyền vào các hàm Numba."""
        num_nodes = self.total_nodes
        # Ma trận khoảng cách và thời gian
        self.dist_matrix_numba = np.zeros((num_nodes, num_nodes), dtype=np.float64)
        self.time_matrix_numba = np.zeros((num_nodes, num_nodes), dtype=np.float64)
        for i in range(num_nodes):
            for j in range(num_nodes):
                dist = self.get_distance(i, j)
                self.dist_matrix_numba[i, j] = dist
                self.time_matrix_numba[i, j] = dist / self.vehicle_speed if self.vehicle_speed > 0 else np.inf

        # Ma trận dữ liệu node: [demand, service_time, ready_time, due_time, is_pickup, deadline]
        self.node_data_for_numba = np.zeros((num_nodes, 6), dtype=np.float64)
        for i in range(num_nodes):
            node = self.node_objects[i]
            self.node_data_for_numba[i, 0] = getattr(node, 'demand', 0.0)
            self.node_data_for_numba[i, 1] = getattr(node, 'service_time', 0.0)
            self.node_data_for_numba[i, 2] = getattr(node, 'ready_time', 0.0)
            self.node_data_for_numba[i, 3] = getattr(node, 'due_time', np.inf)
            self.node_data_for_numba[i, 4] = 1.0 if isinstance(node, PickupCustomer) else 0.0
            self.node_data_for_numba[i, 5] = getattr(node, 'deadline', np.inf)

    def get_distance(self, n1, n2): return self.dist_matrix.get(n1, {}).get(n2, float('inf'))
    
    def get_travel_time(self, n1, n2): 
        return self.get_distance(n1, n2) / self.vehicle_speed if self.vehicle_speed > 0 else float('inf')

# --- END OF FILE problem_parser.py ---