from dataclasses import dataclass  
DIRECTIONS = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


@dataclass(frozen=True)  
class GameState:
    pacman: tuple #vị trí hiện tại của Pặc man
    ghosts: tuple #vị trí hiện tại của từng ghost
    food: frozenset #các ô còn thức ăn {(hàng, cột), ...}
    score: int = 0
@dataclass
class Layout:  
    width: int
    height: int
    walls: frozenset
    costs: dict

def load_layout(path):  #hàm này đọc bản đồ từ file txt
    with open(path, encoding="utf-8") as f:
        lines = [ln.rstrip("\r") for ln in f.read().split("\n")] 
    while lines and lines[-1].strip() == "": 
        lines.pop()

    height = len(lines) 
    width = max(len(ln) for ln in lines)
    walls, costs, food, ghosts, pacman = set(), {}, set(), [], None

    for r, line in enumerate(lines): 
        for c, ch in enumerate(line.ljust(width, "%")): 
            if ch == "%":
                walls.add((r, c))
            elif ch == "P":
                pacman = (r, c)
            elif ch == ".":
                food.add((r, c))
            elif ch == "G":
                ghosts.append((r, c))
                costs[(r, c)] = 99999
            elif ch in "123456789":
                costs[(r, c)] = int(ch)

    if pacman is None:
        raise ValueError("Bản đồ không có Pacman")

    layout = Layout(width=width, height=height, walls=frozenset(walls), costs=costs)
    start_state = GameState(pacman=pacman, ghosts=tuple(ghosts), food=frozenset(food))

    return layout, start_state

def _step(pos, act):
    #step nhận vào vị trí hiện tại và một hướng như up/down/right/left
    dr, dc = DIRECTIONS[act]  

    return (pos[0] + dr, pos[1] + dc) 

def _acceptable(layout, pos):
    #kiểm tra true false của 3 điều, nều cả 3 đều đúng thì đi được
    r, c = pos
    return 0 <= r < layout.height and 0 <= c < layout.width and pos not in layout.walls

def legal_pacman_actions(layout, state):
    #duyệt 4 hướng trong directions rồi tính ô theo _step rồi kiểm tra = _acceptable rồi nhét vào result để ra được list các hướng đi hợp lệ
    result = []
    for a in DIRECTIONS:
        if _acceptable(layout, _step(state.pacman, a)):
            result.append(a)
    return result

GHOST_COST = 99999

def step_cost(layout, state, action):
    next_step = _step(state.pacman, action)
    if next_step in state.ghosts:      # đi vào ô đang có ma
        return GHOST_COST
    return layout.costs.get(next_step, 1)

FOOD_REWARD = 10
def move_pacman(layout, state, action):
    #hàm này trả về 1 gamestate mới không đụng chạm vào state cũ để đảm bảo map thật k bị biến dạng
    next_step = _step(state.pacman, action)
    if not _acceptable(layout, next_step):
        raise ValueError("Nước đi không hợp lệ")
    
    score = state.score - step_cost(layout, state, action)
    
    food = state.food 
    if next_step in food:
        food = food - {next_step} 
        score += FOOD_REWARD
    return GameState(next_step, state.ghosts, food, score)

def is_lose(state):
    return state.pacman in state.ghosts  

def is_win(state):
    return len(state.food) == 0 and not is_lose(state) 

def is_terminal(state):  #gọi hàm này để hỏi nhanh ván kết thúc chưa mà k cần qtam kết thúc kiểu nào
    return is_lose(state) or is_win(state)

def legal_ghost_actions(layout, state, ghost_index):
    pos = state.ghosts[ghost_index]
    other_ghosts = set(state.ghosts) - {pos}
    result = []
    for a in DIRECTIONS:
        next_step = _step(pos, a)
        if _acceptable(layout, next_step) and next_step not in other_ghosts:
            result.append(a)
    return result

def move_ghost(layout, state, ghost_index, action):
    #giống move_pacman
    pos = state.ghosts[ghost_index]
    next_step = _step(pos, action)
    other_ghosts = set(state.ghosts) - {pos}
    if not _acceptable(layout, next_step) or next_step in other_ghosts:
        raise ValueError("Nước đi của ghost không hợp lệ")
    new_ghosts = list(state.ghosts)
    new_ghosts[ghost_index] = next_step
    return GameState(state.pacman, tuple(new_ghosts), state.food, state.score)

class PathProblem:
    #bài toán tìm dường đơn giản: đích là ăn đc 1 ô thức ăn bất kỳ
    def __init__(self, layout, start_state):
        self.layout = layout
        self.start = start_state

    def start_state(self):
        return self.start

    def actions(self, state):
        return legal_pacman_actions(self.layout, state)

    def result(self, state, action):
        return move_pacman(self.layout, state, action)

    def cost(self, state, action):
        return step_cost(self.layout, state, action)

    def is_goal(self, state):
        return len(state.food)<len(self.start.food)

class AllFoodProblem(PathProblem):
    # bài toán đích là ăn hết toàn bộ thức ăn
    def is_goal(self, state):
        return is_win(state)

@dataclass
class SearchResult:  
    #mọi hàm tìm kiếm đường đi phải nhận vào 1 pathproblem và trả về 1 searchresult
    found: bool   #true hoặc false (có tìm thấy lời giải hay k)
    actions: list   # danh sách hành động, ví dụ ["DOWN", "RIGHT", "RIGHT"]
    total_cost: int   #tổng chi phí
    expanded: int   # số trạng thái đã mở rộng (đã xét qua)
    time_sec: float   #thời gian chạy