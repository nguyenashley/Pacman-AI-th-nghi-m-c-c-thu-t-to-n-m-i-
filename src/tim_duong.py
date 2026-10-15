"""
Các thuật toán tìm đường cho Pacman ăn hết food.

Gồm 5 thuật toán: DFS, BFS, UCS, Greedy, A*.
Cả 5 đều có chung một khung:
    - Mỗi trạng thái được đóng gói thành một khóa (key) để lưu vào dict/set.
    - Dict parents sẽ ghi lại: trạng thái này đến từ đâu, bằng hành động nào.
    - Khi tới đích, lần ngược parents để dựng lại đường đi.
    - biến expanded đếm số trạng thái đã mở rộng (dùng để so sánh các thuật toán).
"""

import heapq   #cho hàng đợi ưu tiên (dùng ở UCS/greedy/A*)
import time   #để đo thời gian
from collections import deque   #hàng đợi 2 đầu cho BFS
from itertools import count   #bộ đếm tăng dần

from src.engine import AllFoodProblem, PathProblem, SearchResult


def _key(state):
    """Khóa của một trạng thái. Bỏ score ra vì score khác nhau không làm trạng thái khác nhau.
    2 đường khác nhau tới cùng 1 nơi thì điểm số khác nhau nhưng về mặt tìm đường chúng là 1 trạng thái
    nên nếu để cả score vào thì thuật toán sẽ coi là 2 trạng thái và xét lại nhiều lần
    """
    return (state.pacman, state.ghosts, state.food)


def _path(parents, k):   
    #parents sẽ kiểu {A: (None,None), B: (A,"RIGHT"), C: (B, "DOWN")} nghiã là B đến từ A bằng hướng RIGHT và A là điểm đầu
    """Lần ngược từ trạng thái đích về trạng thái đầu để lấy danh sách hành động"""
    actions = []
    while parents[k][0] is not None:
        k, action = parents[k]
        actions.append(action)
    actions.reverse()
    return actions


def _cost_of(problem, actions):
    """Tính tổng chi phí của 1 danh sách hành động (đi lại từ trạng thái đầu)"""
    state = problem.start_state()
    total = 0
    for action in actions:
        total += problem.cost(state, action)
        state = problem.result(state, action)
    return total


def _fail(t0, expanded):
    """Kết quả khi không tìm được đường (hoặc vượt giới hạn số nút mở rộng)"""
    return SearchResult(False, [], 0, expanded, time.time() - t0)


def _done(problem, parents, k, t0, expanded, total_cost=None):
    """Kết quả khi tìm được đường."""
    actions = _path(parents, k)
    if total_cost is None:   # BFS/DFS không theo dõi chi phí nên phải tính lại
        total_cost = _cost_of(problem, actions)
    return SearchResult(True, actions, total_cost, expanded, time.time() - t0)


def heuristic(problem, state):
    """Heuristic của A* là khoảng cách từ Manhattan tới viên food xa nhất
    Pacman buộc phải đến chỗ viên xa nhất và mỗi bước tốn >=1 nên k bao giờ ước lượng quá chi phí thật
    """
    if not state.food:
        return 0
    r, c = state.pacman
    return max(abs(r - fr) + abs(c - fc) for fr, fc in state.food)

def greedy_heuristic(problem, state):
    """ Heuristic riêng cho greedy:trả về số food còn lại, khoảng cách Manhattan tới food gần nhất
    ưu tiên trạng thái còn ít food hơn, hòa thì ưu tiền trạng thái gần food kế tiếp hơn
    Greedy vẫn chỉ chọn trạng thái có h nhỏ nhất, nhưng h này thấy được lợi ích của việc ăn 1 viên food
    """
    if not state.food:
        return (0,0)
    r,c = state.pacman
    nearest = min(abs(r-fr)+abs(c-fc) for fr,fc in state.food)
    return (len(state.food), nearest)

def dfs(problem: PathProblem, max_expanded=200000) -> SearchResult:
    t0 = time.time()
    start = problem.start_state()
    start_key = _key(start)

    parents = {start_key: (None, None)}
    stack = [start]
    visited = set()
    expanded = 0

    while stack:
        if expanded >= max_expanded:
            return _fail(t0, expanded)

        state = stack.pop()
        k = _key(state)
        if k in visited:
            continue
        visited.add(k)
        expanded += 1

        if problem.is_goal(state):
            return _done(problem, parents, k, t0, expanded)

        # reversed để hành động đầu tiên trong danh sách được xét trước
        for action in reversed(problem.actions(state)):
            next_state = problem.result(state, action)
            next_key = _key(next_state)
            if next_key not in visited:
                parents[next_key] = (k, action)
                stack.append(next_state)

    return _fail(t0, expanded)


def bfs(problem: PathProblem, max_expanded=200000) -> SearchResult:
    t0 = time.time()
    start = problem.start_state()
    start_key = _key(start)

    parents = {start_key: (None, None)}
    queue = deque([start])
    expanded = 0

    while queue:
        if expanded >= max_expanded:
            return _fail(t0, expanded)

        state = queue.popleft()
        k = _key(state)
        expanded += 1

        if problem.is_goal(state):
            return _done(problem, parents, k, t0, expanded)

        for action in problem.actions(state):
            next_state = problem.result(state, action)
            next_key = _key(next_state)
            if next_key not in parents: 
                parents[next_key] = (k, action)
                queue.append(next_state)

    return _fail(t0, expanded)


def _best_first(problem, priority, max_expanded=200000):
    t0 = time.time()
    start = problem.start_state()
    k0 = _key(start)
    parents = {k0: (None, None)}
    best_g = {k0: 0}
    tie = count()
    heap = [(priority(0, start), next(tie), 0, start)]
    #heapq so sánh 2 tuple từ trái sang phải, 2 trạng thái cùng priority sẽ ss sang phần tử t2
    #tie là stt dùng để phá hòa không thể giống nhau
    """ví dụ 2 trạng thái có cùng priority như cùng g+h=7.
    nếu k có tie: tuple là (7,g,state) nếu g bằng nhau, python sẽ so tiếp state mà gamestate là dataclass k định nghĩa <
    => sẽ báo lỗi typeerror: '<' not supported
    nếu có tie: tuple là (7,0,...) và (7,1,...) 2 số này luôn khác nhau nên python phân định đc ptu t2 và kbh phải ss state
    """
    closed = set()
    expanded = 0
    while heap:
        _, _, g, s = heapq.heappop(heap)  #lấy cái priority nhỏ nhất
        #tại sao lại là "_"  vì theo quy ước của python có nghĩa là "giá trị này tôi k dùng đến"
        k = _key(s)
        if k in closed or g > best_g[k]:
            continue
        closed.add(k)
        expanded += 1
        if problem.is_goal(s):
            return _done(problem, parents, k, t0, expanded, g)
        for a in problem.actions(s):
            ns = problem.result(s, a)
            nk = _key(ns)
            ng = g + problem.cost(s, a)
            if nk in closed:
                continue
            if nk not in best_g or ng < best_g[nk]:
                best_g[nk] = ng
                parents[nk] = (k, a)
                heapq.heappush(heap, (priority(ng, ns), next(tie), ng, ns))
    return _fail(t0, expanded)


def ucs(problem: PathProblem) -> SearchResult:
    return _best_first(problem, lambda g, s: g)  #1 hàm nhận vào 2 tham số g,s và trả về g (priority)


def greedy(problem: PathProblem) -> SearchResult:
    return _best_first(problem, lambda g, s: greedy_heuristic(problem, s))  # bỏ qua g, chỉ dùng h => luôn mở rộng trạng thái có h nhỏ nhất


def A_star(problem: PathProblem) -> SearchResult:
    return _best_first(problem, lambda g, s: g + heuristic(problem, s))  # 1 hàm nhận vào g,s và tính tổng chi phí với h


ALGORITHMS = {
    "DFS": dfs,
    "BFS": bfs,
    "UCS": ucs,
    "Greedy": greedy,
    "A*": A_star,
}


def run_search(name, layout, start_state):
    """main.py và gui.py gọi hàm này, kh gọi thẳng dfs/bfs/..."""
    problem = AllFoodProblem(layout, start_state)
    return ALGORITHMS[name](problem)