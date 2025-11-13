# --- START OF FILE core/transaction.py ---

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Union

# Khối này chỉ dùng cho type hinting, không gây lỗi runtime
if TYPE_CHECKING:
    from .data_structures import SERoute, FERoute, Solution

class RouteMemento:
    # ... (Nội dung lớp RouteMemento không đổi)
    def __init__(self, route: Union["SERoute", "FERoute"]):
        if hasattr(route, 'nodes_id'):
            self.nodes_id = route.nodes_id.copy()
            self.total_dist = route.total_dist
            self.total_travel_time = route.total_travel_time
            self.total_load_pickup = route.total_load_pickup
            self.total_load_delivery = route.total_load_delivery
            self.service_start_times = route.service_start_times.copy()
            self.waiting_times = route.waiting_times.copy()
            self.forward_time_slacks = route.forward_time_slacks.copy()
            self.serving_fe_routes = route.serving_fe_routes.copy()
        elif hasattr(route, 'schedule'):
            self.serviced_se_routes = route.serviced_se_routes.copy()
            self.schedule = route.schedule.copy()
            self.total_dist = route.total_dist
            self.total_time = route.total_time
            self.total_travel_time = route.total_travel_time
            self.route_deadline = route.route_deadline
        else:
            raise TypeError(f"Unsupported route type for Memento: {type(route)}")


class ChangeContext:
    # ... (Nội dung các hàm __init__, backup_route, ... không đổi)
    def __init__(self, solution: "Solution"):
        self.solution = solution
        self.affected_routes_mementos: Dict[Union["SERoute", "FERoute"], RouteMemento] = {}
        self.newly_created_routes: List[Union["SERoute", "FERoute"]] = []
        self.removed_routes: List[Union["SERoute", "FERoute"]] = []

    def backup_route(self, route: Union["SERoute", "FERoute"]):
        if route not in self.affected_routes_mementos:
            self.affected_routes_mementos[route] = route.backup()

    def track_new_route(self, route: Union["SERoute", "FERoute"]):
        self.newly_created_routes.append(route)

    def track_removed_route(self, route: Union["SERoute", "FERoute"]):
        self.removed_routes.append(route)

    def rollback(self):
        """Hoàn tác tất cả các thay đổi đã được theo dõi trong context này."""
        
        # <<< SỬA LỖI TẠI ĐÂY >>>
        # Sử dụng import tương đối để tìm module trong cùng package 'core'
        from .data_structures import SERoute, FERoute
        
        # 1. Thêm lại các route đã bị xóa
        for route in self.removed_routes:
            if isinstance(route, SERoute):
                if route not in self.solution.se_routes:
                    self.solution.se_routes.append(route)
            elif isinstance(route, FERoute):
                if route not in self.solution.fe_routes:
                    self.solution.fe_routes.append(route)

        # 2. Xóa các route mới được tạo
        for route in self.newly_created_routes:
            if isinstance(route, SERoute):
                if route in self.solution.se_routes:
                    self.solution.se_routes.remove(route)
            elif isinstance(route, FERoute):
                if route in self.solution.fe_routes:
                    self.solution.fe_routes.remove(route)

        # 3. Khôi phục trạng thái của các route đã bị thay đổi
        for route, memento in self.affected_routes_mementos.items():
            route.restore(memento)
        
        # 4. Cập nhật lại các map toàn cục của Solution
        self.solution.update_customer_map()
# --- END OF FILE core/transaction.py ---