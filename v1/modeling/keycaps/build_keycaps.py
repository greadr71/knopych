# -*- coding: utf-8 -*-
"""Шесть кейкапов MX с углублёнными иконками.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/keycaps/build_keycaps.py

Пишет v1/modeling/keycaps/keycaps.stl: шесть крышек верхом на стол,
слева направо как на лице корпуса.

    положение 1, положение 2, положение 3,
    подогрев водителя, лобовое, подогрев пассажира

Геометрия оболочки, штока и окна светодиода — как у второй печати
(v1/modeling/fit_test_v2/keycap_test.py). Иконка утоплена на 0,6 мм.
Окно светодиода 4,0×1,6 мм на севере (+Y).

Подогрев пассажира — v1/modeling/fit_test/icons/seat-heater.svg.
Подогрев водителя — та же иконка, отражённая по горизонтали.
Лобовое и положения — v1/modeling/keycaps/icons/, ядро линии без ореола.
Длинная сторона подогрева и лобового 12 мм (штрих около 0,65 мм,
один проход сопла 0,4 мм). Положения 10 мм. Лобовое и положения
сидят на 1 мм ниже подогревов: иначе верх вплотную к окну светодиода.

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
    Rectangle,
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

STEM_DIA = 5.5
CROSS_LEN = 4.2
CROSS_ARM = 1.17
CROSS_TOL = 0.2
CROSS_DEPTH = 4.0

ICON_Y = -0.3
# Лобовое и положения: верх был слишком близко к окну светодиода.
ICON_Y_SLOT = ICON_Y - 1.0
ICON_DEPTH = 0.4
# Паз шире контура на ICON_GROW с каждой стороны: штрих 0.65 -> 0.83,
# и кончики, которые сопло 0,4 не рисует, становятся читаемыми.
# Один на весь набор: у подогрева это же значение держит 0.85 мм между головками.
ICON_GROW = 0.10
HEATER_SIZE = 12.0
WIND_SIZE = 12.0
SEAT_POS_SIZE = 10.0

LED_HOLE_GROW = 0.4
LED_HOLE_W = 3.6 + LED_HOLE_GROW
LED_HOLE_H = 1.2 + LED_HOLE_GROW
LED_HOLE_R = 0.45 + LED_HOLE_GROW / 2
LED_HOLE_Y = 5.0

PRINT_SPACING = 5.0

HERE = Path(__file__).resolve().parent
ICONS = HERE / "icons"
HEATER_SVG = ICONS / "seat-heater-2.svg"

# имя, svg, длинная сторона, зеркало по X, уводить от окна светодиода, подпись
LAYOUT = (
    ("pos1", ICONS / "seat-pos-1.svg", SEAT_POS_SIZE, False, True, "Положение 1"),
    ("pos2", ICONS / "seat-pos-2.svg", SEAT_POS_SIZE, False, True, "Положение 2"),
    ("pos3", ICONS / "seat-pos-3.svg", SEAT_POS_SIZE, False, True, "Положение 3"),
    ("driver", HEATER_SVG, HEATER_SIZE, True, False, "Подогрев водителя"),
    ("wind", ICONS / "windshield.svg", WIND_SIZE, False, True, "Лобовое"),
    ("passenger", HEATER_SVG, HEATER_SIZE, False, False, "Подогрев пассажира"),
)


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


def _area(shape):
    if shape is None or not getattr(shape, "area", 0):
        return 0.0
    return shape.area


def _span_at(icon, y, band=0.45):
    hit = icon & (Pos(0, y) * Rectangle(40, band))
    if not getattr(hit, "area", 0):
        return 0.0
    return hit.bounding_box().size.X


def _upper_area(icon, side):
    """Площадь штриха в верхней половине, слева или справа."""
    box = icon.bounding_box()
    x = box.center().X + (-0.25 if side == "left" else 0.25) * box.size.X
    y = box.max.Y - 0.22 * box.size.Y
    sliver = Pos(x, y) * Rectangle(box.size.X * 0.5, box.size.Y * 0.45)
    return _area(icon & sliver)


def _grown(icon, amount):
    """Толще контура: объединение копий со сдвигом, а не offset.

    offset() на этих контурах даёт самопересечения и дырки в сетке:
    объединение сдвинутых копий строит ту же утолщённую форму булевыми
    операциями и остаётся замкнутым.
    """
    out = icon
    for dx in (-amount, 0.0, amount):
        for dy in (-amount, 0.0, amount):
            if dx or dy:
                out = out + Pos(dx, dy) * icon
    return out.clean()


def _prepare(svg, size, mirror_x):
    """Длинная сторона size, центр в нуле. Зеркало — спинка на другую сторону."""
    icon = Sketch(import_svg(svg))
    box = icon.bounding_box()
    icon = scale(icon, size / max(box.size.X, box.size.Y))
    if mirror_x:
        icon = icon.mirror(Plane.YZ)
    if ICON_GROW:
        icon = _grown(icon, ICON_GROW)
    center = icon.bounding_box().center()
    return Pos(-center.X, -center.Y) * icon


def _heater_upright(icon):
    """У подогрева низ (подушка) шире макушки спинки."""
    box = icon.bounding_box()
    bottom = _span_at(icon, box.min.Y + 0.12 * box.size.Y)
    top = _span_at(icon, box.max.Y - 0.08 * box.size.Y)
    return bottom > top * 1.5


def _digit_upper_right(icon):
    """Цифра — отдельный контур справа сверху, сиденье не перевёрнуто и не отзеркалено."""
    faces = list(icon.faces())
    if len(faces) != 2:
        return False
    digit = min(faces, key=lambda face: face.area)
    center = digit.bounding_box().center()
    return center.X > 0.3 and center.Y > 0.3


def _place(icon, y0, avoid_led):
    """y0 — центр иконки. Если задевает окно светодиода, уводим вниз целиком."""
    y = y0
    top = RectangleRounded(CAP_TOP, CAP_TOP, TOP_R)
    hole = Pos(0, LED_HOLE_Y) * RectangleRounded(LED_HOLE_W, LED_HOLE_H, LED_HOLE_R)
    for _ in range(40):
        placed = Pos(0, y) * icon
        on_face = _area(placed & top) > 0.97 * _area(placed)
        clear = _area(placed & hole) < 0.02
        if on_face and (clear or not avoid_led):
            return placed, y, clear
        if avoid_led and on_face and not clear:
            y -= 0.1
            continue
        break
    raise RuntimeError("иконка не помещается на верх кейкапа без окна светодиода")


def _led_hole():
    return Pos(0, LED_HOLE_Y) * RectangleRounded(LED_HOLE_W, LED_HOLE_H, LED_HOLE_R)


def build_keycap(icon, label):
    cap = _shell() + _stem()
    cap -= extrude(Plane.XY.offset(CAP_H - ICON_DEPTH) * icon, ICON_DEPTH + 0.1)
    cap -= extrude(Plane.XY.offset(_inner_top_z() - 0.1) * _led_hole(), TOP_THK + 0.5)
    cap.label = label
    return cap


def for_print(cap, index):
    """Верхом на стол: углубление получает фактуру стола."""
    placed = Rot(180, 0, 0) * cap
    x = index * (CAP_BASE + PRINT_SPACING)
    return Pos(x, 0, -placed.bounding_box().min.Z) * placed


def _report(built, plain):
    z_cross = CROSS_DEPTH / 2
    z_led = CAP_H - TOP_THK / 2
    ok = True
    print("keycaps rebuilt")
    for cap, title, y, led_clear, extra in built:
        checks = {
            "одно тело": len(cap.solids()) == 1,
            "крестовина пустая": not _occupied(cap, 0, 0, z_cross)
            and not _occupied(cap, CROSS_LEN / 2 - 0.2, 0, z_cross),
            "трубка штока цела": _occupied(cap, 1.6, 1.6, z_cross),
            "иконка утоплена": cap.volume < plain.volume - 1.0,
            "отверстие светодиода по ширине": not _occupied(
                cap, LED_HOLE_W / 2 - 0.2, LED_HOLE_Y, z_led
            ),
            "отверстие светодиода по высоте": not _occupied(
                cap, 0, LED_HOLE_Y + LED_HOLE_H / 2 - 0.2, z_led
            ),
            "окно светодиода не съедено иконкой": led_clear,
        }
        checks.update(extra)
        bad = [name for name, good in checks.items() if not good]
        if bad:
            ok = False
        status = "ок" if not bad else "ОШИБКА: " + ", ".join(bad)
        print(f"  {title}: Y={y:+.1f}, {status}")
    return ok


def main():
    plain = _shell() + _stem()
    built = []
    for _name, svg, size, mirror_x, avoid_led, title in LAYOUT:
        icon = _prepare(svg, size, mirror_x)
        extra = {}
        if "pos" in svg.stem:
            extra["цифра справа сверху"] = _digit_upper_right(icon)
        elif svg == HEATER_SVG:
            extra["сиденье не перевёрнуто"] = _heater_upright(icon)
            on_left = _upper_area(icon, "left") > _upper_area(icon, "right")
            extra["спинка слева" if mirror_x else "спинка справа"] = (
                on_left if mirror_x else not on_left
            )
        y0 = ICON_Y_SLOT if avoid_led else ICON_Y
        placed, y, led_clear = _place(icon, y0, avoid_led)
        cap = build_keycap(placed, title)
        built.append((cap, title, y, led_clear, extra))
    if not _report(built, plain):
        raise SystemExit(1)
    printed = [for_print(cap, i) for i, (cap, *_) in enumerate(built)]
    plate = printed[0]
    for cap in printed[1:]:
        plate += cap
    export_stl(plate, HERE / "keycaps.stl")
    print(f"записано {HERE / 'keycaps.stl'}")
    if not _viewer_is_open():
        return
    try:
        from ocp_vscode import show

        shown = [
            Pos(i * (CAP_BASE + PRINT_SPACING), 0, 0) * cap
            for i, (cap, *_) in enumerate(built)
        ]
        show(*shown, names=[cap.label for cap, *_ in built])
        print("viewer: отправлено в панель")
    except Exception as exc:
        print(f"viewer: не открылось ({exc})")


if __name__ == "__main__":
    main()
