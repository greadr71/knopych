# -*- coding: utf-8 -*-
"""Лицо «Кнопыч» — отдельная печатаемая деталь (верхняя половина).

Садится в нишу перед подстаканниками пробкой и поднимается над ободом.
Вся геометрия ниши и компоновки — в niche_panel.py, здесь только пересчёт
высот от обода и колодцы под кейкапы сверху.

  z = 58,7           низ панели: плоский стык с корпусом, ниже — корпус
  z = 65             рот кармана: сечение кармана минус FIT
  z = 65..69         юбка лежит на фаске обода, зазора нет
  z = 63,5..66,0     плита свитчей 1,4 мм, окно 14,0; ниже — выборка 15,6
  z = 66..~78        колодец под кейкап: конус 17,4 у лица → 17,9 у плиты
  z = 69..81,5       стойка заподлицо с кромкой обода
  z = 58,7..71,9     карман 21,0×12,9 под корпус энкодера, открыт снизу
  z = 71,9..80,1     перемычка: втулка Ø7,0 в отверстии Ø7,2 сквозь островок
  z = 79,1..81,5     островок Ø23,2: верх — плоскость лица, печатается от стола
  z = 79,1..79,9     дно канавки Ø28,6×Ø23,2×1,8: кольцо 1,3 и два скоса 45°

Верхняя плоскость наклонена (замер 21.11.2026): над ободом 12,5 слева
(x=−5) и 9,5 справа (x=95) — 3 мм на 100, то есть 1,72°. Плоскость идёт
78,5..81,5; сзади в середине она даёт 11,0, на 0,5 ниже кромки торпедо —
торпедо не параллельно ободу. Кейкапы стоят вертикально (колодцы и стенки
не наклоняются), наклонены только их верха — та же плоскость, на 2,0 выше лица.

Компоновка в плане: крутилка слева, шесть колодцев 2×3 справа, шаг 19,0.
Кейкапы — отдельная деталь, v2/modeling/keycaps.py: 17×17, высота 9,0, верх
выступает на 2,0 над лицом — ступенька между кейкапами и лицом и есть
тактильная карта.
Ход кейкапа одинаков у всех шести: рим опускается до верха плиты своей
колонки, 7,12 (замер по печати) — больше хода MX 4,0, поэтому кейкап не
садится на плиту.
Колодец сужается одной линейной образующей 17,4 у лица → 17,9 у плиты,
уступов нет: фланец свитча 15,6 свободен, кейкап в ходе ничего не зажимает.
Перемычка 1,38 по X в зоне рима и 4,1 по Y у плиты.

Кабель питания (USB-C от ESP) выходит в левом переднем углу, рядом с крутилкой:
вырезка 6,2×4,4 в грани дна у торца губы, открытая спереди и снизу, за ней —
такое же окно в корпусе. Слева от неё ничего не подрезается, ни одна стенка не
двигается: вокруг сплошной материал, потому что слева до первой колонки
21,8 мм, до пилота планки 2,25, а до кармана энкодера 9,05.

Посадка энкодера (ALPS EC11E15244G1, эталон — v2/modeling/encoder.py).
Втулка гладкая Ø7,0×7,0: резьбы и гайки нет, притягивать нечем. Поэтому
корпус 11,7×12,0 входит в карман снизу до передней плоскости 71,9 и держится
прижимной планкой (clamp.py): плоская площадка жмёт бобышку-трещотку Ø8,0
снизу, плита стоит на двух саморезах M3×12 в пилоты панели — клея нет.
Боком корпус центрует отверстие Ø7,2 (0,1 на сторону), от поворота держат
лапки 12,5 в 12,9 кармана (0,2 по Y); по X карман 21,0 — место под паяный
контакт с проводом у выводов, там же корпус упирается в плоский потолок.
Отверстие Ø7,2 идёт сквозь островок Ø23,2 и центрует втулку; верх островка —
плоскость лица. Вокруг — кольцевая канавка Ø28,6×Ø23,2 глубиной 1,8, в неё
заходит юбка ручки. Дно канавки — ответная тень юбки, опущенная на 1,0 ниже:
скос 45° от Ø27,0 на дне до стенки Ø28,6 и такой же скос у островка (его кромка
на 0,6 выше дна), между ними плоское кольцо 1,3. Низ юбки на 0,8 под лицом и
на 1,0 над дном канавки: ход кнопки 0,5 и столько же запаса. Ход проверки 0,8
(даташит 0,5 плюс запас 0,3) обеспечивает полость ручки: у knob_knurl скос
начинается с z=2,0, а не с 1,2, поэтому до островка на этом ходе остаётся 0,55,
а в покое 1,35; до дна канавки 0,1 на r=12,1 — на конце хода ручку держит не
островок, а кольцо дна.

Печать FDM, сопло 0,4 мм, слой 0,2 мм, PETG или ASA. Печатать лицом вниз на
плиту (STL кладёт print_stl.py, сняв наклон лица 1,72°): горизонтальные
потолки — плита над колодцами и плоское кольцо в дне канавки — идут на
поддержки, а оба скоса дна канавки 45° держат себя сами. Островок доходит до
лица и печатается от стола: потолка Ø23,2 над канавкой нет; дыра Ø7,2 проходит
сквозь островок. Раньше здесь
был сплошной мост 21,4 мм (28,6 − 7,2) — дно глухого углубления под ручку,
теперь его нет. Свитч
вставляется сверху: окно 14,0 — только в плите 1,4 мм, ниже неё выборка 15,6,
и защёлка цепляется за низ плиты, а не остаётся сжатой в туннеле. Карман
энкодера открыт вниз, поэтому над ним мост 21,0×12,9 на высоте 13,2 мм —
внутри глухого кармана; энкодер повёрнут в панели на 90° (выводы по ±X),
поэтому по X карман шире, а провода уходят вниз по бокам планки прижима.
Потолок кармана плоский: корпус упирается в него, снизу его держит планка,
а втулку центрует отверстие Ø7,2.
"""

import math

import build123d as bd

import body as body_part
from cad import model
from niche_panel import (
    OPEN_Z,
    NICHE_MOUTH_Z,
    NICHE_FLARE,
    NICHE_SHELF,
    NICHE_FRONT_Z,
    NICHE_MOUTH_X,
    FIT,
    KEYCAP,
    KEYCAP_TOP,
    KEYCAP_H,
    PITCH,
    SWITCH_HOLE,
    SWITCH_BODY,
    SWITCH_H,
    WELL_CLEARANCE,
    KNOB_DIA,
    COLS,
    ROWS,
    deck_bottom,
    button_centers,
    knob_center,
    _niche_body,
    _niche_section,
    _opening_face,
    _rim,
)

# Верх лица — наклонная плоскость, замер 21.11.2026: над кромкой обода
# 12,5 слева (x=−5) и 9,5 справа (x=95), то есть 3 мм на 100 = 1,72°.
# Сзади в середине плоскость даёт 11,0 — на 0,5 ниже кромки торпедо.
TOP_LEFT = 12.5  # над ободом на x=−NICHE_FLARE
TOP_RIGHT = 9.5  # над ободом на x=NICHE_MOUTH_X+NICHE_FLARE
TOP_SLOPE = (TOP_RIGHT - TOP_LEFT) / (NICHE_MOUTH_X + 2 * NICHE_FLARE)  # −0.03


def top_z(x):
    """Верх лица над ободом в точке x: обод z=OPEN_Z плюс наклон по X."""
    return OPEN_Z + TOP_LEFT + TOP_SLOPE * (x + NICHE_FLARE)


# Посадка энкодера. Числа — даташит ALPS EC11E15244G1 (эталон — encoder.py).
ENC_BUSH_D = 7.0  # втулка гладкая, Ø7,0×7,0, резьбы нет
ENC_BUSH_L = 7.0  # от передней плоскости корпуса: целиком в отверстии до островка
ENC_BODY_X = 11.7
ENC_BODY_Y = 12.0
ENC_BODY_T = 4.3  # замер 21.11.2026 (в каталоге 4,5)
ENC_EAR_SPAN = 12.5  # по наружным кромкам лапок
ENC_EAR_T = 4.0  # выступ лапок вниз: замер пользователя, в каталоге не задан
ENC_PIN_OUT = 7.5  # полуразмах рядов выводов по X от оси вала (7,5 и 7,0)
ENC_PIN_D = 1.0  # Ø вывода
# Запас на паяный контакт с проводом сверх вывода: от кромки вывода до стенки
# кармана. 0,2 хватало только голому выводу.
SOLDER_ROOM = 2.5
# Угол установки энкодера в панели, градусы вокруг Z: его ряды выводов (в
# собственной рамке +7,0/−7,5 по Y) смотрят по ±X, поэтому провода идут вниз
# по бокам планки прижима, а не сквозь неё.
ENC_ROT = -90.0
SEAT_FIT = 0.2  # зазор корпуса в кармане на сторону
ENC_BUSH_HOLE = ENC_BUSH_D + 0.2
SEAT_RECESS_D = KNOB_DIA + 0.6  # наружный Ø кольцевой канавки под юбку ручки
SEAT_ISLAND_D = 23.2  # внутренний Ø канавки: островок в центре, верх — лицо
SEAT_RECESS_H = 1.8  # дно канавки под лицом в центре крутилки
SEAT_RING = (SEAT_RECESS_D - SEAT_ISLAND_D) / 2  # 2,7 — кольцо материала в дне
# Дно канавки — не плоскость, а ответная тень юбки ручки (knob_knurl.py и
# knob.py: низ юбки Ø28,2 с фаской 0,6 на z=80,07). Тень опущена на KNOB_SEAT=1,0
# ниже юбки, а не пригнана к ней: ручка нажимная. Скос 45° идёт от r=13,5 на дне
# (Ø27,0 — низ юбки, фаска не доходит до стенки на 0,2) до стенки Ø28,6 на 0,8
# выше; у островка такой же скос 0,6. Плоское дно между ними 1,3.
SEAT_FLOOR_SLOPE_OUT = 0.8
SEAT_FLOOR_SLOPE_IN = 0.6
SEAT_FLOOR_R = SEAT_RECESS_D / 2 - SEAT_FLOOR_SLOPE_OUT  # 13,5 — край плоского дна
ENC_STROKE = 0.5  # ход кнопки энкодера, даташит ALPS EC11E
# Ход проверки: даташитный ход плюс запас 0,3 на печать и на то, что ручку жмут
# до упора. На этом ходе ручка не должна касаться панели нигде.
KNOB_TRAVEL = 0.8
# Низ юбки над дном канавки: ход кнопки плюс запас. 1,0 = 0,5 хода + 0,5 запаса,
# иначе юбка садится на дно ровно на конце хода, без допуска на печать.
KNOB_SEAT = 1.0
# Передняя плоскость корпуса энкодера задана посадкой (дно панели + 13,17) и от
# дна канавки не зависит: карман и упор не менялись.
SEAT_FRONT_Z = 71.87

# Пилоты под планку прижима (clamp.py). Отсчёт от оси вала идёт по Y: по X от
# оси до полости корпуса всего 10,4 мм (поясок корпуса), а саморез с запасом
# 1,5 мм до края плиты требует 14,15 — там планка в корпус не влезает.
CLAMP_SCREW_OFF = 12.0  # ось саморезов от оси вала: до стенки кармана 4,3 материала
CLAMP_PILOT_D = 2.5  # пилот под M3 в PETG
CLAMP_PILOT_H = 10.0  # пилот глубже самореза M3×12 (3 плита + 9 панель) на 1

# Верхняя передняя кромка, выбрана пользователем.
EDGE_R = 3.0

# Защёлки лица: четыре языка свисают с дна панели в полость корпуса и входят
# крючками в сквозные окна его стенок (body.py: CLIP_WIN_*). Верхняя грань
# крючка горизонтальная — положительная полка: она ложится под верхнюю кромку
# окна и держит панель от подъёма. В собранном виде язык прямой, натяга нет;
# снимается нажатием носа крючка внутрь через окно, снаружи остаётся 1,0 мм
# открытого окна под палец.
TONGUE_T = 1.4       # толщина по Y: кантилевер L=16,2 держит δ=1,5 при ε=1,2%
TONGUE_W = 10.0      # ширина ствола по X — он висит в полости, окно шире (10,2)
TONGUE_ROOT_R = 0.8  # галтель корня со стороны полости (снаружи до стенки 0,39)
TONGUE_OUT = 3.5     # передний язык, наружная грань: 0,39 до внутренней грани стенки
REAR_OUT = 49.8      # задний язык, грань к стенке: те же 0,39
HOOK_TOP = body_part.CLIP_WIN_Z1      # опорная грань крючка = верхняя кромка окна
HOOK_T = 2.5         # высота крючка под опорной гранью (z 42,5..40,0)
HOOK_FACE = 0.5      # вертикальная часть носа под опорной гранью
HOOK_ENGAGE = 1.5    # нос входит в стенку от её внутренней грани
# Крючок во всю ширину ствола — 10,0, печатный. Окно корпуса 10,2, боковой люфт
# 0,1 на сторону: ступеньки по бокам нет, крючок и ствол одной ширины.
HOOK_W = 10.0
TONGUE_IN = (TONGUE_OUT + TONGUE_T, REAR_OUT - TONGUE_T)  # 4,9 / 48,4 — корневые рёбра
_HOOK_WALL = _niche_section(HOOK_TOP, FIT + body_part.WALL).bounding_box()
HOOK_NOSE = (_HOOK_WALL.min.Y - HOOK_ENGAGE, _HOOK_WALL.max.Y + HOOK_ENGAGE)

# Маршрут кабеля питания (USB-C от ESP наружу): вырезка в левом переднем углу,
# у крутилки, — в грани дна, которой панель лежит на полке проёма (z=62). Провод
# заходит спереди, в вырезку, и сразу уходит вниз в полость корпуса. Левая грань,
# раструб и верхняя плоскость не режутся. Зеркало прежнего канала 78,6..84,8
# относительно середины панели x=45; ширина и профиль те же.
CABLE_D = 4.0        # Ø кабеля питания
CABLE_W = 6.2        # ширина вырезки по X: кабель 4,0 и 2,2 запаса (как было)
CABLE_H = CABLE_D + 0.4      # высота канала над плоскостью опирания (z=62)
CABLE_EXIT = 6.0     # высота выхода в передней плоскости: 4,4 + пандус 1,6
CABLE_RAMP_Y = 4.0   # пандус потолка кончается здесь (7 мм до торца канала)
CABLE_X0 = 5.2       # зеркало 84,8: от левого края 6,2 — ширина канала
CABLE_X1 = 11.4      # зеркало 78,6
CABLE_Y1 = 11.0      # 17 мм от передней плоскости: место на изгиб; до пилота 2,25

# Плита свитчей: верх — дно колодца и упор фланца, низ — начало окна.
# Высота плиты у каждой колонки своя: она отсчитана от лица вниз на глубину
# колодца, а лицо наклонено. Ход кейкапа и посадка свитча от колонки не зависят.
PLATE_T = 1.4  # проверено на пробнике: 1,2 не защёлкивает свитч, 1,4 держит

# Глубина колодца — самостоятельное число, заданное печатью: дно колодца (верх
# плиты) на 14,12 под лицом, так сходятся зазор до торпедо и ход свитча.
WELL_DEPTH = 14.12
# Посадка кейкапа на свитче, а не глубина колодца. На напечатанной панели верх
# кейкапа выходит ~2,0 над лицом; при глубине 14,12 и кейкапе 9,0 это
# CAP_RIM = 14,12 − 9,0 + 2,0 = 7,12. Больше хода MX 4,0: иначе кейкап садится
# на плиту раньше, чем свитч дойдёт до своего упора.
CAP_RIM = 7.12
# Верх кейкапа над лицом — следствие посадки, а не наоборот. RECESS = −2,0:
# keycaps.py ставит рим на top_z(x) − KEYCAP_H − RECESS, и верх кейкапа
# оказывается на 2,0 выше лица; ступенька между кейкапами и лицом и есть
# тактильная карта.
RECESS = WELL_DEPTH - CAP_RIM - KEYCAP_H


def plate_top(x):
    """Верх плиты свитчей в колонке x: дно колодца и упор фланца."""
    return top_z(x) - WELL_DEPTH


def plate_bottom(x):
    """Низ плиты: здесь начинается окно под свитч."""
    return plate_top(x) - PLATE_T


# Колодец под кейкап: 17,0 + 0,2 на сторону; кейкап прямой, колодец тоже.
WELL = KEYCAP + 2 * WELL_CLEARANCE
WELL_R = 2.0 + WELL_CLEARANCE
# Окно свитча: скругление только чтобы сопло не втыкалось в острый угол.
WINDOW_R = 0.3


def well_width(x, z):
    """Ширина колодца в колонке x на высоте z: конус 17,4 у рта → 17,9 у плиты.

    От 0,5 под лицом (там кончается фаска рта) до верха плиты — одна линейная
    образующая, уступа внутри колодца нет.
    """
    depth = top_z(x) - 0.5 - z
    return WELL + 0.5 * depth / (top_z(x) - 0.5 - plate_top(x))


# Прямые кейкапы 17,0 в колодце 17,4: у лица перемычка 1,6 по X, в зоне рима
# 1,38 — колодец книзу шире, но перемычки хватает. Ряды раздвинуты на 3 мм:
# 5,0 между кейкапами (22,0 − 17,0) и 4,1 между стенками колодцев у плиты.
ROW_PITCH = PITCH + 3.0

# Перед панели обрывается на передней плоскости, на полку не заходит.
FRONT = _opening_face(NICHE_FLARE, past=0.0)


def face_centers():
    """Столбцы как у прототипа. Ряды раздвинуты на ROW_PITCH, блок по центру.

    Ряд 0 — меньший Y, к полке. Ряд 1 — больший Y, к скруглённому ободу.
    """
    seed = button_centers()
    xs = [point[0] for point in seed[:COLS]]
    ys = sorted({point[1] for point in seed})
    mid = (ys[0] + ys[-1]) / 2
    rows = (mid - ROW_PITCH / 2, mid + ROW_PITCH / 2)
    return [(x, rows[row]) for row in range(ROWS) for x in xs]


def _plug():
    """Низ панели: сечение кармана минус FIT от стыка с корпусом до рта."""
    return bd.loft(
        [
            _niche_section(deck_bottom(), FIT),
            _niche_section(NICHE_MOUTH_Z, FIT),
        ],
        ruled=True,
    )


def _skirt():
    """Пробка в раструбе: наружная поверхность совпадает с фаской обода.

    Зазора нет: панель ложится на фаску всей поверхностью и центруется ею.
    """
    return bd.loft(
        [
            bd.Pos(0, 0, NICHE_MOUTH_Z) * _opening_face(0.0, past=0.0),
            bd.Pos(0, 0, OPEN_Z) * _opening_face(NICHE_FLARE, past=0.0),
        ],
        ruled=True,
    )


def _deck():
    """Стойка от обода до наклонной плоскости, заподлицо с наружной стенкой.

    Выдавлена до высокого (левого) края, верх срезан плоскостью top_z(x).
    """
    body = bd.Pos(0, 0, OPEN_Z) * bd.extrude(FRONT, top_z(-NICHE_FLARE) - OPEN_Z)
    # Нижняя грань бокса после Rot(0, beta, 0) идёт как z = const − x·tan(beta).
    beta = -math.degrees(math.atan(TOP_SLOPE))
    cutter = bd.Pos(0, 0, top_z(0.0)) * bd.Rot(0, beta, 0) * bd.Box(
        400, 400, 100, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    return body - cutter


def _front_lip():
    """Передняя губа на полку: продолжение передней стенки на 3 мм вниз.

    Низ ровно на полке (z=62, контакт), бока — в зазор до стенок полки.
    Вырез полки в нише — ровно x 0..90, поэтому 0.2 с каждой стороны.
    Зад заходит в пробку на 1,5 мм: передняя плоскость пробки отступает на FIT
    и с уклоном, поэтому губа до y=0,5 касалась бы её только у рта — щель
    до 0,05 мм и губа висела бы на одном ребре.
    """
    lip_gap = 0.2
    return bd.Pos(lip_gap, -NICHE_SHELF, NICHE_FRONT_Z) * bd.Box(
        NICHE_MOUTH_X - 2 * lip_gap,
        NICHE_SHELF + 2.0,
        4.0,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    )


def _wells(part):
    """Шесть колодцев под кейкапы и шесть окон под свитчи.

    Колодцы прямые в плане: гнёзда под свитчи не наклоняются. Рот срезается
    наклонной плоскостью лица, поэтому фаска 0,5×45° по его кромке режется в
    той же наклонной системе, что и лицо, — иначе кромка рваная. От 17,4 на
    0,5 под лицом колодец сужается одной линейной образующей до 17,9 у верха
    плиты: уступа внутри нет, поэтому кейкап в ходе ничего не зажимает.
    Плита закрывает колодец на своей высоте у каждой колонки: её верх — дно
    колодца и упор фланца, окно 14,0 — только в её толщине 1,4; ниже плиты
    выборка 15,6 (по фланцу): защёлка свитча раскрывается под плитой и
    цепляется за её низ, а не остаётся сжатой в туннеле 14,0.
    """
    beta = -math.degrees(math.atan(TOP_SLOPE))
    for x, y in face_centers():
        frame = bd.Pos(x, y, top_z(x)) * bd.Rot(0, beta, 0)
        # Рот: фаска 18,4 → 17,4 за 0,5 вниз, выше лица продолжена, чтобы
        # снять плёнку наклонного среза.
        # Рот и колодец — одна выемка, а не две: фаска рта 18,4 → 17,4 за 0,5
        # вниз переходит в конус колодца 17,4 → 17,9 у плиты без стыка. Две
        # отдельные выемки сходились крышками в одной плоскости на 0,5 под
        # лицом, и булева операция оставляла на этом стыке рваные копланарные
        # грани — 56 рёбер, использованных один раз (STL был не сшит).
        well = bd.loft(
            [
                frame
                * bd.Plane.XY.offset(0.6)
                * bd.RectangleRounded(WELL + 2 * 1.1, WELL + 2 * 1.1, WELL_R),
                frame
                * bd.Plane.XY
                * bd.RectangleRounded(WELL + 1.0, WELL + 1.0, WELL_R),
                frame
                * bd.Plane.XY.offset(-0.5)
                * bd.RectangleRounded(WELL, WELL, WELL_R),
                bd.Pos(x, y, plate_top(x))
                * bd.RectangleRounded(
                    well_width(x, plate_top(x)), well_width(x, plate_top(x)), WELL_R
                ),
            ],
            ruled=True,
        )
        window = bd.Pos(x, y, plate_bottom(x)) * bd.extrude(
            bd.Plane.XY * bd.RectangleRounded(SWITCH_HOLE, SWITCH_HOLE, WINDOW_R),
            PLATE_T + 0.2,
        )
        relief = bd.Pos(x, y, deck_bottom() - 0.2) * bd.extrude(
            bd.Plane.XY * bd.RectangleRounded(SWITCH_BODY, SWITCH_BODY, WINDOW_R),
            plate_bottom(x) - deck_bottom() + 0.2,
        )
        part = part - well - window - relief
    return part


def knob_face_z():
    """Верх лица над центром крутилки."""
    return top_z(knob_center()[0])


def recess_floor_z():
    """Дно кольцевой канавки под юбку ручки: лицо над крутилкой минус 1,4."""
    return knob_face_z() - SEAT_RECESS_H


def knob_bottom_z():
    """Низ ручки: на 1,0 над дном канавки — ход кнопки 0,5 и запас 0,5."""
    return recess_floor_z() + KNOB_SEAT


def seat_front_z():
    """Передняя плоскость корпуса энкодера: от неё втулка идёт вверх на 7,0."""
    return SEAT_FRONT_Z


def _knob_seat(part):
    """Посадка энкодера: кольцевая канавка под юбку, отверстие, карман.

    Канавка Ø28,6×Ø23,2 глубиной 1,8: кольцо шириной 2,7 прячет юбку ручки.
    Дно — не плоскость, а тень низа юбки на 1,0 ниже (юбка нажимная): скос 45°
    от r=13,5 на дне до стенки 14,3 на 0,8 выше, плоское кольцо 1,3 и скос 0,6
    к островку. Внутренняя стенка выше скоса вертикальная, островок Ø23,2
    доходит до плоскости лица — потолка над канавкой нет, поэтому и моста
    через всё дно нет, а сам островок печатается от стола. Отверстие
    Ø7,2 идёт от передней плоскости 71,9 вверх сквозь островок: втулка 7,0
    целиком в нём, стены вокруг дыры (23,2 − 7,2)/2 = 8,0. Карман под корпус
    открыт снизу прямым 21,0×12,9 на всю глубину: по Y лапки 12,5 держат корпус
    от поворота (0,2 на сторону), по X 21,0 — место под паяный контакт с
    проводом у выводов (запас 2,5 сверх Ø1,0). Потолок — плоскость передней
    плоскости 71,9, в неё корпус упирается, а снизу его прижимает планка
    (clamp.py); клея нет, по X корпус держит отверстие Ø7,2 (0,1 на сторону).
    По бокам кармана, на ky±12, — два глухих пилота Ø2,5×10 под саморезы планки
    прижима: между пилотом и стенкой кармана остаётся 4,3 мм материала.
    """
    x, y = knob_center()
    floor = recess_floor_z()
    front = seat_front_z()
    # Режем обе стенки канавки от дна до лица и выше (лицо наклонено): островок
    # получается сам, из материала перемычки. Профиль вращения: скос 45° от
    # r=13,5 на дне до стенки 14,3 на 0,8 выше, плоское дно 1,3, скос 45° 0,6
    # к островку. Так дно — тень юбки (вертикальный зазор 1,0 по скосу), и в
    # печати лицом вниз нависание в канавке 45°, а не горизонтальное кольцо.
    top = knob_face_z() - floor + 2.0
    groove = bd.Pos(x, y, floor) * bd.revolve(
        bd.Plane.XZ
        * bd.Polygon(
            (SEAT_ISLAND_D / 2, SEAT_FLOOR_SLOPE_IN),
            (SEAT_ISLAND_D / 2 + SEAT_FLOOR_SLOPE_IN, 0.0),
            (SEAT_FLOOR_R, 0.0),
            (SEAT_RECESS_D / 2, SEAT_FLOOR_SLOPE_OUT),
            (SEAT_RECESS_D / 2, top),
            (SEAT_ISLAND_D / 2, top),
            align=None,
        ),
        axis=bd.Axis.Z,
    )
    # Верх островка не режем: он — плоскость лица (наклонная), и в печати
    # лицом вниз островок стоит от стола, потолка над канавкой нет.
    bush = bd.Pos(x, y, front) * bd.Cylinder(
        ENC_BUSH_HOLE / 2,
        knob_face_z() - front + 2.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Карман — один прямой вырез на всю глубину: внизу место под паяный контакт
    # и провод, он же служит посадкой корпуса; потолок режется в плоскость
    # передней плоскости, с запасом 0,2 вверх.
    pocket_z0 = deck_bottom() - 0.2
    pocket = bd.Pos(x, y, pocket_z0) * bd.Box(
        2 * (ENC_PIN_OUT + ENC_PIN_D / 2 + SOLDER_ROOM),
        ENC_EAR_SPAN + 2 * SEAT_FIT,
        front + 0.2 - pocket_z0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    pilots = [
        bd.Pos(x, y + side * CLAMP_SCREW_OFF, deck_bottom())
        * bd.Cylinder(
            CLAMP_PILOT_D / 2,
            CLAMP_PILOT_H,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        for side in (-1, 1)
    ]
    return part - groove - bush - pocket - pilots[0] - pilots[1]


def _cable_notch(part):
    """Вырезка кабеля в левом переднем углу — в грани дна у торца губы.

    Зеркало прежней правой вырезки: тот же профиль потолка и ширина 6,2, только
    x 5,2..11,4. Слева рядом нет ни выборки под плитой (первая колонка начинается
    на x=33,2), ни колодца, поэтому карман простой: вокруг сплошной материал,
    стенку к соседней выборке снимать нечем и не нужно.

    Губа лежит на полке проёма на z=62; вырезка поднимает эту грань в углу и
    открыта спереди, поэтому провод заходит с передней стороны. За губой
    (y>0,5) дно уже на 58,7 — вырезка идёт до него, и дальше вниз, в полость,
    её продолжает такое же окно в корпусе.

    Выход в передней плоскости 6,0, дальше потолок идёт прямым пандусом
    (~9°) до 4,4 на y=CABLE_RAMP_Y, дальше до торца y=CABLE_Y1 — плоско.
    От передней плоскости до торца 17 мм — место на изгиб провода вниз.
    """
    slope = (CABLE_EXIT - CABLE_H) / (CABLE_RAMP_Y + NICHE_SHELF)
    pts = [
        (-NICHE_SHELF - 1.2, deck_bottom() - 0.1),
        (CABLE_Y1, deck_bottom() - 0.1),
        (CABLE_Y1, NICHE_FRONT_Z + CABLE_H),
        (CABLE_RAMP_Y, NICHE_FRONT_Z + CABLE_H),
        (-NICHE_SHELF - 1.2, NICHE_FRONT_Z + CABLE_EXIT + 1.2 * slope),
    ]
    profile = bd.Plane.YZ.offset(CABLE_X0) * bd.Polygon(*pts, align=None)
    return part - bd.extrude(profile, CABLE_X1 - CABLE_X0)


def _tongues(part):
    """Четыре языка с крючками — свисают с дна панели в полость корпуса.

    Профиль в YZ, выдавлен по X: ствол TONGUE_W вниз от стыка 58,7 до опорной
    грани HOOK_TOP, под ней крючок HOOK_W (той же ширины, что ствол), вертикальный
    нос HOOK_FACE и заход снизу-снаружи на HOOK_T−HOOK_FACE (38,8° от вертикали) —
    он скользит по внутренней грани стенки при сборке и отводит язык внутрь, пока
    крючок не дойдёт до окна. Ниже захода язык не выступает: снаружи остаётся
    1,0 мм открытого окна. Язык прямой, натяга нет.
    """
    z0 = deck_bottom()
    for x in body_part.CLIP_WIN_X:
        for front in (True, False):
            out = TONGUE_OUT if front else REAR_OUT
            nose = HOOK_NOSE[0] if front else HOOK_NOSE[1]
            inner = out + (TONGUE_T if front else -TONGUE_T)  # грань к полости
            # Ствол — прямоугольник до стыка; крючок под ним уже ствола.
            part = part + bd.Pos(x - TONGUE_W / 2, min(out, inner), HOOK_TOP) * bd.Box(
                TONGUE_W, TONGUE_T, z0 - HOOK_TOP, align=(bd.Align.MIN,) * 3
            )
            hook = [
                (out, HOOK_TOP),
                (nose, HOOK_TOP),
                (nose, HOOK_TOP - HOOK_FACE),
                (out, HOOK_TOP - HOOK_T),
                (inner, HOOK_TOP - HOOK_T),
                (inner, HOOK_TOP),
            ]
            part = part + bd.Pos(x - HOOK_W / 2, 0, 0) * bd.extrude(
                bd.Plane.YZ * bd.Polygon(*hook, align=None), HOOK_W, dir=(1, 0, 0)
            )
    return part


def _top_front_edges(part, min_len=50.0):
    """Прямые рёбра вдоль X на стыке верхней плоскости и переда (y=−6)."""
    return [
        edge
        for edge in part.edges()
        if abs(edge.center().Y + NICHE_SHELF) < 0.01
        and abs(edge.center().Z - top_z(edge.center().X)) < 0.01
        and abs(edge.tangent_at(0.5).X) > 0.9
        and edge.length > min_len
    ]


def _section_x(part, z, thick=0.1):
    """Габарит сечения по X на высоте z — тонким срезом по геометрии."""
    slab = bd.Pos(45.0, 26.0, z) * bd.Box(400, 400, thick)
    return (part & slab).bounding_box().size.X


def _top_at(part, x, y, top):
    """Верх материала в тонкой колонке от низа до высоты top."""
    column = part & bd.Pos(x, y, top / 2) * bd.Box(0.2, 0.2, top)
    return column.bounding_box().max.Z


def _void_x(part, x, y, z, probe=17.9):
    """Ширина пустоты в колодце на высоте z; срез у́же перемычки, чтобы не задеть сосед."""
    slab = bd.Pos(x, y, z) * bd.Box(probe, 0.2, 0.1)
    return (slab - (part & slab)).bounding_box().size.X


def _island_dia(part, x, y, z, probe=40.0):
    """Ø островка между пустотами среза (внутренний Ø кольцевой канавки).

    Пустот в срезе три: две дуги канавки и дыра под втулку — берём крайние.
    """
    slab = bd.Pos(x, y, z) * bd.Box(probe, 0.2, 0.1)
    lobes = sorted((slab - (part & slab)).solids(), key=lambda solid: solid.center().X)
    assert len(lobes) >= 2, len(lobes)
    return lobes[-1].bounding_box().min.X - lobes[0].bounding_box().max.X


def _void_y(part, x, y, z, probe=17.9):
    """Глубина пустоты в колодце на высоте z; срез у́же перемычки, чтобы не задеть сосед."""
    slab = bd.Pos(x, y, z) * bd.Box(0.2, probe, 0.1)
    return (slab - (part & slab)).bounding_box().size.Y


@model
def face():
    bottom = deck_bottom()
    part = _plug() + _skirt() + _deck() + _front_lip()
    part = _knob_seat(_wells(part))
    part = _cable_notch(part)
    part = _tongues(part)
    # Галтель корня языка — по грани к полости: там ребро входящее (материал
    # добавляется), а снаружи язык стоит в 0,39 от стенки, галтели там нет.
    root = [
        edge
        for edge in part.edges()
        if abs(edge.center().Z - bottom) < 0.01
        and min(abs(edge.center().Y - y) for y in TONGUE_IN) < 0.01
        and abs(edge.tangent_at(0.5).X) > 0.9
    ]
    assert len(root) == 4, len(root)
    part = bd.fillet(root, TONGUE_ROOT_R)
    # Скругление верхней передней кромки: только снимает материал.
    volume_before = part.volume
    front = _top_front_edges(part)
    assert len(front) == 1, [edge.length for edge in front]
    part = bd.fillet(front, EDGE_R)
    part.label = "face"
    part.color = "#4a5160"

    box = part.bounding_box()
    # 1. На ободе панель занимает план кромки обода — ступеньки наружу нет.
    edge_x = _section_x(part, OPEN_Z)
    assert abs(edge_x - FRONT.bounding_box().size.X) < 0.1, edge_x
    # 2. В раструбе юбка идёт ровно по фаске: зазор 0, не FIT.
    z_skirt = NICHE_MOUTH_Z + 1.0
    frac = (z_skirt - NICHE_MOUTH_Z) / (OPEN_Z - NICHE_MOUTH_Z)
    flare_x = _opening_face(NICHE_FLARE * frac).bounding_box().size.X
    skirt_x = _section_x(part, z_skirt, thick=0.02)
    skirt_gap = (flare_x - skirt_x) / 2
    assert abs(skirt_gap) < 0.05, skirt_gap
    # 3. Стык ровно на z=58,7 (ниже уходят только языки защёлок), верх —
    #    наклонная плоскость. Мерим её в трёх точках (слева, справа, в середине
    #    сзади): это ловит и наклон, и его направление, а не повторяет константы.
    mate_z = (
        part & bd.Pos(45.0, 26.0, bottom) * bd.Box(0.2, 0.2, 4.0)
    ).bounding_box().min.Z
    assert abs(mate_z - bottom) < 0.01, mate_z
    assert abs(box.max.Z - top_z(box.min.X)) < 0.01, box.max.Z
    face_left = _top_at(part, -4.8, 26.0, top_z(0) + 2)
    face_right = _top_at(part, 94.8, 20.0, top_z(94.8) + 2)  # y=20: 26,5 — угловая выборка
    face_mid = _top_at(part, 45.0, 52.0, top_z(45.0) + 2)
    assert abs(face_left - top_z(-4.8)) < 0.01, face_left
    assert abs(face_right - top_z(94.8)) < 0.01, face_right
    assert abs(face_mid - top_z(45.0)) < 0.01, face_mid
    # 4. Плита свитчей: у каждой колонки свой верх — на WELL_DEPTH под лицом,
    #    дно колодца — верх плиты, окно 14,0 сквозь неё.
    #    Колонка — в кольце плиты между окном (7,0 от центра) и стенкой колодца.
    centers = face_centers()
    x, y = centers[0]
    #    Верх плиты — числа печати (деталь уже напечатана): 64,86 / 65,43 / 66,00.
    tops = sorted(plate_top(cx) for cx, _ in centers[:COLS])
    assert all(abs(a - b) < 0.01 for a, b in zip(tops, (64.86, 65.43, 66.00))), tops
    wells, mouths, strokes, floors, tapers = [], [], [], [], []
    window_gaps, relief_gaps, switch_clashes = [], [], []
    for cx, cy in centers:
        p_top = plate_top(cx)
        p_bottom = plate_bottom(cx)
        rim = top_z(cx) - KEYCAP_H - RECESS
        ring_x = cx + (SWITCH_HOLE + WELL) / 4
        floor = _top_at(part, ring_x, cy, p_top + 1)
        floors.append(floor)
        assert abs(floor - p_top) < 0.05, (cx, floor, p_top)
        #    Глубина колодца от лица до дна — WELL_DEPTH = 14,12 у всех шести.
        assert abs(top_z(cx) - floor - WELL_DEPTH) <= 0.01, (cx, top_z(cx) - floor)
        plate = part & bd.Pos(ring_x, cy, p_top - PLATE_T / 2) * bd.Box(
            0.2, 0.2, PLATE_T
        )
        assert abs(plate.bounding_box().size.Z - PLATE_T) < 0.05, (
            cx,
            plate.bounding_box().size.Z,
        )
        #    Окно: в центре кнопки пусто, в 7,3 от центра — материал.
        assert not (
            part & bd.Pos(cx, cy, p_bottom + 0.7) * bd.Box(4, 4, 0.1)
        ).solids()
        assert (part & bd.Pos(cx + 7.3, cy, p_bottom + 0.7) * bd.Box(0.2, 0.2, 0.1)).solids()
        window_gaps.append(_void_x(part, cx, cy, p_bottom + 0.7))
        #    Под плитой окно шире — по фланцу 15,6: защёлке есть куда раскрыться,
        #    а её крючок цепляется за низ плиты (перепад 15,6 → 14,0).
        relief_gaps.append(_void_x(part, cx, cy, p_bottom - 0.2))
        #    Корпус свитча 15,6×15,6 идёт от плиты вниз на 11,0 (низ =
        #    plate_bottom − SWITCH_H): материала лица в этом объёме нет, иначе
        #    свитч упрётся в панель, а не сядет фланцем на плиту. Углы пробы
        #    R0,3, как у самой выборки (радиус сопла): квадратный угол цепляет
        #    это скругление и даёт ложные 0,7 мм³.
        switch_box = bd.Pos(cx, cy, p_bottom - SWITCH_H) * bd.extrude(
            bd.Plane.XY * bd.RectangleRounded(SWITCH_BODY, SWITCH_BODY, WINDOW_R),
            SWITCH_H,
        )
        switch_clashes.append((part & switch_box).volume)
        assert abs(_void_x(part, cx, cy, p_bottom + 0.2) - SWITCH_HOLE) < 0.05
        #    Колодец — конус: 17,4 на 0,5 под лицом, 17,9 у верха плиты. Ширину
        #    меряем на трёх глубинах, каждая обязана совпасть с well_width.
        tapers.append(
            (
                cx,
                *(_void_y(part, cx, cy, top_z(cx) - d, probe=18.3) for d in (1.0, 6.0)),
                _void_x(part, cx, cy, top_z(cx) - 13.0, probe=18.3),
            )
        )
        #    Рим (7,0 под лицом): по нему считается перемычка.
        wells.append(_void_y(part, cx, cy, rim, probe=18.3))
        #    Рот: на 0,25 под лицом стенка шире колодца — фаска 0,5×45° есть,
        #    тупого угла 90° по кромке не осталось.
        mouths.append(_void_y(part, cx, cy, top_z(cx) - 0.25, probe=18.3))
        #    Ход кейкапа — от рима до верха плиты, у всех шести CAP_RIM.
        strokes.append(rim - floor)
    for window_gap in window_gaps:
        assert abs(window_gap - SWITCH_HOLE) < 0.05, window_gap
    for relief_gap in relief_gaps:
        assert abs(relief_gap - SWITCH_BODY) < 0.05, relief_gap
    #    Ни один из шести колодцев не перекрывает объём корпуса свитча.
    assert max(switch_clashes) < 1e-6, switch_clashes
    for cx, w1, w6, w13 in tapers:
        assert abs(w1 - well_width(cx, top_z(cx) - 1.0)) < 0.05, (cx, w1)
        assert abs(w6 - well_width(cx, top_z(cx) - 6.0)) < 0.05, (cx, w6)
        assert abs(w13 - well_width(cx, top_z(cx) - 13.0)) < 0.05, (cx, w13)
        #    Уступа нет: с глубиной колодец только расширяется.
        assert w1 < w6 and w6 < w13, (cx, w1, w6, w13)
        assert w6 - w1 > 0.1 and w13 - w6 > 0.1, (cx, w1, w6, w13)
    for (cx, _), width in zip(centers, wells):
        assert abs(width - well_width(cx, top_z(cx) - KEYCAP_H - RECESS)) < 0.05, (
            cx,
            width,
        )
    for mouth in mouths:
        assert abs(mouth - WELL - 0.5) < 0.2, mouth
    for stroke in strokes:
        assert abs(stroke - CAP_RIM) <= 0.01, stroke
    #    Перемычка между выборками остаётся стенкой > 3 мм.
    assert PITCH - SWITCH_BODY > 3.0, PITCH - SWITCH_BODY
    #    Перемычка по X в зоне рима: 19,0 − 17,62 = 1,38.
    well_z = top_z(x) - KEYCAP_H - RECESS
    bridge = part & bd.Pos(x + PITCH / 2, y, well_z) * bd.Box(PITCH, 0.2, 0.1)
    bridge_w = bridge.bounding_box().size.X
    assert abs(bridge_w - (PITCH - well_width(x, well_z))) < 0.05, bridge_w
    #    По Y шире: шаг между рядами 22,0.
    y_next = centers[COLS][1]
    bridge_y = part & bd.Pos(x, (y + y_next) / 2, well_z) * bd.Box(0.2, ROW_PITCH, 0.1)
    assert bridge_y.bounding_box().size.Y > 1.4, bridge_y.bounding_box().size.Y
    # 5. Посадка энкодера: кольцевая канавка Ø28,6×Ø23,2 под юбку ручки,
    #    островок Ø23,2 до лица с отверстием Ø7,2, карман 21,0×12,9.
    kx, ky = knob_center()
    seat_floor = recess_floor_z()
    enc_front = seat_front_z()
    ring_probe = (SEAT_RECESS_D + SEAT_ISLAND_D) / 4  # 13,0: середина кольца
    #    Стенки канавки вертикальны выше верхнего края внешнего скоса (79,87) до
    #    лица: проба на 1,0 над дном, ниже лица над ней (80,48 на r=13).
    wall_z = seat_floor + 1.0
    recess_dia = _void_x(part, kx, ky, wall_z, probe=40.0)
    island_dia = _island_dia(part, kx, ky, wall_z)
    assert abs(recess_dia - SEAT_RECESS_D) < 0.05, recess_dia
    assert abs(island_dia - SEAT_ISLAND_D) < 0.05, island_dia
    #    Дно канавки — плоское кольцо между двумя скосами 45°: столбик в
    #    середине кольца упирается в дно, на 0,4 от края скоса — уже 0,4 над
    #    дном, у островка скос 0,6 поднимается так же.
    assert abs(_top_at(part, kx + ring_probe, ky, knob_face_z() + 2.0) - seat_floor) < 0.02

    def rise(r):
        """Верх материала в столбике на радиусе r от оси крутилки."""
        return _top_at(part, kx + r, ky, knob_face_z() + 2.0) - seat_floor

    #    Оба скоса — 45°: на 0,4 ближе к оси поверхность ниже ровно на 0,4.
    assert abs(rise(14.0) - rise(13.6) - 0.4) < 0.06, rise(14.0) - rise(13.6)
    assert abs(rise(11.9) - rise(12.3) - 0.4) < 0.06, rise(11.9) - rise(12.3)
    seat_flat = SEAT_FLOOR_R - (SEAT_ISLAND_D / 2 + SEAT_FLOOR_SLOPE_IN)
    assert seat_flat >= 0.4, seat_flat
    #    (г) Островок стоит до лица: его верх — та же наклонная плоскость лица
    #    (1,72°), не срез и не потолок. Проверяем в четырёх точках по ходу
    #    наклона и весь островок разом: выше локального лица материала нет, и
    #    внутри Ø24,2 (внутренний Ø юбки ручки) тоже.
    island_recess = [
        _top_at(part, kx + dx, ky, knob_face_z() + 2.0) - top_z(kx + dx)
        for dx in (-SEAT_ISLAND_D / 2 + 0.2, -4.5, 4.5, SEAT_ISLAND_D / 2 - 0.2)
    ]
    assert max(abs(g) for g in island_recess) < 0.01, island_recess
    island_box = (
        part & bd.Pos(kx, ky, seat_floor) * bd.Cylinder(SEAT_ISLAND_D / 2, 6.0)
    ).bounding_box()
    #    Самый высокий край островка — левый, по наклону лица.
    assert abs(island_box.max.Z - top_z(kx - SEAT_ISLAND_D / 2)) < 0.01, island_box.max.Z
    inside_max = (
        part & bd.Pos(kx, ky, seat_floor) * bd.Cylinder(SEAT_ISLAND_D / 2 + 0.5, 6.0)
    ).bounding_box().max.Z
    assert inside_max <= top_z(kx - SEAT_ISLAND_D / 2), (
        inside_max,
        top_z(kx - SEAT_ISLAND_D / 2),
    )
    #    Кольцо канавки 2,7 мм и стена островка вокруг дыры ≥ 5 мм.
    assert abs(SEAT_RING - 2.7) < 1e-6, SEAT_RING
    assert (SEAT_ISLAND_D - ENC_BUSH_HOLE) / 2 >= 5.0, SEAT_ISLAND_D
    #    Дно канавки выше плоскости упора на всю втулку: она целиком в дыре и
    #    её торец на 2,0 ниже лица в центре — из гнезда не торчит.
    assert seat_floor > enc_front + ENC_BUSH_L, (seat_floor, enc_front)
    assert knob_face_z() - (enc_front + ENC_BUSH_L) >= 1.0, enc_front + ENC_BUSH_L
    #    Низ юбки спрятан под лицом и стоит на 1,0 над дном — кнопке нужен
    #    ход 0,5, значит запас на печать 0,5.
    assert KNOB_SEAT - ENC_STROKE >= 0.4, (KNOB_SEAT, ENC_STROKE)
    assert knob_face_z() - knob_bottom_z() > 0.4, knob_bottom_z()
    #    Зазор по вертикали в самом узком месте канавки: под внутренней кромкой
    #    юбки (r=12,1) скос островка поднят на 0,1 над дном, до низа юбки 0,9.
    #    Порог 0,8: даташитный ход кнопки 0,5 (ENC_STROKE) плюс запас 0,3.
    narrow = knob_bottom_z() - _top_at(part, kx + 12.2, ky, knob_face_z())
    assert narrow >= 0.8, narrow
    #    Ручка, опущенная на ход проверки 0,8 (даташит 0,5 плюс запас 0,3), не
    #    пересекает панель ни в одной точке. Тело ручки берём настоящее
    #    (knob_knurl.py — её и печатаем), не копию; импорт локальный —
    #    knob_knurl.py сам импортирует face.py.
    from knob_knurl import knob_knurl as knob_shape

    knob_rest = (
        bd.Pos(kx, ky, knob_bottom_z())
        * bd.Rot(0, 0, ENC_ROT)
        * knob_shape.__wrapped__()
    )
    knob_down = bd.Pos(0, 0, -KNOB_TRAVEL) * knob_rest
    knob_clash = (knob_down & part).volume
    assert knob_clash < 1e-6, knob_clash
    knob_box = knob_rest.bounding_box()

    def clearance(r, deg=0.0, wide=0.1, shape=None):
        """Вертикальный зазор в колонке на радиусе r: низ ручки минус верх панели.

        Колонка узкая: в широкой смешались бы два радиуса, и зазор вышел бы не
        тот — у самой стенки ручки (r=12,1) панель и ручка начинаются с разных
        сторон этого радиуса.
        """
        px = kx + r * math.cos(math.radians(deg))
        py = ky + r * math.sin(math.radians(deg))
        column = bd.Pos(px, py, 70.0) * bd.Box(wide, wide, 40.0)
        return ((shape or knob_down) & column).bounding_box().min.Z - (
            part & column
        ).bounding_box().max.Z

    #    До островка на этом ходе не меньше 0,3: его верх — низкая плоскость, а
    #    низ ручки в кольце островка — скос с r=12,1, поэтому зазор одинаков по
    #    всему кругу (самый узкий у края островка, r=11,6).
    r_edge = SEAT_ISLAND_D / 2 - 0.05
    island_gaps = [clearance(r_edge, deg) for deg in (0, 90, 180, 270)]
    assert min(island_gaps) >= 0.3, min(island_gaps)
    #    В покое до островка на ход больше: 0,8 + 0,9.
    rest_gaps = [clearance(r_edge, deg, shape=knob_rest) for deg in (0, 90, 180, 270)]
    assert min(rest_gaps) >= KNOB_TRAVEL + 0.3, min(rest_gaps)
    #    До дна канавки остаётся 0,1 — на кольце дна у внутреннего скоса (r=12,1),
    #    где дно на 0,1 выше плоского кольца. Это не островок и не правка
    #    островка: юбку от дна отделяет KNOB_SEAT=1,0, и на даташитном ходе 0,5
    #    запас там 0,6. Порог 0,05 — чтобы ловить не касание, а поломку посадки.
    groove_gaps = [clearance(r, wide=0.02) for r in (12.11, 12.2, 12.6, 13.4, 13.9)]
    assert min(groove_gaps) >= 0.05, min(groove_gaps)
    #    Втулка: пусто Ø7,2 сквозь островок, материал в 4,5 от оси.
    bush_dia = _void_x(part, kx, ky, (enc_front + seat_floor) / 2, probe=20.0)
    assert abs(bush_dia - ENC_BUSH_HOLE) < 0.05, bush_dia
    assert (part & bd.Pos(kx + 4.5, ky, (enc_front + seat_floor) / 2) * bd.Box(0.2, 0.2, 0.1)).solids()
    assert (part & bd.Pos(kx, ky + 4.5, (enc_front + seat_floor) / 2) * bd.Box(0.2, 0.2, 0.1)).solids()
    #    Дыра проходит сквозь островок у самого лица: пусто Ø7,2 и на 1,1 над
    #    дном канавки — шток Ø6,0 идёт тем же отверстием, что и раньше.
    rim_hole = _void_x(part, kx, ky, seat_floor + 1.1, probe=20.0)
    assert abs(rim_hole - ENC_BUSH_HOLE) < 0.05, rim_hole
    #    Карман под корпус прямой, 21,0 по X (ряды выводов плюс 2,5 под паяный
    #    контакт с проводом) и 12,9 по Y (лапки), на всю глубину до передней
    #    плоскости. Открыт снизу, глубина больше корпуса с лапками 4,5+4,0 на 4,6.
    pocket_z = bottom + 1.0
    pocket_x = _void_x(part, kx, ky, pocket_z, probe=30.0)
    pocket_y = _void_y(part, kx, ky, pocket_z, probe=20.0)
    assert (
        abs(pocket_x - 2 * (ENC_PIN_OUT + ENC_PIN_D / 2 + SOLDER_ROOM)) < 0.05
    ), pocket_x
    assert abs(pocket_y - (ENC_EAR_SPAN + 2 * SEAT_FIT)) < 0.05, pocket_y
    #    У самой передней плоскости карман тот же: ступени нет.
    pocket_x_top = _void_x(part, kx, ky, enc_front - 1.0, probe=30.0)
    pocket_y_top = _void_y(part, kx, ky, enc_front - 1.0, probe=20.0)
    assert abs(pocket_x_top - pocket_x) < 0.05, pocket_x_top
    assert abs(pocket_y_top - pocket_y) < 0.05, pocket_y_top
    assert enc_front - bottom > ENC_BODY_T + ENC_EAR_T + 0.9, enc_front - bottom
    #    Крайние точки эталона пусты: наружные кромки лапок y=±6,25 и оси
    #    выводов x=±7,5 — иначе вывод упрётся в стенку кармана.
    for z in (pocket_z, enc_front - 1.0):
        for px, py in ((kx, ky + 6.15), (kx, ky - 6.15), (kx + 7.4, ky), (kx - 7.4, ky)):
            assert not (
                part & bd.Pos(px, py, z) * bd.Box(0.2, 0.2, 0.2)
            ).solids(), (px, py, z)
    #    Перемычка над карманом — сплошная: на 0,5 выше передней плоскости
    #    по кольцу Ø8,0 материал, а не пустота втулки.
    assert (part & bd.Pos(kx + 4.0, ky, enc_front + 0.5) * bd.Box(0.2, 0.2, 0.1)).solids()
    # 5б. Пилоты под планку: пусто Ø2,5 на 4 мм выше низа панели, материал между
    #     пилотом и стенкой кармана (0,8 за кромкой отверстия, ещё 1,75 до стенки).
    for side in (-1, 1):
        assert not (
            part & bd.Pos(kx, ky + side * CLAMP_SCREW_OFF, bottom + 4.0) * bd.Box(0.2, 0.2, 0.2)
        ).solids()
        assert (
            part
            & bd.Pos(kx, ky + side * (CLAMP_SCREW_OFF - CLAMP_PILOT_D / 2 - 0.8), bottom + 4.0)
            * bd.Box(0.2, 0.2, 0.2)
        ).solids()
    #     Пилот не врезается в стенку кармана: от стенки до кромки отверстия
    #     остаётся 12 − 1,25 − 6,45 = 4,3 материала.
    assert (
        CLAMP_SCREW_OFF - CLAMP_PILOT_D / 2 - (ENC_EAR_SPAN / 2 + SEAT_FIT) > 2.5
    ), CLAMP_SCREW_OFF
    #     И не выходит наверх за плиту: верх пилота ниже дна канавки.
    assert bottom + CLAMP_PILOT_H < seat_floor, bottom + CLAMP_PILOT_H
    # 5в. Вырезка кабеля в левом переднем углу (у крутилки): пусто в ней на трёх
    #     высотах, вокруг — сплошной материал. Стенка к соседним выборкам не
    #     режется: слева до первой колонки 21,8 мм, до пилота планки 2,25,
    #     до кармана энкодера 9,05.
    for x, y, z in (
        (8.3, -3.0, 63.5),
        (8.3, 3.0, 59.5),
        (10.1, 3.0, 65.0),
        (8.3, 10.5, 63.5),
    ):
        assert not (
            part & bd.Pos(x, y, z) * bd.Box(0.2, 0.2, 0.2)
        ).solids(), (x, y, z)
    for x, y, z in (
        (8.3, -3.0, NICHE_FRONT_Z + CABLE_H + 1.1),   # над пандусом у лица
        (CABLE_X0 - 0.5, 3.0, 63.5),                  # боковая стенка
        (CABLE_X1 + 0.5, 3.0, 63.5),                  # боковая стенка, другая
        (8.3, CABLE_Y1 + 0.5, 66.0),                  # торец: материал за каналом
        (15.0, -3.0, 63.5),                           # губа вне вырезки (справа)
        (3.0, -3.0, 63.0),                            # губа до левого торца полки
    ):
        assert (
            part & bd.Pos(x, y, z) * bd.Box(0.2, 0.2, 0.2)
        ).solids(), (x, y, z)
    #    Выход у лица 6,0 фаской 45°: пусто под фаской, материал над ней и в
    #    глубине над каналом.
    for x, y, z in ((10.0, -5.9, 67.4), (7.0, -5.9, 66.9)):
        assert not (part & bd.Pos(x, y, z) * bd.Box(0.1, 0.05, 0.1)).solids(), (x, y, z)
    for x, y, z in ((10.0, -5.9, 68.2), (10.0, -2.0, 67.6), (10.0, 3.0, 67.0)):
        assert (part & bd.Pos(x, y, z) * bd.Box(0.1, 0.05, 0.1)).solids(), (x, y, z)
    #    Пандус потолка: 6,0 у лица, 4,4 на y=CABLE_RAMP_Y и до торца плоско.
    def roof(y):
        col = part & bd.Pos(9.0, y, NICHE_FRONT_Z) * bd.Box(
            0.05, 0.02, 20, align=(bd.Align.CENTER, bd.Align.MIN, bd.Align.MIN)
        )
        return col.bounding_box().min.Z

    assert abs(roof(-NICHE_SHELF) - (NICHE_FRONT_Z + CABLE_EXIT)) < 0.03, roof(-NICHE_SHELF)
    assert abs(roof(CABLE_RAMP_Y) - (NICHE_FRONT_Z + CABLE_H)) < 0.03, roof(CABLE_RAMP_Y)
    assert abs(roof(CABLE_RAMP_Y + 1.0) - (NICHE_FRONT_Z + CABLE_H)) < 0.03, roof(5.0)
    assert abs(roof(0.0) - (NICHE_FRONT_Z + CABLE_H + 0.64)) < 0.03, roof(0.0)
    #    До самого торца потолок плоский: у новой стенки те же 4,4.
    assert abs(roof(CABLE_Y1 - 0.5) - (NICHE_FRONT_Z + CABLE_H)) < 0.03, roof(10.5)
    #    Размеры вырезки сняты с тела (не с констант): ширина 6,2 по всей глубине,
    #    за торцом y=CABLE_Y1 — сплошной материал до пилота планки (y=13,25) и
    #    до кармана энкодера (y=20,05), то есть 2,25 и 9,05 мм запаса.
    def notch_x(z):
        """Ширина пустоты вырезки на высоте z — срез поперёк канала."""
        slab = bd.Pos(8.3, 5.0, z) * bd.Box(12, 0.2, 0.1)
        return (slab - (part & slab)).bounding_box().size.X

    for z in (59.5, 65.0):
        assert abs(notch_x(z) - CABLE_W) < 0.05, (z, notch_x(z))
    #    Столбик материала за торцом: 2,0 и 7,0 до промежуточных точек, 2,25 до
    #    пилота и 9,05 до кармана — стенки на месте по всей высоте канала.
    #    Второй срез — x=10,5: он в пределах и канала, и кармана, поэтому там
    #    стенка 9,05 кончается на передней стенке кармана y=20,05.
    for x in (8.3, 10.5):
        for end in (13.0, 18.0, 13.25, 18.3):
            col = part & bd.Pos(x, (CABLE_Y1 + end) / 2, 63.5) * bd.Box(
                0.4, end - CABLE_Y1, 0.4
            )
            assert abs(col.bounding_box().size.Y - (end - CABLE_Y1)) < 0.05, (
                x,
                end,
                col.bounding_box().size,
            )
    #    Границы стенок: сразу за ними — пустота кармана и пилота, не материал.
    assert not (part & bd.Pos(10.5, 20.15, 63.5) * bd.Box(0.2, 0.2, 0.2)).solids()
    assert not (part & bd.Pos(16.0, 13.4, 63.5) * bd.Box(0.2, 0.2, 0.2)).solids()
    #    Задняя стенка канала есть: сразу за торцом — материал, а не пустота.
    assert (part & bd.Pos(8.3, CABLE_Y1 + 0.6, 63.0) * bd.Box(0.2, 0.2, 0.2)).solids()
    #    До выборки левой колонки 21,8 мм: вырезка её не задевает.
    assert min(x for x, _ in centers) - SWITCH_BODY / 2 - CABLE_X1 > 20.0
    #    Колодец крайней колонки на глубине 3,0 — тот же конус: вырезка до него
    #    не достаёт, плита и стенки колодца целы.
    well_notch = _void_y(part, 79.0, 37.5, top_z(79.0) - 3.0, probe=18.3)
    assert abs(well_notch - well_width(79.0, top_z(79.0) - 3.0)) < 0.05, well_notch
    for x in (1.0, -2.0, -4.5):
        assert (part & bd.Pos(x, CABLE_Y1, top_z(x) - 2.0) * bd.Box(0.2, 0.2, 0.2)).solids(), x
    # 6. Скруглённая кромка снята: наклонного ребра (y=−6) больше нет,
    #    а срезанный объём — (1−π/4)·R²·100.
    left = _top_front_edges(part)
    assert not left, [edge.length for edge in left]
    cut_volume = volume_before - part.volume
    assert 150 < cut_volume < 220, cut_volume
    # 7. Губа лежит на полке: в передней полосе низ панели — ровно z=NICHE_FRONT_Z.
    lip_bottom = (part & bd.Pos(45, -3, 40) * bd.Box(50, 4, 200)).bounding_box().min.Z
    assert abs(lip_bottom - NICHE_FRONT_Z) < 0.01, lip_bottom
    # 7б. Губа: слева зазор 0,2 до выреза полки; канал сдвинут влево, поэтому
    #     справа от него остаётся полоска губы до торца полки 89,8.
    lip_section = (part & bd.Pos(45, -3, 63) * bd.Box(400, 4, 0.02)).bounding_box()
    assert abs(lip_section.min.X - 0.2) < 0.02, lip_section.min.X
    assert abs(lip_section.max.X - (NICHE_MOUTH_X - 0.2)) < 0.02, lip_section.max.X
    # 7в. Губа сращена с пробкой, а не только касается её у рта: объединение
    #     даёт одно тело, внутренней щели между опорой и телом нет.
    assert len((_plug() + _front_lip()).solids()) == 1
    # 8. Зазор 0, но пересечений с нишей нет: касание, а не натяг.
    rim_body, _void = _rim()
    niche_shell, _pocket, _shelf = _niche_body()
    rim_clash = (part & rim_body).volume
    niche_clash = (part & niche_shell).volume
    assert rim_clash < 1e-3, rim_clash
    assert niche_clash < 1e-3, niche_clash

    # 9. Защёлки. Корпус строится здесь только ради проверки: окна, стенка и
    #    наружная поверхность берутся из него, а не из копии констант.
    klip = body_part.body.__wrapped__()
    mid_win = (body_part.CLIP_WIN_Z0 + body_part.CLIP_WIN_Z1) / 2
    straight = body_part.CLIP_WIN_W / 2  # 5,1 — половина прямой кромки 10,2
    win_outer = body_part._niche_section(mid_win, FIT).bounding_box()
    opens, gaps = [], []
    for x in body_part.CLIP_WIN_X:
        for front in (True, False):
            out = TONGUE_OUT if front else REAR_OUT
            y_in = TONGUE_IN[0] if front else TONGUE_IN[1]  # грань к полости
            cav = 1.0 if front else -1.0
            nose = HOOK_NOSE[0] if front else HOOK_NOSE[1]
            wall_in = _HOOK_WALL.min.Y if front else _HOOK_WALL.max.Y
            y_c = (nose + wall_in) / 2  # середина опорной полки
            # (б) Крючок в окне: во всю ширину кромки (люфт 0,1 на сторону), верх —
            #     на кромке, под крючком 4,5 мм, выше опорной грани язык не выходит.
            hook_box = (
                part & bd.Pos(x, y_c, HOOK_TOP - 0.1) * bd.Box(40, 40, 0.2)
            ).bounding_box()
            assert abs(hook_box.size.X - HOOK_W) < 0.02, hook_box.size.X
            sided = straight - hook_box.size.X / 2
            assert 0.05 <= sided <= 0.2, sided  # люфт 0,1 на сторону — норма
            shaft = (
                part & bd.Pos(x, (out + y_in) / 2, 50.0) * bd.Box(40, 40, 0.2)
            ).bounding_box()
            assert abs(shaft.size.X - TONGUE_W) < 0.02, shaft.size.X
            col = (
                part & bd.Pos(x, (out + y_in) / 2, HOOK_TOP - 2) * bd.Box(0.2, 0.2, 6)
            ).bounding_box()
            assert abs(col.min.Z - (HOOK_TOP - HOOK_T)) < 0.01, col.min.Z
            assert col.min.Z - body_part.CLIP_WIN_Z0 >= 0.3, col.min.Z
            # опорная грань крючка на кромке по всей ширине 10,0, не только в центре
            for xp in (x - HOOK_W / 2 + 0.2, x, x + HOOK_W / 2 - 0.2):
                cap = (
                    part & bd.Pos(xp, y_c, HOOK_TOP) * bd.Box(0.2, 0.2, 2)
                ).bounding_box()
                assert abs(cap.max.Z - HOOK_TOP) < 0.01, cap.max.Z
            assert (
                part & bd.Pos(x, y_c, HOOK_TOP - 0.1) * bd.Box(0.2, 0.2, 0.2)
            ).solids()  # под полкой — крючок
            assert (
                klip & bd.Pos(x, y_c, HOOK_TOP + 0.1) * bd.Box(0.2, 0.2, 0.2)
            ).solids()  # над полкой — стенка
            # (в) Нос не выходит за наружную поверхность: окно открыто снаружи.
            out_y = win_outer.min.Y if front else win_outer.max.Y
            opens.append(abs(nose - out_y))
            assert opens[-1] >= 0.9, opens[-1]
            assert not (
                part & bd.Pos(x, out_y - cav * 0.4, mid_win) * bd.Box(0.2, 0.2, 0.2)
            ).solids()
            # (г) Язык стенки не касается: 0,39 у стыка, 0,11 внизу — уклон 1°.
            for z in (bottom - 0.1, HOOK_TOP + 0.1):
                face = body_part._niche_section(
                    z, FIT + body_part.WALL
                ).bounding_box()
                gaps.append(abs(out - (face.min.Y if front else face.max.Y)))
            assert 0.35 < gaps[-2] < 0.42, gaps[-2]
            assert 0.08 < gaps[-1] < 0.15, gaps[-1]
            # (г) Галтель корня — в углу со стороны полости: материал в углу есть,
            #     за r0,8 пусто, дно панели не прорезано.
            assert (
                part
                & bd.Pos(x, y_in + cav * 0.15, bottom - 0.2)
                * bd.Box(0.2, 0.2, 0.2)
            ).solids()
            assert not (
                part & bd.Pos(x, y_in + cav * 0.9, bottom - 0.1) * bd.Box(0.2, 0.2, 0.2)
            ).solids()
            floor_z = (
                part & bd.Pos(x, y_in + cav * 2.0, bottom + 1.0) * bd.Box(0.2, 0.2, 2)
            ).bounding_box().min.Z
            assert abs(floor_z - bottom) < 0.01, floor_z
            # (д) Вокруг языка воздух: к полости, глубже и по бокам крючка.
            for dy, dz in ((0.5, 55.0), (0.5, 48.0), (2.0, 50.0)):
                assert not (
                    part
                    & bd.Pos(x, y_in + cav * dy, dz) * bd.Box(0.2, 0.2, 0.2)
                ).solids(), (dy, dz)
            for dx in (-1, 1):
                assert not (
                    part
                    & bd.Pos(x + dx * (TONGUE_W / 2 + 0.5), (out + y_in) / 2, 50.0)
                    * bd.Box(0.2, 0.2, 0.2)
                ).solids(), dx

    print(
        f"панель z={box.min.Z:.2f}..{box.max.Z:.2f}: "
        f"низ {_section_x(part, bottom + 0.5):.2f} мм по X, "
        f"юбка z={z_skirt:g}: {skirt_x:.2f} против раструба {flare_x:.2f} "
        f"— зазор {skirt_gap:.2f} мм на сторону; "
        f"обод z={OPEN_Z:g}: {edge_x:.2f} мм (план кромки {FRONT.bounding_box().size.X:.2f}); "
        f"габарит {box.size.X:.1f}×{box.size.Y:.1f}×{box.size.Z:.1f} мм; "
        f"плита {PLATE_T:g} мм, верх {min(plate_top(cx) for cx, _ in centers):.2f}"
        f"..{max(plate_top(cx) for cx, _ in centers):.2f}, "
        f"дно колодца z={min(floors):.2f}..{max(floors):.2f}; "
        f"верх слева {face_left:.2f}, в середине {face_mid:.2f}, справа {face_right:.2f} "
        f"(наклон {math.degrees(math.atan(-TOP_SLOPE)):.2f}°); "
        f"окно {min(window_gaps):.2f}..{max(window_gaps):.2f}, "
        f"выборка под плитой {min(relief_gaps):.2f}..{max(relief_gaps):.2f}, "
        f"корпус свитча под плитой {max(switch_clashes):.1e} мм³, "
        f"колодец сужается {well_width(x, top_z(x) - 0.5):.2f} у лица -> "
        f"{well_width(x, plate_top(x)):.2f} у плиты, фаска рта 0,5, уступов нет; "
        f"ход кейкапов {', '.join(f'{s:.2f}' for s in strokes)}; "
        f"перемычки {bridge_w:.2f} по X и {bridge_y.bounding_box().size.Y:.2f} по Y на z={well_z:g}; "
        f"энкодер: канавка Ø{recess_dia:.2f}×Ø{island_dia:.2f} (кольцо {SEAT_RING:g}) "
        f"до z={seat_floor:.2f}, островок до лица "
        f"(верх z={island_box.max.Z:.2f}, как лицо), "
        f"втулка Ø{bush_dia:.2f} сквозь островок и на "
        f"{knob_face_z() - enc_front - ENC_BUSH_L:.2f} ниже лица, "
        f"карман {pocket_x:.2f}×{pocket_y:.2f} на всю глубину до z={enc_front:.2f}, "
        f"пилоты планки Ø{CLAMP_PILOT_D:g}×{CLAMP_PILOT_H:g} на ky±{CLAMP_SCREW_OFF:g}, "
        f"низ ручки z={knob_bottom_z():.2f}, ручка knob_knurl "
        f"z={knob_box.min.Z:.2f}..{knob_box.max.Z:.2f} "
        f"(габарит Ø{knob_box.size.X:.1f}×{knob_box.size.Y:.1f}×{knob_box.size.Z:.2f}), "
        f"ход проверки {KNOB_TRAVEL:g}: зазор до островка {min(island_gaps):.2f}, "
        f"в покое {min(rest_gaps):.2f}, до дна канавки "
        f"{min(groove_gaps):.2f} на r=12,1, пересечение с ручкой {knob_clash:.4f} мм³; "
        f"вырезка кабеля {CABLE_W:g}×{CABLE_H:g} в левом переднем углу, глубина {CABLE_Y1 + NICHE_SHELF:g} от лица, выход {CABLE_EXIT:g} пандусом до y={CABLE_RAMP_Y:g}, "
        f"x={CABLE_X0:g}..{CABLE_X1:g}, от полки z={NICHE_FRONT_Z:g} (до пилота планки 2,25, до кармана 9,05); "
        f"скругление R{EDGE_R:g} сняло {cut_volume:.0f} мм³; "
        f"губа снизу z={lip_bottom:.2f}, зазор слева {lip_section.min.X:.2f}, "
        f"пересечения с ободом {rim_clash:.1e}, с нишей {niche_clash:.1e} мм³; "
        f"защёлки: 4 языка {TONGUE_T:g}×{TONGUE_W:g} длиной {bottom - HOOK_TOP:g}, "
        f"крючок {HOOK_W:g}×{HOOK_T:g} в окне "
        f"{body_part.CLIP_WIN_W:g}×{body_part.CLIP_WIN_Z1 - body_part.CLIP_WIN_Z0:g}, "
        f"нос входит {HOOK_ENGAGE:g} от внутренней грани, снаружи открыто "
        f"{min(opens):.2f}, под крючком "
        f"{col.min.Z - body_part.CLIP_WIN_Z0:.1f}, до стенки "
        f"{min(gaps):.2f}..{max(gaps):.2f} мм"
    )
    return part


if __name__ == "__main__":
    face()
