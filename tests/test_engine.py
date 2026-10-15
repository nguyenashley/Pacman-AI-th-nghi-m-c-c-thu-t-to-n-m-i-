"""Test engine: đọc bản đồ, luật chơi, hàm chuyển trạng thái."""
import dataclasses

import pytest

from src.engine import (
    FOOD_REWARD, GameState, is_lose, is_win, legal_ghost_actions,
    legal_pacman_actions, load_layout, move_ghost, move_pacman, step_cost,
)
from tests.helpers import load, write_map


def test_load_layout_reads_positions():
    layout, state = load("uniform")
    assert (layout.height, layout.width) == (5, 7)
    assert state.pacman == (1, 1)
    assert state.food == frozenset({(3, 5)})
    assert state.ghosts == ()


def test_load_layout_reads_weighted_cells():
    layout, _ = load("weighted_trap")
    assert len(layout.costs) == 10
    assert set(layout.costs.values()) == {9}


def test_load_layout_without_pacman_raises(tmp_path):
    with pytest.raises(ValueError):
        write_map(tmp_path, "%%%%\n%. %\n%%%%")


def test_load_layout_pads_short_lines(tmp_path):
    # dòng ngắn hơn được độn thêm tường, không làm lệch tọa độ
    layout, state = write_map(tmp_path, "%%%%%\n%P.\n%%%%%")
    assert layout.width == 5
    assert (1, 4) in layout.walls


def test_pacman_cannot_walk_through_walls():
    layout, state = load("uniform")
    assert set(legal_pacman_actions(layout, state)) == {"DOWN", "RIGHT"}
    with pytest.raises(ValueError):
        move_pacman(layout, state, "UP")


def test_move_pacman_does_not_mutate_old_state():
    layout, state = load("uniform")
    new = move_pacman(layout, state, "RIGHT")
    assert state.pacman == (1, 1) and state.score == 0
    assert new.pacman == (1, 2) and new is not state


def test_gamestate_is_frozen():
    _, state = load("uniform")
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.pacman = (0, 0)


def test_default_step_cost_is_one():
    layout, state = load("uniform")
    assert step_cost(layout, state, "RIGHT") == 1
    assert move_pacman(layout, state, "RIGHT").score == -1


def test_weighted_cell_costs_its_number():
    layout, state = load("weighted_trap")
    assert step_cost(layout, state, "RIGHT") == 9
    assert move_pacman(layout, state, "RIGHT").score == -9


def test_eating_food_adds_reward_and_removes_it(tmp_path):
    layout, state = write_map(tmp_path, "%%%%%\n%P. %\n%%%%%")
    new = move_pacman(layout, state, "RIGHT")
    assert new.food == frozenset()
    assert new.score == FOOD_REWARD - 1
    assert len(state.food) == 1  # state cũ không đổi


def test_win_and_lose_conditions():
    win = GameState((1, 1), (), frozenset())
    lose = GameState((1, 1), ((1, 1),), frozenset({(2, 2)}))
    playing = GameState((1, 1), ((3, 3),), frozenset({(2, 2)}))
    assert is_win(win) and not is_lose(win)
    assert is_lose(lose) and not is_win(lose)
    assert not is_win(playing) and not is_lose(playing)


def test_ghosts_never_share_a_cell(tmp_path):
    layout, state = write_map(tmp_path, "%%%%%%\n%PGG %\n%%%%%%")
    # ghost 0 ở (1,2) không được đi RIGHT vào ô của ghost 1 ở (1,3)
    assert "RIGHT" not in legal_ghost_actions(layout, state, 0)
    with pytest.raises(ValueError):
        move_ghost(layout, state, 0, "RIGHT")


def test_move_ghost_keeps_other_fields():
    layout, state = load("ghost_small")
    action = legal_ghost_actions(layout, state, 0)[0]
    new = move_ghost(layout, state, 0, action)
    assert new.pacman == state.pacman and new.food == state.food and new.score == state.score
    assert new.ghosts != state.ghosts
