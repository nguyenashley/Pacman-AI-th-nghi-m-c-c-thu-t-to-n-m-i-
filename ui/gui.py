"""

File gồm 2 phần chính:
  1. GameView: lo việc vẽ (tường, food, Pacman, ma, đường đi).
  2. Controller: quyết định Pacman đi đâu, ma đi đâu, rồi bảo gameview vẽ.

"""

import logging
import random
import time
import tkinter as tk
from collections import deque
from concurrent.futures import ProcessPoolExecutor

from PIL import Image, ImageTk

import src.doi_khang as dk
from src.engine import (DIRECTIONS, is_lose, is_terminal, is_win, legal_ghost_actions,
                        legal_pacman_actions, move_ghost, move_pacman)

#Nơi ghi log
log = logging.getLogger("pacman")

# Màu sắc
BG = "black"             # màu nền
WALL = "#2121ff"         # màu tường
WALL_BORDER = "#4d4dff"  # màu viền tường
FOOD = "#ffffff"         # màu food
PATH_COLOR = "#782257"   # màu đường đi của thuật toán

# Hướng góc xoay của pacman
ROTATIONS = {"RIGHT": 0, "UP": 90, "LEFT": 180, "DOWN": 270}

PACMAN_FRAME_FILES = [f"assets/{i}.png" for i in range(1, 5)]
GHOST_FRAME_FILES = [f"assets/ghost{i}.png" for i in range(1, 4)]


def compute_cell_size(widget, layout, screen_fraction=0.7):
    """Tính kích thước mỗi ô để bản đồ chiếm 70% màn hình."""
    max_cell_by_width = widget.winfo_screenwidth() * screen_fraction / layout.width
    max_cell_by_height = widget.winfo_screenheight() * screen_fraction / layout.height
    return int(min(max_cell_by_width, max_cell_by_height))


#phần Gameview
class GameView(tk.Canvas):
    def __init__(self, master, layout):
        super().__init__(master, bg=BG, highlightthickness=0)
        self.pacman_id = None
        self.pacman_frame_index = 0 
        self.pacman_base = [Image.open(p).convert("RGBA") for p in PACMAN_FRAME_FILES]
        self.ghost_base = [Image.open(p).convert("RGBA") for p in GHOST_FRAME_FILES]
        self.set_layout(layout)

    def set_layout(self, layout):
        """Hiển thị bản đồ mới thì tính lại kích thước ô, co giãn canvas, tạo lại ảnh và vẽ tường"""
        self.layout = layout
        self.cell = compute_cell_size(self, layout)
        self.config(width=layout.width * self.cell, height=layout.height * self.cell)
        self._rebuild_images()
        self.delete("path")
        self.draw_static()

    def _rebuild_images(self):
        """Tạo lại ảnh Pacman và ma theo kích thước ô hiện tại"""
        size = max(1, int(self.cell * 0.9))

        resized_pacman = [img.resize((size, size), Image.LANCZOS) for img in self.pacman_base]
        self.pacman_frames = {}
        for direction, angle in ROTATIONS.items():
            self.pacman_frames[direction] = [ImageTk.PhotoImage(img.rotate(angle))
                                             for img in resized_pacman]

        self.ghost_imgs = [ImageTk.PhotoImage(img.resize((size, size), Image.LANCZOS))
                           for img in self.ghost_base]

    def _center(self, r, c):
        """Tọa độ của tâm ô (r, c)"""
        x = (c + 0.5) * self.cell
        y = (r + 0.5) * self.cell
        return x, y

    def draw_static(self):
        """Vẽ tường """
        self.delete("wall")
        cell = self.cell
        border = max(1, int(cell * 0.05))
        for r, c in self.layout.walls:
            x, y = c * cell, r * cell
            self.create_rectangle(x + 1, y + 1, x + cell - 1, y + cell - 1,
                                  fill=WALL, outline=WALL_BORDER, width=border, tags="wall")

    def _draw_food(self, state):
        """Xóa food cũ rồi vẽ lại all food"""
        self.delete("food")
        radius = self.cell * 0.12
        for r, c in state.food:
            x, y = self._center(r, c)
            self.create_oval(x - radius, y - radius, x + radius, y + radius,
                             fill=FOOD, outline="", tags="food")

    def _draw_ghosts(self, positions):
        """Vẽ lại tất cả ma"""
        self.delete("ghost")
        for i, (r, c) in enumerate(positions):
            image = self.ghost_imgs[i % len(self.ghost_imgs)]
            x, y = self._center(r, c)
            self.create_image(x, y, image=image, tags="ghost")
        self.tag_raise("pacman")  # đảm bảo Pacman nằm trên ma

    def _draw_pacman(self, r, c, direction=None):
        """Vẽ Pacman tại (r, c)"""
        frames = self.pacman_frames.get(direction, self.pacman_frames["RIGHT"])
        image = frames[self.pacman_frame_index % len(frames)]
        x, y = self._center(r, c)

        if self.pacman_id is None:
            self.pacman_id = self.create_image(x, y, image=image, tags="pacman")
        else:
            self.coords(self.pacman_id, x, y)
            self.itemconfigure(self.pacman_id, image=image)

    def draw_state(self, state, direction=None):
        """Vẽ toàn bộ trạng thái của ván"""
        self._draw_food(state)
        self._draw_ghosts(state.ghosts)
        self._draw_pacman(*state.pacman, direction)

    def animate_move(self, old, new, action, steps=8, delay=20, on_done=None):
        """Trượt Pacman và ma từ trạng thái cũ sang mới trong 8 khung hình."""
        (r0, c0), (r1, c1) = old.pacman, new.pacman

        if old.food != new.food:
            self._draw_food(new)

        def draw_frame(k):
            t = k / steps
            self.pacman_frame_index += 1
            self._draw_pacman(r0 + (r1 - r0) * t, c0 + (c1 - c0) * t, action)

            ghost_positions = []
            for (a, b), (x, y) in zip(old.ghosts, new.ghosts):
                ghost_positions.append((a + (x - a) * t, b + (y - b) * t))
            self._draw_ghosts(ghost_positions)

            if k < steps:
                self.after(delay, lambda: draw_frame(k + 1))
            elif on_done:
                on_done()

        draw_frame(0)

    def draw_path(self, cells):
        """Vẽ đường đi"""
        self.delete("path")
        if len(cells) < 2:
            return
        points = []
        for r, c in cells:
            x, y = self._center(r, c)
            points += [x, y]
        self.create_line(*points, fill=PATH_COLOR, width=self.cell * 0.28,
                         capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="path")
        self.tag_raise("pacman")


# Phần controller
class Controller:
    def __init__(self, root, layout, start_state, view):
        self.root = root
        self.layout = layout
        self.view = view

        # Trạng thái ván đấy
        self.start_state = start_state
        self.state = start_state
        self.last_action = None
        self.playing = False
        self.animating = False
        self.turn = 0
        self.single = False
        self.seed = 42
        self.rng = random.Random(self.seed)

        # Tốc độ animation
        self.frame_delay_ms = 80
        self.anim_steps = 8

        # Mỗi lần restart tăng run_id lên 1, để các callback của ván cũ biết mình phải dừng
        self.run_id = 0
        self.on_end = None  # hàm gọi khi ván kết thúc
        self.next_step = self.step
        self.ghost_mode = "random"

        # phát lại lời giải của tìm đường
        self.actions = []  # danh sách hành động của lời giải
        self.i = 0  # đang ở hành động thứ mấy

        # đối kháng
        self.adv_algo = "Alpha-Beta"
        self.adv_depth = 2
        self.adv_mode = False
        self.adv_time = 0.5
        self.pool = ProcessPoolExecutor(max_workers=1)  # tiến trình phụ để tính trước nước sau
        self.future = None
        self.future_run_id = None
        self.future_state = None
        self.recent = deque(maxlen=6)  # các ô Pacman vừa đi qua, để tránh đi vòng vòng
        self.debug_adv = True  # True: ghi log mỗi nước vào file log
        self._wait_start = None

        # chế độ ma greedy
        self.chase_steps = 5  #đuổi 5 lượt
        self.random_steps = 2  #random 2 lượt

    def load_actions(self, actions):
        self.restart()
        self.actions = actions
        self.next_step = self.step
        self.adv_mode = False

    def step(self):
        """Phát hành động tiếp theo"""
        if self.animating or self.i >= len(self.actions):
            self.playing = False
            self.single = False
            return
        action = self.actions[self.i]
        self.i += 1
        new_state = move_pacman(self.layout, self.state, action)
        self._animate(self.state, action, new_state, self._animation_done)

    def _animation_done(self):
        self.animating = False
        self.playing = self.playing and self.i < len(self.actions)
        if self._should_continue():
            self.root.after(1, self.step)

    def play(self):
        if self.playing:
            return
        self.playing = True
        if not self.animating:
            self.next_step()

    def pause(self):
        self.playing = False

    def step_once(self):
        """Đi 1 nước"""
        if self.playing or self.animating or self.next_step is None:
            return
        self.playing = True
        self.single = True 
        self.next_step()

    def _should_continue(self):
        """Sau mỗi nước xem có nên đi tiếp không? Nếu đang ở chế độ 1 nước thì dừng lại"""
        if self.single:
            self.single = False
            self.playing = False
            return False
        return self.playing

    def restart(self):
        """Đưa ván chơi về trạng thái ban đầu"""
        self.run_id += 1
        self.playing = False
        self.animating = False
        self.state = self.start_state
        self.i = 0
        self.last_action = None
        self.future = None
        self.recent.clear()
        self.turn = 0
        self.single = False
        self.rng.seed(self.seed)
        self.view.draw_state(self.state)


    def _animate(self, old, action, new, on_done):
        """Cập nhật trạng thái và chạy animation từ cũ sang mới"""
        self.state = new
        self.last_action = action
        self.animating = True
        self.view.animate_move(old, new, action, self.anim_steps, self.frame_delay_ms, on_done)

    def _start(self, next_step, adv_mode):
        """Bắt đầu một ván mới"""
        self.restart()
        self.next_step = next_step
        self.adv_mode = adv_mode
        self.playing = True
        next_step()

    def _ready(self):
        """True nếu tới lượt đi, nếu ván đã kết thúc thì báo kết thúc rồi trả về False"""
        if not self.playing or self.animating:
            return False
        if is_terminal(self.state):
            self._finish()
            return False
        return True

    def _finish(self):
        """Kết thúc ván"""
        self.playing = False
        self.single = False
        if self.debug_adv and self.adv_mode:   # chỉ ghi khi đang chơi đối kháng
            result = "THẮNG" if is_win(self.state) else "THUA" if is_lose(self.state) else "DỪNG"
            log.info("=== KẾT THÚC: Pacman %s | điểm: %s | food còn: %d ===",
                     result, self.state.score, len(self.state.food))
        if self.on_end:
            self.on_end(self.state)

    def _launch(self, old, action):
        """Pacman đi action, sau đó ma đi rồi chạy animation"""
        self.recent.append(old.pacman)
        after_pacman = move_pacman(self.layout, old, action)
        new = self._move_ghosts(after_pacman)

        # tính trước nước kế tiếp trong lúc animation đang chạy
        if self.adv_mode and not is_terminal(new):
            self._prefetch(new)
        rid = self.run_id
        self._animate(old, action, new, lambda: self._after_pacman(rid))

    def _after_pacman(self, rid):
        """Gọi khi animation xong vẽ lại cho chuẩn rồi đi nước kế tiếp"""
        if rid != self.run_id:
            return
        self.animating = False
        self.view.draw_state(self.state, self.last_action)
        if self._should_continue():
            self.root.after(1, self.next_step)

    def _move_ghosts(self, s):
        """Cho từng con ma đi một bước rồi trả về trạng thái mới"""
        mode = self.ghost_mode
        if mode == "chase":
            chase = True
        elif mode == "greedy":
            cycle = self.chase_steps + self.random_steps
            chase = self.turn % cycle < self.chase_steps
        else:
            chase = False
        self.turn += 1

        # tính khoảng cách từ mọi ô tới Pacman (để ma biết đường đi ngắn nhất)
        dist = self._reach([s.pacman], 10 ** 9) if chase else None
        for i in range(len(s.ghosts)):
            if is_terminal(s):
                break
            actions = legal_ghost_actions(self.layout, s, i)
            if actions:
                action = self._pick_ghost_action(s, i, actions, dist)
                s = move_ghost(self.layout, s, i, action)
        return s

    def _pick_ghost_action(self, s, i, actions, dist):
        """Chọn hướng đi cho ma thứ i
        dist = none => đi ngẫu nhiên, ngược lại chọn hướng đưa ma gần Pacman nhất"""
        if self.ghost_mode == "random" or dist is None:
            return self.rng.choice(actions)

        ghost_r, ghost_c = s.ghosts[i]

        def distance_after(action):
            dr, dc = DIRECTIONS[action]
            return dist.get((ghost_r + dr, ghost_c + dc), 1e9)

        best = min(distance_after(a) for a in actions)
        best_actions = [a for a in actions if distance_after(a) == best]
        return self.rng.choice(best_actions)  # nhiều hướng bằng nhau thì chọn ngẫu nhiên


    def play_adversarial(self, algo, depth, ghost_mode):
        self.adv_algo = algo
        self.adv_depth = depth
        self.ghost_mode = ghost_mode
        if self.debug_adv:
            log.info("=== VÁN MỚI | thuật toán: %s | độ sâu: %d | ma: %s ===",
                     algo, depth, ghost_mode)
        self._start(self._adv_step, True)

    def _adv_step(self):
        if not self._ready():
            return
        # Kết quả tính trước có dùng được không
        prefetched = (self.future is not None
                      and self.future_run_id == self.run_id
                      and self.future_state is self.state)

        if prefetched:
            if not self.future.done():
                if self._wait_start is None:
                    self._wait_start = time.time()
                self.root.after(10, self._adv_step)
                return
            result = self.future.result()
            if self.debug_adv:
                waited = 0.0 if self._wait_start is None else time.time() - self._wait_start
                log.info("Nước %d | %s | đi: %s | điểm đánh giá: %.1f | độ sâu hoàn thành: %d | "
                         "tính: %.3fs | mở rộng: %d | Pacman phải chờ: %.3fs",
                         self.turn + 1, self.adv_algo, result.action, result.value, result.depth,
                         result.time_sec, result.expanded, waited)
            self._wait_start = None
        else:
            # Không có kết quả tính trước => nhờ tiến trình phụ tính
            self._prefetch(self.state)
            self.root.after(10, self._adv_step)
            return
        self.future = None

        if result.action is None:
            self._finish()
            return
        self._launch(self.state, result.action)

    def _prefetch(self, s):
        """Nhờ tiến trình phụ tính trước nước đi cho trạng thái s"""
        self._wait_start = None
        self.future_run_id = self.run_id
        self.future_state = s
        self.future = self.pool.submit(dk.run_adversarial, self.adv_algo, self.layout, s,
                                       self.adv_depth, tuple(self.recent), self.adv_time,
                                       self.ghost_mode)

    def _reach(self, starts, limit):
        "Trả về tập các ô và khoảng cách của nó đến ô ban đầu"
        lay = self.layout
        dist = {p: 0 for p in starts}
        queue = deque(starts)

        while queue:
            p = queue.popleft()
            if dist[p] >= limit:
                continue
            for dr, dc in DIRECTIONS.values():
                n = (p[0] + dr, p[1] + dc)
                inside_map = 0 <= n[0] < lay.height and 0 <= n[1] < lay.width
                if n in dist or n in lay.walls or not inside_map:
                    continue
                dist[n] = dist[p] + 1
                queue.append(n)
        return dist