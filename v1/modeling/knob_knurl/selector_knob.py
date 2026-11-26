# -*- coding: utf-8 -*-
"""Крутилка Ø50: накатка по описанию паттерна — пары встречных треугольников.

Решётка узлов: по окружности шаг = полшага пары (48 узлов), по высоте шаг = s/2.
Высоты в шахматку: узел либо шип (R_CORE + s/2), либо впадина (R_CORE).
Ячейка режется по диагонали, соединяющей ДВЕ ВПАДИНЫ, поэтому каждая грань —
треугольник «шип + две впадины»: пара встречных треугольников со общим шипом,
скаты к противоположным основаниям. Поверхность замкнутая, щелей нет.

Запуск: cad run v1/modeling/knob_knurl/selector_knob.py
"""

import math

import build123d as bd
from cad import model

OUTER_D = 50.0
TOTAL_H = 19.0
SKIRT_H = 3.0
SKIRT_D = 43.0
KNURL_H = 11.5
RIM_TOP_D = 45.0
INNER_RING_D = 38.0
CAP_RECESS = 1.2
GROOVE_W = 0.8
GROOVE_DEPTH = 0.8
KNURL_COUNT = 24
CAVITY_D = 34.0
CAVITY_H = 14.0
BOSS_D = 12.0
SHAFT_D = 6.2
SHAFT_FLAT = 4.7
SHAFT_DEPTH = 12.0

R_OUT = OUTER_D / 2
R_CORE = R_OUT / (1.0 + math.pi / (KNURL_COUNT * math.sqrt(3)))
S = 2 * math.pi * R_CORE / KNURL_COUNT / math.sqrt(3)   # сторона треугольника
D = S / 2.0                                             # подъём шипа
COLS = 2 * KNURL_COUNT                                  # узлов по окружности
ROW_STEP = S / 2.0                                      # шаг рядов узлов
R_BASE = R_CORE - 0.6


def cyl(r: float, t: float, z: float):
    return (r * math.cos(t), r * math.sin(t), z)


def _key(p):
    return (round(math.atan2(p[1], p[0]), 9), round(p[2], 9))


def _inner(p, r_in: float):
    return cyl(r_in, math.atan2(p[1], p[0]), p[2])


def _wall(pa, pb, r_in: float):
    """Стенка между узлами: диагональ выбирается по общему правилу, чтобы у соседа
    получились те же треугольники и щелей не осталось."""
    qa, qb = _inner(pa, r_in), _inner(pb, r_in)
    if _key(pa) <= _key(pb):
        return [[pa, pb, qb], [pa, qb, qa]]
    return [[pb, pa, qa], [pb, qa, qb]]


def facet(p1, p2, p3, r_in: float) -> bd.Solid:
    q1, q2, q3 = _inner(p1, r_in), _inner(p2, r_in), _inner(p3, r_in)
    polys = [[p1, p2, p3], [q1, q3, q2]] + _wall(p1, p2, r_in) + _wall(p2, p3, r_in) + _wall(p3, p1, r_in)
    solid = bd.Solid(bd.Shell([bd.Face(bd.Wire.make_polygon(v, close=True)) for v in polys]))
    if solid.volume > 0:
        return solid
    return bd.Solid(bd.Shell([bd.Face(bd.Wire.make_polygon(list(reversed(v)), close=True)) for v in polys]))


def node(k: int, j: int):
    """Узел решётки. Шип (R_CORE + D) там, где (k + j) чётное."""
    r = R_CORE + D if (k + j) % 2 == 0 else R_CORE
    return cyl(r, 2 * math.pi * (k % COLS) / COLS, SKIRT_H + j * ROW_STEP)


def build_knurling() -> bd.Shape:
    rows = int(math.ceil(KNURL_H / ROW_STEP)) + 2
    cells = []
    for j in range(-1, rows):
        for k in range(COLS):
            a, b = node(k, j), node(k + 1, j)
            c, d = node(k, j + 1), node(k + 1, j + 1)
            if (k + j) % 2 == 0:            # a и d — шипы, впадины b и c
                cells.append(facet(a, b, c, R_BASE))
                cells.append(facet(b, d, c, R_BASE))
            else:                           # b и c — шипы, впадины a и d
                cells.append(facet(a, b, d, R_BASE))
                cells.append(facet(a, d, c, R_BASE))

    fused = cells[0].fuse(*cells[1:])

    with bd.BuildPart() as band_mask:
        with bd.Locations((0, 0, SKIRT_H)):
            bd.Cylinder(
                radius=R_OUT + 1.0,
                height=KNURL_H,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )

    return bd.Compound(children=[fused]).intersect(band_mask.part).solids()[0]


def build_base_body() -> bd.Part:
    r_rim_top = RIM_TOP_D / 2
    r_inner_ring = INNER_RING_D / 2
    r_skirt = SKIRT_D / 2
    r_cavity = CAVITY_D / 2
    r_boss = BOSS_D / 2
    z_knurl_top = SKIRT_H + KNURL_H
    z_cap = TOTAL_H - CAP_RECESS

    profile_pts = [
        (0.0, z_cap),
        (r_inner_ring - GROOVE_W, z_cap),
        (r_inner_ring - GROOVE_W, z_cap - GROOVE_DEPTH),
        (r_inner_ring, z_cap - GROOVE_DEPTH),
        (r_inner_ring, z_cap + 0.3),
        (r_rim_top - 2.0, TOTAL_H - 0.5),
        (r_rim_top, TOTAL_H),
        (R_OUT - 0.8, TOTAL_H - 0.4),
        (R_OUT - 0.2, z_knurl_top + 0.8),
        (R_CORE, z_knurl_top),
        (R_CORE, SKIRT_H),
        (r_skirt, SKIRT_H),
        (r_skirt, 0.5),
        (r_skirt - 0.5, 0.0),
        (r_cavity, 0.0),
        (r_cavity, CAVITY_H),
        (r_boss, CAVITY_H),
        (r_boss, 0.0),
        (0.0, 0.0),
    ]

    with bd.BuildPart() as body:
        with bd.BuildSketch(bd.Plane.XZ):
            with bd.BuildLine():
                bd.Polyline(profile_pts, close=True)
            bd.make_face()
        bd.revolve(axis=bd.Axis.Z)

        with bd.BuildSketch(bd.Plane.XY):
            bd.Circle(SHAFT_D / 2)
            with bd.Locations((SHAFT_FLAT - SHAFT_D / 2, 0)):
                bd.Rectangle(
                    SHAFT_D,
                    SHAFT_D * 2,
                    align=(bd.Align.MIN, bd.Align.CENTER),
                    mode=bd.Mode.SUBTRACT,
                )
        bd.extrude(amount=SHAFT_DEPTH, mode=bd.Mode.SUBTRACT)

    return body.part


@model
def selector_knob_diamond():
    return build_base_body() + build_knurling()


if __name__ == "__main__":
    selector_knob_diamond()
