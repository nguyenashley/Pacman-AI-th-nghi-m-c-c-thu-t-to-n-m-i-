# Đóng góp của các thành viên - Nhóm 4

## Bảng tổng hợp

| Thành viên     | Vai trò                     | Phụ trách chính                                  | Tỉ lệ đóng góp |
| -------------- | --------------------------- | ------------------------------------------------ | -------------- |
| Nguyễn Thảo Ly | Engine, giao diện, tích hợp | `src/engine.py`, `ui/gui.py`, `main.py`, `maps/` | ...%           |
| Vũ Quốc Anh    | Tìm kiếm đường đi           | `src/tim_duong.py`                               | ...%           |
| Hoàng Lộc      | Đối kháng                   | `src/doi_khang.py`                               | ...%           |
| Thanh Bình     | Kiểm thử, báo cáo           | `tests/`, `report.pdf`                           | ...%           |

## Chi tiết

### Nguyễn Thảo Ly - Engine, giao diện, tích hợp

- Thiết kế định dạng bản đồ (`%` tường, `P` Pacman, `G` ma, `.` thức ăn, chữ số 1-9 là chi phí ô) và viết hàm đọc bản đồ `load_layout`.
- Cài đặt luật chơi trong `src/engine.py`: trạng thái bất biến `GameState`, nước đi hợp lệ, chi phí bước đi, điểm thưởng thức ăn, điều kiện thắng/thua, bài toán `PathProblem` / `AllFoodProblem`.
- Xây dựng giao diện Tkinter (`ui/gui.py`, `main.py`): vẽ bản đồ, hoạt ảnh di chuyển, chọn bản đồ/thuật toán, điều khiển Run/Pause/Step/Restart, bảng so sánh thuật toán.
- Cài đặt cách ma di chuyển (random, greedy, chase) và tích hợp các thuật toán của các bạn vào giao diện.
- Tạo các bản đồ trong `maps/`.

### Vũ Quốc Anh - Tìm kiếm đường đi

- Cài đặt DFS, BFS, UCS, Greedy, A\* trong `src/tim_duong.py` cho bài toán ăn hết thức ăn.
- Thiết kế heuristic cho A\* (khoảng cách Manhattan tới thức ăn xa nhất) và heuristic riêng cho Greedy.
- Lập luận bốn tính chất của heuristic (không âm, bằng 0 tại đích, admissible, consistent) trong báo cáo.

### Hoàng Lộc - Đối kháng

- Cài đặt Minimax, Alpha-Beta, Expectimax trong `src/doi_khang.py`.
- Thiết kế hàm đánh giá (khoảng cách thức ăn, nguy hiểm từ ma, vùng an toàn) và các biện pháp chống đi qua đi lại.
- Mô hình xác suất hành vi ma cho Expectimax theo từng kiểu ma (random, greedy, chase).
- Xử lý nhiều ma không đi trùng ô.

### Thanh Bình - Kiểm thử, báo cáo

- Viết và chạy bộ test trong `tests/` (engine, tìm đường, đối kháng, bản đồ).
- Chơi thử, ghi nhận lỗi và báo lại cho nhóm.
- Tổng hợp và hoàn thiện báo cáo `report.pdf`.

### Phần làm chung

- Thực nghiệm và file kết quả trong `results/`
- Thiết kế bản đồ thử nghiệm
