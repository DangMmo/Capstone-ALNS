# --- START OF FILE config.py ---

# ==============================================================================
# 1. CẤU HÌNH BÀI TOÁN & DỮ LIỆU
# ==============================================================================
# Đường dẫn đầy đủ đến file dữ liệu GỐC (bài toán lớn).
# Đây là file sẽ được sử dụng cho quy trình clustering hoặc giải trực tiếp.
FILE_PATH = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-tight-deadline\\100_customers_TD\\C_100_10_TD.csv"
#FILE_PATH = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_1_D.csv"

# Định nghĩa các mã loại node để code dễ đọc hơn
HUB_TYPE = 0
SATELLITE_TYPE = 1
DELIVERY_TYPE = 2
PICKUP_TYPE = 3

# ==============================================================================
# 2. CẤU HÌNH BỘ GIẢI ALNS
# ==============================================================================

# ----- 2.1. Tham số phương tiện -----
# Tốc độ của phương tiện (đơn vị/thời gian), ảnh hưởng đến việc chuyển đổi khoảng cách sang thời gian.
# Giả định tốc độ của xe FE và SE là như nhau.
VEHICLE_SPEED = 1.0

# Tải trọng của các loại xe (dùng trong cả clustering và bộ giải)
SE_VEHICLE_CAPACITY = 10.0
FE_VEHICLE_CAPACITY = 75.0

# ----- 2.2. Giai đoạn tạo lời giải ban đầu -----
# Số lần lặp LNS để tinh chỉnh lời giải ban đầu.
LNS_INITIAL_ITERATIONS = 25
# Tỷ lệ khách hàng bị phá hủy trong giai đoạn tạo lời giải ban đầu.
Q_PERCENTAGE_INITIAL = 0.4

# ----- 2.3. Giai đoạn ALNS chính -----
# Tổng số lần lặp cho thuật toán ALNS (áp dụng cho mỗi bài toán con nếu chạy clustering).
ALNS_MAIN_ITERATIONS = 250

# ----- 2.4. Các tham số cho Simulated Annealing (SA) -----
# Xác suất chấp nhận lời giải tệ hơn ở ban đầu.
START_TEMP_ACCEPT_PROB = 0.5
# Mức độ tệ hơn (tính theo %) của chi phí di chuyển được dùng để tính nhiệt độ ban đầu.
START_TEMP_WORSENING_PCT = 0.05
# Tỷ lệ làm nguội nhiệt độ sau mỗi lần lặp (càng gần 1 thì càng nguội chậm).
COOLING_RATE = 0.9995

# ----- 2.5. Các tham số cho Cơ chế Học Thích ứng (Adaptive Mechanism) -----
# Hệ số phản ứng (0 < r < 1), quyết định tốc độ học của trọng số.
REACTION_FACTOR = 0.1
# Số lần lặp trong một "segment" trước khi cập nhật lại trọng số toán tử.
SEGMENT_LENGTH = 100
# Điểm thưởng khi tìm thấy lời giải tốt nhất toàn cục (global best).
SIGMA_1_NEW_BEST = 9
# Điểm thưởng khi tìm thấy lời giải tốt hơn lời giải hiện tại (nhưng không phải global best).
SIGMA_2_BETTER = 5
# Điểm thưởng khi chấp nhận một lời giải (kể cả tệ hơn) thông qua SA.
SIGMA_3_ACCEPTED = 2

# ----- 2.6. Các tham số cho Logic Điều khiển ALNS Nâng cao -----
# Khoảng tỷ lệ phá hủy cho chế độ "phá hủy nhỏ" (local search).
Q_SMALL_RANGE = (0.05, 0.2)
# Khoảng tỷ lệ phá hủy cho chế độ "phá hủy lớn" (diversification).
Q_LARGE_RANGE = (0.25, 0.5)
# Số lần phá hủy nhỏ liên tiếp trước khi thực hiện một lần phá hủy lớn.
SMALL_DESTROY_SEGMENT_LENGTH = 500
# Số lần lặp không cải thiện lời giải tốt nhất trước khi khởi động lại về lời giải tốt nhất đã biết.
RESTART_THRESHOLD = 2500

# ----- 2.7. Cấu hình Pruning (Cắt tỉa) cho Logic chèn -----
# Số lượng láng giềng gần nhất (khách hàng khác) để xem xét cho mỗi khách hàng.
PRUNING_K_CUSTOMER_NEIGHBORS = 20
# Số lượng vệ tinh gần nhất để xem xét cho mỗi khách hàng.
PRUNING_M_SATELLITE_NEIGHBORS = 3
# Số lượng tuyến SE hàng đầu (theo độ gần) để xem xét chèn vào.
PRUNING_N_SE_ROUTE_CANDIDATES = 2

# ==============================================================================
# 3. CẤU HÌNH HÀM MỤC TIÊU (OBJECTIVE FUNCTION)
# ==============================================================================
# Thành phần chính của chi phí di chuyển.
# Giá trị hợp lệ: "DISTANCE", "TRAVEL_TIME"
PRIMARY_OBJECTIVE = "TRAVEL_TIME" 

# Bật/tắt thành phần tối ưu hóa số lượng xe.
# Nếu True, chi phí phạt cho mỗi xe sẽ được cộng vào hàm mục tiêu.
OPTIMIZE_VEHICLE_COUNT = True

# Trọng số (chi phí phạt) cho các thành phần.
# WEIGHT_PRIMARY: thường giữ là 1.0.
# WEIGHT_FE/SE_VEHICLE: Chi phí ảo cho việc sử dụng một xe. Đặt giá trị lớn để ưu tiên giảm xe.
WEIGHT_PRIMARY = 1.0
WEIGHT_FE_VEHICLE = 1000.0
WEIGHT_SE_VEHICLE = 200.0

# ==============================================================================
# 4. CẤU HÌNH CLUSTERING (CHO BÀI TOÁN LỚN)
# ==============================================================================
# Khoảng giá trị 'k' (số cụm) để thử nghiệm và tìm giá trị tối ưu bằng Silhouette Score.
K_CLUSTERS_RANGE = range(2, 10) # Thử từ 5 đến 15 cụm

# Hằng số để chuẩn hóa thước đo thời gian, dựa trên thời gian hoạt động trong ngày (ví dụ: 15 giờ * 60 phút = 900).
MAX_SCHEDULING_FLEXIBILITY = 900.0

# ==============================================================================
# 5. CẤU HÌNH QUY TRÌNH CHẠY & KẾT QUẢ
# ==============================================================================
# Nếu True, chương trình sẽ chạy quy trình clustering trước, sau đó giải từng cụm.
# Nếu False, chương trình sẽ giải trực tiếp toàn bộ file trong FILE_PATH.
ENABLE_CLUSTER_PIPELINE = False

# Thư mục tạm thời để lưu các file CSV của từng cụm. Sẽ bị xóa sau khi chạy xong.
CLUSTER_DATA_DIR = "temp_cluster_data"

# Nếu True, chương trình sẽ dừng lại để hỏi người dùng chọn 'k' sau khi phân tích.
# Nếu False, nó sẽ tự động sử dụng 'k' được gợi ý bởi Silhouette Score.
INTERACTIVE_K_SELECTION = True

# Thư mục gốc để lưu kết quả của mỗi lần chạy (log, biểu đồ, config snapshot).
BASE_RESULTS_DIR = "results"

# Nếu True, thư mục 'results' cũ sẽ bị xóa hoàn toàn mỗi khi bắt đầu một lần chạy mới.
# Nếu False, các lần chạy cũ sẽ được giữ lại trong các thư mục con riêng biệt.
CLEAR_OLD_RESULTS_ON_START = True

# Hạt giống cho bộ sinh số ngẫu nhiên để đảm bảo kết quả có thể lặp lại khi cần.
RANDOM_SEED = 42

# --- END OF FILE config.py ---