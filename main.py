"""

Việc của file này:
1. Tạo cửa sổ, nạp bản đồ, tạo GameView (vẽ) và Controller (điều khiển).
2. Tạo thanh nút bấm / menu chọn, mỗi nút gắn với một hàm xử lý (on_...).
3. Chạy vòng lặp sự kiện của tkinter (root.mainloop()).

"""

import glob
import itertools
import logging
import multiprocessing
import tkinter as tk
from tkinter import ttk

from src.doi_khang import run_adversarial
from src.engine import is_lose, is_win, load_layout, move_pacman
from ui.gui import Controller, GameView
from src.tim_duong import ALGORITHMS, run_search

# hằng số
BASE_DELAY_MS = 20  # độ trễ mỗi khung hình
LOG_FILE = "log_doi_khang.txt"  # file log ghi lại quá trình chạy Minimax / Alpha-Beta / Expectimax

# Mỗi lần bấm nút tốc độ, lấy giá trị kế tiếp trong danh sách (hết thì quay lại).
SPEEDS = itertools.cycle([1, 1.5, 2, 2.5, 3, 0.5])

COMPARE_HEADERS = {
    "algo": "Thuật toán",
    "found": "Tìm thấy",
    "steps": "Số bước",
    "cost": "Chi phí",
    "expanded": "Mở rộng",
    "time": "Thời gian (s)",
}


COMPARE_ADV_HEADERS = {
    "algo": "Thuật toán",
    "value": "Điểm đánh giá",
    "depth": "Độ sâu",
    "expanded": "Mở rộng",
    "time": "Thời gian (s)",
}


def path_cells(layout, state, actions):
    """Danh sách các ô Pacman đi qua"""
    cells = [state.pacman]
    for action in actions:
        state = move_pacman(layout, state, action)
        cells.append(state.pacman)
    return cells


def setup_log():
    """Cài đặt log của chương trình ghi vào file log thay vì in ra terminal"""
    handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")  # mỗi lần mở chương trình ghi lại từ đầu
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%H:%M:%S"))
    log = logging.getLogger("pacman")
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    log.propagate = False


def main():
    setup_log()

    root = tk.Tk()
    root.title("Pacman - Nhóm 4")

    layout, start_state = load_layout("maps/tiny.txt")
    view = GameView(root, layout)
    view.pack()
    controller = Controller(root, layout, start_state, view)
    controller.restart()

    # Thanh nút bấm (phía trên) và dòng thông tin (phía dưới)
    controls = tk.Frame(root)
    controls.pack(fill="x")
    stats = tk.Label(root, text="Chưa chạy thuật toán nào", anchor="w")
    stats.pack(fill="x")

    # Các biến lưu lựa chọn hiện tại của người dùng trong các menu
    map_var = tk.StringVar(value="maps/tiny.txt")  # bản đồ
    algo_var = tk.StringVar(value="BFS")  # thuật toán tìm đường
    adv_var = tk.StringVar(value="Alpha-Beta")  # thuật toán đối kháng
    depth_var = tk.IntVar(value=2)  # độ sâu
    ghost_var = tk.StringVar(value="random")  # kiểu di chuyển của ma

    def on_load_map(_=None):
        """Người chơi chọn bản đồ khác"""
        new_layout, new_start = load_layout(map_var.get())
        controller.layout = new_layout
        controller.start_state = new_start
        controller.set_map(map_var.get())  # playmod: ma greedy không đón đầu
        view.set_layout(new_layout)
        controller.load_actions([])

    def on_run_algo():
        """Chạy thuật toán tìm đường, vẽ đường đi và hiện thống kê"""
        lay, start = controller.layout, controller.start_state
        result = run_search(algo_var.get(), lay, start)

        view.draw_path(path_cells(lay, start, result.actions))
        controller.load_actions(result.actions)

        stats.config(text=(
            f"Tìm thấy: {result.found} | Số bước: {len(result.actions)} | "
            f"Chi phí: {result.total_cost} | Mở rộng: {result.expanded} | "
            f"Thời gian: {result.time_sec:.4f}s"
        ))

    def on_compare_all():
        """Chạy tất cả thuật toán và hiện kết quả trong một bảng ở cửa sổ mới"""
        win = tk.Toplevel(root)
        win.title("So sánh thuật toán")

        # Tạo bảng và các cột
        tree = ttk.Treeview(win, columns=list(COMPARE_HEADERS), show="headings")
        for col, title in COMPARE_HEADERS.items():
            tree.heading(col, text=title)
            tree.column(col, width=100, anchor="center")
        tree.pack(fill="both", expand=True)

        # Mỗi thuật toán là một dòng
        for name in ALGORITHMS:
            r = run_search(name, controller.layout, controller.start_state)
            tree.insert("", "end", values=(name, r.found, len(r.actions), r.total_cost,
                                           r.expanded, f"{r.time_sec:.4f}"))

    def on_compare_adv():
        """Chạy 3 thuật toán đối kháng (cùng độ sâu, chế độ ma) và hiện bảng so sánh."""
        win = tk.Toplevel(root)
        win.title(f"So sánh đối kháng (độ sâu {depth_var.get()})")

        # Tạo bảng và các cột
        tree = ttk.Treeview(win, columns=list(COMPARE_ADV_HEADERS), show="headings", height=3)
        for col, title in COMPARE_ADV_HEADERS.items():
            tree.heading(col, text=title)
            tree.column(col, width=100, anchor="center")
        tree.pack(fill="both", expand=True)

        # Mỗi thuật toán là một dòng. recent=() và time_limit=None: chạy đủ độ sâu, không giới hạn giờ
        for name in ("Minimax", "Alpha-Beta", "Expectimax"):
            r = run_adversarial(name, controller.layout, controller.start_state,
                                depth_var.get(), (), None)
            tree.insert("", "end", values=(name, f"{r.value:.1f}", r.depth,
                                           r.expanded, f"{r.time_sec:.4f}"))

    def on_play_adv():
        """Bắt đầu chơi"""
        view.draw_path([])
        controller.play_adversarial(adv_var.get(), depth_var.get(), ghost_var.get())

    def on_game_end(state):
        """Controller gọi hàm này khi ván kết thúc"""
        if is_win(state):
            result = "Pacman THẮNG"
        elif is_lose(state):
            result = "Pacman THUA"
        else:
            result = "Dừng: thuật toán không trả nước đi"
        stats.config(text=f"{result} | Điểm: {state.score} | Food còn: {len(state.food)}")

    def cycle_speed():
        """tăng tốc độ, tốc độ càng cao thì độ trễ mỗi khung hình càng nhỏ"""
        speed = next(SPEEDS)
        controller.frame_delay_ms = max(8, int(BASE_DELAY_MS / speed))
        speed_button.config(text=f"x{speed}")

    def on_close():
        """Đóng cửa sổ"""
        controller.pool.shutdown(wait=False, cancel_futures=True)
        root.destroy()

    # Tạo thanh nút bấm
    def add_menu(var, *values, command=None):
        """Thêm menu chọn giá trị vào thanh điều khiển"""
        tk.OptionMenu(controls, var, *values, command=command).pack(side="left")

    def add_button(text, command):
        """Thêm nút bấm vào thanh điều khiển và trả về nút đó"""
        button = tk.Button(controls, text=text, command=command)
        button.pack(side="left")
        return button

    controller.on_end = on_game_end  # nhận thông báo hết ván

    # chọn bản đồ + tìm đường
    add_menu(map_var, *sorted(glob.glob("maps/*.txt")), command=on_load_map)
    add_menu(algo_var, *ALGORITHMS)
    add_button("Chạy thuật toán", on_run_algo)

    # điều khiển phát lại
    add_button("Run", controller.play)
    add_button("Pause", controller.pause)
    add_button("Step", controller.step_once)
    add_button("Restart", controller.restart)
    speed_button = add_button("x1", cycle_speed)
    cycle_speed()

    # so sánh và đối kháng
    add_button("So sánh tất cả", on_compare_all)
    add_menu(adv_var, "Minimax", "Alpha-Beta", "Expectimax")
    add_menu(depth_var, 1, 2,3)
    add_menu(ghost_var, "random", "greedy", "chase")
    add_button("Đối kháng", on_play_adv)
    add_button("So sánh đối kháng", on_compare_adv)

    
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()