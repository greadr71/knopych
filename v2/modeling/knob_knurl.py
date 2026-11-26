# -*- coding: utf-8 -*-
"""Ручка энкодера Ø28 с накаткой на боку — как knob.py, только бок не гладкий.

Всё, что ниже лица, взято у knob.py один в один: юбка Ø28,2 в канавке лица
Ø28,6×Ø23,2, гнездо под D-вал Ø6 (круг Ø6,1 и срез по лыске); пилота M3 нет (в
гладкой он остался). Полость под юбкой поднята: скос 45° начинается с z=2,0, а
не с 1,2, — на ходе проверки 0,8 он не касается островка панели (тот снова до
лица). Отличается и бок над лицом: в него врезана накатка из пар встречных
треугольников (раскладка как в v1/modeling/knob_knurl/selector_knob.py).

Накатка: KNURL_PAIRS пар по окружности (шаг пары 5,9 мм — как у Ø50),
вершины шипов ровно на Ø28,0 (габарит ручки не растёт), глубина впадин
RIDGE = s/4 ≈ 0,85 — половина прежнего s/2. Бок между шипами — Ø26,3.

Пояс накатки — KNURL_ROWS полных рядов: основания крайних рядов ложатся точно
на границы пояса, поэтому на обеих границах наружная поверхность — ровный
Ø26,3, и накатка начинается и заканчивается целыми треугольниками, срезанных
ячеек нет. Снизу до первого ряда полшага ровного бока, сверху — сразу верхняя
фаска. Рядов чётное число, поэтому верхний ряд по углу смещён на полшага
относительно нижнего — на глаз не читается, но строгой симметрии нет.

Ручка выше гладкой на один ряд: 15,58 мм (над лицом 14,78) вместо 14,8.

Печать FDM, сопло 0,4 мм, слой 0,2 мм. Низом на стол.
Запуск: cad run v2/modeling/knob_knurl.py
"""

import math

import build123d as bd
from cad import model
from knob import (
    BORE_D,
    BORE_DEPTH,
    BORE_FLAT,
    BOTTOM_CHAMFER,
    CONE_RISE,
    FACE_REL,
    SKIRT_D,
    SKIRT_IN_D,
    TOP_CHAMFER,
    flat_z0,
)
from niche_panel import KNOB_DIA

from encoder import ENC_SHAFT_L
from face import knob_bottom_z, seat_front_z

# Полость под юбкой выше, чем у гладкой ручки (knob.py: CONE_Z0 = 1,2): верх
# островка панели снова на плоскости лица, и на ходе проверки 0,8 скос 45° не
# должен его задеть. С 2,0 до островка на этом ходе остаётся 0,55.
CONE_Z0 = 2.0
FLOOR_REL = CONE_Z0 + CONE_RISE  # 3,8 — плоское дно полости

KNURL_PAIRS = 14  # пар треугольников по окружности
KNURL_ROWS = 6  # полных рядов накатки (у гладкой ручки влезало 5)
GAP = 1.0  # клинья соседних рядов смыкаются: щелей под сопло нет
OVERLAP = 0.05  # мм: половины пары заводятся друг за друга по линии пика

R_OUT = KNOB_DIA / 2
# Вершина шипа на R_OUT, подъём RIDGE = s/4, сторона s = 2π·r_core/(N·√3):
# отсюда r_core = R_OUT / (1 + π/(2·N·√3)).
R_CORE = R_OUT / (1.0 + math.pi / (2 * KNURL_PAIRS * math.sqrt(3)))
RIDGE = R_OUT - R_CORE
S = 2 * math.pi * R_CORE / (KNURL_PAIRS * math.sqrt(3))
ROW_STEP = S / 2.0


def band() -> tuple[float, float]:
    """Границы пояса накатки: снизу полшага ровного бока, сверху — сразу фаска."""
    z0 = FACE_REL + ROW_STEP / 2
    return z0, z0 + (KNURL_ROWS + 1) * ROW_STEP


def knob_knurl_height() -> float:
    """Высота ручки: пояс накатки упирается в верхнюю фаску, выше — только она."""
    return band()[1] + TOP_CHAMFER


def cyl(r: float, theta: float, z: float) -> tuple[float, float, float]:
    return (r * math.cos(theta), r * math.sin(theta), z)


def make_triangle_wedge(r_base: float, d_theta: float) -> bd.Solid:
    """Пара встречных треугольников: основание на угле ±d_theta, пик на 0."""
    s_eff = S * GAP
    b1 = cyl(r_base, -d_theta, -s_eff / 2)
    b2 = cyl(r_base, -d_theta, s_eff / 2)
    # Низ пары заведён на 0,05 за плоскость зеркала: иначе половины касаются
    # друг друга по линии пика встык, и меш получает там ребро на 4 грани
    # (слайсер ругается на non-manifold edges).
    b3 = cyl(r_base, OVERLAP / r_base, 0.0)
    t1 = cyl(R_CORE, -d_theta, -s_eff / 2)
    t2 = cyl(R_CORE, -d_theta, s_eff / 2)
    t3 = cyl(R_OUT, 0.0, 0.0)

    faces = [
        bd.Face(bd.Wire.make_polygon([b1, b3, b2], close=True)),
        bd.Face(bd.Wire.make_polygon([t1, t2, t3], close=True)),
        bd.Face(bd.Wire.make_polygon([b1, b2, t2, t1], close=True)),
        bd.Face(bd.Wire.make_polygon([b1, t1, t3], close=True)),
        bd.Face(bd.Wire.make_polygon([b1, t3, b3], close=True)),
        bd.Face(bd.Wire.make_polygon([b2, b3, t3], close=True)),
        bd.Face(bd.Wire.make_polygon([b2, t3, t2], close=True)),
    ]
    return bd.Solid(bd.Shell(faces))


def build_knurling() -> bd.Shape:
    """Пояс накатки: ряды начинаются и кончаются по плоскостям оснований."""
    z0, _ = band()
    r_base = R_CORE - 0.6
    d_theta = math.pi / KNURL_PAIRS

    left = make_triangle_wedge(r_base, d_theta)
    pair = bd.Compound(children=[left, left.mirror(bd.Plane.XZ)])

    # Вершины рядов на z0 + k*ROW_STEP: основания крайних рядов — точно на
    # границах, поэтому срез по границе не режет ни одной ячейки, и накатка
    # выходит из гладкого бока целыми треугольниками.
    angle_step = 360.0 / KNURL_PAIRS

    elements = []
    for row in range(KNURL_ROWS):
        z = z0 + (row + 1) * ROW_STEP
        offset = (angle_step / 2.0) if (row % 2) else 0.0
        for i in range(KNURL_PAIRS):
            elements.append(
                pair.located(bd.Location((0, 0, z), (0, 0, i * angle_step + offset)))
            )

    return bd.Compound(children=elements)


def build_body(height: float) -> bd.Part:
    """Тело ручки: юбка Ø28,2, сход на бок Ø26,3, верхняя фаска, без полостей."""
    r_skirt = SKIRT_D / 2
    z_band, z_band_top = band()

    profile = [
        (0.0, 0.0),
        (r_skirt - BOTTOM_CHAMFER, 0.0),
        (r_skirt, BOTTOM_CHAMFER),
        (r_skirt, FACE_REL),
        (R_CORE, z_band),
        (R_CORE, z_band_top),  # верх пояса — тут же начинается фаска
        (R_CORE - TOP_CHAMFER, height),
        (0.0, height),
    ]
    with bd.BuildPart() as body:
        with bd.BuildSketch(bd.Plane.XZ):
            with bd.BuildLine():
                bd.Polyline(profile, close=True)
            bd.make_face()
        bd.revolve(axis=bd.Axis.Z)

    body = body.part

    # Внутри юбки: стенка Ø24,2 до z=2,0 (выше лица на 1,2), скос 45°, плоское дно.
    cavity = bd.Pos(0, 0, -0.5) * bd.Cylinder(
        SKIRT_IN_D / 2, CONE_Z0 + 0.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    ) + bd.Pos(0, 0, CONE_Z0) * bd.Cone(
        SKIRT_IN_D / 2,
        SKIRT_IN_D / 2 - CONE_RISE,
        CONE_RISE,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Гнездо: круг Ø6,1 и срез по лыске выше круглого участка вала.
    z0 = flat_z0()
    round_bore = bd.Pos(0, 0, -0.5) * bd.Cylinder(
        BORE_D / 2, z0 + 0.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    flat_profile = bd.Circle(BORE_D / 2) - bd.Pos(0, BORE_FLAT + 10.0) * bd.Rectangle(20, 20)
    flat_bore = bd.Pos(0, 0, z0) * bd.extrude(flat_profile, BORE_DEPTH - z0)

    return body - cavity - round_bore - flat_bore


@model
def knob_knurl():
    height = knob_knurl_height()
    body = build_body(height) + build_knurling()
    body.label = "knob_knurl"
    body.color = "#1c1e22"

    box = body.bounding_box()
    # Габарит задаёт юбка Ø28,2; шипы накатки выходят ровно на Ø28,0.
    assert abs(box.size.X - SKIRT_D) < 0.02, box.size
    assert abs(box.size.X - box.size.Y) < 0.02, box.size
    assert abs(box.min.Z) < 0.01 and abs(box.max.Z - height) < 0.01, (box.min.Z, box.max.Z)

    # Пояс: середина пояса в срезе на 2 шага ряда — шипы Ø28,0 есть на любом угле.
    z_band, z_band_top = band()
    slice_h = 2 * ROW_STEP
    ring = body & bd.Pos(0, 0, z_band + slice_h + 0.5) * bd.Box(60, 60, slice_h)
    assert abs(ring.bounding_box().size.X - KNOB_DIA) < 0.02, ring.bounding_box().size
    # Сверху накатка упирается в фаску: выше пояса гладких полей нет.
    assert abs(z_band_top - (height - TOP_CHAMFER)) < 1e-9
    # Оба края пояса — ровный бок Ø26,3: накатка начинается и кончается целыми
    # треугольниками, срезанных ячеек нет.
    lo = body & bd.Pos(0, 0, z_band + 0.02) * bd.Box(60, 60, 0.04)
    hi = body & bd.Pos(0, 0, z_band_top - 0.02) * bd.Box(60, 60, 0.04)
    assert abs(lo.bounding_box().size.X - 2 * R_CORE) < 0.05, lo.bounding_box().size
    assert abs(hi.bounding_box().size.X - 2 * R_CORE) < 0.05, hi.bounding_box().size

    # Гнездо и срез по лыске выше дна ручки.
    z_probe = FLOOR_REL + 1.0
    assert not (body & bd.Pos(0, 0, z_probe) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert (body & bd.Pos(3.4, 0, z_probe) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert not (body & bd.Pos(0, 1.4, z_probe) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert (body & bd.Pos(0, 1.7, z_probe) * bd.Box(0.2, 0.2, 0.2)).solids()
    # Вал входит на 11,8 при глубине гнезда 12,6.
    shaft_in = seat_front_z() + ENC_SHAFT_L - knob_bottom_z()
    assert shaft_in < BORE_DEPTH - 0.3, (shaft_in, BORE_DEPTH)
    # Юбка: ниже лица материал только в кольце 2,0.
    assert (body & bd.Pos(SKIRT_D / 2 - 0.6, 0, 0.3) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert not (body & bd.Pos(SKIRT_IN_D / 2 - 0.3, 0, 0.3) * bd.Box(0.2, 0.2, 0.2)).solids()
    # Полость поднята ради хода 0,8: над её дном остаётся стенка height − FLOOR_REL,
    # не тоньше 1,2. Стенка вокруг полости на её верху (над лицом, где бок уже
    # Ø26,3) — R_CORE − SKIRT_IN_D/2 = 1,05, это дело накатки, не полости.
    assert height - FLOOR_REL >= 1.2, (height, FLOOR_REL)

    print(
        f"ручка Ø{KNOB_DIA:g}×{height:.2f} с накаткой: {KNURL_PAIRS} пар, шаг пары "
        f"{2 * math.pi * R_CORE / KNURL_PAIRS:.2f}, шип +{RIDGE:.2f} до Ø{KNOB_DIA:g}, "
        f"бок Ø{2 * R_CORE:.2f}; пояс накатки z={z_band:.2f}…{z_band_top:.2f} "
        f"({KNURL_ROWS} рядов, снизу {z_band - FACE_REL:.2f} ровного бока, сверху сразу "
        f"фаска, над лицом {height - FACE_REL:.2f}); юбка Ø{SKIRT_D:g} на {FACE_REL:.2f}, "
        f"полость: скос 45° с z={CONE_Z0:.2f}, дно z={FLOOR_REL:.2f} "
        f"Ø{SKIRT_IN_D - 2 * CONE_RISE:g}, над полостью {height - FLOOR_REL:.2f}; "
        f"гнездо Ø{BORE_D:g} глубиной {BORE_DEPTH:g}, вал входит на {shaft_in:.2f}"
    )
    return body


if __name__ == "__main__":
    knob_knurl()
