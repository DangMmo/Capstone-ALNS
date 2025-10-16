# --- START OF FILE Heuristics.py (FINAL CORRECTED VERSION) ---

import random
import copy
from typing import Dict, Optional, List, Tuple

from Parser import ProblemInstance, Customer, Satellite
from DataStructures import Solution, SERoute, FERoute

class VRP2E_State:
    """
    Lop 'trang thai' ma thu vien ALNS se su dung.
    No dong goi toan bo thong tin cua mot loi giai tai mot thoi diem.
    """
    def __init__(self, solution: 'Solution'):
        self.solution = solution

    def copy(self) -> 'VRP2E_State':
        """
        Phuong thuc bat buoc phai co. ALNS can tao cac ban sao
        de thu nghiem ma khong anh huong den loi giai goc.
        """
        return copy.deepcopy(self)

    @property
    def cost(self) -> float:
        """
        Mot property tien loi de lay chi phi cua loi giai hien tai.
        """
        return self.solution.calculate_total_cost()


class InsertionProcessor:
    """
    Lop nay chua logic thuat toan lien quan den viec chen khach hang vao cac tuyen duong.
    """
    def __init__(self, problem: 'ProblemInstance'):
        self.problem = problem

    def find_best_insertion_for_se_route(self, route: 'SERoute', customer: 'Customer') -> Optional[Dict]:
        """
        Tim vi tri va chi phi tot nhat de chen mot khach hang vao mot SERoute cu the.
        PHIÊN BẢN ĐÃ SỬA LỖI: Lặp qua các cặp node thay vì chỉ số để tránh lỗi.
        """
        best_candidate = {"pos": None, "cost_increase": float('inf')}
        
        # A SERoute must have at least 2 nodes (dist_id and coll_id) to be valid for insertion.
        if len(route.nodes_id) < 2:
            return None

        for i in range(len(route.nodes_id) - 1):
            pos_to_insert = i + 1

            temp_route = copy.deepcopy(route)
            
            # Kiem tra tai trong
            is_cap_ok = True
            temp_del_load = route.total_load_delivery
            if customer.type == 'DeliveryCustomer':
                temp_del_load += customer.demand
            if temp_del_load > self.problem.se_vehicle_capacity:
                continue

            temp_nodes_for_cap_check = route.nodes_id[:pos_to_insert] + [customer.id] + route.nodes_id[pos_to_insert:]
            running_load = temp_del_load
            for node_id in temp_nodes_for_cap_check[1:-1]:
                cust_obj = self.problem.node_objects[node_id]
                if cust_obj.type == 'DeliveryCustomer':
                    running_load -= cust_obj.demand
                else:
                    running_load += cust_obj.demand
                if running_load > self.problem.se_vehicle_capacity:
                    is_cap_ok = False
                    break
            if not is_cap_ok: continue
            
            # Kiem tra thoi gian
            temp_route.insert_customer_at_pos(customer, pos_to_insert)
            is_feasible = all(
                temp_route.service_start_times[node_id] <= self.problem.node_objects[node_id % self.problem.total_nodes].due_time
                for node_id in temp_route.nodes_id[1:-1]
            )
            if not is_feasible: continue
            
            cost_increase = temp_route.total_dist - route.total_dist
            if cost_increase < best_candidate["cost_increase"]:
                best_candidate["pos"] = pos_to_insert
                best_candidate["cost_increase"] = cost_increase
        
        if best_candidate["pos"] is None:
            return None
        return best_candidate


def _recalculate_fe_route_and_check_feasibility(fe_route: 'FERoute', problem: 'ProblemInstance') -> Tuple[Optional[float], bool]:
    """
    (HAM COT LOI) Tinh toan lai toan bo lich trinh, chi phi cho mot FE route va kiem tra tinh kha thi.
    Tra ve (chi phi moi, tinh kha thi).
    """
    if not fe_route.serviced_se_routes:
        fe_route.total_dist = 0.0
        fe_route.total_time = 0.0
        fe_route.schedule = []
        return 0.0, True

    depot = problem.depot
    # 1. Tim trinh tu ghe tham satellite (dung Nearest Neighbor heuristic)
    sat_sequence: List[Satellite] = []
    sats_to_visit = {se.satellite for se in fe_route.serviced_se_routes}
    current_loc = depot
    
    while sats_to_visit:
        nearest_sat = min(sats_to_visit, key=lambda s: problem.get_distance(current_loc.id, s.id))
        sat_sequence.append(nearest_sat)
        sats_to_visit.remove(nearest_sat)
        current_loc = nearest_sat

    # 2. Xay dung lich trinh chi tiet va dong bo hoa
    schedule = []
    current_time = 0.0
    total_delivery_load = sum(se.total_load_delivery for se in fe_route.serviced_se_routes)
    current_load = total_delivery_load
    
    schedule.append({'activity': 'DEPART_DEPOT', 'node_id': depot.id, 'load_change': current_load, 'load_after': current_load,
                     'arrival_time': 0.0, 'start_svc_time': 0.0, 'departure_time': 0.0})
    
    last_node_id = depot.id
    route_deadlines = set()

    for satellite in sat_sequence:
        travel_time = problem.get_travel_time(last_node_id, satellite.id)
        arrival_at_sat = current_time + travel_time
        
        se_routes_at_this_sat = [r for r in fe_route.serviced_se_routes if r.satellite == satellite]
        delivery_load_at_sat = sum(r.total_load_delivery for r in se_routes_at_this_sat)
        
        schedule.append({'activity': 'UNLOAD_DELIV', 'node_id': satellite.id, 'load_change': -delivery_load_at_sat, 'load_after': current_load - delivery_load_at_sat,
                         'arrival_time': arrival_at_sat, 'start_svc_time': arrival_at_sat, 'departure_time': arrival_at_sat})
        
        latest_se_finish_time = 0
        for se_route in se_routes_at_this_sat:
            se_route.service_start_times[se_route.nodes_id[0]] = arrival_at_sat
            se_route.calculate_full_schedule_and_slacks()
            # Kiem tra tinh kha thi cua SE route
            for cust in se_route.get_customers():
                if se_route.service_start_times[cust.id] > cust.due_time:
                    return None, False # Khong kha thi
                if hasattr(cust, 'deadline'):
                    route_deadlines.add(cust.deadline)
            latest_se_finish_time = max(latest_se_finish_time, se_route.service_start_times[se_route.nodes_id[-1]])
            
        pickup_load_at_sat = sum(r.total_load_pickup for r in se_routes_at_this_sat)
        departure_from_sat = latest_se_finish_time + satellite.service_time
        
        schedule.append({'activity': 'LOAD_PICKUP', 'node_id': satellite.id, 'load_change': pickup_load_at_sat, 'load_after': current_load - delivery_load_at_sat + pickup_load_at_sat,
                         'arrival_time': latest_se_finish_time, 'start_svc_time': latest_se_finish_time, 'departure_time': departure_from_sat})
        
        current_time = departure_from_sat
        current_load += pickup_load_at_sat - delivery_load_at_sat
        last_node_id = satellite.id

    travel_time = problem.get_travel_time(last_node_id, depot.id)
    arrival_at_depot = current_time + travel_time
    schedule.append({'activity': 'ARRIVE_DEPOT', 'node_id': depot.id, 'load_change': -current_load, 'load_after': 0,
                     'arrival_time': arrival_at_depot, 'start_svc_time': arrival_at_depot, 'departure_time': arrival_at_depot})

    fe_route.schedule = schedule
    fe_route.calculate_route_properties()
    
    # 3. Kiem tra tinh kha thi toan cuc cua FE Route
    effective_deadline = min(route_deadlines) if route_deadlines else float('inf')
    if arrival_at_depot > effective_deadline:
        return None, False # Vi pham deadline

    return fe_route.total_dist, True

def create_integrated_initial_solution(problem: 'ProblemInstance', random_customers: bool = True) -> 'VRP2E_State':
    print("\n>>> Bat dau xay dung loi giai ban dau (Phien ban Chen Tich Hop)...")
    solution = Solution(problem)
    insertion_processor = InsertionProcessor(problem)
    
    customers_to_serve = list(problem.customers)
    if random_customers:
        random.shuffle(customers_to_serve)

    unserved_customers_list = list(customers_to_serve)

    for i, customer in enumerate(customers_to_serve):
        print(f"  -> Xu ly khach hang {i+1}/{len(customers_to_serve)} (ID: {customer.id})...", end='\r')
        
        best_global_option = {'total_cost_increase': float('inf'), 'type': None}

        # === KICH BAN 1: Chen vao mot SERoute hien co ===
        for se_route in solution.se_routes:
            insertion_result = insertion_processor.find_best_insertion_for_se_route(se_route, customer)
            if not insertion_result: continue
            
            if not se_route.serving_fe_routes: continue
            fe_route = list(se_route.serving_fe_routes)[0]
            
            original_global_cost = se_route.total_dist + fe_route.total_dist
            
            temp_fe_route = copy.deepcopy(fe_route)
            
            # --- START OF FINAL FIX ---
            # So sánh cả danh sách node để đảm bảo tìm đúng bản sao của tuyến đường đang xét,
            # tránh nhầm lẫn khi 1 xe FE phục vụ nhiều tuyến SE từ cùng 1 vệ tinh.
            try:
                temp_se_route_ref = next(r for r in temp_fe_route.serviced_se_routes 
                                         if r.nodes_id == se_route.nodes_id and r.satellite.id == se_route.satellite.id)
            except StopIteration:
                # This should not happen if deepcopy works correctly, but it's a safe guard.
                print(f"\nCANH BAO: Khong tim thay ban sao cua SE Route cho satellite {se_route.satellite.id} trong FE Route copy. Bo qua...")
                continue
            # --- END OF FINAL FIX ---
            
            temp_se_route_ref.insert_customer_at_pos(customer, insertion_result['pos'])
            
            new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
            
            if is_feasible:
                new_se_cost = temp_se_route_ref.total_dist
                new_global_cost = new_se_cost + new_fe_cost
                total_increase = new_global_cost - original_global_cost

                if total_increase < best_global_option['total_cost_increase']:
                    best_global_option.update({
                        'total_cost_increase': total_increase, 'type': 'insert_into_existing_se',
                        'se_route': se_route, 'se_pos': insertion_result['pos']
                    })

        # === KICH BAN 2: Tao mot SERoute moi ===
        for satellite in problem.satellites:
            temp_new_se = SERoute(satellite, problem)
            temp_new_se.insert_customer_at_pos(customer, 1)
            se_cost = temp_new_se.total_dist

            # --- Phuong an 2b: Tao mot FERoute moi ---
            temp_fe_for_new = FERoute(problem)
            temp_fe_for_new.add_serviced_se_route(temp_new_se)
            new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_for_new, problem)
            
            if is_feasible and (se_cost + new_fe_cost) < best_global_option['total_cost_increase']:
                best_global_option.update({
                    'total_cost_increase': se_cost + new_fe_cost, 'type': 'create_new_se_new_fe',
                    'new_satellite': satellite
                })

            # --- Phuong an 2a: Mo rong mot FERoute hien co ---
            for fe_route in solution.fe_routes:
                current_del_load = sum(r.total_load_delivery for r in fe_route.serviced_se_routes)
                if current_del_load + temp_new_se.total_load_delivery > problem.fe_vehicle_capacity:
                    continue

                original_fe_cost = fe_route.total_dist
                temp_fe_route = copy.deepcopy(fe_route)
                temp_fe_route.add_serviced_se_route(temp_new_se)
                
                new_fe_cost, is_feasible = _recalculate_fe_route_and_check_feasibility(temp_fe_route, problem)
                
                if is_feasible:
                    total_increase = se_cost + (new_fe_cost - original_fe_cost)
                    if total_increase < best_global_option['total_cost_increase']:
                        best_global_option.update({
                            'total_cost_increase': total_increase, 'type': 'create_new_se_expand_fe',
                            'new_satellite': satellite, 'fe_route': fe_route
                        })

        # === Thuc hien phuong an tot nhat ===
        option_type = best_global_option.get('type')

        if option_type == 'insert_into_existing_se':
            se_route = best_global_option['se_route']
            se_pos = best_global_option['se_pos']
            fe_route = list(se_route.serving_fe_routes)[0]
            se_route.insert_customer_at_pos(customer, se_pos)
            solution.customer_to_se_route_map[customer.id] = se_route
            _recalculate_fe_route_and_check_feasibility(fe_route, problem)
            unserved_customers_list.remove(customer)

        elif option_type == 'create_new_se_new_fe':
            satellite = best_global_option['new_satellite']
            new_se_route = SERoute(satellite, problem)
            new_se_route.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se_route)
            new_fe_route = FERoute(problem)
            solution.add_fe_route(new_fe_route)
            solution.link_routes(new_fe_route, new_se_route)
            _recalculate_fe_route_and_check_feasibility(new_fe_route, problem)
            unserved_customers_list.remove(customer)
        
        elif option_type == 'create_new_se_expand_fe':
            satellite = best_global_option['new_satellite']
            fe_route = best_global_option['fe_route']
            new_se_route = SERoute(satellite, problem)
            new_se_route.insert_customer_at_pos(customer, 1)
            solution.add_se_route(new_se_route)
            solution.link_routes(fe_route, new_se_route)
            _recalculate_fe_route_and_check_feasibility(fe_route, problem)
            unserved_customers_list.remove(customer)
            
        else:
            print(f"\nCanh bao: Khong tim thay phuong an kha thi de phuc vu khach hang {customer.id}")

    solution.unserved_customers = unserved_customers_list
    print("\n>>> Xay dung loi giai ban dau hoan tat!")
    return VRP2E_State(solution)