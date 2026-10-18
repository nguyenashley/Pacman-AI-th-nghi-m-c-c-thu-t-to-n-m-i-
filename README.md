# Pacman - Nhóm 4

Đồ án môn Biểu diễn tri thức: cài đặt Pacman với hai nhóm bài toán trên cùng một bản đồ: **tìm đường** (Pacman đi một mình) và **đối kháng** (Pacman đối đầu với Ghost).

## Thành viên

| Họ tên         | Phụ trách                                      |
| -------------- | ---------------------------------------------- |
| Nguyễn Thảo Ly | Engine, giao diện, tích hợp                    |
| Vũ Quốc Anh    | Tìm kiếm đường đi (DFS, BFS, UCS, Greedy, A\*) |
| Hoàng Lộc      | Đối kháng (Minimax, Alpha-Beta, Expectimax)    |
| Thanh Bình     | Kiểm thử, báo cáo                              |

Chi tiết đóng góp xem trong `CONTRIBUTIONS.md`.

## Môi trường

- Python 3.10 trở lên
- Hệ điều hành: Windows
- Thư viện: `pillow`, `pytest` (xem `requirements.txt`)

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy chương trình

```bash
python main.py
```

Cách dùng giao diện:

1. Chọn bản đồ trong ô **chọn bản đồ**.
2. Chọn thuật toán:
   - Tìm đường: DFS, BFS, UCS, Greedy, A\*
   - Đối kháng: Minimax, Alpha-Beta, Expectimax (chọn độ sâu và kiểu Ghost: ngẫu nhiên hoặc đuổi theo)
3. Bấm nút chạy để Pacman di chuyển. Có thể tạm dừng, đi từng bước, chạy lại hoặc đổi tốc độ.
4. Có chức năng so sánh các thuật toán (số bước, chi phí, số nút mở rộng, thời gian).

Quá trình chạy của các thuật toán đối kháng được ghi vào file `log_doi_khang.txt`.

## Chạy test

```bash
python -m pytest tests/ -v
```

## thực nghiệm

Kết quả thực nghiệm được lưu trong `results/`:

- `search_results.csv`, `search_heuristic.csv`: so sánh các thuật toán tìm đường
- `adversarial_compare.csv`, `adversarial_games.csv`: so sánh các thuật toán đối kháng

## Cấu trúc thư mục

```
P1_Nhom4/
├── src/                  mã nguồn thuật toán và logic Pacman
│   ├── engine.py         đọc bản đồ, luật chơi, hàm chuyển trạng thái
│   ├── tim_duong.py      DFS, BFS, UCS, Greedy, A*
│   └── doi_khang.py      Minimax, Alpha-Beta, Expectimax
├── ui/                   mã nguồn giao diện (Tkinter)
│   └── gui.py            GameView (vẽ) và Controller (điều khiển)
├── assets/               hình ảnh Pacman, Ghost
├── tests/                kiểm thử của nhóm
├── maps/                 các bản đồ sử dụng
├── results/              kết quả thực nghiệm (CSV)
├── main.py               điểm bắt đầu chương trình
├── run_experiments.py    chạy thực nghiệm và xuất CSV
├── requirements.txt      thư viện cần cài
├── README.md
├── CONTRIBUTIONS.md
└── report.pdf            báo cáo
```

## Định dạng bản đồ

Mỗi bản đồ là một file `.txt` trong `maps/`:

| Ký tự        | Ý nghĩa                             |
| ------------ | ----------------------------------- |
| `%`          | Tường                               |
| `P`          | Vị trí xuất phát của Pacman         |
| `.`          | Thức ăn                             |
| `G`          | Ghost                               |
| `1`-`9`      | Ô có chi phí đi vào bằng giá trị đó |
| khoảng trắng | Ô trống                             |

Để thêm bản đồ mới: tạo file `.txt` trong `maps/`, sau đó chọn trong ô chọn bản đồ trên giao diện.

## Giới hạn đã biết

- DFS và Greedy không đảm bảo đường đi tối ưu.
- Minimax/Alpha-Beta/Expectimax chạy chậm khi độ sâu lớn hoặc có nhiều Ghost.
- Bản đồ không có lời giải (`no_solution.txt`) chỉ báo không tìm thấy đường đi.
- Ghost đuổi theo chọn hướng gần Pacman nhất theo từng bước, không lập kế hoạch dài hạn.
- Chương trình chỉ được kiểm thử trên Windows.
- Chưa có âm thanh.
