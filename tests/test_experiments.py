"""Test run_experiments.py: ghi đúng file CSV với đúng cột và số dòng."""
import csv

import run_experiments as ex
from tests.helpers import MAPS


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_search_experiment_writes_one_row_per_map_and_algorithm(tmp_path):
    ex.exp_search(str(tmp_path))
    rows = read(tmp_path / "search_results.csv")
    assert len(rows) == len(MAPS) * 5
    assert {r["algorithm"] for r in rows} == {"DFS", "BFS", "UCS", "Greedy", "A*"}
    assert all(r["found"] == "False" for r in rows if r["map"] == "no_solution")


def test_heuristic_experiment_marks_optimal_costs(tmp_path):
    ex.exp_heuristic(str(tmp_path))
    rows = read(tmp_path / "search_heuristic.csv")
    assert len(rows) == len(MAPS) * 3
    assert all(r["optimal"] == "True" for r in rows if r["map"] != "no_solution")


def test_adversarial_experiment_only_uses_ghost_maps(tmp_path):
    ex.exp_adversarial(str(tmp_path), max_depth=2, budget=10)
    rows = read(tmp_path / "adversarial_compare.csv")
    assert rows and all(int(r["ghosts"]) > 0 for r in rows)
    assert all(r["alphabeta_matches_minimax"] == "True" for r in rows if r["algorithm"] == "Alpha-Beta")


def test_write_csv_works_when_output_is_on_another_drive(tmp_path, monkeypatch):
    # Windows: os.path.relpath báo ValueError khi hai đường dẫn khác ổ đĩa (C: và D:)
    def fake_relpath(*args, **kwargs):
        raise ValueError("path is on mount 'C:', start on mount 'D:'")
    monkeypatch.setattr(ex.os.path, "relpath", fake_relpath)
    ex.write_csv(str(tmp_path), "x.csv", ["a"], [[1]])
    assert read(tmp_path / "x.csv") == [{"a": "1"}]