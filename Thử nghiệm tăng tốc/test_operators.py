# --- START OF FILE test_operators.py ---

import unittest
from problem_parser import ProblemInstance
from solution_generator import generate_initial_solution # Sử dụng tên hàm đã thống nhất
from destroy_operators import random_removal, shaw_removal
from repair_operators import greedy_repair, regret_insertion # THÊM IMPORT MỚI


class TestDestroyOperators(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Chạy một lần trước tất cả các test để tạo lời giải ban đầu.
        """
        print("Setting up initial solution for tests...")
        # !!! THAY ĐỔI ĐƯỜNG DẪN NÀY NẾU CẦN !!!
        file_path = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_10_TD.csv"
        try:
            problem = ProblemInstance(file_path=file_path)
            # Chạy LNS hạn chế với số lần lặp nhỏ để có lời giải ban đầu nhanh
            cls.initial_state = generate_initial_solution(problem, lns_iterations=20, q_percentage=0.4)
            cls.initial_customer_count = len(cls.initial_state.solution.customer_to_se_route_map)
            print(f"Setup complete. Initial solution has {cls.initial_customer_count} customers.")
        except FileNotFoundError:
            print(f"FATAL: Test data file not found at {file_path}. Skipping tests.")
            cls.initial_state = None


    def test_shaw_removal_execution(self):
        """
        Kiểm tra xem shaw_removal có chạy và xóa đúng số lượng khách hàng không.
        """
        if not self.initial_state:
            self.skipTest("Skipping test because initial state could not be created.")

        q = 5
        print(f"\n--- Testing shaw_removal with q={q} ---")
        
        self.assertGreaterEqual(self.initial_customer_count, q, "Not enough customers to test removal.")

        new_state, removed_customers = shaw_removal(self.initial_state, q)
        
        # 1. Kiểm tra số lượng khách hàng bị xóa
        self.assertEqual(len(removed_customers), q, "Incorrect number of customers removed.")
        
        # 2. Kiểm tra số lượng khách hàng còn lại trong lời giải
        remaining_customers = len(new_state.solution.customer_to_se_route_map)
        self.assertEqual(remaining_customers, self.initial_customer_count - q, "Incorrect number of customers remaining in solution.")

        # 3. Kiểm tra tính hợp lệ của lời giải sau khi xóa
        for fe_route in new_state.solution.fe_routes:
            self.assertFalse(not fe_route.serviced_se_routes, "Empty FE route found.")
        for se_route in new_state.solution.se_routes:
            self.assertFalse(not se_route.get_customers(), "Empty SE route found.")
        
        print("shaw_removal execution test passed.")
    def test_regret_insertion_execution(self):
        """
        Kiểm tra xem regret_insertion có chèn lại hết khách hàng không.
        """
        if not self.initial_state:
            self.skipTest("Skipping test because initial state could not be created.")

        q = 5
        print(f"\n--- Testing regret_insertion with q={q} ---")
        
        # 1. Phá hủy lời giải để có một danh sách khách hàng cần chèn
        destroyed_state, customers_to_insert = random_removal(self.initial_state, q)
        self.assertEqual(len(customers_to_insert), q)
        
        # 2. Sửa chữa lời giải bằng regret_insertion
        repaired_state = regret_insertion(destroyed_state, customers_to_insert, k=2) # Dùng k=2 để test cho nhanh

        # 3. Kiểm tra kết quả
        final_customer_count = len(repaired_state.solution.customer_to_se_route_map)
        unserved_count = len(repaired_state.solution.unserved_customers)
        
        # Đảm bảo tất cả khách hàng đã được chèn lại
        self.assertEqual(final_customer_count, self.initial_customer_count, "Not all customers were re-inserted.")
        self.assertEqual(unserved_count, 0, "Some customers were left unserved.")

        print("regret_insertion execution test passed.")


# Cách chạy: Mở terminal trong thư mục dự án và chạy lệnh: python -m unittest test_operators.py
if __name__ == '__main__':
    unittest.main()

# --- END OF FILE test_operators.py ---