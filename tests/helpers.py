"""Hàm dùng chung cho các file test."""
import glob
import os
from dataclasses import replace

from src.engine import load_layout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPS = {os.path.splitext(os.path.basename(p))[0]: p
        for p in sorted(glob.glob(os.path.join(ROOT, "maps", "*.txt")))}


def load(name):
    """Nạp bản đồ theo tên (không có .txt)."""
    return load_layout(MAPS[name])


def load_solo(name):
    """Nạp bản đồ và bỏ ghost (bài toán tìm đường: Pacman đi một mình)."""
    layout, start = load(name)
    return layout, replace(start, ghosts=())


def write_map(tmp_path, text, name="m.txt"):
    """Ghi một bản đồ tạm để test các tình huống tự dựng."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return load_layout(str(path))
