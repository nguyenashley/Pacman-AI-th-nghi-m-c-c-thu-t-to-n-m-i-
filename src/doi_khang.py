"""

điều kiện duyệt hoàn thiện file này: Mỗi hàm phải trả về đúng một AdversarialResult với đủ 5 trường:
    action      : hành động Pacman nên chọn
    value       : số điểm đánh giá tại nhánh được chọn
    depth       : độ sâu đã dùng để tính (đúng bằng tham số depth truyền vào)
    expanded    : số trạng thái đã xét (để so sánh minimax vs alpha-beta)
    time_sec    : thời gian chạy, đo bằng time.time() đầu và cuối hàm
"""

from dataclasses import dataclass
from src.engine import (
    legal_pacman_actions, move_pacman,
    legal_ghost_actions, move_ghost,
    is_terminal, is_win, is_lose,
)
import time
from collections import deque
from src.engine import DIRECTIONS
import heapq

_map = {"layout" : None, "neighbours": {}, "steps": {}, "eval":{}, "costs": {}}  #steps là nơi nhớ kq BFS của từng ô xuất phát
#caay timf kieesm goij evaluate hàng chục nghìn lần mà bản đồ không đổi nên không có lý do tính lại

@dataclass
class AdversarialResult:
    action: str
    value: float
    depth: int
    expanded: int
    time_sec: float

INF = float("inf")
WIN_SCORE = 999999
FOOD_WEIGHT = 500     # mỗi viên food còn lại bị trừ 500
BUOC_GAN_FOOD = 3       # mỗi bước tới food gần nhất bị trừ 3
NEAR_GHOST = 3      # ma cách Pacman <= 3 bước là "rất gần"
DI_SAT_DIT = 8          # mức phạt khi ma rất gần (càng gần phạt càng nặng)
SAFE_TRIGGER = 6    # chỉ xét vùng an toàn khi ma cách <= 6 bước
SAFE_COUNT = 30       # đếm vùng an toàn tối đa 30 ô cho nhanh
SAFE_MIN = 12    # vùng an toàn < 12 ô thì bắt đầu bị phạt
THIEU_O_AN_TOAN = 5          # mỗi ô thiếu bị phạt 5 điểm
TRAP_MAX = 25       # mức phạt tối đa
REVERSE_PEN = 40

"""
Vấn đề 9: Tthời gian tìm kiếm tăng rất nhanh theo độ sâu
=> cheat để gui k bị treo máy :))) tránh trường hợp xấu nhất trong quá trình thuyết trình. Cụ thể:
thay vì chạy thẳng đepth lớn, ta chạy depth 1,2,3 tới depth yêu cầu. Mỗi lần xong 1 độ sâu thì lưu lại kết quả
Nếu hết giờ suy nghĩ giữa chừng thì bỏ đi và dùng lại kết quả của độ sâu hoàn thành gần nhất (lý do tại sao độ sâu cao hơn lại chạy giống độ sâu thấp hơn)
"""
class _Timeout(Exception):
    """Ném ra khi hết thời gian suy nghĩ."""

"""
Vấn đề 1: cần biết từ ô này có thể sang những ô nào (ô nào hợp lệ) và biết từ ô này có những ô nào an toàn
"""

def _load_map(layout):   #phân tích map
    if _map["layout"] is layout or _map["layout"] == layout:
        return        #nếu là bản đồ cũ hoặc nội dung y chang bản đồ cũ thì khỏi tính lại
    neighbors = {}
    for r in range(layout.height):
        for c in range(layout.width):
            if (r, c) in layout.walls:
                continue
            cells = []
            for dr, dc in DIRECTIONS.values():
                n = (r + dr, c + dc)
                in_map = 0 <= n[0] < layout.height and 0 <= n[1] < layout.width
                if in_map and n not in layout.walls:
                    cells.append(n)
            neighbors[(r, c)] = cells
    _map["layout"] = layout
    _map["neighbors"] = neighbors
    _map["steps"] = {}      # để nếu như đổi bản đồ => xóa steps cũ đi 
    _map["costs"] = {}
    _map["eval"] = {}

def _steps_from(src):   #trả về tập dict khoảng cách từ điểm bắt đầu đến tất các ô đi được còn lại trong map
    dist = _map["steps"].get(src)
    if dist is None:
        dist = {src: 0}
        queue = deque([src])
        while queue:
            p = queue.popleft()
            for n in _map["neighbors"].get(p, ()):
                if n not in dist:
                    dist[n] = dist[p] + 1
                    queue.append(n)
        _map["steps"][src] = dist
    return dist

"""
Vấn đề 7: Vì map sẽ có một số ô có chi phí, Pacman cần tới 1 viên food nhưng có 2 đường đi:
- Đường A: số bước = 3, tổng chi phí = 11
- Đường B: số bước = 5, tổng chi phí = 5
=> BFS nói A gần hơn (3<5) nên evaluate sẽ chọn A. Tuy nhiên Dijkstra lại nói B rẻ hơn (5<11)
=> nếu chỉ dùng BFS Pacman sẽ cứ lao vào ô đắt vì tưởng đó là đường tắt rồi mất điểm ngu
"""
def _cost_from(src):
    dist = _map["costs"].get(src)
    if dist is None:
        dist = {src: 0}
        heap = [(0, src)]
        costs = _map["layout"].costs
        while heap:
            cost, p = heapq.heappop(heap)
            if cost > dist[p]:
                continue
            for n in _map["neighbors"].get(p, ()):
                new_cost = cost + costs.get(n, 1)
                if new_cost < dist.get(n, INF):
                    dist[n] = new_cost
                    heapq.heappush(heap, (new_cost, n))
        _map["costs"][src] = dist
    return dist

"""
Vấn đề 3: hiện evaluate chỉ biết food, nên Pacman kh biết sợ ma. Cần thêm:
- food nào Pacman tới trước ma thì ăn thoải mái. chỉ cần thấy 1 viên như vậy là lao tới (race distance)
- nếu k có food nào an toàn thì trử điểm khi ma ở sát đít hoặc trừ điểm khi bị dồn vào góc không lối thoát (update lại toàn bộ hàm evaluate (ver2))
"""

def _race_distance(state, ghost_dists):   #trả về khoảng cách an toàn mà tốt nhất cho pacman đến ăn food
    pacman_dist = _steps_from(state.pacman)
    best = None
    for food in state.food:
        d_pacman = pacman_dist.get(food)
        if d_pacman is None:
            continue
        d_ghost = min((m.get(food, 99) for m in ghost_dists), default=99)
        if d_pacman < d_ghost and (best is None or d_pacman < best):
            best = d_pacman
    return best

def _safe_area(start, ghost_dists):   #trả về số ô an toàn
    seen = {start}
    queue = deque([(start, 0)])
    while queue and len(seen) < SAFE_COUNT:
        pos, d = queue.popleft()
        d += 1 
        for n in _map["neighbors"].get(pos, ()):
            if n in seen:
                continue
            ma_toi_truoc = any(m.get(n, 99) <= d for m in ghost_dists)
            if not ma_toi_truoc:
                seen.add(n)
                queue.append((n, d))
    return len(seen)

"""def evaluate(state) (ver1)
    if is_win(state):
        return WIN_SCORE
    if is_lose(state):
        return -WIN_SCORE
    score = state.score - FOOD_WEIGHT * len(state.food) 
    dist = _steps_from(state.pacman)
    food_dist = min((dist[f] for f in state.food), default=0)
    return float(score - BUOC_GAN_FOOD * food_dist) """

"""def evaluate(state) -> float:   (ver2)
    if is_win(state):
        return WIN_SCORE
    if is_lose(state):
        return -WIN_SCORE

    score = state.score - FOOD_WEIGHT * len(state.food)   #mỗi lần ăn 1 viên food điểm tăng 500 => pacman luôn ưu tiên ăn hơn là lượn lờ quanh food
    ghost_dists = [_steps_from(g) for g in state.ghosts]

    # có food thắng được ma thì cứ lao tới ăn
    race = _race_distance(state, ghost_dists)
    if race is not None:
        return float(score - BUOC_GAN_FOOD * race)

    # Không có food nào an toàn: tính thêm mức nguy hiểm
    dist = _steps_from(state.pacman)
    food_dist = min((dist[f] for f in state.food), default=0)
    ghost_dist = min((m.get(state.pacman, 99) for m in ghost_dists), default=99)

    # ma ở rất gần thì phạt, càng gần phạt càng nặng
    near = DI_SAT_DIT * (NEAR_GHOST + 1 - ghost_dist) if ghost_dist <= NEAR_GHOST else 0

    # bị dồn góc thì phạt (chỉ xét khi ma đủ gần)
    trap = 0
    if ghost_dist <= SAFE_TRIGGER:
        shortage = max(0, SAFE_MIN - _safe_area(state.pacman, ghost_dists))
        trap = min(TRAP_MAX, THIEU_O_AN_TOAN * shortage)

    return float(score - BUOC_GAN_FOOD * food_dist - near - trap)"""

"""
Vấn đề 4: cây tìm kiếm gặp lại cùng 1 vị trí nhiều lần, tính lại mỗi lần sẽ làm GUI chậm 
=> nhớ điểm theo key (pacman state, ghosts state, food state) k cần nhớ state.score vì cùng 1 vị trí có thể có score khác nhau tạo ra 2 trạng thái khác nhau
"""
#tách evaluate ra làm 2. phần lớn nội dung chuyển sang position score (để tính điểm)
def _position_score(state):   #tính điểm phạt
    score = -FOOD_WEIGHT * len(state.food)
    ghost_dists = [_steps_from(g) for g in state.ghosts]

    # có food thắng được ma thì cứ lao tới ăn
    race = _race_distance(state, ghost_dists)
    if race is not None:
        return score - BUOC_GAN_FOOD * race
    
    # Không có food nào an toàn: tính thêm mức nguy hiểm
    """dist = _steps_from(state.pacman)
    food_dist = min((dist[f] for f in state.food), default=0)"""
    cost_table = _cost_from(state.pacman)
    food_dist = min((cost_table[f] for f in state.food if f in cost_table), default=0)
    ghost_dist = min((m.get(state.pacman, 99) for m in ghost_dists), default=99)

    # ma ở rất gần thì phạt, càng gần phạt càng nặng
    near = DI_SAT_DIT * (NEAR_GHOST + 1 - ghost_dist) if ghost_dist <= NEAR_GHOST else 0

    # bị dồn góc thì phạt (chỉ xét khi ma đủ gần)
    trap = 0
    if ghost_dist <= SAFE_TRIGGER:
        shortage = max(0, SAFE_MIN - _safe_area(state.pacman, ghost_dists))
        trap = min(TRAP_MAX, THIEU_O_AN_TOAN * shortage)

    return score - BUOC_GAN_FOOD * food_dist - near - trap


def evaluate(state) -> float:   
    if is_win(state):
        return WIN_SCORE
    if is_lose(state):
        return -WIN_SCORE
    key = (state.pacman, state.ghosts, state.food)
    pos = _map["eval"].get(key)
    if pos is None:
        if len(_map["eval"]) > 300000:
            _map["eval"].clear()
        pos = _map["eval"][key] = _position_score(state)   #điểm đến thức ăn gần nhất
    return float(state.score + pos)

"""
Vấn đề 2: pacman chọn đường vòng để ăn food thay vì đi thẳng khi chỉ còn 1 food
- Nếu k có leaf: cả 2 đường A đi thẳng,B đi vòng trả về win score = 99999. khi 2 nhánh bằng điểm thì code chọn nhánh nào duyệt trước kể cả khi nhánh đó đi dài hơn (đi đường vòng)
- Nếu có leaf: A thắng ở depth = 1, dư 3 depth điểm win_score + 3, B thắng ở depth 3, dư 1 depth điểm win_score + 1 => A>B nên Pacman chọn A
"""

def _leaf(state, depth): 
    if is_win(state):
        return WIN_SCORE + depth
    if is_lose(state):
        return -WIN_SCORE - depth
    return evaluate(state)

"""
Vấn đề 6: Pacman đi qua đi lại, lặp nước đi giữa 2 ô liền kề
Thuật toán tìm kiếm k có trí nhớ nên mỗi lượt nó nhìn trước depth bước từ vị trí hiện tại và chọn nước tốt nhất mà k biết mik vừa từ đâu đến
=> hậu quả khi 2 nước có điểm bằng nhau hoặc gần bằng n hau Pacman sẽ bị do dự 
=> cách giải quyết: tạo 1 hàm back cell trả về ô vừa đi qua (recent[-1]) để trừ 40 điểm nếu Pacman quay lại đúng ô đấy
con số 40 vừa đủ để phá thế hòa nhau mà k lấn át những thứ qtrong hơn (như food = 500)
"""
def _back_cell(state, recent):  #recent là danh sách các ô vừa đi qua theo thứ tự cũ đến mới, phần tử cuối recent[-1] là ô Pacman vừa đứng ngay trước ô hiện tại
    if not recent:
        return None
    if state.ghosts:
        closest = min(_steps_from(g).get(state.pacman, 99) for g in state.ghosts)
        if closest <= 2:
            return None
    return recent[-1]   #nếu pacman dí ngay trước mắt thì k phạt điểm nếu quay lại đường cũ


def minimax(layout, state, depth, time_limit=None, ghost_mode=None, recent=()) -> AdversarialResult:
    t0 = time.time()
    _load_map(layout)
    back_cell = _back_cell(state, recent)
    expanded = [0]

    def max_value(current_state, current_depth):
        if is_terminal(current_state) or current_depth == 0:
            return _leaf(current_state, current_depth), None
        actions = legal_pacman_actions(layout, current_state)
        if not actions:
            return _leaf(current_state, current_depth), None

        v, best_action = -INF, None
        for action in actions:
            expanded[0] += 1
            successor = move_pacman(layout, current_state, action)
            if successor.ghosts:
                score, _ = min_value(successor, current_depth, 1)
            else:
                score, _ = max_value(successor, current_depth - 1)
            if current_depth == depth and back_cell is not None and successor.pacman == back_cell:
                score -= REVERSE_PEN
            if score > v:
                v, best_action = score, action
        return v, best_action

    def min_value(current_state, current_depth, ghost_index):
        if is_terminal(current_state):
            return _leaf(current_state, current_depth), None
        actions = legal_ghost_actions(layout, current_state, ghost_index - 1)
        if not actions:
            return _leaf(current_state, current_depth), None

        v, best_action = INF, None
        for action in actions:
            expanded[0] += 1
            successor = move_ghost(layout, current_state, ghost_index - 1, action)
            if ghost_index == len(current_state.ghosts):
                score, _ = max_value(successor, current_depth - 1)
            else:
                score, _ = min_value(successor, current_depth, ghost_index + 1)
            if score < v:
                v, best_action = score, action
        return v, best_action

    best_val, best_act = max_value(state, depth)
    return AdversarialResult(best_act, best_val, depth, expanded[0], time.time() - t0)



"""
Vấn đề 5: Alpha beta cắt nhánh nhiều hay ít phụ thuộc vào việc nước đi tốt hay có được xét sớm k? nếu nước tốt nhất mà xét cuối thì k cắt đc gì
=> Pacman thử nước xa ma nhất, ma thử nước gần Pacman nhất
"""
def _move_cell(cell, action):
    dr, dc = DIRECTIONS[action]
    return (cell[0] + dr, cell[1] + dc)

def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def alpha_beta(layout, state, depth, time_limit=None, ghost_mode=None, recent=()) -> AdversarialResult:
    t0 = time.time()
    _load_map(layout)
    back_cell = _back_cell(state, recent)
    # TODO (Lộc): logic Alpha-Beta ở đây — phải ra cùng action với minimax
    expanded = [0]
    def max_value(current_state, current_depth, alpha, beta):
        if is_terminal(current_state) or current_depth == 0:
            return _leaf(current_state, current_depth), None
        
        v = -float('inf')
        best_action = None
        actions = legal_pacman_actions(layout, current_state)
        if not actions:
            return _leaf(current_state, current_depth), None
        if current_depth < depth and current_state.ghosts:   # không phải root
            actions.sort(key=lambda a: -min(
                _manhattan(_move_cell(current_state.pacman, a), g)
                for g in current_state.ghosts))
        
        for action in actions:
            expanded[0] += 1
            successor = move_pacman(layout, current_state, action)

            if successor.ghosts:
                score, _ = min_value(successor, current_depth, 1, alpha, beta)
            else:
                score, _ = max_value(successor, current_depth - 1, alpha, beta)

            if current_depth == depth and back_cell is not None and successor.pacman == back_cell:
                score -= REVERSE_PEN

            if score > v:
                v, best_action = score, action

            if v >= beta:
                return v, best_action
            alpha = max(alpha, v)

        return v, best_action

    def min_value(current_state, current_depth, ghost_index, alpha, beta):
        if is_terminal(current_state):
            return _leaf(current_state, current_depth), None

        v = float('inf')
        best_action = None
        actions = legal_ghost_actions(layout, current_state, ghost_index - 1)
        
    
        if not actions:
            return _leaf(current_state, current_depth), None
        if len(actions) > 1:
            ghost = current_state.ghosts[ghost_index - 1]
            actions.sort(key=lambda a: _manhattan(_move_cell(ghost, a), current_state.pacman))
            
        for action in actions:
            expanded[0] += 1
            successor = move_ghost(layout, current_state, ghost_index - 1, action)
            
        
            if ghost_index == len(current_state.ghosts):
                score, _ = max_value(successor, current_depth - 1, alpha, beta)
            else:
                score, _ = min_value(successor, current_depth, ghost_index + 1, alpha, beta)
                
            if score < v:
                v, best_action = score, action
                

            if v <= alpha:
                return v, best_action
            beta = min(beta, v)
            
        return v, best_action

    best_val, best_act = max_value(state, depth, -float('inf'), float('inf'))

    return AdversarialResult(best_act, best_val, depth, expanded[0], time.time() - t0)


"""
Vấn đề 8: hiện exp_value chia xác suất đều cho mọi hướng đi của ma
Nhưng khi GUI chọn chế độ chase, ma không đi ngẫu nhiên mà luôn đi hướng đưa nó gần Pacman nhất
=> Ở chế độ chase, chỉ giữ lại các hướng làm ma tới gần Pacman nhất, các hướng còn lại có xác suất = 0 bỏ đi luôn, hòa thì chia đều giữa các hướng hòa
"""

def _chase_actions(state, i, actions):   #trả về hướng hành động tốt nhất của ghost (gần pacman nhất)
    to_pacman = _steps_from(state.pacman)
    ghost = state.ghosts[i]
    dist_after = {a: to_pacman.get(_move_cell(ghost, a), 10 ** 9) for a in actions}
    best = min(dist_after.values())
    return [a for a in actions if dist_after[a] == best]

"""
Vấn đề 10: Expectimax chỉ biết chế độ chase, còn greedy bị coi như random nên đánh giá sai hành vi của ma
Mỗi chế độ ma có một phân phối xác suất riêng cho các hướng đi:
- random: mọi hướng bằng nhau
- chase: chỉ các hướng gần Pacman nhất (hòa thì chia đều)
- greedy: pha trộn. Với xác suất GREEDY_CHASE_PROB (5/7) ma đang trong đợt đuổi nên đi như chase,
  còn lại (2/7) ma đang trong đợt đi bừa nên đi như random. Cộng hai phần lại thì hướng gần Pacman nhất có xác suất cao nhất
  nhưng các hướng khác vẫn có xác suất > 0 (không giả định ma luôn đuổi, vì có 2 lượt ma đi bừa)
Lý do pha trộn kiểu này là vì Expectimax không biết lượt hiện tại là random hay chase, và cây tìm kiếm nhìn trước nhiều lượt nên lượt nào cũng có thể rơi vào đợt đuổi hoặc đợt bừa
"""
GREEDY_CHASE_PROB = 5 / 7 

def _ghost_distribution(state, i, actions, ghost_mode):   #trả về [(hướng, xác suất)] của ma thứ i
    uniform = 1 / len(actions)
    if ghost_mode == "chase":
        best = _chase_actions(state, i, actions)
        return [(a, 1.0 / len(best)) for a in best]
    if ghost_mode == "greedy":
        best = _chase_actions(state, i, actions)
        probs = {a: (1 - GREEDY_CHASE_PROB) * uniform for a in actions}
        for a in best:
            probs[a] += GREEDY_CHASE_PROB / len(best)
        return list(probs.items())
    return [(a, uniform) for a in actions]   # random

def expectimax(layout, state, depth, time_limit=None, ghost_mode=None, recent=()) -> AdversarialResult:
    t0 = time.time()
    _load_map(layout)
    back_cell = _back_cell(state, recent)
    # TODO (Lộc): logic Expectimax ở đây — lượt ghost lấy trung bình có trọng số
    expanded = [0]
    deadline = [None]

    def run(root_depth):
        def max_value(current_state, current_depth):
            if deadline[0] and time.time() > deadline[0]:
                raise _Timeout
            if is_terminal(current_state) or current_depth == 0:
                return _leaf(current_state, current_depth), None
            actions = legal_pacman_actions(layout, current_state)
            if not actions:
                return _leaf(current_state, current_depth), None

            v, best_action = -INF, None
            for action in actions:
                expanded[0] += 1
                successor = move_pacman(layout, current_state, action)
                if successor.ghosts:
                    score, _ = exp_value(successor, current_depth, 1)
                else:
                    score, _ = max_value(successor, current_depth - 1)

                if current_depth == root_depth and back_cell is not None and successor.pacman == back_cell:
                    score -= REVERSE_PEN
                if score > v:
                    v, best_action = score, action
            return v, best_action

        def exp_value(current_state, current_depth, ghost_index):
            if is_terminal(current_state):
                return _leaf(current_state, current_depth), None
            actions = legal_ghost_actions(layout, current_state, ghost_index - 1)
            if not actions:
                return _leaf(current_state, current_depth), None
            expected_score = 0
            for action, prob in _ghost_distribution(current_state, ghost_index - 1, actions, ghost_mode):
                expanded[0] += 1
                successor = move_ghost(layout, current_state, ghost_index - 1, action)
                if ghost_index == len(current_state.ghosts):
                    score, _ = max_value(successor, current_depth - 1)
                else:
                    score, _ = exp_value(successor, current_depth, ghost_index + 1)
                expected_score += score * prob
            return expected_score, None
            
        return max_value(state, root_depth)

    if not time_limit:
        value, action = run(depth)
        return AdversarialResult(action, value, depth, expanded[0], time.time() - t0)

    deadline[0] = t0 + time_limit
    value, action, finished = None, None, 0
    for d in range(1, depth + 1):
        try:
            v, a = run(d)
        except _Timeout:
            break
        value, action, finished = v, a, d
        if a is None: 
            break

    if finished == 0:
        deadline[0] = None
        value, action = run(1)
        finished = 1

    return AdversarialResult(action, value, finished, expanded[0], time.time() - t0)


ADVERSARIAL_ALGORITHMS = {
    "Minimax": minimax,
    "Alpha-Beta": alpha_beta,
    "Expectimax": expectimax,
}


def run_adversarial(name, layout, state, depth, recent = (), time_limit = None, ghost_mode = None):
    return ADVERSARIAL_ALGORITHMS[name](layout, state, depth, time_limit, ghost_mode, recent or ())