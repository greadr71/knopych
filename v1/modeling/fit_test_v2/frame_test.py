# -*- coding: utf-8 -*-
"""Кусок лица с рамкой: проверка колодца под кейкапы.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/fit_test_v2/frame_test.py

Пишет v1/modeling/fit_test_v2/frame_test.stl, печатать лицом на стол.

Два окна 14,0 мм на шаге корпуса, общий колодец, борт у торца как у
корпуса. Проверить: кромка нажатого кейкапа уходит в колодец и в дно
не бьётся; кейкап не трёт стенку у торца и соседа; как напечаталась
пластина над колодцем (она висит над столом на высоте рамки).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Axis, export_stl

from build_housing import (
    CORNER_R,
    FACE_EDGE_R,
    FACE_THK,
    HEIGHT,
    OUTER_MARGIN,
    SWITCH_GAP,
    SWITCH_SIZE,
    WALL,
    _box,
    _edges,
    _fillet,
    _occupied,
    _rounded_box,
    _viewer_is_open,
    well_cut,
)

WINDOWS = 2
RIM_DEPTH = 6.0
FRAME = 3.0
DEPTH = FRAME + RIM_DEPTH

HERE = Path(__file__).resolve().parent


def window_centers():
    pitch = SWITCH_SIZE + SWITCH_GAP
    first = OUTER_MARGIN + SWITCH_SIZE / 2
    return [first + i * pitch for i in range(WINDOWS)]


def frame_test_width():
    return 2 * OUTER_MARGIN + WINDOWS * SWITCH_SIZE + (WINDOWS - 1) * SWITCH_GAP


def build_frame_test():
    width = frame_test_width()
    centers = window_centers()
    part = _rounded_box(0, 0, 0, width, HEIGHT, DEPTH, CORNER_R)
    part -= _rounded_box(
        WALL,
        WALL,
        FRAME + FACE_THK,
        width - 2 * WALL,
        HEIGHT - 2 * WALL,
        DEPTH,
        CORNER_R - WALL,
    )
    part -= well_cut(centers, FRAME)
    switch_y0 = (HEIGHT - SWITCH_SIZE) / 2
    for center_x in centers:
        part -= _box(
            center_x - SWITCH_SIZE / 2, switch_y0, -0.2, SWITCH_SIZE, SWITCH_SIZE, DEPTH + 0.4
        )
    part = _fillet(
        part,
        _edges(part, Axis.X, lambda c: abs(c.Y - HEIGHT) < 0.3 and abs(c.Z) < 0.2),
        FACE_EDGE_R,
        "кромка лица",
    )
    part.label = "FrameTest"
    return part


def _report(part):
    size = part.bounding_box().size
    centers = window_centers()
    plate_mid = FRAME + FACE_THK / 2
    gap_x = (centers[0] + centers[1]) / 2
    checks = {
        "окно пустое": not _occupied(part, centers[0], HEIGHT / 2, plate_mid),
        "пластина между окнами": _occupied(part, gap_x, HEIGHT / 2, plate_mid),
        "колодец пустой": not _occupied(part, gap_x, HEIGHT / 2, FRAME - 0.5),
        "борт у торца": _occupied(part, 1.5, HEIGHT / 2, FRAME - 0.5),
        "кромка лица скруглена": not _occupied(part, 0.2, HEIGHT / 2, 0.2),
    }
    print(f"frame test rebuilt\nbbox mm: {size.X:.1f} x {size.Y:.1f} x {size.Z:.1f}")
    for name, ok in checks.items():
        print(f"  {'ок' if ok else 'ОШИБКА'}: {name}")


def main():
    part = build_frame_test()
    _report(part)
    export_stl(part, HERE / "frame_test.stl")
    print(f"записано {HERE / 'frame_test.stl'}")
    if not _viewer_is_open():
        return
    try:
        from ocp_vscode import show

        show(part, names=[part.label])
        print("viewer: отправлено в панель")
    except Exception as exc:
        print(f"viewer: не открылось ({exc})")


if __name__ == "__main__":
    main()
