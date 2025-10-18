# --- START OF FILE problem_parser.py ---

import pandas as pd
import math
from typing import List, Dict

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
        self.fe_vehicle_capacity, self.se_vehicle_capacity, self.vehicle_speed = df.iloc[0]['FE Cap'], df.iloc[0]['SE Cap'], vehicle_speed
        nodes = [self.depot] + self.satellites + self.customers; self.dist_matrix = {n1.id: {n2.id: math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2) for n2 in nodes} for n1 in nodes}
    def get_distance(self, n1, n2): return self.dist_matrix.get(n1, {}).get(n2, float('inf'))
    def get_travel_time(self, n1, n2): return self.get_distance(n1, n2) / self.vehicle_speed if self.vehicle_speed > 0 else float('inf')

# --- END OF FILE problem_parser.py ---