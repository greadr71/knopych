# -*- coding: utf-8 -*-
"""Купон дна колодца: три варианта кромки над окном свитча, срез колодца 6,0.

Это ровно срез панельного колодца от глубины 8,12 до 14,12: сверху лицо
купона — панельная ширина колодца на 8,12 (17,68), фаски рта здесь нет.
Высота 9,9: 6,0 колодец + 1,4 плита + 2,5 выборка в тыл.

Лицо наклонено 1,72° (TOP_SLOPE), колодцы режутся в наклонной системе лица
(frame в face._wells), а плита свитча ГОРИЗОНТАЛЬНА в модели — в печати
наклон снимается (как у панели в print_stl), лицо ложится на стол, а плита
выходит наклонённой на 1,72°: её первый слой над колодцем провисает.

Три купончика 23×23 R3 в ряд по X (шаг 25,0), два ребра 3×6×4 в зазорах
держат ряд одной деталью.

  A (x=0)   сейчас: конус до 17,9 на дне, плита 1,4. Свес 1,95
  B (x=25)  конус до 17,871 на 5,22, уступ 45° до 16,3. Свес 1,15
  C (x=50)  конус до 17,866 на 5,07, уступ 45° до 16,0. Свес 1,00

Запуск: cad run v2/modeling/coupon.py
"""

import math
from pathlib import Path

import build123d as bd
from cad import model

import face as face_part
from print_stl import _on_bed, _tilt

TOL = 0.02

# Числа из face.py / niche_panel.py — не менять
TOP_SLOPE = face_part.TOP_SLOPE      # −0,03: лицо падает по X
PLATE_T = face_part.PLATE_T          # 1,4
WELL_R = face_part.WELL_R            # 2,2
WINDOW_R = face_part.WINDOW_R        # 0,3
WINDOW = face_part.SWITCH_HOLE       # 14,0 сквозь плиту
RELIEF = face_part.SWITCH_BODY       # 15,6 выборка под фланец

# Купон
WELL_D = 6.0                         # колодец над плитой (срез с 8,12 до 14,12)
RELIEF_D = 2.5                       # выборка от низа плиты в тыл
HEIGHT = WELL_D + PLATE_T + RELIEF_D  # 9,9
MOUTH = 17.680                        # панельный колодец на глубине 8,12 — это лицо
SIZE = 23.0
CORNER_R = 3.0
PITCH = 25.0
RIB = (3.0, 6.0, 4.0)                # X × Y × вниз от лица
RIB_Y = 5.0                          # ребро у верхней кромки по Y (2,0…8,0)

# вариант: (x, сечения от лица до дна [(глубина, ширина, R)], устье)
VARIANTS = {
    "A": (0.0, [(WELL_D, 17.9, WELL_R)], 17.9),
    "B": (25.0, [(5.22, 17.871, WELL_R), (WELL_D, 16.3, 1.42)], 16.3),
    "C": (50.0, [(5.07, 17.866, WELL_R), (WELL_D, 16.0, 1.27)], 16.0),
}


def face_z(x):
    """Плоскость лица в модели: проходит через ноль купона A и падает по X."""
    return TOP_SLOPE * x


def plate_top(x):
    """Дно колодца в колонке x — ГОРИЗОНТАЛЬНАЯ плоскость: колодцы не наклоняются."""
    return face_z(x) - WELL_D


def plate_bottom(x):
    """Низ плиты: здесь начинается выборка 15,6."""
    return plate_top(x) - PLATE_T


def _frame(x):
    """Наклонная система лица в колонке x — та же, что frame в face._wells."""
    beta = -math.degrees(math.atan(TOP_SLOPE))
    return bd.Pos(x, 0.0, face_z(x)) * bd.Rot(0, beta, 0)


def _coupon(x):
    """Купончик 23×23 R3, 9,9 вниз от лица; тыл параллелен лицу."""
    return _frame(x) * bd.extrude(
        bd.Plane.XY * bd.RectangleRounded(SIZE, SIZE, CORNER_R), -HEIGHT
    )


def _well(x, lead_to):
    """Колодец: рот в наклонной системе лица, дно и уступ — горизонтальные.

    От лица идёт одна общая образующая (панельный конус 17,68 → 17,9), у B и C
    она кончается раньше и переходит в уступ 45°, как в face.py.
    """
    sections = [_frame(x) * bd.RectangleRounded(MOUTH, MOUTH, WELL_R)]
    for depth, width, radius in lead_to:
        sections.append(
            bd.Pos(x, 0.0, face_z(x) - depth) * bd.RectangleRounded(width, width, radius)
        )
    return bd.loft(sections, ruled=True)


def _window(x):
    """Окно свитча 14,0 сквозь плиту: запас 0,2 на сторону."""
    return bd.Pos(x, 0.0, plate_bottom(x) - 0.2) * bd.extrude(
        bd.Plane.XY * bd.RectangleRounded(WINDOW, WINDOW, WINDOW_R),
        PLATE_T + 0.4,
    )


def _relief(x):
    """Выборка 15,6 от низа плиты в тыл: за тылом материала нет, она открыта."""
    return bd.Pos(x, 0.0, plate_bottom(x)) * bd.extrude(
        bd.Plane.XY * bd.RectangleRounded(RELIEF, RELIEF, WINDOW_R),
        -(RELIEF_D + 1.0),
    )


def _rib(x):
    """Ребро 3×6×4 от лица в зазоре: три купона держатся одной деталью."""
    return _frame(x) * bd.Pos(0.0, RIB_Y, 0.0) * bd.extrude(
        bd.Plane.XY * bd.Rectangle(RIB[0], RIB[1]), -RIB[2]
    )


def _cut_width(part, x, z, probe=21.0):
    """Ширина пустоты в колодце на высоте z: тонкий срез поперёк X (в модели)."""
    slab = bd.Pos(x, 0.0, z) * bd.Box(probe, 0.2, 0.004)
    return (slab - (part & slab)).bounding_box().size.X


def _plate(part, x):
    """Толщина плиты и её дно: столбик 0,4×0,4 в 7,5 от центра колодца.

    Выше дна там пусто (устье не уже 16,0), ниже — выборка 15,6.
    """
    box = (part & (bd.Pos(x + 7.5, 0.0, plate_top(x) - 0.7) * bd.Box(0.4, 0.4, 6.0)))
    return box.bounding_box().size.Z, box.bounding_box().max.Z


def _wells_in(part, x, z):
    """Сколько отдельных пустот в срезе 21×21 вокруг колодца колонки x."""
    slab = bd.Pos(x, 0.0, z) * bd.Box(21.0, 21.0, 0.1)
    return len((slab - (part & slab)).solids())


def _void_center(part, z):
    """Центр колодца A в печатной ориентации: тонкий срез 20×21 в первом купоне."""
    slab = bd.Pos(0.0, 0.0, z) * bd.Box(20.0, 21.0, 0.1)
    voids = (slab - (part & slab)).solids()
    assert len(voids) == 1, len(voids)
    return voids[0].center().X


def _plate_top_z(part, x):
    """Z дна колодца в столбике 0,2×0,2 (печатная ориентация: стол — z=0)."""
    column = bd.Pos(x, 0.0, HEIGHT / 2 - 1.0) * bd.Box(0.2, 0.2, HEIGHT + 2.0)
    return (part & column).bounding_box().min.Z


@model
def coupon():
    part = _coupon(0.0)
    for x in (PITCH, 2 * PITCH):
        part = part + _coupon(x)
    for x in (PITCH / 2, PITCH * 1.5):
        part = part + _rib(x)
    for x, lead_to, _ in VARIANTS.values():
        part = part - _well(x, lead_to) - _relief(x) - _window(x)

    # 1. Одна деталь, в каждом купоне ровно один колодец.
    assert len(part.solids()) == 1, len(part.solids())
    wells = [
        _wells_in(part, x, plate_top(x) + WELL_D / 2) for x in (v[0] for v in VARIANTS.values())
    ]
    assert wells == [1, 1, 1], wells
    # 2. Ряд 23 по Y (X и Z в модели косые — они проверяются в печати).
    assert abs(part.bounding_box().size.Y - SIZE) < 0.05, part.bounding_box().size.Y

    # 3. Устье над окном — горизонтальный срез на уровне дна колодца.
    print("вариант  устье  свес")
    for name, (x, _, throat) in VARIANTS.items():
        got = _cut_width(part, x, plate_top(x))
        assert abs(got - throat) < 0.05, (name, got, throat)
        print(f"{name} (x={x:4.1f})  {got:5.2f}  {(throat - WINDOW) / 2:4.2f}")

    # 4. Плита 1,4 у всех, её верх — дно колодца; в A на 0,4 ниже дна окно 14,0.
    for name, (x, _, _) in VARIANTS.items():
        thick, top = _plate(part, x)
        assert abs(thick - PLATE_T) < 0.02, (name, thick)
        assert abs(top - plate_top(x)) < 0.02, (name, top)
    assert abs(_cut_width(part, 0.0, plate_top(0.0) - 0.4) - WINDOW) < 0.05, "в A окно"

    # Печать: лицом на стол, наклон 1,72° снят — он остаётся у плиты.
    printed = _on_bed(bd.Rot(0, _tilt(), 0) * bd.Rot(180, 0, 0) * part)
    pbox = printed.bounding_box()
    assert abs(pbox.min.Z) < 0.01, pbox.min.Z
    bed = [
        face
        for face in printed.faces()
        if face.geom_type == bd.GeomType.PLANE and abs(face.center().Z) < 1e-6
    ]
    # Лицо всех трёх купонов лежит на столе одной плоскостью (≈639 мм²)
    assert len(bed) == 1 and 600 < bed[0].area < 680, (len(bed), bed[0].area)
    assert abs(pbox.size.X - (3 * SIZE + 2 * (PITCH - SIZE))) < 0.2, pbox.size.X
    assert abs(pbox.size.Y - SIZE) < 0.2, pbox.size.Y
    assert abs(pbox.size.Z - HEIGHT) < 0.2, pbox.size.Z

    # Наклон плиты к столу: Z дна колодца A в двух точках по X.
    center = _void_center(printed, WELL_D / 2)
    reach = 7.4
    drop = _plate_top_z(printed, center - reach) - _plate_top_z(printed, center + reach)
    angle = math.degrees(math.atan(drop / (2 * reach)))
    assert abs(angle - _tilt()) < 0.05, angle
    print(
        f"габарит печати {pbox.size.X:.1f}×{pbox.size.Y:.1f}×{pbox.size.Z:.1f} мм, "
        f"объём {printed.volume / 1000:.1f} см³"
    )
    print(
        f"наклон плиты {angle:.2f}°: на 10 мм {drop / (2 * reach) * 10:.2f} "
        f"(на {2 * reach:.1f} мм {drop:.2f})"
    )
    printed.label = "coupon"
    return printed


def main():
    out = Path(__file__).parent / "stl"
    out.mkdir(exist_ok=True)
    part = coupon.__wrapped__()
    path = out / "coupon.stl"
    bd.export_stl(part, path, tolerance=TOL, angular_tolerance=0.15)
    size = part.bounding_box().size
    print(
        f"coupon.stl  {size.X:.1f}×{size.Y:.1f}×{size.Z:.1f} мм, "
        f"{path.stat().st_size / 1e6:.2f} МБ"
    )


if __name__ == "__main__":
    main()
