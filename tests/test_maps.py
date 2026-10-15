"""Test các file bản đồ: định dạng đúng, đủ các nhóm đặc điểm mà đề yêu cầu."""
from collections import deque

import pytest

from src.engine import DIRECTIONS, load_layout
from tests.helpers import MAPS, load

ALL = sorted(MAPS)


def reachable(layout, start):
    seen, queue = {start}, deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in DIRECTIONS.values():
            n = (r + dr, c + dc)
            if 0 <= n[0] < layout.height and 0 <= n[1] < layout.width and n not in layout.walls and n not in seen:
                seen.add(n)
                queue.append(n)
    return seen


@pytest.mark.parametrize("name", ALL)
def test_every_map_loads_and_is_rectangular(name):
    with open(MAPS[name], encoding="utf-8") as f:
        lines = [ln.rstrip("\r") for ln in f.read().split("\n") if ln.strip()]
    assert len({len(ln) for ln in lines}) == 1
    layout, state = load_layout(MAPS[name])
    assert state.pacman not in layout.walls


@pytest.mark.parametrize("name", [n for n in ALL if n != "no_solution"])
def test_food_and_ghosts_are_reachable(name):
    layout, state = load(name)
    area = reachable(layout, state.pacman)
    assert state.food <= area
    assert set(state.ghosts) <= area


def test_no_solution_map_really_has_no_solution():
    layout, state = load("no_solution")
    assert not (state.food & reachable(layout, state.pacman))


def test_required_map_categories_are_covered():
    info = {}
    for name in ALL:
        layout, state = load(name)
        info[name] = (layout.width * layout.height, len(state.food), bool(layout.costs), len(state.ghosts))
    assert min(a for a, *_ in info.values()) <= 100             # có bản đồ nhỏ
    assert max(a for a, *_ in info.values()) >= 300             # có bản đồ lớn
    assert any(f == 1 for _, f, *_ in info.values())            # một mục tiêu
    assert any(f > 1 for _, f, *_ in info.values())             # nhiều mục tiêu
    assert any(w for *_, w, _ in info.values())                 # chi phí không đồng nhất
    assert any(not w for _, _, w, _ in info.values())           # chi phí đồng nhất
    assert any(g for *_, g in info.values())                    # có ghost
