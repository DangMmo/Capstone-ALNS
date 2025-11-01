# --- File Paths and Basic Info ---
#DATA_PATH = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\instance-set-case-study\\CS_1_D.csv"
#DATA_PATH = "C:\\Users\\Dang\\Documents\\Capstone\\2e-vrp-pdd-main\\J&T Case Study\\A_100_1_TD.csv"
DATA_PATH = "C:\\Users\\Dang\\Documents\\Capstone\\Khách hàng\\output\\Generated_Instance_1710_Cus_Fixed.csv"
OUTPUT_DIR = "output_clusters" # Thư mục để lưu các file CSV kết quả

# --- Node Types ---
# Định nghĩa các mã loại để code dễ đọc hơn
HUB_TYPE = 0
SATELLITE_TYPE = 1
DELIVERY_TYPE = 2  # Giao hàng (last-mile)
PICKUP_TYPE = 3    # Lấy hàng (first-mile)

# --- Vehicle Parameters ---
# Tải trọng của các loại xe
SE_VEHICLE_CAPACITY = 160.0
FE_VEHICLE_CAPACITY = 750.0

# Tốc độ trung bình (đơn vị: mét / phút)
# Dựa theo paper của Zamal, bạn có thể điều chỉnh nếu cần
SE_VEHICLE_SPEED = 350.0
FE_VEHICLE_SPEED = 350.0

# --- Clustering Parameters ---
# Khoảng giá trị 'k' (số cụm) để thử nghiệm tìm giá trị tối ưu
K_CLUSTERS_RANGE = range(2, 10) # Thử từ 2 đến 15 cụm

# --- Dissimilarity Metric Parameters ---
# Hằng số để chuẩn hóa thước đo thời gian, dựa trên thời gian hoạt động trong ngày (ví dụ: 15 giờ * 60 phút)
MAX_SCHEDULING_FLEXIBILITY = 900.0

# Trọng số để cân bằng giữa các thành phần của thước đo STD-PDD
# Bạn có thể thử nghiệm với các giá trị khác nhau sau này
# Ví dụ: W_SPATIAL=1.0, W_TEMPORAL=0.5, W_DEMAND=0.5
W_SPATIAL = 1.0
W_TEMPORAL = 1.0
W_DEMAND = 1.0