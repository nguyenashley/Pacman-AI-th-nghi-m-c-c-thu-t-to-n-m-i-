"""Test các thuật toán tìm đường DFS, BFS, UCS, Greedy, A*."""
import pytest

from src.engine import AllFoodProblem, is_win, move_pacman
from src.tim_duong import ALGORITHMS, _best_first, heuristic, run_search
from tests.helpers import MAPS, load_solo

SOLVABLE = [n for n in sorted(MAPS) if n != "no_solution"]
SINGLE_GOAL = [n for n in SOLVABLE if len(load_solo(n)[1].food) == 1]


def replay(layout, state, actions):
    for a in actions:
        state = move_pacman(layout, state, a)
    return state


@pytest.mark.parametrize("algo", list(ALGORITHMS))
def test_all_algorithms_solve_simple_map(algo):
    layout, start = load_solo("uniform")
    r = run_search(algo, layout, start)
    assert r.found and r.total_cost == 6 and len(r.actions) == 6


@pytest.mark.parametrize("algo", list(ALGORITHMS))
def test_all_algorithms_report_no_solution(algo):
    layout, start = load_solo("no_solution")
    r = run_search(algo, layout, start)
    assert not r.found and r.actions == []


@pytest.mark.parametrize("name", SOLVABLE)
@pytest.mark.parametrize("algo", list(ALGORITHMS))
def test_returned_plan_really_eats_all_food(name, algo):
    layout, start = load_solo(name)
    r = run_search(algo, layout, start)
    assert r.found
    final = replay(layout, start, r.actions)
    assert is_win(final)
    # total_cost báo cáo phải khớp với chi phí đi lại thật
    assert r.total_cost == len(start.food) * 10 - final.score


@pytest.mark.parametrize("name", SOLVABLE)
def test_ucs_and_astar_find_the_same_optimal_cost(name):
    layout, start = load_solo(name)
    assert run_search("UCS", layout, start).total_cost == run_search("A*", layout, start).total_cost


@pytest.mark.parametrize("name", SOLVABLE)
def test_no_algorithm_beats_ucs_cost(name):
    layout, start = load_solo(name)
    best = run_search("UCS", layout, start).total_cost
    for algo in ALGORITHMS:
        assert run_search(algo, layout, start).total_cost >= best


@pytest.mark.parametrize("name", SINGLE_GOAL)
def test_bfs_uses_fewest_steps_on_single_goal_maps(name):
    layout, start = load_solo(name)
    steps = {a: len(run_search(a, layout, start).actions) for a in ALGORITHMS}
    assert steps["BFS"] == min(steps.values())


def test_weighted_trap_separates_bfs_from_ucs():
    layout, start = load_solo("weighted_trap")
    bfs, ucs, astar = (run_search(a, layout, start) for a in ("BFS", "UCS", "A*"))
    assert len(bfs.actions) < len(ucs.actions)   # BFS ít bước hơn...
    assert bfs.total_cost > ucs.total_cost       # ...nhưng đắt hơn nhiều
    assert ucs.total_cost == astar.total_cost == 15


@pytest.mark.parametrize("name", SOLVABLE)
def test_astar_expands_no_more_than_ucs(name):
    layout, start = load_solo(name)
    assert run_search("A*", layout, start).expanded <= run_search("UCS", layout, start).expanded


@pytest.mark.parametrize("name", SOLVABLE)
def test_heuristic_is_nonnegative_zero_at_goal_and_admissible(name):
    layout, start = load_solo(name)
    problem = AllFoodProblem(layout, start)
    assert heuristic(problem, start) >= 0
    assert heuristic(problem, start) <= run_search("UCS", layout, start).total_cost
    # tại đích (hết food) heuristic bằng 0
    r = run_search("UCS", layout, start)
    assert heuristic(problem, replay(layout, start, r.actions)) == 0


def test_astar_with_zero_heuristic_equals_ucs():
    layout, start = load_solo("tiny")
    problem = AllFoodProblem(layout, start)
    h0 = _best_first(problem, lambda g, s: g + 0)
    ucs = run_search("UCS", layout, start)
    assert (h0.total_cost, h0.expanded) == (ucs.total_cost, ucs.expanded)