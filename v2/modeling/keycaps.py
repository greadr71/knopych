# -*- coding: utf-8 -*-
"""Шесть кейкапов MX лица. Отдельная деталь, не часть панели.

Низ кромки на Z=0, у центра верх на Z=CAP_H, но на лицо кейкап ставится на
RECESS (−2,0): верх на 2,0 выше плоскости лица — ступенька между кейкапами и
лицом и есть тактильная карта. Верх кейкапа лежит на наклонной плоскости лица
(TOP_SLOPE, 1,72° по X):
весь верх срезан ею после сборки, поэтому кромка параллельна лицу — у левого
края CAP_H+0,26, у правого CAP_H−0,26. Гнездо и стенки при этом вертикальные:
колодец в лице тоже прямой.
Оболочка — прямой 17×17 (R2,0) на всю высоту, стенка CAP_WALL, верх TOP_THK.
Верх — плоскость лица, без ступеньки и окна; единственная неровность — риска.

Снизу по центру гнездо MX: бобышка Ø5,5 от рима до потолка оболочки (7,6),
в ней крестовина 4,2 × 1,37 (CROSS_ARM + CROSS_TOL), вырезанная снизу
на глубину 7,2. Выше 7,2 ничего не вырезано: над гнездом остаётся верх
кейкапа не тоньше 1,1.

Снаружи кейкап симметричен, а верх скошен 1,72° по X, поэтому в лице есть
тактильная риска ориентации, как планка на F/J: канавка 5,0 по X × 1,0 по Y
глубиной 0,4, низ — в 2,0 от нижней кромки лица (сторона к полке). Кейкап
ставится канавкой вниз; при повороте на 90/180° верх перекашивается на 3,4°, и
канавка оказывается сверху или сбоку. Печатается лицом вниз, поэтому риска —
углубление: выступ на лице не напечатать.

Кейкапы все одинаковы — различие только в Y при расстановке.

Печать FDM, сопло 0,4 мм, слой 0,2 мм, PETG или ASA. Лицом на стол:
print_stl.py переворачивает кейкапы на 180° и снимает наклон лица 1,72° (как у
панели), поэтому лицо ложится плоско на текстурированную PEI и получает матовую
текстуру, приятнее под палец; гнездо открыто вверх. Мост остаётся только над
бобышкой Ø5,5 (потолок гнезда).

Запуск: cad run v2/modeling/keycaps.py
"""

import math

import build123d as bd
from cad import model
from cad.build123d import closest_points
from face import RECESS, TOP_SLOPE, top_z

CAP = 17.0
CAP_TOP = 17.0
CAP_H = 9.0
CAP_WALL = 1.2
TOP_THK = 1.4
BASE_R = 2.0
# Фаска верхней кромки: кейкап печатается верхом вниз, этот край — контакт со
# столом, фаска 45° прячет «слоновью ногу» вместо посадки 17,0 в колодце 17,4.
CAP_BEVEL = 0.5
# Фаска нижней кромки: в стенке CAP_WALL остаётся 0,8 материала.
RIM_CHAMFER = 0.4
# Риска ориентации — канавка в лице, как планка на F/J: верх скошен на 1,72°, а
# по крестовине кейкап симметричен, поэтому планка говорит, где низ. Печать
# лицом вниз: выступ на лице не напечатать, поэтому канавка на 0,4 внутрь.
MARK_LEN = 5.0
MARK_W = 1.0
MARK_D = 0.4
# От нижней кромки лица (y=−8,5) до канавки; её центр — MARK_INSET + MARK_W/2.
MARK_INSET = 2.0

STEM_DIA = 5.5
CROSS_LEN = 4.2
CROSS_ARM = 1.17
CROSS_TOL = 0.2
# Потолок гнезда от рима; выше — сплошной верх кейкапа.
SOCKET_DEPTH = 7.2


def _surface(x):
    """Высота лица над центром кейкапа: та же наклонная плоскость, что у панели."""
    return CAP_H + TOP_SLOPE * x


def _shell():
    """Оболочка: прямой 17×17 на всю высоту, стенка CAP_WALL, верх TOP_THK.

    Наружная выдавлена до высокого края наклона — верх срезается плоскостью
    лица, поэтому у левой стенки он выше CAP_H на |TOP_SLOPE|·CAP/2.
    """
    outer = bd.extrude(
        bd.Plane.XY * bd.RectangleRounded(CAP, CAP, BASE_R),
        CAP_H + TOP_SLOPE * (-CAP / 2),
    )
    inner = bd.Pos(0, 0, -0.1) * bd.extrude(
        bd.Plane.XY
        * bd.RectangleRounded(CAP - 2 * CAP_WALL, CAP - 2 * CAP_WALL, 0.8),
        CAP_H - TOP_THK + 0.1,
    )
    return outer - inner


def _stem():
    """Бобышка штока от рима до потолка оболочки; крестовина вырезана снизу."""
    z_top = CAP_H - TOP_THK
    stem = bd.Pos(0, 0, z_top / 2) * bd.Cylinder(STEM_DIA / 2, z_top)
    depth = SOCKET_DEPTH + 0.1
    z_mid = -0.1 + depth / 2
    arm = CROSS_ARM + CROSS_TOL
    stem -= bd.Pos(0, 0, z_mid) * bd.Box(CROSS_LEN, arm, depth)
    stem -= bd.Pos(0, 0, z_mid) * bd.Box(arm, CROSS_LEN, depth)
    return stem


def _outer(edge):
    """Ребро на наружном контуре: его габарит доходит до стенки CAP/2."""
    box = edge.bounding_box()
    return max(abs(box.min.X), abs(box.max.X), abs(box.min.Y), abs(box.max.Y)) > CAP / 2 - 0.05


def _keycap():
    """Оболочка со штоком и гладкой плоскостью лица."""
    # Наклон лица: та же плоскость, что top_z(x), но в местной системе у центра.
    beta = -math.degrees(math.atan(TOP_SLOPE))
    face = bd.Pos(0, 0, CAP_H) * bd.Rot(0, beta, 0)
    cap = _shell() + _stem()
    # Весь верх — на наклонной плоскости лица: оболочка и шток остаются
    # вертикальными, срезается только верх по плоскости.
    cap -= face * bd.Box(
        CAP + 6,
        CAP + 6,
        20,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Риска ориентации — канавка в лице по нормали к нему (вертикальный рез на
    # наклоне 1,72° увёл бы глубину по длине на 0,15): от плоскости лица вниз,
    # 0,1 сверху — чтобы рез не спорил с гранью.
    cap -= face * bd.Pos(0, -CAP / 2 + MARK_INSET + MARK_W / 2, 0.1) * bd.Box(
        MARK_LEN,
        MARK_W,
        MARK_D + 0.1,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    )
    # Периметр верха — единственные рёбра на плоскости лица. Кейкап печатается
    # верхом вниз, этот край ложится на стол: фаска 45° гасит «слоновью ногу»
    # вместо того, чтобы она портила посадку 17,0 в колодце 17,4.
    top = [
        edge
        for edge in cap.edges()
        if _outer(edge)
        and all(abs(v.Z - _surface(v.X)) < 0.01 for v in edge.vertices())
    ]
    cap = bd.chamfer(top, CAP_BEVEL)
    # Нижняя кромка: фаска 0,4×45° только снаружи, в стенке 1,2 остаётся 0,8.
    rim = [edge for edge in cap.edges() if abs(edge.center().Z) < 0.01 and _outer(edge)]
    cap = bd.chamfer(rim, RIM_CHAMFER)
    cap.label = "keycap"
    cap.color = "#1c1e22"
    return cap


def _verify(cap):
    """Проверки одного кейкапа в его системе координат (до переноса на лицо)."""
    assert len(cap.solids()) == 1
    box = cap.bounding_box()
    assert abs(box.min.Z) < 0.01, box.min.Z
    # Верх наклонён: максимум у левого края. С фаской верхний край начинается
    # не от CAP/2, а на CAP_BEVEL внутрь — там CAP_H + 0,24.
    assert abs(box.max.Z - _surface(-(CAP / 2 - CAP_BEVEL))) < 0.01, box.max.Z
    # Крестовина пуста в центре и на конце луча; материал между лучами цел.
    for px, py in ((0, 0), (CROSS_LEN / 2 - 0.2, 0), (0, CROSS_LEN / 2 - 0.2)):
        probe = cap & bd.Pos(px, py, SOCKET_DEPTH - 0.1) * bd.Box(0.2, 0.2, 0.2)
        assert not probe.solids(), (px, py)
    assert (cap & bd.Pos(1.6, 1.6, 4.0) * bd.Box(0.2, 0.2, 0.2)).solids()
    # Потолок гнезда ровно 7,2: в центре и у края бобышки, где тарелка ниже.
    ceiling = cap & bd.Pos(0, 0, CAP_H / 2) * bd.Box(0.3, 0.3, CAP_H + 1)
    assert abs(ceiling.bounding_box().min.Z - SOCKET_DEPTH) < 0.02, (
        ceiling.bounding_box().min.Z
    )
    roof = cap & bd.Pos(0, -1.8, CAP_H / 2) * bd.Box(0.3, 0.3, CAP_H + 1)
    roof_box = roof.bounding_box()
    assert abs(roof_box.min.Z - SOCKET_DEPTH) < 0.02, roof_box.min.Z
    # Верх над гнездом на наклонном верху тоньше у высокого края: наклон лица
    # съедает |TOP_SLOPE|·CAP/2 = 0,25 мм, остаётся ≈ 1,15.
    thin = TOP_THK - abs(TOP_SLOPE) * CAP / 2
    assert thin >= 1.1, thin
    # Верх — ровно плоскость `_surface(x)`: сплошной и гладкий, без окна и канавки.
    for px, py in ((0.0, 0.0), (-5.0, 0.0), (5.0, 0.0), (0.0, -5.0), (0.0, 5.0)):
        column = cap & (
            bd.Pos(px, py, SOCKET_DEPTH + 0.5)
            * bd.Box(
                0.2, 0.2, CAP_H, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
            )
        )
        assert column.solids(), (px, py)
        assert abs(column.bounding_box().max.Z - _surface(px)) < 0.03, (
            (px, py),
            column.bounding_box().max.Z,
        )
    # Материал над крестовиной в центре: потолок 7,2, лицо 9,0 — 1,8.
    over_cross = _surface(0) - ceiling.bounding_box().min.Z
    assert abs(over_cross - (CAP_H - SOCKET_DEPTH)) < 0.03, over_cross
    assert over_cross >= 1.5, over_cross
    # Риска ориентации — канавка в лице: пуста на обоих концах по X, дно на 0,4,
    # лицо вокруг цело (по Y ±1,5 и за торцом), вторая половина лица (y=6) цела.
    for px in (0.0, 2.0):
        assert not (
            cap & bd.Pos(px, -6.0, _surface(px) - 0.2) * bd.Box(0.2, 0.2, 0.2)
        ).solids(), px
    assert (cap & bd.Pos(0, -6.0, _surface(0) - 0.55) * bd.Box(0.2, 0.2, 0.2)).solids()
    for px, py in ((0, -4.5), (0, -7.5), (3.0, -6.0), (0, 6.0)):
        assert (
            cap & bd.Pos(px, py, _surface(px) - 0.2) * bd.Box(0.2, 0.2, 0.2)
        ).solids(), (px, py)
    # Габарит не тронут: 17,0 × 17,0 (min Z = 0 — проверено выше).
    for got in (box.min.X, box.max.X, box.min.Y, box.max.Y):
        assert abs(abs(got) - CAP / 2) < 0.01, got
    return cap


@model
def keycap():
    """Один кейкап: верх — плоскость лица с тактильной риской, гнездо MX снизу."""
    return _verify(_keycap())


@model
def keycaps():
    """Шесть кейкапов на лице, рим на top_z(x) − CAP_H − RECESS — свой у каждого.

    Кейкапы все одинаковы: верх на 2,0 выше плоскости лица (RECESS = −2,0),
    плоскость лица с тактильной риской, без окна.
    """
    import face as face_part

    part = face_part.face().shape
    blank = keycap().shape
    caps = []
    centers = face_part.face_centers()
    for index, (x, y) in enumerate(centers, 1):
        rim_z = face_part.top_z(x) - CAP_H - RECESS
        cap = bd.Pos(x, y, rim_z) * blank
        cap.label = f"keycap_{index}"
        cap.color = "#1c1e22"
        caps.append(cap)

    for cap, (x, y) in zip(caps, centers):
        rim_z = face_part.top_z(x) - CAP_H - RECESS
        box = cap.bounding_box()
        assert abs(box.min.Z - rim_z) < 0.01, (cap.label, box.min.Z)
        # Максимум у левого края кейкапа: лицо выше слева. С фаской верхний
        # край начинается на CAP_BEVEL внутрь, поэтому минус 0,5 от края.
        assert abs(box.max.Z - (face_part.top_z(x - CAP / 2 + CAP_BEVEL) - RECESS)) < 0.01, (
            cap.label,
            box.max.Z,
        )
        # Верх кейкапа — ровно на 2,0 над плоскостью лица своей колонки
        # (замер по печати; RECESS — только следствие посадки на свитч).
        lift = rim_z + _surface(0) - face_part.top_z(x)
        assert abs(lift - 2.0) < 0.01, (cap.label, lift)
        # Верх — плоскость лица на всём верхе, без канавки и окна.
        for py in (-6.0, 6.0):
            column = cap & (
                bd.Pos(x + 4.0, y + py, rim_z + SOCKET_DEPTH + 0.5)
                * bd.Box(0.2, 0.2, 3)
            )
            assert column.solids(), (cap.label, py)
            assert abs(column.bounding_box().max.Z - rim_z - _surface(4.0)) < 0.03, (
                cap.label,
                py,
                column.bounding_box().max.Z,
            )

    for cap in caps:
        common = part & cap
        overlap = common.volume if common.solids() else 0.0
        assert overlap < 0.01, overlap
        # Минимум — на скруглённых углах R2,0 кейкапа против R2,2 колодца:
        # ровно зазор 0,2 по контуру. По стенке у рима 0,31 — шире.
        gap = closest_points(part, cap).distance
        assert 0.15 < gap < 0.25, gap

    assembly = bd.Compound(children=[part, *caps], label="keycaps")
    assert len(assembly.solids()) == 1 + len(caps), len(assembly.solids())
    rims = [face_part.top_z(x) - CAP_H - RECESS for x, _ in centers]
    tops = [face_part.top_z(x - CAP / 2 + CAP_BEVEL) - RECESS for x, _ in centers]
    print(
        f"кейкап {CAP:g}×{CAP:g} (прямой, стенки и гнездо вертикальные), h={CAP_H:g}, "
        f"стенка {CAP_WALL:g}, верх {TOP_THK:g}; верх на {-RECESS:g} над "
        f"плоскостью лица (z={min(tops):.2f}..{max(tops):.2f}, "
        f"({math.degrees(math.atan(-TOP_SLOPE)):.2f}° по X)), фаска верха {CAP_BEVEL:g}, "
        f"фаска низа {RIM_CHAMFER:g}; "
        f"рим z={min(rims):.2f}..{max(rims):.2f} по кейкапам "
        f"({', '.join(f'{z:.2f}' for z in rims)}); "
        f"верх — плоскость лица с риской; "
        f"гнездо MX Ø{STEM_DIA:g}×{SOCKET_DEPTH:g}, крестовина "
        f"{CROSS_LEN:g}×{CROSS_ARM + CROSS_TOL:g}; "
        f"зазор кейкап↔колодец {closest_points(part, caps[0]).distance:.2f} мм"
    )
    return assembly


if __name__ == "__main__":
    keycaps()
