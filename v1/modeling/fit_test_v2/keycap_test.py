# -*- coding: utf-8 -*-
"""Кейкап MX с углублённой иконкой подогрева сиденья, вторая печать.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/fit_test_v2/keycap_test.py

Пишет v1/modeling/fit_test_v2/keycap_test.stl: один кейкап, верхом на стол.

По первой печати: выпуклая иконка не нужна, шток и крестовина те же.
Отверстие под светодиод на 0,4 мм шире и выше, чем в первой печати
(3,6 × 1,2 → 4,0 × 1,6), углы скруглены с тем же отступом.

Иконка — v1/modeling/fit_test/icons/seat-heater.svg.

Оси кейкапа: низ кромки при Z=0, верх при Z=CAP_H, +Y — север свитча.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import (
    Box,
    Cylinder,
    Plane,
    Pos,
    RectangleRounded,
    Rot,
    Sketch,
    export_stl,
    extrude,
    import_svg,
    loft,
    scale,
)

from build_housing import KEYCAP_BASE, KEYCAP_BASE_R, _occupied, _viewer_is_open

CAP_BASE = KEYCAP_BASE
CAP_TOP = 14.0
CAP_H = 9.0
CAP_WALL = 1.2
TOP_THK = 1.4
BASE_R = KEYCAP_BASE_R
TOP_R = 1.5

# Шток по спецификации Cherry: крестовина 4,1 × 1,17 мм, лучи шире на CROSS_TOL.
STEM_DIA = 5.5
CROSS_LEN = 4.2
CROSS_ARM = 1.17
CROSS_TOL = 0.2
CROSS_DEPTH = 4.0

ICON_SVG = Path(__file__).resolve().parents[1] / "fit_test" / "icons" / "seat-heater.svg"
ICON_SIZE = 12.0
ICON_Y = -0.3
ICON_DEPTH = 0.6

LED_HOLE_GROW = 0.4
LED_HOLE_W = 3.6 + LED_HOLE_GROW
LED_HOLE_H = 1.2 + LED_HOLE_GROW
LED_HOLE_R = 0.45 + LED_HOLE_GROW / 2
LED_HOLE_Y = 5.0

HERE = Path(__file__).resolve().parent


def _inner_top_z():
    return CAP_H - TOP_THK


def _width_at(z):
    return CAP_BASE - (CAP_BASE - CAP_TOP) * z / CAP_H


def _shell():
    outer = loft(
        [
            Plane.XY * RectangleRounded(CAP_BASE, CAP_BASE, BASE_R),
            Plane.XY.offset(CAP_H) * RectangleRounded(CAP_TOP, CAP_TOP, TOP_R),
        ]
    )
    z_top = _inner_top_z()
    inner = loft(
        [
            Plane.XY.offset(-0.1)
            * RectangleRounded(CAP_BASE - 2 * CAP_WALL, CAP_BASE - 2 * CAP_WALL, 0.8),
            Plane.XY.offset(z_top)
            * RectangleRounded(
                _width_at(z_top) - 2 * CAP_WALL, _width_at(z_top) - 2 * CAP_WALL, 0.5
            ),
        ]
    )
    return outer - inner


def _stem():
    z_top = _inner_top_z()
    length = z_top + 0.1
    stem = Pos(0, 0, length / 2) * Cylinder(STEM_DIA / 2, length)
    depth = CROSS_DEPTH + 0.1
    z_mid = -0.1 + depth / 2
    cross_arm = CROSS_ARM + CROSS_TOL
    stem -= Pos(0, 0, z_mid) * Box(CROSS_LEN, cross_arm, depth)
    stem -= Pos(0, 0, z_mid) * Box(cross_arm, CROSS_LEN, depth)
    return stem


def seat_heat_icon():
    """Иконка из SVG: длинная сторона ICON_SIZE, центр чуть ниже середины."""
    icon = Sketch(import_svg(ICON_SVG))
    box = icon.bounding_box()
    icon = scale(icon, ICON_SIZE / max(box.size.X, box.size.Y))
    center = icon.bounding_box().center()
    return Pos(-center.X, ICON_Y - center.Y) * icon


def build_keycap():
    cap = _shell() + _stem()
    cap -= extrude(Plane.XY.offset(CAP_H - ICON_DEPTH) * seat_heat_icon(), ICON_DEPTH + 0.1)
    hole = Pos(0, LED_HOLE_Y) * RectangleRounded(LED_HOLE_W, LED_HOLE_H, LED_HOLE_R)
    cap -= extrude(Plane.XY.offset(_inner_top_z() - 0.1) * hole, TOP_THK + 0.5)
    cap.label = "Keycap_v2"
    return cap


def for_print(cap):
    """Верхом на стол: углубление иконки получает фактуру стола, как лицо."""
    placed = Rot(180, 0, 0) * cap
    return Pos(0, 0, -placed.bounding_box().min.Z) * placed


def _report(cap):
    z_cross = CROSS_DEPTH / 2
    plain = _shell() + _stem()
    checks = {
        "одно тело": len(cap.solids()) == 1,
        "крестовина пустая": not _occupied(cap, 0, 0, z_cross)
        and not _occupied(cap, CROSS_LEN / 2 - 0.2, 0, z_cross),
        "трубка штока цела": _occupied(cap, 1.6, 1.6, z_cross),
        "иконка утоплена": cap.volume < plain.volume - 1.0,
        "отверстие светодиода по ширине": not _occupied(
            cap, LED_HOLE_W / 2 - 0.2, LED_HOLE_Y, CAP_H - TOP_THK / 2
        ),
        "отверстие светодиода по высоте": not _occupied(
            cap, 0, LED_HOLE_Y + LED_HOLE_H / 2 - 0.2, CAP_H - TOP_THK / 2
        ),
    }
    print("keycap v2 rebuilt")
    for name, ok in checks.items():
        print(f"  {'ок' if ok else 'ОШИБКА'}: {name}")
    print(f"  отверстие светодиода {LED_HOLE_W:.1f} x {LED_HOLE_H:.1f} мм")


def main():
    cap = build_keycap()
    _report(cap)
    export_stl(for_print(cap), HERE / "keycap_test.stl")
    print(f"записано {HERE / 'keycap_test.stl'}")
    if not _viewer_is_open():
        return
    try:
        from ocp_vscode import show

        show(cap, names=[cap.label])
        print("viewer: отправлено в панель")
    except Exception as exc:
        print(f"viewer: не открылось ({exc})")


if __name__ == "__main__":
    main()
