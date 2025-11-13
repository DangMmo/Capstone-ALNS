import math
import random
from typing import Callable, List, Tuple, Dict, TYPE_CHECKING
import config

from adaptive_mechanism import AdaptiveOperatorSelector
from transaction import ChangeContext  # <<< Import mới

if TYPE_CHECKING:
    from data_structures import VRP2E_State, Solution
    from problem_parser import Customer

# Các type hint được cập nhật để phản ánh signature mới của các toán tử
DestroyOperatorFunc = Callable[['Solution', 'ChangeContext', int], List['Customer']]
RepairOperatorFunc = Callable[['Solution', 'ChangeContext', List['Customer']], None]


def run_local_search_phase(initial_state: "VRP2E_State", iterations: int, q_percentage: float, 
                           destroy_op: Callable, repair_op: Callable) -> "VRP2E_State":
    """
    Pha LNS đơn giản để tinh chỉnh lời giải, đã được cập nhật để dùng cơ chế mới.
    Chỉ chấp nhận các lời giải tốt hơn.
    """
    current_state = initial_state  # Không copy, làm việc trực tiếp
    best_state = initial_state.copy() # Chỉ copy một lần để lưu best

    print("--- Starting Local Search Refinement ---")
    for i in range(iterations):
        context = ChangeContext(current_state.solution)
        cost_before = current_state.cost

        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0:
            print("No customers to optimize. Stopping.")
            break
        
        q = max(2, int(num_cust * q_percentage))
        
        # Thực hiện thay đổi tại chỗ
        removed_customers = destroy_op(current_state.solution, context, q)
        repair_op(current_state.solution, context, removed_customers)

        cost_after = current_state.cost
        best_cost = best_state.cost
        log_str = f"  LNS Iter {i+1:>4}/{iterations} | Current: {cost_before:>10.2f}, New: {cost_after:>10.2f}, Best: {best_cost:>10.2f}"

        if cost_after < cost_before:
            # Commit (Không cần làm gì)
            log_str += " -> ACCEPTED"
            if cost_after < best_cost:
                best_state = current_state.copy() # Deepcopy để lưu snapshot tốt nhất
                log_str += " (NEW BEST!)"
        else:
            # Rollback
            context.rollback()
            assert abs(current_state.cost - cost_before) < 1e-9 # Đảm bảo rollback thành công

        print(log_str)
        
    print(f"--- Local Search complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state


def run_alns_phase(initial_state: "VRP2E_State", iterations: int, 
                   destroy_operators: Dict[str, DestroyOperatorFunc], 
                   repair_operators: Dict[str, RepairOperatorFunc]) -> Tuple["VRP2E_State", Tuple[List, List]]:
    """
    Pha ALNS chính, đã được tái cấu trúc hoàn toàn để loại bỏ deepcopy trong vòng lặp.
    """
    current_state = initial_state  # Không copy, làm việc trực tiếp
    best_state = initial_state.copy()      # Chỉ copy một lần để lưu trữ snapshot tốt nhất

    operator_selector = AdaptiveOperatorSelector(destroy_operators, repair_operators, config.REACTION_FACTOR)
    
    # Tính nhiệt độ ban đầu
    T_start = 0
    if config.START_TEMP_ACCEPT_PROB > 0 and current_state.cost > 0:
        T_start = -(config.START_TEMP_WORSENING_PCT * current_state.cost) / math.log(config.START_TEMP_ACCEPT_PROB)
    T = T_start if T_start > 0 else 1.0 # Tránh T=0

    fe_route_pool, se_route_pool = [], []
    
    print(f"\n--- Starting ALNS Phase ---")
    print(f"  Iterations: {iterations}, Initial Temp: {T:.2f}, Initial Cost: {current_state.cost:.2f}")

    small_destroy_counter = 0
    iterations_without_improvement = 0

    for i in range(1, iterations + 1):
        # 1. Bắt đầu giao dịch mới cho vòng lặp này
        context = ChangeContext(current_state.solution)
        cost_before_change = current_state.cost

        # 2. Chọn toán tử và xác định chiến lược (phá hủy lớn/nhỏ)
        destroy_op_obj = operator_selector.select_destroy_operator()
        repair_op_obj = operator_selector.select_repair_operator()
        num_cust = len(current_state.solution.customer_to_se_route_map)
        if num_cust == 0: break

        is_large_destroy = (small_destroy_counter >= config.SMALL_DESTROY_SEGMENT_LENGTH)
        
        if is_large_destroy:
            # LƯU Ý: Phá hủy từ best_state đòi hỏi logic phức tạp hơn (copy best_state, 
            # sửa nó, rồi gán lại cho current_state).
            # Để đơn giản hóa bước đầu, ta vẫn phá hủy từ current_state nhưng với q lớn hơn.
            q_percentage = random.uniform(*config.Q_LARGE_RANGE)
            small_destroy_counter = 0
        else:
            q_percentage = random.uniform(*config.Q_SMALL_RANGE)
            small_destroy_counter += 1
        
        q = max(2, int(num_cust * q_percentage))

        # 3. Thực thi destroy & repair tại chỗ
        removed_customers = destroy_op_obj.function(current_state.solution, context, q)
        repair_op_obj.function(current_state.solution, context, removed_customers)

        # 4. Đánh giá kết quả
        cost_after_change = current_state.cost
        sigma_update = 0
        log_msg = ""
        accepted = False

        if cost_after_change < cost_before_change:
            accepted = True
            if cost_after_change < best_state.cost:
                sigma_update = config.SIGMA_1_NEW_BEST
                log_msg = f"(NEW BEST: {cost_after_change:.2f})"
            else:
                sigma_update = config.SIGMA_2_BETTER
                log_msg = f"(Accepted: {cost_after_change:.2f})"
        elif T > 1e-6 and random.random() < math.exp(-(cost_after_change - cost_before_change) / T):
            accepted = True
            sigma_update = config.SIGMA_3_ACCEPTED
            log_msg = f"(SA Accepted: {cost_after_change:.2f})"

        # 5. Quyết định Commit hoặc Rollback
        if accepted:
            # COMMIT: Không làm gì, thay đổi đã được giữ lại
            operator_selector.update_scores(destroy_op_obj, repair_op_obj, sigma_update)
            # fe_route_pool.extend(current_state.solution.fe_routes) # Logic cho post-processing
            # se_route_pool.extend(current_state.solution.se_routes)
            if cost_after_change < best_state.cost:
                best_state = current_state.copy() # Lưu lại snapshot tốt nhất
        else:
            # ROLLBACK
            context.rollback()

        # 6. Cập nhật trạng thái thuật toán
        if sigma_update == config.SIGMA_1_NEW_BEST:
            iterations_without_improvement = 0
        else:
            iterations_without_improvement += 1
        
        if iterations_without_improvement >= config.RESTART_THRESHOLD:
            print(f"  >>> Restart triggered at iter {i}. Resetting to best known solution. <<<")
            current_state = best_state.copy() # Reset current_state về trạng thái tốt nhất đã lưu
            iterations_without_improvement = 0
        
        T *= config.COOLING_RATE
        
        if i % config.SEGMENT_LENGTH == 0:
            operator_selector.update_weights()
            
        if i % 100 == 0 or log_msg:
            print(f"  Iter {i:>5}/{iterations} | Best: {best_state.cost:<10.2f} | Current: {current_state.cost:<10.2f} | Temp: {T:<8.2f} | Ops: {destroy_op_obj.name}/{repair_op_obj.name} | {log_msg}")
    
    print(f"\n--- ALNS phase complete. Best cost found: {best_state.cost:.2f} ---")
    return best_state, (fe_route_pool, se_route_pool)