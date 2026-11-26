# -*- coding: utf-8 -*-
"""Пробник крышки, вторая печать: два окна, язычки и полочка.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/fit_test_v2/switch_fit_test.py

Пишет v1/modeling/fit_test_v2/switch_fit_test.stl (короб, лицом на стол) и
v1/modeling/fit_test_v2/switch_fit_test_lid.stl (крышка, наружной стороной на стол).

Два окна 14,0 мм с шагом корпуса. Под левым одна точка — пластина 1,2 мм,
под правым две — 1,4 мм. Колодец 3 мм, как у корпуса: печатать с
поддержками и смотреть, какая толщина защёлкивает свитч. Винтов нет.
Язычки с обоих торцов на коротком коробе сходятся, поэтому одна риска
для открывания стоит на левом торце. Свитч и крышку пробуют по отдельности.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Axis, Cylinder, Pos, export_stl

from build_housing import (
    CORNER_R,
    FACE_EDGE_R,
    HEIGHT,
    LID_CLEARANCE,
    LID_THK,
    OUTER_MARGIN,
    PRY_DEPTH,
    TONGUE_LEN,
    TONGUE_SLOT,
    WALL,
    _box,
    _edges,
    _fillet,
    _occupied,
    _rounded_box,
    _viewer_is_open,
    lid_blank,
    lid_checks,
    lid_for_print,
    perimeter_ledges,
    tongue_groove,
    tongue_slot,
    tongue_tooth,
    tongue_zone,
    well_cut,
)

WINDOW_SIZES = (14.0, 14.0)
WINDOW_GAPS = (4.0,)
PLATE_THICKNESS = (1.2, 1.4)
MARK_DIA = 1.2
MARK_PITCH = 2.5

# Колодец как у корпуса. За пластиной 6 мм, чтобы защёлка свитча прошла.
FRAME = 3.0
RIM_DEPTH = 6.0
PROBE_DEPTH = FRAME + RIM_DEPTH
LID_Z = PROBE_DEPTH - LID_THK

HERE = Path(__file__).resolve().parent


def window_lefts():
    lefts = [OUTER_MARGIN]
    for size, gap in zip(WINDOW_SIZES, WINDOW_GAPS):
        lefts.append(lefts[-1] + size + gap)
    return lefts


def probe_width():
    """Два окна и запас, чтобы язычки с торцов не встретились."""
    windows = window_lefts()[-1] + WINDOW_SIZES[-1] + OUTER_MARGIN
    tongue_span = CORNER_R + TONGUE_SLOT / 2 + TONGUE_LEN
    return max(windows, 2 * tongue_span + 4.0)


def tongues():
    """(корень, свободный конец, сторона): корни у торцов."""
    width = probe_width()
    root = WALL + LID_CLEARANCE + CORNER_R - WALL - LID_CLEARANCE + TONGUE_SLOT / 2
    return tuple(
        (x_root, x_free, side)
        for side in ("bottom", "top")
        for x_root, x_free in (
            (root, root + TONGUE_LEN),
            (width - root, width - root - TONGUE_LEN),
        )
    )


def end_pry(z_back):
    """Риска на левом торце. Снизу язычки сходятся и места нет.

    Высота — прямой участок торца между скруглениями углов.
    """
    notch_h = HEIGHT - 2 * CORNER_R - 1.0
    return _box(
        -0.1,
        (HEIGHT - notch_h) / 2,
        z_back - PRY_DEPTH,
        WALL + 0.2,
        notch_h,
        PRY_DEPTH + 0.1,
    )


def ledge_blocks():
    blocked = {}
    for side in ("bottom", "top"):
        spans = [tongue_zone(t) for t in tongues() if t[2] == side]
        blocked[side] = spans
    return blocked


def build_fit_test():
    width = probe_width()
    thin = min(PLATE_THICKNESS)
    part = _rounded_box(0, 0, 0, width, HEIGHT, PROBE_DEPTH, CORNER_R)
    part -= _rounded_box(
        WALL,
        WALL,
        FRAME + thin,
        width - 2 * WALL,
        HEIGHT - 2 * WALL,
        PROBE_DEPTH - FRAME - thin,
        CORNER_R - WALL,
    )
    part -= well_cut(
        [left + size / 2 for left, size in zip(window_lefts(), WINDOW_SIZES)],
        FRAME,
    )
    # Правая половина пластины толще. Лишние 0,2 мм — в полость, не в колодец,
    # чтобы оба окна печатались одним и тем же мостом.
    split = window_lefts()[0] + WINDOW_SIZES[0] + WINDOW_GAPS[0] / 2
    part += _box(
        split,
        WALL,
        FRAME + thin,
        width - WALL - split,
        HEIGHT - 2 * WALL,
        max(PLATE_THICKNESS) - thin,
    )
    part = _fillet(
        part,
        _edges(part, Axis.X, lambda c: abs(c.Y - HEIGHT) < 0.3 and abs(c.Z) < 0.2),
        FACE_EDGE_R,
        "кромка лица",
    )

    mark_y = (HEIGHT - max(WINDOW_SIZES)) / 2 / 2
    for number, (left, size) in enumerate(zip(window_lefts(), WINDOW_SIZES), 1):
        part -= _box(left, (HEIGHT - size) / 2, -0.2, size, size, PROBE_DEPTH + 0.4)
        center_x = left + size / 2
        for i in range(number):
            x = center_x + (i - (number - 1) / 2) * MARK_PITCH
            part -= Pos(x, mark_y, FRAME / 2) * Cylinder(MARK_DIA / 2, FRAME + 0.4)

    part += perimeter_ledges(width, HEIGHT, LID_Z, ledge_blocks(), ends=("left", "right"))
    for tongue in tongues():
        part -= tongue_groove(tongue, HEIGHT, LID_Z)
    part -= end_pry(PROBE_DEPTH)
    part.label = "SwitchFitTestV2"
    return part


def build_lid():
    """Крышка в закрытом положении: лежит на полочке, заподлицо со спиной."""
    lid = lid_blank(probe_width(), HEIGHT, LID_Z)
    for tongue in tongues():
        lid -= tongue_slot(tongue, HEIGHT, LID_Z)
        lid += tongue_tooth(tongue, HEIGHT, LID_Z)
    lid.label = "SwitchFitTestV2Lid"
    return lid


def _report(part, lid):
    size = part.bounding_box().size
    print(f"switch fit test v2 rebuilt\nbbox mm: {size.X:.1f} x {size.Y:.1f} x {size.Z:.1f}")
    for (left, size_mm), thick in zip(zip(window_lefts(), WINDOW_SIZES), PLATE_THICKNESS):
        x = left - 0.4
        inside = not _occupied(part, left + size_mm / 2, HEIGHT / 2, FRAME + thick / 2)
        edge = _occupied(part, x, HEIGHT / 2, FRAME + thick / 2)
        stopped = not _occupied(part, x, HEIGHT / 2, FRAME + thick + 0.15)
        ok = inside and edge and stopped
        print(f"  {'ок' if ok else 'ОШИБКА'}: окно {size_mm:.1f} мм, пластина {thick:.1f} мм")
    checks, overlap = lid_checks(part, lid, tongues(), (), HEIGHT, LID_Z)
    checks["полочка: крышка лежит"] = _occupied(
        part, WALL + 0.75, HEIGHT / 2 + 5, LID_Z - 0.2
    ) and _occupied(lid, WALL + 0.75, HEIGHT / 2 + 5, LID_Z + 0.2)
    checks["риска на торце"] = not _occupied(part, 1.0, HEIGHT / 2, PROBE_DEPTH - 0.4)
    for name, ok in checks.items():
        print(f"  {'ок' if ok else 'ОШИБКА'}: {name}")
    lid_size = lid.bounding_box().size
    print(
        f"  крышка {lid_size.X:.1f} x {lid_size.Y:.1f} x {lid_size.Z:.1f} мм, "
        f"натяг зубов {overlap:.2f} мм3"
    )


def main():
    part = build_fit_test()
    lid = build_lid()
    _report(part, lid)
    export_stl(part, HERE / "switch_fit_test.stl")
    export_stl(lid_for_print(lid), HERE / "switch_fit_test_lid.stl")
    print(f"записано {HERE / 'switch_fit_test.stl'} и {HERE / 'switch_fit_test_lid.stl'}")
    if not _viewer_is_open():
        return
    try:
        from ocp_vscode import show

        show(part, Pos(0, 0, 10) * lid, names=[part.label, lid.label])
        print("viewer: отправлено в панель")
    except Exception as exc:
        print(f"viewer: не открылось ({exc})")


if __name__ == "__main__":
    main()
