# -*- coding: utf-8 -*-
"""Ручка энкодера — крутилка Ø28 с юбкой, низ которой спрятан в канавке лица.

Садится на вал Ø6 с лыской (ALPS EC11E15244G1, см. encoder.py). Гнездо —
D-отверстие: круг Ø6,1 на всю глубину и срез по лыске с 1,8 от низа. Ниже
срез не нужен: вал круглый на 10 мм от своей передней плоскости, и первые
1,8 мм в гнезде приходятся как раз на круглый участок — срез там цеплял бы
вал. Срез гнезда на 1,55 от оси, у вала 1,5 — зазор 0,05, по кругу тоже 0,05:
в модели посадка почти без зазора, а напечатанное гнездо обычно выходит на
0,1 уже — садится враспор и держится трением.

Глубина гнезда 12,6: вал входит на 11,8, над торцом вала остаётся 2,2
материала. Провернуться не может: лыска — геометрический упор, люфт в
0,05 — около 2°. Держится посадкой; на случай, если разболтается, с боку
(+Y) на 7,0 от низа есть пилот Ø2,5 под саморез M3×12 в лыску (от наружной
поверхности до лыски 12,3, 12-й достаёт до вала). Ориентацию задаёт гнездо,
поэтому винт всегда в лыску.

Стоит в кольцевой канавке лица Ø28,6×Ø23,2 (face.py): юбка Ø28,2 (к лицу
сходится к Ø28,0, ступеньки нет) со стенкой 2,0 заходит в неё, низ юбки на
0,8 под лицом и на 1,0 над дном канавки — ход кнопки 0,5 и столько же
запаса. Внутри юбки — островок панели Ø23,2 до самого
лица, поэтому ниже лица материал есть только в кольце юбки, а от её
внутреннего края вверх идёт скос 45°: при ходе 0,5 он не задевает островок.
Над лицом 14,0, всего 14,8.

Печать FDM, сопло 0,4 мм, слой 0,2 мм, PETG или ASA. Низом на стол: гнездо
уходит вверх, поддержек нет, скос 45° держит плоское дно ручки Ø20,6 на
высоте 3,0 (это её единственный мост), а над торцом вала — Ø6,1 на 12,6.
Запуск: cad run v2/modeling/knob.py
"""

import build123d as bd
from cad import model
from niche_panel import KNOB_DIA, knob_center

from encoder import ENC_FLAT, ENC_FLAT_Z0, ENC_SHAFT_D, ENC_SHAFT_L
from face import SEAT_ISLAND_D, knob_bottom_z, knob_face_z, seat_front_z, top_z

PROUD = 14.0  # высота ручки над лицом в центре
TOP_CHAMFER = 2.0
BOTTOM_CHAMFER = 0.6

SKIRT_D = 28.2  # юбка в канавке Ø28,6: зазор 0,2 на сторону
SKIRT_WALL = 2.0
SKIRT_IN_D = SKIRT_D - 2 * SKIRT_WALL  # 24,2, до островка 0,5
FACE_REL = knob_face_z() - knob_bottom_z()  # 0,8 — лицо над низом ручки
CONE_Z0 = FACE_REL + 0.4  # 1,2 — откуда идёт скос 45° внутрь-вверх
CONE_RISE = 1.8  # 1,8 по высоте = 1,8 радиально: 12,1 → 10,3
FLOOR_REL = CONE_Z0 + CONE_RISE  # 2,8 — плоское дно ручки (лицо + 2,0)
PRESS = 0.5  # ход кнопки: столько скос не должен наезжать на островок

BORE_D = ENC_SHAFT_D + 0.1  # 0,05 на сторону: посадка враспор
# Расстояние от оси до плоскости лыски в гнезде: 4,5 «по лыске» — это
# 4,5 − Ø6/2 = 1,5 от оси, у гнезда на 0,05 больше.
BORE_FLAT = ENC_FLAT - ENC_SHAFT_D / 2 + 0.05
BORE_DEPTH = 12.6
SCREW_D = 2.5  # пилот под саморез M3 (не сквозное Ø3,2: резьбы нет)
SCREW_Z = 7.0  # от низа ручки, середина лыски


def knob_height():
    """Высота ручки: 14,0 над лицом в центре плюс 0,8 юбки под лицом."""
    return top_z(knob_center()[0]) + PROUD - knob_bottom_z()


def flat_z0():
    """Откуда в гнезде начинается срез по лыске: столько же, сколько у вала."""
    return seat_front_z() + ENC_FLAT_Z0 - knob_bottom_z()


@model
def knob():
    height = knob_height()
    body = bd.Cylinder(
        KNOB_DIA / 2, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    # Юбка: снизу Ø28,2, к лицу сходится к Ø28,0 — на уровне лица ступеньки нет,
    # а в канавку (Ø28,6) она входит с зазором 0,2.
    body += bd.Cone(
        SKIRT_D / 2,
        KNOB_DIA / 2,
        FACE_REL,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    top = [
        edge
        for edge in body.edges()
        if edge.geom_type == bd.GeomType.CIRCLE and abs(edge.center().Z - height) < 1e-6
    ]
    assert len(top) == 1, len(top)
    body = bd.chamfer(top, TOP_CHAMFER)
    bottom = [
        edge
        for edge in body.edges()
        if edge.geom_type == bd.GeomType.CIRCLE
        and abs(edge.center().Z) < 1e-6
        and abs(edge.radius - SKIRT_D / 2) < 0.01
    ]
    assert len(bottom) == 1, len(bottom)
    body = bd.chamfer(bottom, BOTTOM_CHAMFER)

    # Внутри юбки: вертикальная стенка до лица + 0,2, потом скос 45° и плоское
    # дно. Островок панели доходит до лица, поэтому скос выше — иначе при ходе
    # 0,5 он наезжал бы на него.
    # shortcut: дно Ø20,6 — мост 17,5 мм (DFM ругается), но печатается без
    # поддержки: прогиб уходит вниз в пустоту над островком (запас 2,2 мм) и не
    # виден. Сужать дно — только если прогиб начнёт задевать островок при ходе.
    cavity = bd.Pos(0, 0, -0.5) * bd.Cylinder(
        SKIRT_IN_D / 2, CONE_Z0 + 0.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    ) + bd.Pos(0, 0, CONE_Z0) * bd.Cone(
        SKIRT_IN_D / 2,
        SKIRT_IN_D / 2 - CONE_RISE,
        CONE_RISE,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = body - cavity

    # Гнездо: круг Ø6,2 на всю глубину и срез по лыске выше круглого участка.
    z0 = flat_z0()
    assert 0.0 < z0 < BORE_DEPTH - 0.3, z0
    round_bore = bd.Pos(0, 0, -0.5) * bd.Cylinder(
        BORE_D / 2, z0 + 0.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    flat_profile = bd.Circle(BORE_D / 2) - bd.Pos(0, BORE_FLAT + 10.0) * bd.Rectangle(20, 20)
    flat_bore = bd.Pos(0, 0, z0) * bd.extrude(flat_profile, BORE_DEPTH - z0)
    body = body - round_bore - flat_bore

    # Саморез M3 в лыску: пилот Ø2,5 с боку +Y, на 7,0 от низа, сквозь стенку.
    screw = bd.Pos(0, 8.5, SCREW_Z) * bd.Rot(90, 0, 0) * bd.Cylinder(SCREW_D / 2, 15)
    body = body - screw

    body.label = "knob"
    body.color = "#1c1e22"

    box = body.bounding_box()
    assert SKIRT_D - 2 * BOTTOM_CHAMFER < box.size.X <= SKIRT_D + 1e-6, box.size.X
    assert abs(box.size.X - box.size.Y) < 0.01, box.size
    assert abs(box.min.Z) < 0.01 and abs(box.max.Z - height) < 0.01, (box.min.Z, box.max.Z)
    # Тело над лицом — ровно Ø28,0; юбка ниже шире.
    face_dia = (
        body & bd.Pos(0, 0, FACE_REL + 1.0) * bd.Box(40, 0.2, 0.1)
    ).bounding_box().size.X
    assert abs(face_dia - KNOB_DIA) < 0.01, face_dia
    # Юбка: ниже лица материал только в кольце 2,0 — в 13,5 от оси он есть,
    # в 11,8 (место островка) и в 8,0 его нет.
    assert (body & bd.Pos(SKIRT_D / 2 - 0.6, 0, 0.3) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert not (body & bd.Pos(SKIRT_IN_D / 2 - 0.3, 0, 0.3) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert not (body & bd.Pos(8.0, 0, 0.3) * bd.Box(0.2, 0.2, 0.2)).solids()
    # Скос 45° от 11,8 вниз: при ходе кнопки 0,5 островок Ø23,2 не задет.
    assert not (
        body
        & bd.Pos(SEAT_ISLAND_D / 2, 0, FACE_REL + PRESS) * bd.Box(0.05, 0.2, 0.05)
    ).solids()
    assert not (body & bd.Pos(11.6, 0, CONE_Z0 + 0.3) * bd.Box(0.05, 0.2, 0.05)).solids()
    assert (body & bd.Pos(12.0, 0, CONE_Z0 + 0.3) * bd.Box(0.2, 0.2, 0.2)).solids()
    # Дно ручки — плоское, на высоте FLOOR_REL: под ним пусто, над ним материал.
    assert not (body & bd.Pos(7.0, 0, FLOOR_REL - 0.2) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert (body & bd.Pos(7.0, 0, FLOOR_REL + 0.2) * bd.Box(0.2, 0.2, 0.2)).solids()
    # Гнездо выше дна: круг Ø6,1 и срез по лыске 1,55 от оси.
    probe_z = FLOOR_REL + 1.0
    assert not (body & bd.Pos(0, 0, probe_z) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert not (body & bd.Pos(2.9, 0, probe_z) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert (body & bd.Pos(3.4, 0, probe_z) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert not (body & bd.Pos(0, 1.4, probe_z) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert (body & bd.Pos(0, 1.7, probe_z) * bd.Box(0.2, 0.2, 0.2)).solids()
    # Вал входит на 11,8 при глубине гнезда 12,6 — над торцом 0,8 материала.
    shaft_in = seat_front_z() + ENC_SHAFT_L - knob_bottom_z()
    assert shaft_in < BORE_DEPTH - 0.3, (shaft_in, BORE_DEPTH)
    assert (
        body & bd.Pos(0, 0, BORE_DEPTH + 0.3) * bd.Box(0.2, 0.2, 0.2)
    ).solids(), "верх над гнездом сквозной"
    assert BORE_DEPTH < height - 1.0, (BORE_DEPTH, height)
    # Винт: на 7,0 стенка с +Y сквозная, с −Y — целая.
    assert not (body & bd.Pos(0, 8.0, SCREW_Z) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert (body & bd.Pos(0, -8.0, SCREW_Z) * bd.Box(0.2, 0.2, 0.2)).solids()

    print(
        f"ручка Ø{KNOB_DIA:g}×{height:.2f} (юбка Ø{SKIRT_D:g}×{FACE_REL:.2f}, "
        f"стенка {SKIRT_WALL:g}, внутри Ø{SKIRT_IN_D:g}): над лицом {PROUD:g} "
        f"({top_z(knob_center()[0]):.2f}), под лицом {FACE_REL:.2f} до z={knob_bottom_z():.2f}; "
        f"скос 45° с z={CONE_Z0:.2f}, дно ручки z={FLOOR_REL:.2f} Ø{SKIRT_IN_D - 2 * CONE_RISE:g}, "
        f"гнездо Ø{BORE_D:g} глубиной {BORE_DEPTH:g}, срез {BORE_FLAT:.2f} от оси с z={z0:.2f}, "
        f"торец вала входит на {shaft_in:.2f} (запас {BORE_DEPTH - shaft_in:.2f}); "
        f"саморез M3 в пилот Ø{SCREW_D:g} с +Y на z={SCREW_Z:g} (до лыски 12,3); "
        f"фаски {TOP_CHAMFER:g} сверху и {BOTTOM_CHAMFER:g} снизу"
    )
    return body


if __name__ == "__main__":
    knob()
