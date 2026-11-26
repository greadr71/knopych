# -*- coding: utf-8 -*-
"""Корпус кнопок «Кнопыч». Параметрическая модель на build123d.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/build_housing.py

Скрипт пересобирает короб и заднюю крышку, пишет v1/modeling/button_housing.stl
(короб, лицом на стол) и v1/modeling/button_housing_lid.stl (крышка, наружной
стороной на стол) и, если панель OCP CAD Viewer открыта, показывает их там.

Оси: лицо в плоскости XY при Z=0, +Z вглубь к открытой спине,
+X ширина, +Y высота. Единицы — миллиметры.

Лицо — рамка 3 мм с колодцами. Пластина свитчей под ними 1,4 мм: на пробнике
с поддержками именно эта толщина защёлкивала свитч.
"""

import math
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Cone,
    Cylinder,
    GeomType,
    Plane,
    Polygon,
    Pos,
    RectangleRounded,
    Rot,
    export_stl,
    extrude,
    fillet,
)

# Габарит. DEPTH — от пластины свитчей до спины, рамка спереди сверх неё.
WIDTH = 145.0
HEIGHT = 25.0
DEPTH = 20.0
WALL = 2.0
# Пластина 1,4 мм: на пробнике с поддержками (две точки) свитч защёлкивался.
# 1,2 мм (одна точка) — нет. Поддержки прилипают и добавляют толщину к модели.
FACE_THK = 1.4

FRAME_DEPTH = 3.0
KEYCAP_BASE = 17.0
KEYCAP_BASE_R = 2.0
WELL_CLEARANCE = 0.5
BOX_DEPTH = FRAME_DEPTH + DEPTH
PLATE_Z = FRAME_DEPTH

# Свитчи и вертушок
SWITCH_SIZE = 14.0
OUTER_MARGIN = 4.0
SWITCH_GAP = 4.0
KNOB_GAP = 3.5
KNOB_DIA = 30.0
KNOB_WALL = WALL

# Кабель: прорезь в правой стенке, открыта к задней кромке.
CABLE_DIA = 8.0
CABLE_Y = 12.0

# Скругления. BOTTOM_R оставлен как напоминание: отдельный радиус низа лица
# ядро применить не может, низ входит в общую кромку FACE_EDGE_R.
CORNER_R = 6.0
BOTTOM_R = 2.0
FACE_EDGE_R = 1.2
KNOB_EDGE_R = 1.2

# Задняя крышка: плита заподлицо со спиной, лежит на торцах бобышек.
LID_THK = 3.0
LID_CLEARANCE = 0.1
LID_Z = BOX_DEPTH - LID_THK

# Защёлка: язычок в краю крышки гнётся в её плоскости, вдоль слоёв печати.
# Зуб цепляет канавку на внутренней стороне длинной стенки. Расчёт по
# Bayer: изгиб 1,5·t·y/L². Перекрытие зуба — TOOTH_H минус зазор крышки.
TONGUE_LEN = 14.0
TONGUE_THK = 1.6
TONGUE_SLOT = 1.2
TONGUE_END_GAP = 0.6
TOOTH_LEN = 4.0
TOOTH_H = 0.9
TOOTH_ENTRY_DEG = 30.0
GROOVE_DEPTH = 1.0
GROOVE_FLOOR_GAP = 0.3
# Потолок канавки 45° ближе к лицу на столько: зуб не доходит до конца
# и прижимает крышку к бобышкам, без этого крышка болтается.
GROOVE_PRELOAD = 0.15

# Бобышки под самонарезающий винт M2 прямо в пластик. В крышке потай,
# чтобы головка не торчала из спины.
BOSS_D = 5.0
PILOT_D = 1.7
PILOT_DEPTH = 6.0
SCREW_HOLE_D = 2.4
SCREW_HEAD_D = 4.2

# Бобышки у верхней стенки по бокам от вертушка: под стенкой вертушка
# и за окнами места нет. По X — от оси вертушка. Между бобышкой и стенкой
# вертушка 5,5 мм на провода левой тройки.
BOSS_DX = 14.0

# Язычки (корень, свободный конец) по X, на обеих длинных стенках.
TONGUE_SPANS = ((15.0, 29.0), (130.0, 116.0))

# Полочка-упор крышки по периметру, кроме язычков и вертушка.
# Низ 45° для печати. За свитчами на этой глубине ничего нет.
LEDGE_W = 1.5

# Риски на нижней грани по сторонам от арки, открыты к спине: поддеть крышку
PRY_WIDTH = 14.0
PRY_DEPTH = 1.0
PRY_GAP = 1.0

# Демо платы под левым рядом. В обычной сборке выключено.
BUILD_PCB_DEMO = False
PCB_Z = 5.0
PCB_THK = 1.6

HERE = Path(__file__).resolve().parent


def switch_centers():
    """Шесть центров окон по X: три слева от вертушка и три справа."""
    pitch = SWITCH_SIZE + SWITCH_GAP
    left0 = OUTER_MARGIN + SWITCH_SIZE / 2
    left = [left0 + i * pitch for i in range(3)]
    right0 = WIDTH / 2 + KNOB_DIA / 2 + KNOB_GAP + SWITCH_SIZE / 2
    right = [right0 + i * pitch for i in range(3)]
    return left + right


def _box(x, y, z, sx, sy, sz):
    """Прямоугольный брусок, угол (x, y, z) — минимальный."""
    return Pos(x, y, z) * Box(
        sx, sy, sz, align=(Align.MIN, Align.MIN, Align.MIN)
    )


def _rounded_box(x, y, z, sx, sy, sz, radius):
    """Брусок со скруглёнными углами в плане XY."""
    profile = Pos(x, y) * RectangleRounded(
        sx, sy, radius, align=(Align.MIN, Align.MIN)
    )
    return Pos(0, 0, z) * extrude(profile, sz)


def well_cut(centers, depth):
    """Колодец под ряд кейкапов глубиной depth. В корпусе не используется.

    Один на ряд. Шаг 18 мм при низе кейкапа 17 мм: стенки между
    соседними кнопками не остаётся. Печатать лицом на стол нельзя:
    пластина над колодцем — мост, кромка окна выходит рыхлой.
    """
    half = KEYCAP_BASE / 2 + WELL_CLEARANCE
    x0 = min(centers) - half
    y0 = HEIGHT / 2 - half
    return _rounded_box(
        x0,
        y0,
        -0.1,
        max(centers) + half - x0,
        2 * half,
        depth + 0.1,
        KEYCAP_BASE_R + WELL_CLEARANCE,
    )


def _yz_prism(points, x0, x1):
    """Призма вдоль X от x0 до x1 с профилем из точек (y, z)."""
    solid = extrude(Plane.YZ * Polygon(*points, align=None), abs(x1 - x0))
    # Сторону вытягивания задаёт обход точек, поэтому ставим призму по факту.
    return Pos(min(x0, x1) - solid.bounding_box().min.X, 0, 0) * solid


def _latch_side(side, height):
    """Внутренняя грань длинной стенки и направление наружу, в стенку."""
    if side == "top":
        return height - WALL, 1
    return WALL, -1


def _tooth_z(lid_z):
    """Вершина зуба и верх его удерживающего скоса 45°."""
    z_tip = lid_z + TOOTH_H / math.tan(math.radians(TOOTH_ENTRY_DEG))
    return z_tip, z_tip + TOOTH_H


def tongue_slot(tongue, height, lid_z):
    """Г-образная прорезь в краю крышки: вдоль края и поперёк у свободного конца."""
    x_root, x_free, side = tongue
    wall_y, out = _latch_side(side, height)
    edge_y = wall_y - out * LID_CLEARANCE
    slot_mid = edge_y - out * (TONGUE_THK + TONGUE_SLOT / 2)
    step = 1 if x_free > x_root else -1
    slot_end = x_free + step * TONGUE_END_GAP
    z0 = lid_z - 0.1
    cut_h = LID_THK + 0.2
    # Полукруглый конец прорези у корня — скругление корня язычка R = TONGUE_SLOT/2
    cut = _box(
        min(x_root, slot_end),
        slot_mid - TONGUE_SLOT / 2,
        z0,
        abs(slot_end - x_root),
        TONGUE_SLOT,
        cut_h,
    )
    cut += Pos(x_root, slot_mid, lid_z + LID_THK / 2) * Cylinder(TONGUE_SLOT / 2, cut_h)
    outside = edge_y + out * 0.1
    cut += _box(
        min(x_free, slot_end),
        min(slot_mid, outside),
        z0,
        TONGUE_END_GAP,
        abs(outside - slot_mid),
        cut_h,
    )
    return cut


def tongue_tooth(tongue, height, lid_z):
    """Зуб у свободного конца: заход 30° к оси вставки, удержание 45°."""
    x_root, x_free, side = tongue
    wall_y, out = _latch_side(side, height)
    edge_y = wall_y - out * LID_CLEARANCE
    z_tip, z_top = _tooth_z(lid_z)
    points = [
        (edge_y - out * 0.1, lid_z),
        (edge_y, lid_z),
        (edge_y + out * TOOTH_H, z_tip),
        (edge_y, z_top),
        (edge_y - out * 0.1, z_top),
    ]
    step = 1 if x_free > x_root else -1
    return _yz_prism(points, x_free - step * TOOTH_LEN, x_free)


def tongue_groove(tongue, height, lid_z):
    """Канавка под зуб в стенке. Потолок 45° печатается без поддержки."""
    x_root, x_free, side = tongue
    wall_y, out = _latch_side(side, height)
    z_tip, _ = _tooth_z(lid_z)
    tip_in_wall = TOOTH_H - LID_CLEARANCE
    floor = lid_z - GROOVE_FLOOR_GAP

    def ceiling(w):
        return z_tip - GROOVE_PRELOAD + (tip_in_wall - w)

    points = [
        (wall_y - out * 0.1, floor),
        (wall_y + out * GROOVE_DEPTH, floor),
        (wall_y + out * GROOVE_DEPTH, ceiling(GROOVE_DEPTH)),
        (wall_y - out * 0.1, ceiling(-0.1)),
    ]
    step = 1 if x_free > x_root else -1
    return _yz_prism(
        points, x_free - step * (TOOTH_LEN + 0.5), x_free + step * 0.5
    )


def _xz_prism(points, y0, y1):
    """Призма вдоль Y от y0 до y1 с профилем из точек (x, z)."""
    solid = extrude(Plane.XZ * Polygon(*points, align=None), abs(y1 - y0))
    return Pos(0, min(y0, y1) - solid.bounding_box().min.Y, 0) * solid


def _spans(x0, x1, blocked):
    """Отрезки [x0, x1] за вычетом занятых промежутков."""
    spans = [(x0, x1)]
    for b0, b1 in blocked:
        spans = [
            piece
            for s0, s1 in spans
            for piece in ((s0, min(s1, b0)), (max(s0, b1), s1))
            if piece[1] - piece[0] > 1.0
        ]
    return spans


def tongue_zone(tongue):
    """Промежуток по X, который занимает язычок с прорезью, с запасом 1 мм."""
    x_root, x_free, _ = tongue
    step = 1 if x_free > x_root else -1
    ends = (x_root - step * (TONGUE_SLOT / 2 + 1.0), x_free + step * (TONGUE_END_GAP + 1.0))
    return min(ends), max(ends)


def _corner_ledge(cx, cy, lid_z, rotation_z):
    """Четверть полочки по скруглению внутреннего угла.

    Тот же профиль, что у прямой: верх на уровне низа крышки, низ под 45°.
    """
    r_wall = CORNER_R - WALL
    height = LEDGE_W + 0.1
    r_out = r_wall + 0.1
    z0 = lid_z - height
    # align=None: ось остаётся в начале координат. CENTER сдвинул бы ось
    # в центр ограничивающего прямоугольника сектора.
    sector = Pos(cx, cy, z0) * Cylinder(
        r_out, height, arc_size=90, rotation=(0, 0, rotation_z), align=None
    )
    slope = Pos(cx, cy, z0) * Cone(
        r_out,
        r_wall - LEDGE_W,
        height,
        arc_size=90,
        rotation=(0, 0, rotation_z),
        align=None,
    )
    return sector - slope


def perimeter_ledges(width, height, lid_z, blocked, ends=("left",)):
    """Полочка по длинным стенкам и торцам, верх на уровне низа крышки.

    На скруглении угла прямые куски соединены четвертью того же профиля.
    blocked — {"bottom": [...], "top": [...]}: промежутки по X без полочки.
    """
    straight = CORNER_R
    pieces = []
    spans = {}
    for side in ("bottom", "top"):
        wall_y, out = _latch_side(side, height)
        points = [
            (wall_y + out * 0.1, lid_z),
            (wall_y - out * LEDGE_W, lid_z),
            (wall_y + out * 0.1, lid_z - LEDGE_W - 0.1),
        ]
        spans[side] = _spans(straight, width - straight, blocked[side])
        for x0, x1 in spans[side]:
            pieces.append(_yz_prism(points, x0, x1))
    for end in ends:
        wall_x, out = (WALL, -1) if end == "left" else (width - WALL, 1)
        points = [
            (wall_x + out * 0.1, lid_z),
            (wall_x - out * LEDGE_W, lid_z),
            (wall_x + out * 0.1, lid_z - LEDGE_W - 0.1),
        ]
        pieces.append(_xz_prism(points, straight, height - straight))
    # Угол есть, только если к нему подходят и торец, и длинная стенка.
    corners = {
        ("left", "bottom"): (straight, straight, 180),
        ("left", "top"): (straight, height - straight, 90),
        ("right", "bottom"): (width - straight, straight, 270),
        ("right", "top"): (width - straight, height - straight, 0),
    }
    for end in ends:
        x_end = straight if end == "left" else width - straight
        for side, spans_side in spans.items():
            meets = any(
                abs((x0 if end == "left" else x1) - x_end) < 0.2 for x0, x1 in spans_side
            )
            if meets:
                cx, cy, rotation_z = corners[(end, side)]
                pieces.append(_corner_ledge(cx, cy, lid_z, rotation_z))
    solid = pieces[0]
    for piece in pieces[1:]:
        solid += piece
    return solid


def boss(x, y, z0, z_top):
    """Бобышка от z0 до упора крышки z_top, сверху отверстие под саморез M2."""
    height = z_top - z0
    body = Pos(x, y, z0 + height / 2) * Cylinder(BOSS_D / 2, height)
    hole = Pos(x, y, z_top - PILOT_DEPTH / 2 + 0.05) * Cylinder(PILOT_D / 2, PILOT_DEPTH + 0.1)
    return body, hole


def screw_hole(x, y, lid_z):
    """Сквозное отверстие в крышке и потай под головку на наружной стороне."""
    top = lid_z + LID_THK
    hole = Pos(x, y, lid_z + LID_THK / 2) * Cylinder(SCREW_HOLE_D / 2, LID_THK + 0.2)
    sink_h = (SCREW_HEAD_D - SCREW_HOLE_D) / 2
    hole += Pos(x, y, top - sink_h / 2 + 0.05) * Cone(
        SCREW_HOLE_D / 2, SCREW_HEAD_D / 2 + 0.05, sink_h + 0.1
    )
    return hole


def lid_blank(width, height, lid_z):
    """Плита крышки по полости с зазором LID_CLEARANCE, заподлицо со спиной."""
    inset = WALL + LID_CLEARANCE
    return _rounded_box(
        inset,
        inset,
        lid_z,
        width - 2 * inset,
        height - 2 * inset,
        LID_THK,
        CORNER_R - inset,
    )


def lid_for_print(lid):
    """Наружной стороной на стол."""
    flipped = Rot(180, 0, 0) * lid
    return Pos(0, 0, -flipped.bounding_box().min.Z) * flipped


def _half_cylinder(radius, height):
    """Полуцилиндр: плоский диаметр на Y=0, выпуклость в +Y, ось вдоль Z."""
    return Cylinder(
        radius,
        height,
        arc_size=180,
        align=(Align.CENTER, Align.MIN, Align.CENTER),
    )


def _fillet(part, edges, radius, label):
    if not edges:
        print(f"knopych: {label} пропуск (нет рёбер)")
        return part
    try:
        part = fillet(edges, radius)
    except Exception as exc:
        print(f"knopych: {label} не вышло ({exc})")
        return part
    print(f"knopych: {label} ок ({len(edges)})")
    return part


def _edges(part, axis, pred):
    return [edge for edge in part.edges().filter_by(axis) if pred(edge.center())]


def _knob_rims(part, knob_r):
    rims = []
    for edge in part.edges():
        if edge.geom_type != GeomType.CIRCLE or abs(edge.radius - knob_r) > 0.8:
            continue
        z = edge.arc_center.Z
        # Только лицо. Задняя кромка отверстия ни к чему: спина открыта.
        if abs(z) < 0.3:
            rims.append(edge)
    return rims


def housing_tongues():
    """(корень, свободный конец, сторона) для четырёх язычков крышки."""
    return tuple(
        (x_root, x_free, side)
        for side in ("bottom", "top")
        for x_root, x_free in TONGUE_SPANS
    )


def housing_bosses():
    y = HEIGHT - WALL - BOSS_D / 2 + 0.2
    return ((WIDTH / 2 - BOSS_DX, y), (WIDTH / 2 + BOSS_DX, y))


def housing_ledge_blocks():
    """Где полочки нет: только под язычками. До арки полочку подрезает сама арка."""
    blocked = {}
    for side in ("bottom", "top"):
        blocked[side] = [tongue_zone(t) for t in housing_tongues() if t[2] == side]
    return blocked


def bottom_pry(x0, z_back):
    """Риска на нижней грани: вырез задней кромки стенки, открыт вниз и к спине."""
    return _box(x0, -0.1, z_back - PRY_DEPTH, PRY_WIDTH, WALL + 0.2, PRY_DEPTH + 0.1)


def arch_pry_xs():
    """Левые края двух рисок: сразу снаружи стенки арки."""
    edge = WIDTH / 2 - (KNOB_DIA / 2 + KNOB_WALL) - PRY_GAP
    return (edge - PRY_WIDTH, WIDTH - edge)


def build_housing():
    """Собрать корпус. Возвращает тело и, если включено, демо платы."""
    centers = switch_centers()
    switch_y0 = (HEIGHT - SWITCH_SIZE) / 2
    knob_cx = WIDTH / 2
    knob_r = KNOB_DIA / 2

    # Углы R6 в контуре, не отдельным 3D-скруглением: иначе радиус
    # склеивается с кромкой лица и ядро не даёт задать им разные радиусы.
    part = _rounded_box(0, 0, 0, WIDTH, HEIGHT, BOX_DEPTH, CORNER_R)
    part -= _rounded_box(
        WALL,
        WALL,
        PLATE_Z + FACE_THK,
        WIDTH - 2 * WALL,
        HEIGHT - 2 * WALL,
        DEPTH - FACE_THK,
        CORNER_R - WALL,
    )
    part -= well_cut(centers[:3], FRAME_DEPTH)
    part -= well_cut(centers[3:], FRAME_DEPTH)

    for center_x in centers:
        part -= _box(
            center_x - SWITCH_SIZE / 2,
            switch_y0,
            -0.2,
            SWITCH_SIZE,
            SWITCH_SIZE,
            BOX_DEPTH + 0.4,
        )

    mid_z = BOX_DEPTH / 2
    part -= Pos(knob_cx, 0, mid_z) * Cylinder(knob_r, BOX_DEPTH + 0.4)

    outer = Pos(knob_cx, 0, mid_z) * _half_cylinder(knob_r + KNOB_WALL, BOX_DEPTH)
    inner = Pos(knob_cx, 0, mid_z) * _half_cylinder(knob_r, BOX_DEPTH + 0.4)
    part += outer - inner

    part -= Pos(WIDTH, CABLE_Y, BOX_DEPTH) * Rot(0, 90, 0) * Cylinder(
        CABLE_DIA / 2, WALL + 4
    )

    # Мелкие кромки лица — пока углы острые. Иначе скругление угла
    # делает их одной цепью, и радиус 6 мм залезает на верхнюю кромку.
    # Нижний сегмент лица в одной касательной цепи с верхней кромкой
    # (через скруглённые углы), поэтому отдельный радиус 2 мм сюда не встаёт:
    # ядро скруглило бы весь периметр лица одним числом. Берём 1.2 мм.
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
    part = _fillet(part, _knob_rims(part, knob_r), KNOB_EDGE_R, "передняя кромка вертушка")

    for x, y in housing_bosses():
        body, hole = boss(x, y, PLATE_Z + FACE_THK - 0.1, LID_Z)
        part += body
        part -= hole
    ledges = perimeter_ledges(WIDTH, HEIGHT, LID_Z, housing_ledge_blocks())
    # Полочка входит в стенку арки на 0,05 мм и сливается с ней в одно тело
    ledges -= Pos(knob_cx, 0, mid_z) * Cylinder(knob_r + KNOB_WALL - 0.05, BOX_DEPTH + 2)
    part += ledges
    for tongue in housing_tongues():
        part -= tongue_groove(tongue, HEIGHT, LID_Z)
    for x0 in arch_pry_xs():
        part -= bottom_pry(x0, BOX_DEPTH)

    part.label = "ButtonHousing"
    pcb = _pcb_demo(centers[:3], switch_y0) if BUILD_PCB_DEMO else None
    return part, pcb


def build_lid():
    """Задняя крышка в закрытом положении: на бобышках и полочках, заподлицо со спиной."""
    lid = lid_blank(WIDTH, HEIGHT, LID_Z)
    lid_mid = LID_Z + LID_THK / 2
    cut_h = LID_THK + 0.2
    lid -= Pos(WIDTH / 2, 0, lid_mid) * Cylinder(
        KNOB_DIA / 2 + KNOB_WALL + LID_CLEARANCE, cut_h
    )
    # Кабель из полости выходит к прорези в стенке через вырез у правого края
    lid -= _box(
        WIDTH - WALL - CABLE_DIA,
        CABLE_Y - CABLE_DIA / 2,
        LID_Z - 0.1,
        CABLE_DIA + WALL,
        CABLE_DIA,
        cut_h,
    )
    for x, y in housing_bosses():
        lid -= screw_hole(x, y, LID_Z)
    for tongue in housing_tongues():
        lid -= tongue_slot(tongue, HEIGHT, LID_Z)
        lid += tongue_tooth(tongue, HEIGHT, LID_Z)
    lid.label = "ButtonHousingLid"
    return lid


def _pcb_demo(centers, switch_y0):
    """Пластина с отверстиями MX под тремя левыми окнами."""
    pcb_z = PLATE_Z + PCB_Z
    plate = _box(3.0, 3.5, pcb_z, 52.0, 18.0, PCB_THK)
    center_y = switch_y0 + SWITCH_SIZE / 2
    for center_x in centers:
        holes = [
            (center_x, center_y, 2.0),
            (center_x - 5.08, center_y, 0.85),
            (center_x + 5.08, center_y, 0.85),
            (center_x - 3.81, center_y + 2.54, 0.75),
            (center_x + 2.54, center_y + 5.08, 0.75),
        ]
        for x, y, radius in holes:
            plate -= Pos(x, y, pcb_z + PCB_THK / 2) * Cylinder(radius, PCB_THK + 0.4)
    plate.label = "PCB_MountDemo_Left"
    return plate


def _occupied(part, x, y, z):
    probe = _box(x - 0.15, y - 0.15, z - 0.15, 0.3, 0.3, 0.3)
    hit = part & probe
    return hit is not None and hit.volume > 1e-4


def lid_checks(part, lid, tongues, bosses, height, lid_z):
    """Проверки крышки на коробе. Пересечение тел — только натяг зубов."""
    common = part & lid
    overlap = common.volume if common is not None else 0.0
    pieces = common.solids() if common is not None else []
    z_tip, z_top = _tooth_z(lid_z)
    only_teeth = len(pieces) == len(tongues) and all(
        piece.bounding_box().min.Z > z_tip - 0.3 and piece.bounding_box().max.Z < z_top
        for piece in pieces
    )
    checks = {
        "крышка заподлицо со спиной": abs(lid.bounding_box().max.Z - (lid_z + LID_THK)) < 1e-6,
        "пересечение только натяг зубов": only_teeth,
    }
    ring = (BOSS_D + PILOT_D) / 4
    for i, (x, y) in enumerate(bosses, 1):
        checks[f"бобышка {i}: крышка лежит на торце"] = _occupied(
            part, x + ring, y, lid_z - 0.2
        ) and _occupied(lid, x + ring, y, lid_z + 0.2)
        checks[f"бобышка {i}: отверстие под саморез"] = not _occupied(part, x, y, lid_z - 1)
        checks[f"бобышка {i}: отверстие винта в крышке"] = not _occupied(
            lid, x, y, lid_z + LID_THK / 2
        )
    for i, tongue in enumerate(tongues, 1):
        x_root, x_free, side = tongue
        wall_y, out = _latch_side(side, height)
        edge_y = wall_y - out * LID_CLEARANCE
        step = 1 if x_free > x_root else -1
        x_tooth = x_free - step * TOOTH_LEN / 2
        x_mid = (x_root + x_free) / 2
        slot_y = edge_y - out * (TONGUE_THK + TONGUE_SLOT / 2)
        checks[f"язычок {i}: прорезь"] = all(
            not _occupied(lid, x, slot_y, z)
            for x in (x_root + step * 0.8, x_mid, x_free - step * 0.3)
            for z in (lid_z + 0.05, lid_z + LID_THK - 0.05)
        )
        checks[f"язычок {i}: свободный конец"] = not _occupied(
            lid, x_free + step * TONGUE_END_GAP / 2, edge_y - out * 0.5, lid_z + 1
        )
        checks[f"язычок {i}: зуб"] = _occupied(lid, x_tooth, edge_y + out * 0.5, z_tip)
        checks[f"язычок {i}: канавка"] = not _occupied(
            part, x_tooth, wall_y + out * 0.5, lid_z + 0.5
        )
    return checks, overlap


def _report(part):
    box = part.bounding_box()
    size = box.size
    print(
        "knopych housing rebuilt\n"
        f"volume mm3: {part.volume:.1f}\n"
        f"bbox mm: {size.X:.1f} x {size.Y:.1f} x {size.Z:.1f}"
    )
    plate_mid = PLATE_Z + FACE_THK / 2
    checks = {
        "окно свитча пустое": (not _occupied(part, 11, 12.5, plate_mid), True),
        "пластина между окнами": (_occupied(part, 20, 12.5, plate_mid), True),
        "колодец пустой": (not _occupied(part, 20, 12.5, PLATE_Z - 0.5), True),
        "борт рамки у торца": (_occupied(part, 1.5, 12.5, PLATE_Z - 0.5), True),
        "полость пустая": (not _occupied(part, 20, 12, 13), True),
        "стенка вертушка": (_occupied(part, WIDTH / 2, 16, 13), True),
        "кабель вырезан": (
            not _occupied(part, WIDTH - 0.4, CABLE_Y, BOX_DEPTH - 0.4),
            True,
        ),
        "полочка сливается с аркой": (
            _occupied(part, WIDTH / 2 - 16.95, WALL + 0.6, LID_Z - 0.2),
            True,
        ),
        "риска слева от арки": (
            not _occupied(part, arch_pry_xs()[0] + PRY_WIDTH / 2, 1.0, BOX_DEPTH - 0.4),
            True,
        ),
        "риска справа от арки": (
            not _occupied(part, arch_pry_xs()[1] + PRY_WIDTH / 2, 1.0, BOX_DEPTH - 0.4),
            True,
        ),
        "торец без риски": (_occupied(part, 1.0, HEIGHT / 2, BOX_DEPTH - 0.4), True),
    }
    for name, (got, want) in checks.items():
        print(f"  {'ок' if got == want else 'ОШИБКА'}: {name}")


def _report_lid(part, lid):
    checks, overlap = lid_checks(
        part, lid, housing_tongues(), housing_bosses(), HEIGHT, LID_Z
    )
    probes = {
        "полочка у левого торца": (WALL + LEDGE_W / 2, HEIGHT / 2),
        "полочка на левом нижнем углу": (3.5, 3.5),
        "полочка снизу слева": (40.0, WALL + LEDGE_W / 2),
        "полочка сверху посередине": (WIDTH / 2, HEIGHT - WALL - LEDGE_W / 2),
        "полочка снизу справа": (135.0, WALL + LEDGE_W / 2),
    }
    for name, (x, y) in probes.items():
        checks[f"{name}: крышка лежит"] = _occupied(part, x, y, LID_Z - 0.2) and _occupied(
            lid, x, y, LID_Z + 0.2
        )
    checks["проход кабеля в крышке"] = not _occupied(
        lid, WIDTH - WALL - 2, CABLE_Y, LID_Z + LID_THK / 2
    )
    checks["вертушок не закрыт"] = not _occupied(lid, WIDTH / 2, 16, LID_Z + LID_THK / 2)
    for name, ok in checks.items():
        print(f"  {'ок' if ok else 'ОШИБКА'}: {name}")
    size = lid.bounding_box().size
    boss_x, boss_y = housing_bosses()[0]
    knob_gap = math.hypot(WIDTH / 2 - boss_x, boss_y) - BOSS_D / 2 - KNOB_DIA / 2 - KNOB_WALL
    print(
        f"  крышка {size.X:.1f} x {size.Y:.1f} x {size.Z:.1f} мм, "
        f"натяг зубов {overlap:.2f} мм3, "
        f"от бобышки до стенки вертушка {knob_gap:.1f} мм"
    )


def main():
    part, pcb = build_housing()
    lid = build_lid()
    _report(part)
    _report_lid(part, lid)
    shapes = [part, lid] if pcb is None else [part, lid, pcb]
    export_stl(part, HERE / "button_housing.stl")
    export_stl(lid_for_print(lid), HERE / "button_housing_lid.stl")
    print(f"записано {HERE / 'button_housing.stl'} и {HERE / 'button_housing_lid.stl'}")
    if not _viewer_is_open():
        print(
            "viewer: панель закрыта. Cmd+Shift+P → OCP CAD Viewer: Open Viewer, "
            "затем снова запусти этот скрипт"
        )
        return
    try:
        from ocp_vscode import show

        shapes[1] = Pos(0, 0, 15) * lid
        show(*shapes, names=[shape.label for shape in (part, lid, pcb) if shape is not None])
        print("viewer: отправлено в панель")
    except Exception as exc:
        print(f"viewer: не открылось ({exc})")


def _viewer_is_open():
    import json
    import socket

    path = Path.home() / ".ocpvscode"
    if not path.exists():
        return False
    try:
        services = json.loads(path.read_text()).get("services") or {}
    except (OSError, json.JSONDecodeError):
        return False
    for port in services:
        sock = socket.socket()
        sock.settimeout(0.2)
        try:
            if sock.connect_ex(("127.0.0.1", int(port))) == 0:
                return True
        except (TypeError, ValueError):
            continue
        finally:
            sock.close()
    return False


if __name__ == "__main__":
    main()
