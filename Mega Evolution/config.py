# --- START OF FILE config.py (UPDATED FOR PHASE 2) ---

import random

# ==============================================================================
# 1. CẤU HÌNH BÀI TOÁN & DỮ LIỆU
# ==============================================================================
# Đường dẫn đầy đủ đến file dữ liệu đầu vào
FILE_PATH = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\50_customers_TD\\C_50_10_TD.csv"

# Tốc độ của phương tiện (đơn vị/thời gian), ảnh hưởng đến việc chuyển đổi khoảng cách sang thời gian di chuyển
VEHICLE_SPEED = 1.0


# ==============================================================================
# 2. CẤU HÌNH GIAI ĐOẠN TẠO LỜI GIẢI BAN ĐẦU
# ==============================================================================
# Số lần lặp LNS để tinh chỉnh lời giải ban đầu
LNS_INITIAL_ITERATIONS = 50

# Tỷ lệ khách hàng bị phá hủy trong giai đoạn tạo lời giải ban đầu
Q_PERCENTAGE_INITIAL = 0.4


# ==============================================================================
# 3. CẤU HÌNH GIAI ĐOẠN ALNS CHÍNH
# ==============================================================================
# Tổng số lần lặp cho thuật toán ALNS
ALNS_MAIN_ITERATIONS = 250

# ----- 3.1. Các tham số cho Simulated Annealing (SA) -----
# Xác suất chấp nhận lời giải tệ hơn ở ban đầu
START_TEMP_ACCEPT_PROB = 0.5
# Mức độ tệ hơn (tính theo %) của lời giải được dùng để tính nhiệt độ ban đầu
START_TEMP_WORSENING_PCT = 0.05
# Tỷ lệ làm nguội nhiệt độ sau mỗi lần lặp
COOLING_RATE = 0.99975

# ----- 3.2. Các tham số cho Cơ chế Học Thích ứng (Adaptive Mechanism) -----
# Hệ số phản ứng (reaction factor), quyết định tốc độ học của trọng số
REACTION_FACTOR = 0.5
# Số lần lặp trong một "segment" trước khi cập nhật lại trọng số
SEGMENT_LENGTH = 100
# Điểm thưởng khi tìm thấy lời giải tốt nhất toàn cục
SIGMA_1_NEW_BEST = 9
# Điểm thưởng khi tìm thấy lời giải tốt hơn lời giải hiện tại
SIGMA_2_BETTER = 5
# Điểm thưởng khi chấp nhận một lời giải (kể cả tệ hơn)
SIGMA_3_ACCEPTED = 2

# ----- 3.3. Các tham số cho Logic Điều khiển ALNS Nâng cao (GIAI ĐOẠN 2) -----
# Khoảng tỷ lệ phá hủy cho chế độ "phá hủy nhỏ"
Q_SMALL_RANGE = (0.05, 0.15)
# Khoảng tỷ lệ phá hủy cho chế độ "phá hủy lớn"
Q_LARGE_RANGE = (0.3, 0.5)
# Số lần phá hủy nhỏ liên tiếp trước khi thực hiện một lần phá hủy lớn
SMALL_DESTROY_SEGMENT_LENGTH = 100
# Số lần lặp không cải thiện lời giải tốt nhất trước khi khởi động lại
RESTART_THRESHOLD = 2000


# ==============================================================================
# 4. CẤU HÌNH CHUNG
# ==============================================================================
# Hạt giống cho bộ sinh số ngẫu nhiên để đảm bảo kết quả có thể lặp lại
RANDOM_SEED = 42

# --- END OF FILE config.py ---