# -*- coding: utf-8 -*-
"""Ниша перед подстаканниками: карман, полка и обод. Только геометрия ниши.

Ниша — карман с профилем ободка: дно предварительно 88.7×52.0 на z=0
(оценка, не замер), рот кармана 90.0×53.3 на z=65, все углы R8 (выведен из диагоналей
штангенциркулем). От рта к ободу z=69 — раструб НАРУЖУ на 5 мм в плане
по задней и двум боковым граням.
Спереди раструба нет: стенка кармана кончается на z=62, от неё полка 6 мм
до передней плоскости; обод выступает над полкой на 7 мм.
Обод — отдельное тело, только фаска: кромка острая, плоской площадки сверху нет.
Фаска идёт по заду и двум бокам и продолжается прямо по боковой грани
до передней плоскости, не заворачивая на полку.

Здесь же живут константы профиля и компоновки (NICHE_*, KEYCAP*, KNOB_*, COLS,
ROWS), их берут face.py и body.py. Панель с колодцами и плитой строится в face.py,
настоящие MX-кейкапы — в keycaps.py, корпус — в body.py.

Оси: X — 90 мм, Y — 53 мм, Z вверх, пол ниши на Z=0, обод на Z=69.
"""

import math

import build123d as bd
from cad import model

OPEN_X = 90.0
OPEN_Y = 53.0
OPEN_Z = 69.0
FLOOR = 3.0

# Профиль ниши (NICHE.md, разрез ободка 21.11.2026). Замеры пользователя:
# рот кармана 90.0×53.3 на z=65, обод на z=69, углы R4;
# 5 мм в плане и 4 мм по высоте — фаска ободка; 6 мм — передняя полка;
# 7 мм — выступ обода над передней плоскостью (69 − 62).
# Дно не меряно: 88.7 и 52.0 в замерах — хорды у углов на уровне обода.
# Вместо них принят уклон стенок 1° на сторону (литейные обычно 0.5–1°).
# Диагонали равны (98 мм) — стенки параллельны, клина нет.
# «Наружу» (раструб шире кармана) — подтверждено пользователем 21.11.
NICHE_MOUTH_X = 90.0
NICHE_MOUTH_Y = 53.3
NICHE_MOUTH_Z = 65.0
NICHE_DRAFT = 1.0
_DRAFT_DROP = NICHE_MOUTH_Z * math.tan(math.radians(NICHE_DRAFT))
NICHE_FLOOR_X = NICHE_MOUTH_X - 2 * _DRAFT_DROP
NICHE_FLOOR_Y = NICHE_MOUTH_Y - 2 * _DRAFT_DROP
NICHE_FLARE = 5.0
NICHE_FLARE_Z = 4.0
NICHE_SHELF = 6.0
NICHE_FRONT_Z = OPEN_Z - 7.0
NICHE_CORNER_R = 8.0
# R8 выведен из замера диагоналей (98 мм): номинальная диагональ 90×53.3 — 104.6,
# губки в углу читают её короче на 0.83R. Не замер радиуса.
NICHE_CX = NICHE_MOUTH_X / 2
NICHE_CY = NICHE_MOUTH_Y / 2
# Рот кармана в абсолютных координатах. Левый край приходится на x=0.
_MOUTH_X0 = NICHE_CX - NICHE_MOUTH_X / 2
_MOUTH_X1 = NICHE_CX + NICHE_MOUTH_X / 2
_MOUTH_Y1 = NICHE_CY + NICHE_MOUTH_Y / 2

KEYCAP = 17.0
KEYCAP_TOP = 17.0
KEYCAP_H = 9.0
PITCH = 19.0
MARGIN_X = 2.5

KNOB_DIA = 28.0
KNOB_GAP = 3.0
KNOB_EDGE = 2.0
KNOB_H = 12.0

FIT = 0.5
LID_T = 3.0
SWITCH_HOLE = 14.0
AIR = 0.3
# Выступ кейкапа над плоскостью лица (не над ободом): над ободом кейкап стоит
# выше на 2,0 плюс стойка панели 10,0..11,1, то есть 12,0..13,1. Остальные 7 мм
# кейкапа — в колодце. В геометрии не участвует, только для справки.
PROUD = 2.0
# Зазор кейкапа в колодце на сторону: 17,0 → колодец 17,4.
WELL_CLEARANCE = 0.2

SWITCH_BODY = 15.6
SWITCH_H = 11.0

COLS = 3
ROWS = 2


def button_centers():
    """Центры шести окон справа: 2,5 мм до крутилки и столько же до проёма."""
    block_y = KEYCAP + (ROWS - 1) * PITCH
    x_right = OPEN_X - MARGIN_X - KEYCAP / 2
    x0 = x_right - (COLS - 1) * PITCH
    y0 = (OPEN_Y - block_y) / 2 + KEYCAP / 2
    return [
        (x0 + col * PITCH, y0 + row * PITCH)
        for row in range(ROWS)
        for col in range(COLS)
    ]


def knob_center():
    """Крутилка у левого края проёма."""
    return (KNOB_EDGE + KNOB_DIA / 2, OPEN_Y / 2)


def deck_bottom():
    """Низ панели: свитч низом до 62,0, выводы до 58,7, ниже полость корпуса."""
    return 58.7


def _niche_section(z, inset=0.0):
    """Сечение кармана на высоте z, суженное на inset с каждой стороны.

    Стенки сужаются линейно от рта к дну. Выше рта сечение не растёт:
    раструб идёт наружу и в карман не заходит.
    """
    t = min(z, NICHE_MOUTH_Z) / NICHE_MOUTH_Z
    width = NICHE_FLOOR_X + (NICHE_MOUTH_X - NICHE_FLOOR_X) * t
    depth = NICHE_FLOOR_Y + (NICHE_MOUTH_Y - NICHE_FLOOR_Y) * t
    return bd.Pos(NICHE_CX, NICHE_CY, z) * bd.RectangleRounded(
        width - 2 * inset, depth - 2 * inset, NICHE_CORNER_R - inset
    )


def _front_square_face(x0, x1, y0, y1, radius):
    """План со скруглённым задом и прямым передом.

    Боковые грани — прямые до самой передней плоскости: фаска, которая идёт
    по ним, не сворачивает на полку вместе со скруглением угла кармана.
    """
    cl = (x0 + radius, y1 - radius)
    cr = (x1 - radius, y1 - radius)
    with bd.BuildLine() as outline:
        bd.Polyline((x0, y0), (x1, y0), (x1, cr[1]))
        bd.CenterArc(cr, radius, 0.0, 90.0)
        bd.Line((cr[0], y1), (cl[0], y1))
        bd.CenterArc(cl, radius, 90.0, 90.0)
        bd.Line((x0, cl[1]), (x0, y0))
    return bd.make_face(outline.wire())


def _opening_face(spread, past=1.0):
    """Проём обода. Бока прямые и доходят за переднюю плоскость, зад — дуга рта.

    spread — насколько проём шире рта наружу. 0 на низе фаски, NICHE_FLARE на кромке.
    past — насколько перед уведён за переднюю плоскость, чтобы срез не оставлял плёнку.
    """
    return _front_square_face(
        _MOUTH_X0 - spread,
        _MOUTH_X1 + spread,
        -NICHE_SHELF - past,
        _MOUTH_Y1 + spread,
        NICHE_CORNER_R + spread,
    )


def _outer_face():
    """Наружный план совпадает с кромкой фаски. Плоской площадки снаружи кромки нет."""
    return _opening_face(NICHE_FLARE, past=0.0)


def _niche_body():
    """Корпус ниши до рта кармана: пол, стенки, полка. Фаски на нём нет."""
    outer = bd.Pos(0, 0, -FLOOR) * bd.extrude(_outer_face(), NICHE_MOUTH_Z + FLOOR)
    pocket = bd.loft(
        [_niche_section(0.0), _niche_section(NICHE_MOUTH_Z)],
        ruled=True,
    )
    shelf_h = NICHE_MOUTH_Z - NICHE_FRONT_Z
    # Над полкой пусто до линии касания углов кармана. Иначе снаружи дуги R8
    # остаётся порожек на 3 мм выше полки — его и понижаем до z=62.
    shelf = bd.Pos(_MOUTH_X0, -NICHE_SHELF - 0.05, NICHE_FRONT_Z) * bd.Box(
        NICHE_MOUTH_X,
        NICHE_SHELF + NICHE_CORNER_R + 0.05,
        shelf_h + 0.02,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    )
    part = outer - pocket - shelf
    part.label = "niche"
    part.color = "#3a4048aa"
    return part, pocket, shelf


def _rim():
    """Обод отдельным телом: только фаска 5×4 мм, кромка острая.

    Боковая кромка не следует за углом кармана. Она продолжает боковую грань
    до передней плоскости и там обрывается. На полку фаска не заходит.
    Сверху площадки нет: в оригинале кромка сходится в ребро.
    """
    outer = bd.Pos(0, 0, NICHE_MOUTH_Z) * bd.extrude(_outer_face(), NICHE_FLARE_Z)
    # Выше кромки проём чуть шире неё, чтобы срез снял торец и не оставил
    # горизонтальную площадку. Наклон фаски — только между z=65 и z=69.
    void = bd.loft(
        [
            bd.Pos(0, 0, NICHE_MOUTH_Z - 0.2) * _opening_face(0.0),
            bd.Pos(0, 0, NICHE_MOUTH_Z) * _opening_face(0.0),
            bd.Pos(0, 0, OPEN_Z) * _opening_face(NICHE_FLARE),
            bd.Pos(0, 0, OPEN_Z + 0.3) * _opening_face(NICHE_FLARE + 0.5),
        ],
        ruled=True,
    )
    part = outer - void
    part.label = "rim"
    part.color = "#4e5966"
    return part, void


def _board():
    pcb = bd.Box(23.5, 18.0, 1.6, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN))
    pcb.color = "#0f6b3c"
    usb = bd.Pos(23.5, 5.0, 0) * bd.Box(
        6.0, 8.0, 3.0, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)
    )
    usb.color = "#c5c8ce"
    part = bd.Compound(children=[pcb, usb], label="esp32")
    return part


def _opening_size(niche):
    """Пол кармана и высота до обода — с готового тела, не из констант."""
    upward = [face for face in niche.faces() if face.normal_at().Z > 0.9]
    floor = min(upward, key=lambda face: face.center().Z)
    rim_z = max(face.center().Z for face in upward)
    box = floor.bounding_box().size
    return box.X, box.Y, rim_z - floor.center().Z


def _section_size(part, z, thick=0.05):
    """Внешний размер тела на высоте z — тонким срезом по геометрии."""
    slab = bd.Pos(OPEN_X / 2, OPEN_Y / 2, z) * bd.Box(
        OPEN_X * 2, OPEN_Y * 2, thick
    )
    box = (part & slab).bounding_box().size
    return box.X, box.Y


def _section_box(part, z, thick=0.05):
    """Габарит сечения тела на высоте z."""
    slab = bd.Pos(OPEN_X / 2, OPEN_Y / 2, z) * bd.Box(
        OPEN_X * 2, OPEN_Y * 2, thick
    )
    return (part & slab).bounding_box()


def _pocket_size(part, z, thick=0.05):
    """Стенка кармана у рта по бокам и сзади, без переда: перед уже раскрыт.

    Возвращает ширину сечения и задний край: спереди над полкой стенки нет,
    поэтому габарит по Y меряется по задней стенке.
    """
    slab = bd.Pos(NICHE_CX, NICHE_CY + NICHE_MOUTH_Y / 2, z) * bd.Box(
        NICHE_MOUTH_X * 2, NICHE_MOUTH_Y, thick
    )
    box = (part & slab).bounding_box()
    return box.size.X, box.max.Y


def _left_inner(rim, y, z):
    """Внутренняя кромка левой фаски: правый край левого обода на высоте z."""
    probe = bd.Pos(_MOUTH_X0 - NICHE_FLARE / 2, y, z) * bd.Box(
        NICHE_FLARE + 2, 0.2, 0.05
    )
    hit = rim & probe
    if not hit.solids():
        return None
    return hit.bounding_box().max.X


@model
def niche_panel():
    bottom = deck_bottom()
    niche, pocket, front_air = _niche_body()
    rim, rim_void = _rim()
    air = pocket + front_air

    open_x, open_y, _floor_to_wall = _opening_size(niche)
    # Пол кармана меряется по дну корпуса. Верх обода — отдельное тело.
    assert abs(open_x - NICHE_FLOOR_X) < 0.05, open_x
    assert abs(open_y - NICHE_FLOOR_Y) < 0.05, open_y
    assert abs(niche.bounding_box().max.Z - NICHE_MOUTH_Z) < 0.05
    assert abs(rim.bounding_box().max.Z - OPEN_Z) < 0.05
    assert abs(rim.bounding_box().min.Z - NICHE_MOUTH_Z) < 0.05
    # Плоской площадки сверху нет: у обода не остаётся широкой грани, смотрящей вверх.
    flat_top = [
        face.area
        for face in rim.faces()
        if face.normal_at().Z > 0.9 and face.area > 1.0
    ]
    assert not flat_top, flat_top
    assert abs(niche.bounding_box().min.Y + NICHE_SHELF) < 0.05
    assert abs(rim.bounding_box().min.Y + NICHE_SHELF) < 0.05

    # Дно меряется срезом у самого пола: конус стенок на 0.02 мм не виден.
    floor_x, floor_y = _section_size(pocket, 0.02)
    assert abs(floor_x - NICHE_FLOOR_X) < 0.05, floor_x
    assert abs(floor_y - NICHE_FLOOR_Y) < 0.05, floor_y

    # Сечения по готовой полости: рот кармана, перед под полкой, кромка, колодец.
    mouth_x, mouth_y = _pocket_size(pocket, NICHE_MOUTH_Z, thick=0.02)
    front_x, front_y = _section_size(pocket, NICHE_FRONT_Z - 0.1)
    # Сечение фаски у кромки, целиком ниже z=69: выше проём шире, чтобы снять плоский торец.
    rim_z = OPEN_Z - 0.2
    rim_frac = (rim_z - NICHE_MOUTH_Z) / NICHE_FLARE_Z
    rim_x, rim_y = _pocket_size(rim_void, rim_z, thick=0.02)
    well_x, well_y = _section_size(pocket, bottom)
    assert abs(mouth_x - NICHE_MOUTH_X) < 0.1, mouth_x
    assert abs(mouth_y - NICHE_MOUTH_Y) < 0.1, mouth_y
    # Перед на z=61.9: стенка кармана у рта, конус за 3 мм съедает 0.1 мм.
    assert abs(front_x - NICHE_MOUTH_X) < 0.2, front_x
    # Полка на z=62: сразу над ней перед открыт на её ширину (53.3 + 6).
    above_shelf = _section_size(air, NICHE_FRONT_Z + 0.1)[1]
    assert abs(above_shelf - (NICHE_MOUTH_Y + NICHE_SHELF)) < 0.2, above_shelf
    # Фаска линейная: на этой высоте проём уже на доле раструба. Спереди кромки нет,
    # поэтому по Y меряется задний край.
    assert abs(rim_x - (NICHE_MOUTH_X + 2 * NICHE_FLARE * rim_frac)) < 0.08, rim_x
    assert abs(rim_y - (NICHE_MOUTH_Y + NICHE_FLARE * rim_frac)) < 0.08, rim_y
    # Над полкой проём доходит до передней плоскости на всю ширину рта.
    shelf_box = _section_box(air, NICHE_FRONT_Z + 0.05, thick=0.02)
    assert shelf_box.min.Y < -NICHE_SHELF + 0.1, shelf_box.min.Y
    assert shelf_box.size.X > NICHE_MOUTH_X - 0.2, shelf_box.size.X
    # Середина полки пустая и выше неё: ни корпус, ни обод туда не заходят.
    shelf_probe = bd.Pos(NICHE_CX, -NICHE_SHELF / 2, NICHE_FRONT_Z + 1) * bd.Box(
        NICHE_MOUTH_X - 40, NICHE_SHELF, 2.0
    )
    above = niche & shelf_probe
    above_vol = above.volume if above.solids() else 0.0
    assert above_vol < 0.2, above_vol
    # Уголок снаружи дуги рта не торчит над полкой: сверху он с ней в одной плоскости.
    for side in (_MOUTH_X0, _MOUTH_X1 - NICHE_CORNER_R):
        wedge = niche & bd.Pos(side, 0.0, NICHE_FRONT_Z + 0.4) * bd.Box(
            NICHE_CORNER_R,
            NICHE_CORNER_R,
            NICHE_MOUTH_Z - NICHE_FRONT_Z - 0.6,
            align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
        )
        wedge_vol = wedge.volume if wedge.solids() else 0.0
        assert wedge_vol < 0.05, (side, wedge_vol)
    # Фаска на половине высоты: внутренняя кромка на боку и над полкой — один X.
    # Заворот на полку сдвинул бы кромку к центру.
    flare_z = NICHE_MOUTH_Z + NICHE_FLARE_Z * 0.5
    expect_x = _MOUTH_X0 - NICHE_FLARE * 0.5
    x_side = _left_inner(rim, 24.0, flare_z)
    x_over_shelf = _left_inner(rim, -1.0, flare_z)
    x_at_front = _left_inner(rim, -NICHE_SHELF + 0.4, flare_z)
    assert x_side is not None and x_over_shelf is not None and x_at_front is not None
    assert abs(x_side - expect_x) < 0.2, (x_side, expect_x)
    assert abs(x_over_shelf - x_side) < 0.15, (x_side, x_over_shelf)
    assert abs(x_at_front - x_side) < 0.15, (x_side, x_at_front)
    # На самой полке, между боковыми гранями, обода нет.
    on_shelf = rim & bd.Pos(NICHE_CX, -NICHE_SHELF / 2, flare_z) * bd.Box(
        NICHE_MOUTH_X - 6, NICHE_SHELF - 1, 3
    )
    on_shelf_vol = on_shelf.volume if on_shelf.solids() else 0.0
    assert on_shelf_vol < 0.05, on_shelf_vol

    assembly = bd.Compound(children=[niche, rim], label="niche_panel")
    print(
        f"рот z={NICHE_MOUTH_Z:g}: {mouth_x:.1f}×{mouth_y:.1f} мм, "
        f"перед z={NICHE_FRONT_Z:g}: {front_x:.1f}×{front_y:.1f} + полка {NICHE_SHELF:g}, "
        f"фаска z={rim_z:g}: {rim_x:.1f}×{rim_y:.1f} мм, "
        f"низ колодца z={bottom:.1f}: {well_x:.1f}×{well_y:.1f} мм, "
        f"кромка фаски X {x_side:.2f} на боку и {x_at_front:.2f} у переда; "
        "панель и кейкапы — в face.py и keycaps.py"
    )
    return assembly


if __name__ == "__main__":
    niche_panel()
