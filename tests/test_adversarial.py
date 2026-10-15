"""Test Minimax, Alpha-Beta, Expectimax và việc ghost di chuyển trong ván chơi."""
import pytest

from run_experiments import move_ghosts, play_game
from src.doi_khang import (
    ADVERSARIAL_ALGORITHMS, GREEDY_CHASE_PROB, WIN_SCORE, _chase_actions, _ghost_distribution, _load_map,
    evaluate, run_adversarial,
)
from src.engine import GameState, is_terminal, legal_ghost_actions, legal_pacman_actions
from tests.helpers import load, write_map

GHOST_MAPS = ["ghost_small", "ghost_two", "playmod"]


@pytest.mark.parametrize("name", GHOST_MAPS)
@pytest.mark.parametrize("depth", [1, 2, 3])
def test_alpha_beta_matches_minimax_but_expands_fewer(name, depth):
    layout, state = load(name)
    mm = run_adversarial("Minimax", layout, state, depth, (), None)
    ab = run_adversarial("Alpha-Beta", layout, state, depth, (), None)
    assert ab.action == mm.action
    assert ab.value == pytest.approx(mm.value)
    assert ab.expanded <= mm.expanded


def test_alpha_beta_prunes_strictly_on_deeper_search():
    layout, state = load("playmod")
    mm = run_adversarial("Minimax", layout, state, 3, (), None)
    ab = run_adversarial("Alpha-Beta", layout, state, 3, (), None)
    assert ab.expanded < mm.expanded


@pytest.mark.parametrize("algo", list(ADVERSARIAL_ALGORITHMS))
@pytest.mark.parametrize("name", GHOST_MAPS)
def test_result_has_legal_action_and_requested_depth(algo, name):
    layout, state = load(name)
    r = run_adversarial(algo, layout, state, 2, (), None)
    assert r.action in legal_pacman_actions(layout, state)
    assert r.depth == 2 and r.expanded > 0 and r.time_sec >= 0


@pytest.mark.parametrize("algo", list(ADVERSARIAL_ALGORITHMS))
def test_pacman_runs_toward_food_not_toward_ghost(algo, tmp_path):
    layout, state = write_map(tmp_path, "%%%%%%%%%\n%G  P  .%\n%%%%%%%%%")
    assert run_adversarial(algo, layout, state, 2, (), None).action == "RIGHT"


def test_evaluate_terminal_states():
    layout, state = load("ghost_small")
    run_adversarial("Minimax", layout, state, 1, (), None)  # nạp bản đồ vào bộ nhớ đệm của evaluate
    win = GameState(state.pacman, state.ghosts, frozenset())
    lose = GameState(state.pacman, (state.pacman,), state.food)
    assert evaluate(win) == WIN_SCORE
    assert evaluate(lose) == -WIN_SCORE


@pytest.mark.parametrize("mode", ["random", "greedy", "chase"])
def test_ghosts_never_overlap_while_moving(mode):
    import random
    layout, state = load("ghost_two")
    rng = random.Random(0)
    for turn in range(60):
        state = move_ghosts(layout, state, mode, turn, rng)
        if is_terminal(state):
            break
        assert len(set(state.ghosts)) == len(state.ghosts)


def test_chase_ghost_gets_closer_to_pacman():
    import random
    layout, state = load("ghost_small")
    new = move_ghosts(layout, state, "chase", 0, random.Random(0))
    old_d = abs(state.ghosts[0][0] - state.pacman[0]) + abs(state.ghosts[0][1] - state.pacman[1])
    new_d = abs(new.ghosts[0][0] - new.pacman[0]) + abs(new.ghosts[0][1] - new.pacman[1])
    assert new_d <= old_d


def test_game_is_reproducible_with_same_seed():
    layout, state = load("ghost_small")
    a = play_game(layout, state, "Alpha-Beta", 2, "random", 3, 100)
    b = play_game(layout, state, "Alpha-Beta", 2, "random", 3, 100)
    assert a[:2] == b[:2] and a[2] == b[2]


def test_pacman_wins_easy_ghost_map():
    layout, state = load("ghost_small")
    result, turns, final, *_ = play_game(layout, state, "Expectimax", 2, "random", 0, 200)
    assert result == "win" and not final.food


# ---------- phân phối xác suất của ghost trong Expectimax ----------
ROOM = "%%%%%%%\n%     %\n%  G  %\n%    P%\n%%%%%%%"   # ma (2,3), Pacman (3,5): DOWN và RIGHT hòa nhau là gần nhất


@pytest.mark.parametrize("mode", ["random", "greedy", "chase", None])
@pytest.mark.parametrize("name", GHOST_MAPS)
def test_ghost_distribution_is_a_valid_probability(mode, name):
    layout, state = load(name)
    _load_map(layout)
    for i in range(len(state.ghosts)):
        dist = _ghost_distribution(state, i, legal_ghost_actions(layout, state, i), mode)
        assert sum(p for _, p in dist) == pytest.approx(1.0)
        assert all(p > 0 for _, p in dist)


def test_random_distribution_is_uniform(tmp_path):
    layout, state = write_map(tmp_path, ROOM)
    _load_map(layout)
    dist = dict(_ghost_distribution(state, 0, legal_ghost_actions(layout, state, 0), "random"))
    assert set(dist.values()) == {0.25}


def test_chase_distribution_only_keeps_closest_directions(tmp_path):
    layout, state = write_map(tmp_path, ROOM)
    _load_map(layout)
    actions = legal_ghost_actions(layout, state, 0)
    dist = dict(_ghost_distribution(state, 0, actions, "chase"))
    assert set(dist) == {"DOWN", "RIGHT"} == set(_chase_actions(state, 0, actions))
    assert all(p == pytest.approx(0.5) for p in dist.values())


def test_greedy_distribution_mixes_chase_and_random(tmp_path):
    layout, state = write_map(tmp_path, ROOM)
    _load_map(layout)
    dist = dict(_ghost_distribution(state, 0, legal_ghost_actions(layout, state, 0), "greedy"))
    explore = (1 - GREEDY_CHASE_PROB) / 4
    assert dist["DOWN"] == pytest.approx(GREEDY_CHASE_PROB / 2 + explore)
    assert dist["RIGHT"] == pytest.approx(GREEDY_CHASE_PROB / 2 + explore)
    assert dist["UP"] == pytest.approx(explore) and dist["LEFT"] == pytest.approx(explore)  # vẫn có thể đi bừa


@pytest.mark.parametrize("mode", ["random", "greedy", "chase"])
@pytest.mark.parametrize("name", GHOST_MAPS)
def test_expectimax_returns_legal_action_in_every_ghost_mode(mode, name):
    layout, state = load(name)
    r = run_adversarial("Expectimax", layout, state, 2, (), None, mode)
    assert r.action in legal_pacman_actions(layout, state)