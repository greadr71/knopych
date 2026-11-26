# -*- coding: utf-8 -*-
"""Пробник посадки свитча и крышки-защёлки: кусок корпуса с тремя окнами.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/fit_test/switch_fit_test.py

Пишет v1/modeling/fit_test/switch_fit_test.stl (короб, печатать лицом на стол) и
v1/modeling/fit_test/switch_fit_test_lid.stl (крышка, приклеиваемой стороной на стол).
Окна 14,0 / 14,1 / 14,2 мм, под окном столько точек, каков его номер.
Между первым и вторым окном 5 мм, между вторым и третьим 4 мм, как в
корпусе: так видно, трутся ли соседние кейкапы.
Лицо и стенки той же толщины, что у корпуса, чтобы защёлка свитча вела
себя так же.

Крышка — вкладыш в открытую спину, заподлицо с задней кромкой. Короб
защёлкивается на неё: гребешки посередине длинных стенок входят в
канавки на кромке крышки. Тугость подбирается числом SNAP_H.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Axis, Cylinder, Plane, Polygon, Pos, Rot, export_stl, extrude

from build_housing import (
    CORNER_R,
    FACE_EDGE_R,
    FACE_THK,
    HEIGHT,
    OUTER_MARGIN,
    WALL,
    _box,
    _edges,
    _fillet,
    _occupied,
    _rounded_box,
    _viewer_is_open,
)

WINDOW_SIZES = (14.0, 14.1, 14.2)
# Промежутки между соседними окнами: 5 мм — шаг около 19, 4 мм — шаг корпуса
WINDOW_GAPS = (5.0, 4.0)
RIM_DEPTH = 6.0
MARK_DIA = 1.2
MARK_PITCH = 2.5

# Крышка-вкладыш
LID_CLEARANCE = 0.2
LID_THK = 1.6
SKIRT_H = 2.0
SKIRT_THK = 1.6

# Защёлка: гребешок на стенке короба, канавка на крышке, скосы 45°
SNAP_H = 0.5
SNAP_LEN = 12.0
GROOVE_DEPTH = 0.6
SNAP_Z = RIM_DEPTH - (LID_THK + SKIRT_H) / 2

# Паз на задней кромке торца, чтобы подцепить короб
PRY_WIDTH = 8.0
PRY_DEPTH = 1.0

HERE = Path(__file__).resolve().parent


def window_lefts():
    """Левый край каждого окна по X."""
    lefts = [OUTER_MARGIN]
    for size, gap in zip(WINDOW_SIZES, WINDOW_GAPS):
        lefts.append(lefts[-1] + size + gap)
    return lefts


def fit_test_width():
    last = window_lefts()[-1] + WINDOW_SIZES[-1]
    return last + OUTER_MARGIN


def _v_prism(x0, length, y_base, height, sign, z, overlap=0.1):
    """Треугольный брусок вдоль X со скосами 45°: основание на y_base, вершина в sign·Y."""
    points = [
        (y_base - sign * overlap, z - height - overlap),
        (y_base + sign * height, z),
        (y_base - sign * overlap, z + height + overlap),
    ]
    # Порядок вершин задаёт сторону вытягивания: держим его одним для обоих знаков.
    if sign < 0:
        points.reverse()
    return Pos(x0, 0, 0) * extrude(Plane.YZ * Polygon(*points, align=None), length)


def build_fit_test():
    width = fit_test_width()
    part = _rounded_box(0, 0, 0, width, HEIGHT, RIM_DEPTH, CORNER_R)
    part -= _rounded_box(
        WALL,
        WALL,
        FACE_THK,
        width - 2 * WALL,
        HEIGHT - 2 * WALL,
        RIM_DEPTH,
        CORNER_R - WALL,
    )
    part = _fillet(
        part,
        _edges(
            part,
            Axis.X,
            lambda c: abs(c.Y - HEIGHT) < 0.3 and abs(c.Z) < 0.2,
        ),
        FACE_EDGE_R,
        "кромка лица",
    )

    mark_y = (WALL + (HEIGHT - max(WINDOW_SIZES)) / 2) / 2
    for number, (left, size) in enumerate(zip(window_lefts(), WINDOW_SIZES), 1):
        part -= _box(left, (HEIGHT - size) / 2, -0.2, size, size, RIM_DEPTH + 0.4)
        center_x = left + size / 2
        for i in range(number):
            x = center_x + (i - (number - 1) / 2) * MARK_PITCH
            part -= Pos(x, mark_y, FACE_THK / 2) * Cylinder(
                MARK_DIA / 2, FACE_THK + 0.4
            )

    snap_x = width / 2 - SNAP_LEN / 2
    part += _v_prism(snap_x, SNAP_LEN, WALL, SNAP_H, 1, SNAP_Z)
    part += _v_prism(snap_x, SNAP_LEN, HEIGHT - WALL, SNAP_H, -1, SNAP_Z)

    part -= _box(
        -0.1,
        (HEIGHT - PRY_WIDTH) / 2,
        RIM_DEPTH - PRY_DEPTH,
        WALL + 0.2,
        PRY_WIDTH,
        PRY_DEPTH + 0.1,
    )

    part.label = "SwitchFitTest"
    return part


def build_lid():
    """Крышка-вкладыш в закрытом положении: задняя плоскость на Z = RIM_DEPTH."""
    width = fit_test_width()
    x0 = WALL + LID_CLEARANCE
    y0 = WALL + LID_CLEARANCE
    lid_w = width - 2 * x0
    lid_h = HEIGHT - 2 * y0
    radius = CORNER_R - WALL - LID_CLEARANCE
    z_bottom = RIM_DEPTH - LID_THK - SKIRT_H

    lid = _rounded_box(x0, y0, z_bottom, lid_w, lid_h, LID_THK + SKIRT_H, radius)
    lid -= _rounded_box(
        x0 + SKIRT_THK,
        y0 + SKIRT_THK,
        z_bottom - 0.1,
        lid_w - 2 * SKIRT_THK,
        lid_h - 2 * SKIRT_THK,
        SKIRT_H + 0.1,
        radius - SKIRT_THK,
    )

    groove_len = SNAP_LEN + 2.0
    groove_x = width / 2 - groove_len / 2
    lid -= _v_prism(groove_x, groove_len, y0, GROOVE_DEPTH, 1, SNAP_Z, 0.2)
    lid -= _v_prism(groove_x, groove_len, HEIGHT - y0, GROOVE_DEPTH, -1, SNAP_Z, 0.2)

    lid.label = "SwitchFitTestLid"
    return lid


def lid_for_print(lid):
    """Крышка приклеиваемой стороной на стол, юбкой вверх."""
    flipped = Rot(180, 0, 0) * lid
    return Pos(0, 0, -flipped.bounding_box().min.Z) * flipped


def _report(part):
    size = part.bounding_box().size
    print(
        "switch fit test rebuilt\n"
        f"bbox mm: {size.X:.1f} x {size.Y:.1f} x {size.Z:.1f}"
    )
    for left, size_mm in zip(window_lefts(), WINDOW_SIZES):
        center = left + size_mm / 2
        inside = not _occupied(part, left + 0.2, HEIGHT / 2, FACE_THK / 2)
        edge = _occupied(part, left - 0.2, HEIGHT / 2, FACE_THK / 2)
        status = "ок" if inside and edge else "ОШИБКА"
        print(f"  {status}: окно {size_mm:.1f} мм, центр X {center:.2f}")


def _report_lid(part, lid):
    mid_x = fit_test_width() / 2
    y0 = WALL + LID_CLEARANCE
    common = part & lid
    overlap = common.volume if common is not None else 0.0
    lid_box = lid.bounding_box()
    checks = {
        "крышка не пересекает короб": overlap < 1e-3,
        "крышка заподлицо с кромкой": abs(lid_box.max.Z - RIM_DEPTH) < 1e-6,
        "до лица есть зазор": lid_box.min.Z > FACE_THK,
    }
    for side, sign, wall_y, lid_y in (
        ("низ", 1, WALL, y0),
        ("верх", -1, HEIGHT - WALL, HEIGHT - y0),
    ):
        checks[f"{side}: гребешок на стенке"] = _occupied(
            part, mid_x, wall_y + sign * 0.2, SNAP_Z
        )
        checks[f"{side}: канавка на крышке"] = not _occupied(
            lid, mid_x, lid_y + sign * 0.3, SNAP_Z
        )
        checks[f"{side}: гребешок в канавке"] = _occupied(
            part, mid_x, lid_y + sign * 0.1, SNAP_Z
        )
    for name, ok in checks.items():
        print(f"  {'ок' if ok else 'ОШИБКА'}: {name}")
    print(
        f"  крышка {lid_box.size.X:.1f} x {lid_box.size.Y:.1f} x {lid_box.size.Z:.1f} мм, "
        f"натяг защёлки {SNAP_H - LID_CLEARANCE:.2f} мм"
    )


def main():
    part = build_fit_test()
    lid = build_lid()
    _report(part)
    _report_lid(part, lid)
    export_stl(part, HERE / "switch_fit_test.stl")
    export_stl(lid_for_print(lid), HERE / "switch_fit_test_lid.stl")
    print(f"записано {HERE / 'switch_fit_test.stl'} и {HERE / 'switch_fit_test_lid.stl'}")
    if not _viewer_is_open():
        return
    try:
        from ocp_vscode import show

        show(part, Pos(0, 0, 10) * lid, names=["SwitchFitTest", "SwitchFitTestLid"])
        print("viewer: отправлено в панель")
    except Exception as exc:
        print(f"viewer: не открылось ({exc})")


if __name__ == "__main__":
    main()
