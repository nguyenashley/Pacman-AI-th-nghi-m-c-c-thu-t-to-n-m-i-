"""
run_experiments.py - Chạy thí nghiệm cho báo cáo và ghi kết quả ra file CSV trong thư mục results/.

Chạy từ thư mục gốc của dự án (nơi có main.py):
    python run_experiments.py                 # chạy cả 4 nhóm thí nghiệm
    python run_experiments.py --only search   # chỉ chạy 1 nhóm (search / heuristic / adversarial / games)
    python run_experiments.py --quick         # bản nhanh: ít độ sâu, ít seed (để thử trước)

4 file CSV được tạo:
    results/search_results.csv       DFS/BFS/UCS/Greedy/A* trên mọi bản đồ (Pacman đi một mình, bỏ ghost)
    results/search_heuristic.csv     UCS vs A* (h=0) vs A* (heuristic của nhóm) trên bài toán ăn hết food
    results/adversarial_compare.csv  Minimax vs Alpha-Beta vs Expectimax tại trạng thái đầu, theo độ sâu
    results/adversarial_games.csv    chơi nguyên ván với ghost random/greedy/chase, ghi thắng/thua/điểm

Ghost trong các ván chơi di chuyển giống hệt trong GUI (src/gui.py): cùng luật random / greedy / chase,
mỗi ván dùng một seed riêng nên chạy lại sẽ ra đúng kết quả cũ.
"""

import argparse
import csv
import glob
import os
import random
import sys
import time
from collections import deque
from dataclasses import replace

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)  # để chạy được dù đứng ở thư mục nào

from src.doi_khang import ADVERSARIAL_ALGORITHMS, run_adversarial
from src.engine import (
    DIRECTIONS, AllFoodProblem, is_lose, is_terminal, is_win,
    legal_ghost_actions, load_layout, move_ghost, move_pacman,
)
from src.tim_duong import ALGORITHMS, _best_first, heuristic

MAPS_DIR = os.path.join(ROOT, "maps")
DEFAULT_OUT = os.path.join(ROOT, "results")

# Các thông số giống GUI để kết quả khớp với những gì nhìn thấy khi chạy giao diện
CHASE_STEPS = 5      # ghost "greedy": đuổi 5 lượt...
RANDOM_STEPS = 2     # ...rồi đi bừa 2 lượt
RECENT_SIZE = 6      # Pacman nhớ 6 ô vừa đi qua để tránh quay đầu
GHOST_MODES = ("random", "greedy", "chase")


# ======================================================================
# TIỆN ÍCH
# ======================================================================
def list_maps():
    """Trả về [(tên bản đồ, đường dẫn)] cho mọi file .txt trong maps/, theo thứ tự tên."""
    paths = sorted(glob.glob(os.path.join(MAPS_DIR, "*.txt")))
    return [(os.path.splitext(os.path.basename(p))[0], p) for p in paths]


def write_csv(out_dir, filename, header, rows):
    """Ghi một file CSV (utf-8-sig để Excel trên Windows mở không lỗi font)."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    try:
        shown = os.path.relpath(path, ROOT)
    except ValueError:  # Windows: thư mục ghi nằm khác ổ đĩa với dự án (vd. C: và D:) thì không tính được đường dẫn tương đối
        shown = path
    print(f"  -> đã ghi {shown} ({len(rows)} dòng)")


def map_info(name, layout, state):
    """Các cột mô tả bản đồ, dùng chung cho mọi file CSV."""
    open_cells = layout.width * layout.height - len(layout.walls)
    return [name, f"{layout.height}x{layout.width}", open_cells,
            len(state.food), len(state.ghosts), len(layout.costs)]


MAP_COLUMNS = ["map", "size", "open_cells", "food", "ghosts", "weighted_cells"]


def fmt_time(seconds):
    return f"{seconds:.6f}"


# ======================================================================
# 1. TÌM ĐƯỜNG: 5 thuật toán x mọi bản đồ
# ======================================================================
def exp_search(out_dir):
    print("[1/4] Tìm đường (DFS, BFS, UCS, Greedy, A*)")
    rows = []
    for name, path in list_maps():
        layout, start = load_layout(path)
        solo = replace(start, ghosts=())  # bài toán tìm đường: Pacman đi một mình
        for algo_name, algo in ALGORITHMS.items():
            r = algo(AllFoodProblem(layout, solo))
            rows.append(map_info(name, layout, start) +
                        [algo_name, r.found, len(r.actions), r.total_cost, r.expanded, fmt_time(r.time_sec)])
    write_csv(out_dir, "search_results.csv",
              MAP_COLUMNS + ["algorithm", "found", "steps", "cost", "expanded", "time_sec"], rows)


# ======================================================================
# 2. HEURISTIC: UCS vs A*(h=0) vs A*(heuristic của nhóm), bài toán ăn hết food
# ======================================================================
def exp_heuristic(out_dir):
    print("[2/4] So sánh heuristic trên bài toán ăn hết food")
    rows = []
    for name, path in list_maps():
        layout, start = load_layout(path)
        solo = replace(start, ghosts=())
        problem = AllFoodProblem(layout, solo)
        variants = {
            "UCS": _best_first(problem, lambda g, s: g),
            "A* (h=0)": _best_first(problem, lambda g, s: g + 0),
            "A* (heuristic nhom)": _best_first(problem, lambda g, s: g + heuristic(problem, s)),
        }
        optimal = variants["UCS"].total_cost if variants["UCS"].found else None
        for variant, r in variants.items():
            rows.append(map_info(name, layout, start) +
                        [variant, r.found, r.total_cost, r.expanded, fmt_time(r.time_sec),
                         "" if optimal is None else r.found and r.total_cost == optimal])
    write_csv(out_dir, "search_heuristic.csv",
              MAP_COLUMNS + ["algorithm", "found", "cost", "expanded", "time_sec", "optimal"], rows)


# ======================================================================
# 3. ĐỐI KHÁNG: Minimax vs Alpha-Beta vs Expectimax tại trạng thái đầu
# ======================================================================
def exp_adversarial(out_dir, max_depth, budget):
    print(f"[3/4] So sánh đối kháng (độ sâu 1..{max_depth})")
    rows = []
    for name, path in list_maps():
        layout, start = load_layout(path)
        if not start.ghosts:
            continue  # bản đồ không có ghost thì không có đối kháng
        for depth in range(1, max_depth + 1):
            results = {a: run_adversarial(a, layout, start, depth, (), None) for a in ADVERSARIAL_ALGORITHMS}
            mm = results["Minimax"]
            for algo, r in results.items():
                # Minimax và Alpha-Beta bắt buộc cho cùng điểm và cùng nước đi; nếu khác là có lỗi
                same = (r.action == mm.action and abs(r.value - mm.value) < 1e-9) if algo == "Alpha-Beta" else ""
                rows.append(map_info(name, layout, start) +
                            [depth, algo, r.action, f"{r.value:.2f}", r.expanded, fmt_time(r.time_sec), same])
                if algo == "Alpha-Beta" and same is False:
                    print(f"  !! {name} depth {depth}: Alpha-Beta khác Minimax (kiểm tra lại code)")
            if mm.time_sec > budget:  # độ sâu này đã chậm, không chạy sâu hơn nữa trên bản đồ này
                print(f"  (bỏ qua độ sâu cao hơn trên {name}: Minimax mất {mm.time_sec:.1f}s > {budget}s)")
                break
    write_csv(out_dir, "adversarial_compare.csv",
              MAP_COLUMNS + ["depth", "algorithm", "action", "value", "expanded", "time_sec", "alphabeta_matches_minimax"],
              rows)


# ======================================================================
# 4. CHƠI NGUYÊN VÁN: Pacman (thuật toán đối kháng) vs ghost random/greedy/chase
# ======================================================================
def bfs_dist(layout, source):
    """Khoảng cách (số bước) từ source tới mọi ô đi được. Ghost dùng để biết hướng đuổi Pacman."""
    dist = {source: 0}
    queue = deque([source])
    while queue:
        p = queue.popleft()
        for dr, dc in DIRECTIONS.values():
            n = (p[0] + dr, p[1] + dc)
            if (0 <= n[0] < layout.height and 0 <= n[1] < layout.width
                    and n not in layout.walls and n not in dist):
                dist[n] = dist[p] + 1
                queue.append(n)
    return dist


def move_ghosts(layout, state, mode, turn, rng):
    """Cho từng ghost đi một bước, giống hệt Controller._move_ghosts trong gui.py."""
    if mode == "chase":
        chase = True
    elif mode == "greedy":
        chase = turn % (CHASE_STEPS + RANDOM_STEPS) < CHASE_STEPS
    else:
        chase = False
    dist = bfs_dist(layout, state.pacman) if chase else None

    for i in range(len(state.ghosts)):
        if is_terminal(state):
            break
        actions = legal_ghost_actions(layout, state, i)
        if not actions:
            continue
        if dist is None:
            action = rng.choice(actions)
        else:
            gr, gc = state.ghosts[i]
            after = {a: dist.get((gr + DIRECTIONS[a][0], gc + DIRECTIONS[a][1]), 1e9) for a in actions}
            best = min(after.values())
            action = rng.choice([a for a in actions if after[a] == best])
        state = move_ghost(layout, state, i, action)
    return state


def play_game(layout, start, algo, depth, mode, seed, max_turns):
    """Chơi một ván. Trả về (kết quả, số lượt, state cuối, tổng số state đã mở rộng, tổng thời gian nghĩ)."""
    rng = random.Random(seed)
    recent = deque(maxlen=RECENT_SIZE)
    state, expanded, think = start, 0, 0.0
    turn = 0
    while not is_terminal(state):
        if turn >= max_turns:
            return "timeout", turn, state, expanded, think
        r = run_adversarial(algo, layout, state, depth, tuple(recent), None, mode)
        expanded += r.expanded
        think += r.time_sec
        if r.action is None:
            return "stuck", turn, state, expanded, think
        recent.append(state.pacman)
        state = move_ghosts(layout, move_pacman(layout, state, r.action), mode, turn, rng)
        turn += 1
    return ("win" if is_win(state) else "lose"), turn, state, expanded, think


def exp_games(out_dir, depth, seeds, max_turns):
    print(f"[4/4] Chơi nguyên ván (độ sâu {depth}, {seeds} seed, tối đa {max_turns} lượt)")
    rows = []
    for name, path in list_maps():
        layout, start = load_layout(path)
        if not start.ghosts:
            continue
        for algo in ADVERSARIAL_ALGORITHMS:
            for mode in GHOST_MODES:
                for seed in range(seeds):
                    result, turns, final, expanded, think = play_game(layout, start, algo, depth, mode, seed, max_turns)
                    avg_ms = 1000 * think / turns if turns else 0.0
                    rows.append(map_info(name, layout, start) +
                                [algo, mode, depth, result, turns, final.score, len(final.food),
                                 expanded, f"{avg_ms:.3f}"])
        print(f"  xong {name}")
    write_csv(out_dir, "adversarial_games.csv",
              MAP_COLUMNS + ["algorithm", "ghost_mode", "depth", "result", "turns", "score",
                             "food_left", "expanded", "avg_decision_ms"], rows)


# ======================================================================
# CHƯƠNG TRÌNH CHÍNH
# ======================================================================
def main():
    parser = argparse.ArgumentParser(description="Chạy thí nghiệm Pacman và ghi CSV vào results/")
    parser.add_argument("--out", default=DEFAULT_OUT, help="thư mục ghi CSV (mặc định: results/)")
    parser.add_argument("--only", choices=["search", "heuristic", "adversarial", "games"],
                        help="chỉ chạy một nhóm thí nghiệm")
    parser.add_argument("--max-depth", type=int, default=3, help="độ sâu lớn nhất cho so sánh đối kháng")
    parser.add_argument("--budget", type=float, default=20.0,
                        help="nếu Minimax mất quá số giây này ở một độ sâu thì không chạy sâu hơn (mặc định 20)")
    parser.add_argument("--depth", type=int, default=2, help="độ sâu dùng khi chơi nguyên ván")
    parser.add_argument("--seeds", type=int, default=5, help="số ván (seed) cho mỗi cấu hình khi chơi nguyên ván")
    parser.add_argument("--max-turns", type=int, default=200, help="quá số lượt này thì tính là hòa (timeout)")
    parser.add_argument("--quick", action="store_true", help="bản nhanh: độ sâu tối đa 2, 2 seed, 100 lượt")
    args = parser.parse_args()

    if args.quick:
        args.max_depth, args.seeds, args.max_turns = 2, 2, 100

    t0 = time.time()
    steps = {
        "search": lambda: exp_search(args.out),
        "heuristic": lambda: exp_heuristic(args.out),
        "adversarial": lambda: exp_adversarial(args.out, args.max_depth, args.budget),
        "games": lambda: exp_games(args.out, args.depth, args.seeds, args.max_turns),
    }
    for key, run in steps.items():
        if args.only in (None, key):
            run()
    print(f"Xong sau {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()