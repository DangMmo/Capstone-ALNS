# Capstone-ALNS
Chắc chắn rồi. Một file README.md rõ ràng là rất cần thiết để quản lý dự án và hiểu cách các thành phần hoạt động cùng nhau. Dưới đây là một bản README.md được cấu trúc đơn giản, dễ hiểu, tóm tắt toàn bộ dự án của bạn tính đến thời điểm hiện tại.

Dự án 2E-VRP-PDD Solver (Phiên bản Initial Solution)
1. Giới thiệu

Dự án này nhằm xây dựng một bộ giải (solver) cho bài toán Định tuyến xe hai cấp với Giao hàng, Nhận hàng và Deadline (2E-VRP-PDD). Đây là một bài toán logistics phức tạp, mô phỏng hoạt động giao nhận trong các đô thị lớn.

Hiện tại, dự án tập trung vào việc xây dựng một Lời giải ban đầu (Initial Solution) chất lượng cao thông qua phương pháp Heuristic Phân rã và Xây dựng (Cluster-first, Route-second Heuristic).

Mục tiêu chính:

Phân chia bài toán lớn thành các cụm khách hàng nhỏ hơn.

Xây dựng các tuyến đường hợp lệ cho xe cấp 2 (SE - Second Echelon) phục vụ từng cụm.

Xây dựng các tuyến đường hợp lệ cho xe cấp 1 (FE - First Echelon) kết nối Kho với các Vệ tinh.

Đảm bảo tuân thủ các ràng buộc về sức chứa, cửa sổ thời gian, và (tùy chọn) deadline.

2. Cấu trúc Dự án & Danh sách File

Dự án bao gồm các file mã nguồn Python chính sau:

Các file cơ sở (Dữ liệu & Cấu trúc)

📄 Parser.py:

Chức năng: Đọc dữ liệu từ file CSV đầu vào (ví dụ: CS_2_D.csv).

Vai trò: Chuyển đổi dữ liệu thô thành các đối tượng Python (Depot, Satellite, Customer) và tạo ra đối tượng ProblemInstance chứa toàn bộ thông tin bài toán.

📄 DataStructures.py:

Chức năng: Định nghĩa các lớp để biểu diễn lời giải.

Thành phần:

class SERoute: Đại diện cho một tuyến đường xe cấp 2 (Vệ tinh -> Khách hàng -> Vệ tinh). Chứa logic tính toán thời gian và kiểm tra tính khả thi chèn điểm.

class FERoute: Đại diện cho một tuyến đường xe cấp 1 (Kho -> Vệ tinh A -> Vệ tinh B -> ... -> Kho).

class Solution: Đối tượng chứa toàn bộ lời giải (danh sách các tuyến FE, SE, và khách hàng chưa phục vụ).

Các file Logic (Thuật toán)

📄 manual_clustering.py:

Chức năng: Thực hiện bước Phân cụm (Clustering).

Đặc điểm: Sử dụng thước đo dị biệt STD (Spatial-Temporal-Demand) và thuật toán K-Medoids. Cho phép người dùng chỉ định số lượng cụm (K) mong muốn.

📄 SolutionBuilder.py:

Chức năng: Thực hiện bước Xây dựng Tuyến (Routing).

Quy trình:

Nhận danh sách các cụm từ manual_clustering.py.

Xây dựng các tuyến SE ban đầu cho từng cụm bằng thuật toán chèn tham lam.

Xây dựng các tuyến FE ban đầu để phục vụ các vệ tinh.

Thực hiện Pha Giải Cứu (Rescue Phase) để cố gắng phục vụ những khách hàng bị bỏ sót.

Xây dựng lại toàn bộ tuyến FE để tối ưu hóa sau khi giải cứu.

Các file Công cụ & Thực thi

📄 main_flexible.py (File Chạy Chính):

Chức năng: Điều phối toàn bộ quy trình và là nơi người dùng tương tác.

Cách dùng: Cho phép cấu hình file dữ liệu, số cụm K, và tùy chọn bật/tắt ràng buộc Deadline. In kết quả chi tiết ra màn hình.

📄 verify_feasibility.py:

Chức năng: Công cụ kiểm tra dữ liệu độc lập.

Mục đích: Xác định các khách hàng "bất khả thi" về mặt vật lý (thời gian di chuyển tối thiểu từ kho lớn hơn thời hạn nhận hàng của họ). Giúp giải thích tại sao một số khách hàng không bao giờ được phục vụ.

3. Cách sử dụng

Để chạy chương trình và tạo ra lời giải ban đầu:

Cài đặt thư viện: Đảm bảo bạn đã cài đặt các thư viện cần thiết:

code
Bash
download
content_copy
expand_less
pip install numpy pandas scikit-learn matplotlib kmedoids_py

Cấu hình: Mở file main_flexible.py.

Thay đổi biến file_name để trỏ đến file dữ liệu CSV của bạn.

Điều chỉnh biến K_VALUE (số cụm mong muốn).

Đặt CONSIDER_DEADLINE = True hoặc False tùy theo kịch bản bạn muốn kiểm tra.

Thực thi: Chạy file main_flexible.py từ terminal hoặc IDE của bạn.

code
Bash
download
content_copy
expand_less
python main_flexible.py

Xem kết quả: Kết quả chi tiết về quá trình phân cụm, các tuyến đường được tạo, tổng chi phí, và danh sách khách hàng không được phục vụ (nếu có) sẽ được in ra màn hình.

Để kiểm tra dữ liệu đầu vào (tìm khách hàng bất khả thi):

Mở file verify_feasibility.py và cập nhật đường dẫn file_name.

Chạy file:

code
Bash
download
content_copy
expand_less
python verify_feasibility.py
4. Tình trạng Hiện tại & Ghi chú Quan trọng

Trạng thái: Chương trình hiện tại có khả năng tạo ra một lời giải ban đầu khả thi (tuân thủ các ràng buộc).

Vấn đề đã biết: Với các bộ dữ liệu lớn và phức tạp (như CS_2_D.csv), số lượng khách hàng không được phục vụ có thể rất lớn.

Nguyên nhân: Điều này chủ yếu là do:

Dữ liệu chứa các khách hàng "bất khả thi" về mặt vật lý (xác minh bằng verify_feasibility.py).

Bản chất "tham lam" của thuật toán xây dựng, dẫn đến việc lấp đầy các tuyến đường quá sớm và không tối ưu toàn cục (Hiệu ứng "Cầu tuyết").

Hướng phát triển tiếp theo: Để giảm số lượng khách hàng không được phục vụ và cải thiện chất lượng lời giải, cần triển khai các thuật toán cải thiện (Improvement Heuristics) như Large Neighborhood Search (LNS) để tối ưu hóa lời giải ban đầu này.

(File README này được tạo vào ngày [Ngày hiện tại] cho phiên bản Initial Solution)
