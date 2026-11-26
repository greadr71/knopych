# -*- coding: utf-8 -*-
"""Пробные кейкапы MX с иконкой подогрева сиденья.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/fit_test/keycap_test.py

Пишет v1/modeling/fit_test/keycap_test.stl: два кейкапа на одном столе, луч
крестовины у обоих на 0,2 мм шире номинала. Зарубки на кромке:
1 углубление, 2 выпуклая.

- углубление: иконка утоплена в верх под краску. Печать верхом на стол;
- выпуклая: иконка выступает. Печать верхом вверх, на высоте CAP_H
  сменить пластик, и иконка выйдет белой без AMS.

Над светодиодом свитча (север, +Y) горизонтальный прямоугольник
со скруглёнными углами.

Исходная картинка — v1/modeling/fit_test/icons/seat-heater.png, обводка для модели —
v1/modeling/fit_test/icons/seat-heater.svg. На верхе 14 мм линии около 0,65 мм:
это один проход сопла 0,4 мм, толще при этом размере не выходит.

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

from build_housing import _occupied, _viewer_is_open

CAP_BASE = 17.0
CAP_TOP = 14.0
CAP_H = 9.0
CAP_WALL = 1.2
TOP_THK = 1.4
BASE_R = 2.0
TOP_R = 1.5

# Шток по спецификации Cherry: крестовина 4,1 × 1,17 мм. Трубка не шире
# 5,5 мм, иначе при нажатии не войдёт в корпус свитча. Допуск только на
# ширину лучей: она держит кейкап, а длина с запасом съела бы стенку трубки.
# Низ штока вровень с кромкой: выпуклый вариант стоит на столе и штоком.
STEM_DIA = 5.5
CROSS_LEN = 4.2
CROSS_ARM = 1.17
CROSS_DEPTH = 4.0

NOTCH_W = 0.8
NOTCH_H = 0.6
NOTCH_PITCH = 2.0

ICON_SVG = Path(__file__).resolve().parent / "icons" / "seat-heater.svg"
ICON_SIZE = 12.0
ICON_Y = -0.3
ICON_DEPTH = 0.6
LED_HOLE_W = 3.6
LED_HOLE_H = 1.2
LED_HOLE_R = 0.45
LED_HOLE_Y = 5.0

# (вид иконки, допуск лучей, зарубок)
VARIANTS = (
    ("engraved", 0.2, 1),
    ("raised", 0.2, 2),
)
STYLE_NAMES = {"engraved": "углубление", "raised": "выпуклая"}

PRINT_SPACING = 5.0

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


def _stem(tol):
    z_top = _inner_top_z()
    length = z_top + 0.1
    stem = Pos(0, 0, length / 2) * Cylinder(STEM_DIA / 2, length)
    depth = CROSS_DEPTH + 0.1
    z_mid = -0.1 + depth / 2
    cross_arm = CROSS_ARM + tol
    stem -= Pos(0, 0, z_mid) * Box(CROSS_LEN, cross_arm, depth)
    stem -= Pos(0, 0, z_mid) * Box(cross_arm, CROSS_LEN, depth)
    return stem


def _notches(count):
    y = -CAP_BASE / 2 + CAP_WALL / 2
    cuts = None
    for i in range(count):
        x = (i - (count - 1) / 2) * NOTCH_PITCH
        cut = Pos(x, y, NOTCH_H / 2 - 0.05) * Box(NOTCH_W, CAP_WALL + 0.4, NOTCH_H + 0.1)
        cuts = cut if cuts is None else cuts + cut
    return cuts


def seat_heat_icon():
    """Иконка из SVG: длинная сторона ICON_SIZE, центр чуть ниже середины."""
    icon = Sketch(import_svg(ICON_SVG))
    box = icon.bounding_box()
    icon = scale(icon, ICON_SIZE / max(box.size.X, box.size.Y))
    center = icon.bounding_box().center()
    return Pos(-center.X, ICON_Y - center.Y) * icon


def _base(tol, marks):
    return _shell() + _stem(tol) - _notches(marks)


def build_keycap(style, tol, marks):
    cap = _base(tol, marks)
    icon = seat_heat_icon()
    if style == "engraved":
        cap -= extrude(Plane.XY.offset(CAP_H - ICON_DEPTH) * icon, ICON_DEPTH + 0.1)
    else:
        cap += extrude(Plane.XY.offset(CAP_H - 0.05) * icon, ICON_DEPTH + 0.05)
    hole_h = TOP_THK + ICON_DEPTH + 0.4
    hole = Pos(0, LED_HOLE_Y) * RectangleRounded(LED_HOLE_W, LED_HOLE_H, LED_HOLE_R)
    cap -= extrude(Plane.XY.offset(_inner_top_z() - 0.1) * hole, hole_h)
    cap.label = f"Keycap_{style}_tol{tol:.1f}"
    return cap


def for_print(cap, style, index):
    """Углубление — верхом на стол, выпуклая — верхом вверх."""
    placed = cap if style == "raised" else Rot(180, 0, 0) * cap
    x = index * (CAP_BASE + PRINT_SPACING)
    return Pos(x, 0, -placed.bounding_box().min.Z) * placed


def _report(caps):
    print("keycap test rebuilt")
    z_cross = CROSS_DEPTH / 2
    for cap, (style, tol, marks) in zip(caps, VARIANTS):
        base = _base(tol, marks)
        delta = cap.volume - base.volume
        checks = {
            "одно тело": len(cap.solids()) == 1,
            "крестовина пустая": not _occupied(cap, 0, 0, z_cross)
            and not _occupied(cap, CROSS_LEN / 2 - 0.2, 0, z_cross),
            "трубка штока цела": _occupied(cap, 1.6, 1.6, z_cross),
            "иконка есть": delta > 1.0 if style == "raised" else delta < -1.0,
        }
        checks["отверстие светодиода"] = not _occupied(
            cap, 0, LED_HOLE_Y, CAP_H - TOP_THK / 2
        )
        bad = [name for name, ok in checks.items() if not ok]
        status = "ок" if not bad else "ОШИБКА: " + ", ".join(bad)
        print(
            f"  {STYLE_NAMES[style]}, лучи {CROSS_ARM + tol:.2f}: "
            f"иконка {delta:+.1f} мм3, {status}"
        )


def main():
    caps = [build_keycap(*variant) for variant in VARIANTS]
    _report(caps)
    printed = [
        for_print(cap, style, i) for i, (cap, (style, _, _)) in enumerate(zip(caps, VARIANTS))
    ]
    plate = printed[0]
    for cap in printed[1:]:
        plate += cap
    export_stl(plate, HERE / "keycap_test.stl")
    print(f"записано {HERE / 'keycap_test.stl'}")
    if not _viewer_is_open():
        return
    try:
        from ocp_vscode import show

        shown = [
            Pos(i * (CAP_BASE + PRINT_SPACING), 0, 0) * cap for i, cap in enumerate(caps)
        ]
        show(*shown, names=[cap.label for cap in caps])
        print("viewer: отправлено в панель")
    except Exception as exc:
        print(f"viewer: не открылось ({exc})")


if __name__ == "__main__":
    main()
