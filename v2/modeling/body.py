# -*- coding: utf-8 -*-
"""Корпус «Кнопыч» — печатаемая деталь под панелью (нижняя половина).

Наружная стенка идёт по РЕАЛЬНОМУ карману ниши (замер: рот 89,9×53,3 на z=65,
дно 80×43 на z=0, линейно, углы R8) — не по модельному с уклоном 1°. На стыке с
панелью (z=58,7) контур дополнительно утоплен на 0,4 под нависающую пробку лица;
ниже стыка стенка идёт прямым уклоном 4,5°/сторона. Стенка 2,5 мм, дно 2,5 мм.

  z = FLOOR - 1 = 2        низ корпуса, 2 мм над полом ниши
  z = 2..4.5               дно на всю полость
  z = 35.5..42.5           сквозные окна под крючки панели в переде и заде
  z = 42.5..58.7           выемки 1,7 под стволы языков на внутренней грани
  z = deck_bottom() ≈ 58.7 верх корпуса, стык с панелью

Внутри — гнездо платы ESP32 в правом заднем углу (плата на скотче, деталями
вниз) и защёлка кабеля на левой стенке. Стоек под плату больше нет.
"""

import math

import build123d as bd

import clip_ref
from cad import model
from niche_panel import (
    FIT,
    FLOOR,
    NICHE_CORNER_R,
    NICHE_CX,
    NICHE_CY,
    NICHE_MOUTH_Z,
    _niche_section,
    deck_bottom,
)

TOP_Z = deck_bottom()
BODY_FLOOR = FLOOR - 1
WALL = 2.5
FLOOR_T = 2.5
DECK_Z = BODY_FLOOR + FLOOR_T

# Уклон стенки: реальный карман (дно 80×43 на z=0, рот 89,9×53,3 на z=65) —
# 4,36–4,53°/сторона. От стыка вниз берём 4,5° по обеим осям, как велел замер.
BODY_DRAFT = 4.5
# Скрытая ступенька на стыке: под нависающей пробкой лица наружная стенка ещё
# на 0,4 внутрь кармана (итого 0,9 вместо FIT 0,5). Согласована с пользователем.
STEP = 0.4

# План на стыке — сечение кармана минус FIT + STEP. Ниже стыка тот же план,
# сужающийся прямо (BODY_DRAFT), поэтому размеры берутся один раз здесь.
_JOINT = _niche_section(TOP_Z, FIT + STEP).bounding_box().size
_JOINT_R = NICHE_CORNER_R - (FIT + STEP)  # 7,1 — скругление угла на стыке

# Окна под крючки панели: сквозь стенку, по два в переде и заде. Окно — простой
# прямоугольник 10,2×7 с прямыми углами: скруглений нет, они заставляли делать
# крючок 7,4 вместо 10. Верхняя кромка — плоская опорная грань положительной
# полки крючка, на неё панель и держится; снизу окно открыто на 4,5 мм — крючок
# туда не достаёт. Язык панели 10,0, боковой люфт 0,1 на сторону. Фаски снаружи
# нет: при выемке 1,4 она срезала опорную полку до 0,6 (DFM: тонкая стенка), а
# любой сдвиг фаски выше лишь уносит эту стенку вверх — выемка держит 1,1 по всей
# высоте. Без фаски кромка прямая, полка остаётся 2,5 − 1,4 = 1,1.
CLIP_WIN_W = 10.2
CLIP_WIN_Z0 = 35.5
CLIP_WIN_Z1 = 42.5
CLIP_WIN_X = (25.0, 65.0)

# Выемка под ствол языка на внутренней грани стенки, у каждого окна: половина
# по X и глубина от внутренней грани. Ствол (face.py: y 3,5..4,9 впереди и
# 48,4..49,8 сзади, x ±5,0) идёт прямо, а стенка с уклоном 4,5° наезжает на
# него книзу на 1,3 — без выемки панель не сядет. Выемка 1,4 оставляет стенку
# 1,1 и зазор до ствола 0,11.
# Опорную кромку окна на z=42,5 не трогаем: выемка кончается ровно на ней.
RELIEF_HALF = 5.5
TONGUE_RELIEF = 1.4

# Гнездо платы ESP32: плата перевёрнута деталями вниз и посажена на
# двусторонний скотч, который клеится на борт. Борт — верх стенки гнезда на
# плоскости платы; внутренний размер гнезда — плата плюс зазор на сторону.
BOARD_W, BOARD_D = 23.7, 18.0   # плата по замеру
BOARD_CLEAR = 0.3               # зазор в гнезде на сторону
BOARD_R = 2.0                   # притупление углов кармана — повторяет скругление
                                # уголков платы (у платы уголки до R1,85, по дуге
                                # остаётся 0,15…0,4 зазора)
BOARD_Z = 10.0                  # плоскость платы = верх борта, сюда скотч
BOARD_POCKET_H = 5.0            # дно гнезда ниже плоскости платы (z=5,0)
RIM_W = 2.5                     # борт по периметру, скотч клеится на него
NEST_GAP = 3.0                  # от борта до стенок полости, гнездо в углу
SLOT_W = 6.0                    # прорезь под провода в борту у зажима, по Y
SLOT_H = 2.0                    # и глубиной сверху
LIP_H = 1.2                     # бортик над бортом по трём сторонам кармана
VENT_W, VENT_H = 8.0, 3.0       # проём вентиляции в борту +X (тыл платы)

# Защёлка кабеля — покупной зажим из эталона `ref/cable_clip_tape.stl`
# (clip_ref.py): форма берётся из файла, не рисуется. Масштаб один на все оси —
# внешний: при 1:1,6 стенка кольца эталона 1,56 становится печатной. Гнездо
# эталона при этом шире кабеля, поэтому его перерезаем обратно цилиндром
# ØCLIP_BORE по той же оси: меняется только диаметр отверстия, кольцо — из
# файла. Плоский тыл пластины ложится на левую стенку (зеркало прежней правой)
# и утоплен в неё на CLIP_SINK — сварка сплошным материалом, не касание. Ось
# гнезда по Z (кабель идёт сверху вниз), зев смотрит вдоль стенки в +y — в
# полость, не в стенку.
CABLE_D = 3.0         # Ø реального кабеля (замер 22.11.2026)
CLIP_BORE = 2.95
CLIP_OUT = 0.62       # внешний масштаб эталона
CLIP_SINK = 0.45      # пластина в стенке: 0,45 из 0,93 толщины
CLIP_Y = 24.0         # центр зажима вдоль левой стенки, к середине (по снимку)
CLIP_TOP = 47.0       # верх зажима по z; низ = CLIP_TOP − 10·CLIP_OUT
# Выступающую в полость часть пластины (0,93 − CLIP_SINK) срезаем заподлицо с
# внутренней гранью стенки: в полости остаётся только кольцо, ступеньки нет.
CLIP_PLATE_OUT = clip_ref.PLATE_T * CLIP_OUT - CLIP_SINK
# Линия щели зева смещена от оси гнезда: 1,525 в единицах файла (замер по
# сечению) — та же доля при любом масштабе, в мм корпуса.
CLIP_MOUTH_X = 1.525 * CLIP_OUT

# Реальный карман ниши: рот и дно по замеру, стенки линейные, углы R8.
REAL_MOUTH = (89.9, 53.3)   # на NICHE_MOUTH_Z
REAL_FLOOR = (80.0, 43.0)   # на z=0


def _vol(shape, tool):
    """Объём пересечения; пустое пересечение build123d отдаёт как None."""
    got = shape & tool
    return got.volume if got else 0.0


def _mask(z, extra=0.0):
    """Сечение корпуса на высоте z, суженное ещё на extra.

    План — сечение кармана на стыке (модель + STEP); ниже стыка стенка идёт
    прямо с уклоном BODY_DRAFT, а не по 1° модели. Скругление угла вниз не
    уменьшаем: меньший радиус уводит угол наружу от R8 реального кармана.
    """
    drop = max(0.0, TOP_Z - z) * math.tan(math.radians(BODY_DRAFT))
    return bd.Pos(NICHE_CX, NICHE_CY, z) * bd.RectangleRounded(
        _JOINT.X - 2 * (extra + drop),
        _JOINT.Y - 2 * (extra + drop),
        _JOINT_R - extra,
    )


def _loft(extra, z0, z1):
    """Лофт сечения корпуса с дополнительным отступом extra от z0 до z1."""
    return bd.loft([_mask(z0, extra), _mask(z1, extra)], ruled=True)


def _real(z):
    """Сечение РЕАЛЬНОГО кармана ниши на высоте z (замер пользователя)."""
    t = z / NICHE_MOUTH_Z
    return bd.Pos(NICHE_CX, NICHE_CY, z) * bd.RectangleRounded(
        REAL_FLOOR[0] + (REAL_MOUTH[0] - REAL_FLOOR[0]) * t,
        REAL_FLOOR[1] + (REAL_MOUTH[1] - REAL_FLOOR[1]) * t,
        NICHE_CORNER_R,
    )


def _window(x, front):
    """Сквозное окно под крючок: прямоугольник 10,2×7 в XZ с прямыми углами.

    Стенка наклонена 4,5° и толще модельной, поэтому обе грани берутся из
    сечения самого корпуса, с запасом 1,0 за грань.
    """
    zc = (CLIP_WIN_Z0 + CLIP_WIN_Z1) / 2
    outer = _mask(zc).bounding_box()
    inner = _mask(zc, WALL).bounding_box()
    if front:  # наружная грань — меньше y, внутренняя — больше
        lo, hi = outer.min.Y - 1.0, inner.min.Y + 1.0
    else:
        lo, hi = inner.max.Y - 1.0, outer.max.Y + 1.0
    return bd.Pos(x, hi, zc) * bd.extrude(
        bd.Plane.XZ * bd.Rectangle(CLIP_WIN_W, CLIP_WIN_Z1 - CLIP_WIN_Z0),
        hi - lo,
    )


def _nest_rect():
    """Планы гнезда платы: (борт, карман), правый задний угол полости."""
    cav = _mask(BOARD_Z, WALL).bounding_box()
    w = BOARD_W + BOARD_CLEAR + 2 * RIM_W
    d = BOARD_D + BOARD_CLEAR + 2 * RIM_W
    x1, y1 = cav.max.X - NEST_GAP, cav.max.Y - NEST_GAP
    rim = (x1 - w, y1 - d, x1, y1)
    pocket = (rim[0] + RIM_W, rim[1] + RIM_W, rim[2] - RIM_W, rim[3] - RIM_W)
    return rim, pocket


@model
def body():
    part = _loft(0.0, BODY_FLOOR, TOP_Z)
    # Полость на всю высоту — стенка WALL; полки под панель нет.
    cavity = _loft(WALL, DECK_Z, TOP_Z)
    part = part - cavity

    # Окно кабеля: продолжение вырезки панели вниз — только верхние 4 мм
    # стенки, провод проходит из панели в полость. Ниже стенка целая: сквозного
    # вертикального канала до z=40 нет. Зеркало прежнего окна 77,5..84,4
    # относительно x=45: x 5,6..12,5, левая стенка.
    notch = bd.Pos(5.6, 0.4, TOP_Z - 4.0) * bd.Box(
        6.9, 7.6, 4.3, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)
    )
    part = part - notch

    # Четыре окна под крючки панели: по два в переде и заде, сквозь стенку.
    for x in CLIP_WIN_X:
        for front in (True, False):
            part = part - _window(x, front)

    # Выемки под стволы языков: от стыка вниз до верха окна, глубина
    # TONGUE_RELIEF от внутренней грани — тем же уклоном, что и стенка, иначе
    # на z=42,5 стенка съест ствол.
    relief = _loft(WALL - TONGUE_RELIEF, CLIP_WIN_Z1, TOP_Z)
    for x in CLIP_WIN_X:
        part = part - (
            relief
            & bd.Pos(x, NICHE_CY, (CLIP_WIN_Z1 + TOP_Z) / 2)
            * bd.Box(2 * RELIEF_HALF, 300.0, TOP_Z - CLIP_WIN_Z1)
        )

    # Гнездо платы: бобышка в правом заднем углу, карман в ней до z=5,0, борт
    # 2,5 по периметру на плоскости платы, прорезь под провода в борту у зажима.
    rim, (px0, py0, px1, py1) = _nest_rect()
    part = part + bd.Pos(rim[0], rim[1], DECK_Z) * bd.Box(
        rim[2] - rim[0], rim[3] - rim[1], BOARD_Z - DECK_Z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    )
    # Углы кармана скруглены по вертикальным кромкам на BOARD_R: дуга идёт на
    # всю глубину кармана и через верх борта, уступов на кромке нет.
    pocket = bd.Pos(px0, py0, BOARD_Z - BOARD_POCKET_H) * bd.Box(
        px1 - px0, py1 - py0, BOARD_POCKET_H + 1.0,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    )
    part = part - bd.fillet(pocket.edges().filter_by(bd.Axis.Z), radius=BOARD_R)
    # Бортик над бортом по трём сторонам кармана — держит плату и изоленту
    # сверху. Внутренние углы острые: по прямоугольнику кармана, не по дуге —
    # иначе бортик залез бы под скруглённый уголок платы. Со стороны +X (тыл
    # платы, напротив разъёма) бортика нет.
    lip = (
        bd.Pos(rim[0], py0 - RIM_W, BOARD_Z)
        * bd.Box(rim[2] - rim[0], RIM_W, LIP_H, align=(bd.Align.MIN,) * 3)
        + bd.Pos(rim[0], py1, BOARD_Z)
        * bd.Box(rim[2] - rim[0], RIM_W, LIP_H, align=(bd.Align.MIN,) * 3)
        + bd.Pos(px0 - RIM_W, py0, BOARD_Z)
        * bd.Box(RIM_W, py1 - py0, LIP_H, align=(bd.Align.MIN,) * 3)
    )
    part = part + lip
    sy = (py0 + py1) / 2
    # Вентиляция сзади платы: проём насквозь через борт +X, снизу до z=7,0.
    # Бортик там отсутствует, поэтому сверху проём открыт.
    part = part - bd.Pos(px1 - 0.1, sy - VENT_W / 2, BOARD_Z - VENT_H) * bd.Box(
        RIM_W + 0.2, VENT_W, VENT_H + 0.2,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    )
    # Прорезь под провода: в левом борту от z=8,0 и вверх через бортик, провод
    # проходит над ним.
    part = part - bd.Pos(px0 - RIM_W - 0.1, sy - SLOT_W / 2, BOARD_Z - SLOT_H) * bd.Box(
        RIM_W + 0.2, SLOT_W, SLOT_H + LIP_H + 0.1,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    )

    # Защёлка кабеля: solid целиком из файла эталона — внешний масштаб, поворот
    # осью гнезда по Z, зеркало по X (тыл пластины смотрит в стенку −x), перенос
    # к левой стенке. Гнездо после масштаба шире кабеля — перерезаем его до
    # CLIP_BORE.
    zc = CLIP_TOP - 5.0 * CLIP_OUT                       # середина зажима
    wall_x = _mask(zc, WALL).bounding_box().min.X        # грань левой стенки
    cx = wall_x - CLIP_SINK + clip_ref.AXIS[1] * CLIP_OUT   # ось гнезда
    cy = CLIP_Y
    clip = bd.Pos(
        wall_x - CLIP_SINK,
        cy - clip_ref.AXIS[0] * CLIP_OUT,
        CLIP_TOP - 10.0 * CLIP_OUT,
    ) * bd.mirror(
        bd.Rot(0, 0, 90) * bd.scale(clip_ref.solid(), by=CLIP_OUT), about=bd.Plane.YZ
    )
    cbb = clip.bounding_box()
    clip0 = clip  # до среза — для контроля «кольцо не тронуто»
    # Пластина-основание торчит в полость на CLIP_PLATE_OUT (0,48 из 0,93) —
    # в полости должно остаться только кольцо. Срезаем её выступающий слой
    # ровно по внутренней грани стенки: слоем пластины от её передней
    # плоскости до грани стенки, минус цилиндр обоймы R_outer по оси гнезда.
    # Кольцо целиком лежит внутри R_outer, срез его не задевает (проверка
    # ниже), а язык зева остаётся перед плоскостью пластины нетронутым.
    sleeve = bd.Pos(cx, cy, cbb.min.Z - 1.0) * bd.Cylinder(
        clip_ref.SLEEVE_R * CLIP_OUT,
        cbb.size.Z + 2.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    plate_front = wall_x - CLIP_SINK + clip_ref.PLATE_T * CLIP_OUT
    plate_slab = bd.Pos(plate_front, cy, zc) * bd.Box(
        WALL - CLIP_SINK + clip_ref.PLATE_T * CLIP_OUT + 0.2, 14.0, 7.0,
        align=(bd.Align.MAX, bd.Align.CENTER, bd.Align.CENTER),
    )
    cut_off = (plate_slab & cavity) - sleeve
    clip = clip - cut_off
    # Срез оставил в полости торец пластины: её лицевая сторона в файле не
    # плоская — у зева и по краям она на 0,3–0,48 впереди плоскости 0,93, и
    # этот торец висел над воздухом (щели у стенки, DFM: gap 0,43). Заливаем
    # ровно этот воздух: сечение зажима ровно в плоскости среза, протянутое к
    # внутренней грани стенки. Плоскость среза идёт по касательной к
    # скруглённому торцу пластины, поэтому сечение чуть позади оставляло у
    # краёв лезвие 0,03×0,002 мм (DFM: knife edge); сечение в самой плоскости
    # смыкается с торцом вплотную и в полость не выступает. Берём самую
    # большую грань: вторая — срез обоймы, её вычтет clip.
    wall_top = _mask(CLIP_TOP, WALL).bounding_box().min.X
    sec = bd.section(
        clip0, section_by=bd.Plane(origin=(plate_front, cy, zc), z_dir=(1, 0, 0))
    )
    seam_prism = bd.extrude(
        max(sec.faces(), key=lambda f: f.area),
        amount=plate_front - wall_top + 0.2,
        dir=(-1, 0, 0),
    )
    seam = (seam_prism & cavity) - clip
    clip_cut = clip  # после среза пластины, до заливки щелей — для контроля
    clip = clip + seam
    cbb = clip.bounding_box()
    bore = bd.Pos(cx, cy, cbb.min.Z - 1.0) * bd.Cylinder(
        CLIP_BORE / 2,
        cbb.size.Z + 2.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    part = part + clip - bore

    part.label = "body"
    part.color = "#4a5160"

    # Верх корпуса — ровно стык с панелью.
    part_top = part.bounding_box().max.Z
    assert abs(part_top - deck_bottom()) < 0.01, part_top
    # Окно кабеля: только верхние 4 мм стенки — пусто сверху, ниже стенка целая
    # (сквозного канала до z=40 нет), материал справа и слева.
    # Проба — в середине толщины стенки на каждой высоте (стенка наклонена).
    mid_y = {z: (_mask(z).bounding_box().min.Y + _mask(z, WALL).bounding_box().min.Y) / 2
             for z in (TOP_Z - 1.0, TOP_Z - 6.0, 50.0, 44.0, 41.0, 37.0)}
    assert not (
        part & bd.Pos(10.0, mid_y[TOP_Z - 1.0], TOP_Z - 1.0) * bd.Box(0.2, 0.2, 0.2)
    ).solids()
    for z in (TOP_Z - 6.0, 50.0, 44.0, 41.0, 37.0):
        assert (part & bd.Pos(10.0, mid_y[z], z) * bd.Box(0.2, 0.2, 0.2)).solids(), z
    assert (
        part & bd.Pos(15.0, mid_y[TOP_Z - 1.0], TOP_Z - 1.0) * bd.Box(0.2, 0.2, 0.2)
    ).solids()

    # Главный зазор — до РЕАЛЬНОГО кармана: корпус целиком лежит в нём, на
    # контрольных высотах по X и по Y остаётся не меньше 0,4 мм.
    real = bd.loft([_real(0.0), _real(NICHE_MOUTH_Z)], ruled=True)
    outside = part - real
    out_vol = outside.volume if outside else 0.0
    assert out_vol < 1e-6, out_vol
    gaps = []
    for z in (58.5, 50.0, 42.5, 30.0, 10.0, 2.5):
        got = (
            part & bd.Pos(NICHE_CX, NICHE_CY, z) * bd.Box(300, 300, 0.05)
        ).bounding_box().size
        want = _real(z).bounding_box().size
        gx, gy = (want.X - got.X) / 2, (want.Y - got.Y) / 2
        gaps.append((z, gx, gy))
        assert gx >= 0.4 and gy >= 0.4, (z, gx, gy)
    bottom = (
        part & bd.Pos(NICHE_CX, NICHE_CY, BODY_FLOOR + 0.05) * bd.Box(300, 300, 0.05)
    ).bounding_box().size

    # Толщина стенки посередине высоты: срез поперёк левой стенки.
    probe = bd.Pos(0, NICHE_CY, 30.0) * bd.Box(
        20, 0.6, 0.05, align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER)
    )
    wall_t = (part & probe).bounding_box().size.X
    assert abs(wall_t - WALL) < 0.1, wall_t

    # Дно на всю полость и 2,5 мм толщиной.
    floor_probe = bd.Pos(NICHE_CX, NICHE_CY, BODY_FLOOR + 0.25) * bd.Box(
        0.6, 0.6, FLOOR_T + 3
    )
    floor_box = (part & floor_probe).bounding_box()
    assert (
        abs(floor_box.min.Z - BODY_FLOOR) < 0.05
        and abs(floor_box.max.Z - DECK_Z) < 0.05
    ), (floor_box.min.Z, floor_box.max.Z)

    # Гнездо платы: карман 24,0×18,3, дно на 5,0 ниже плоскости платы, борт 2,5
    # на плоскости z=10,0 (скотч), прорезь под провода в левом борту.
    probe = bd.Box(0.2, 0.2, 0.2)
    pocket_floor = BOARD_Z - BOARD_POCKET_H
    pcx, pcy = (px0 + px1) / 2, (py0 + py1) / 2
    air = (
        bd.Pos(px0, py0, pocket_floor) * bd.Box(
            px1 - px0, py1 - py0, BOARD_POCKET_H, align=(bd.Align.MIN,) * 3
        )
    ) - part
    air_box = air.bounding_box()
    assert abs(air_box.size.X - (BOARD_W + BOARD_CLEAR)) < 0.02, air_box.size.X
    assert abs(air_box.size.Y - (BOARD_D + BOARD_CLEAR)) < 0.02, air_box.size.Y
    assert abs(air_box.min.Z - pocket_floor) < 0.02, air_box.min.Z
    assert not (part & bd.Pos(pcx, pcy, pocket_floor + 1.0) * probe).solids(), (
        "карман гнезда пуст"
    )
    # Углы кармана притуплены R BOARD_R по вертикальным кромкам: в плане у
    # самого угла материал, под дугой воздух, середина каждой стенки — воздух;
    # габарит воздуха и его дно от скругления не изменились (ассерты выше).
    z_arc = pocket_floor + 1.0
    for corner_pt, arc_pt in (
        ((px0 + 0.1, py0 + 0.1), (px0 + 0.8, py0 + 0.8)),
        ((px1 - 0.1, py0 + 0.1), (px1 - 0.8, py0 + 0.8)),
        ((px0 + 0.1, py1 - 0.1), (px0 + 0.8, py1 - 0.8)),
        ((px1 - 0.1, py1 - 0.1), (px1 - 0.8, py1 - 0.8)),
    ):
        assert (part & bd.Pos(*corner_pt, z_arc) * probe).solids(), corner_pt
        assert not (part & bd.Pos(*arc_pt, z_arc) * probe).solids(), arc_pt
    for wall_pt in (
        (pcx, py0 + 0.1), (pcx, py1 - 0.1), (px0 + 0.1, pcy), (px1 - 0.1, pcy)
    ):
        assert not (part & bd.Pos(*wall_pt, z_arc) * probe).solids(), wall_pt
    under = (
        part & bd.Pos(pcx, pcy, BODY_FLOOR - 1.0) * bd.Box(
            0.2, 0.2, 40, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)
        )
    ).bounding_box()
    assert abs(under.max.Z - pocket_floor) < 0.02, under.max.Z
    assert abs(under.min.Z - BODY_FLOOR) < 0.02, under.min.Z
    # Борт: на плоскости платы материал по всему периметру, кроме прорези.
    # Верх меряется на +X (там бортика нет): плоскость платы остаётся z=10,0.
    rim_top = (part & bd.Pos(px1, py0, 0.0) * bd.Box(
        rim[2] - px1, py1 - py0, BOARD_Z + 2,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    )).bounding_box().max.Z
    assert abs(rim_top - BOARD_Z) < 0.02, rim_top
    rim_c = (px0 + (px1 - px0) / 2, (py0 + py1) / 2 + 6.0)  # борт не у прорези
    for p in (
        ((rim[0] + px0) / 2, rim_c[1]),
        ((px1 + rim[2]) / 2, rim_c[1]),
        (rim_c[0], (rim[1] + py0) / 2),
        (rim_c[0], (py1 + rim[3]) / 2),
    ):
        assert (
            part & bd.Pos(p[0], p[1], BOARD_Z - 0.3) * probe
        ).solids(), p
    # Прорезь под провода: в левом борту пусто до 2,0 вниз, ниже борт целый.
    assert not (part & bd.Pos((rim[0] + px0) / 2, sy, BOARD_Z - 0.5) * probe).solids()
    assert (
        part & bd.Pos((rim[0] + px0) / 2, sy, BOARD_Z - SLOT_H - 0.5) * probe
    ).solids()
    # Бортик по трём сторонам кармана (+X без него): верх на z=11,2, стенки на
    # центре каждой из трёх сторон — материал.
    lip_top = (part & bd.Pos(rim[0], rim[1], BOARD_Z) * bd.Box(
        rim[2] - rim[0], rim[3] - rim[1], 3.0, align=(bd.Align.MIN,) * 3
    )).bounding_box().max.Z
    assert abs(lip_top - (BOARD_Z + LIP_H)) < 0.02, lip_top
    for p in (
        (pcx, py0 - RIM_W / 2), (pcx, py1 + RIM_W / 2),
        # на −X посередине прорезь под провода — проба мимо неё
        (px0 - RIM_W / 2, sy - SLOT_W / 2 - 2.0),
        (px0 - RIM_W / 2, sy + SLOT_W / 2 + 2.0),
    ):
        assert (part & bd.Pos(p[0], p[1], BOARD_Z + 1.0) * probe).solids(), p
    # Над плоскостью платы в объёме платы пусто — изолента сверху ляжет плоско.
    board_air = bd.Pos(pcx - BOARD_W / 2, pcy - BOARD_D / 2, BOARD_Z) * bd.Box(
        BOARD_W, BOARD_D, 1.6, align=(bd.Align.MIN,) * 3
    )
    v_board_air = _vol(part, board_air)
    assert v_board_air < 1e-6, v_board_air
    # +X: бортика нет (проба выше плоскости платы — воздух), проём вентиляции
    # насквозь борта — воздух на z=8,5, материал ниже на z=6,0.
    vent_x = (px1 + rim[2]) / 2
    assert not (part & bd.Pos(vent_x, sy, BOARD_Z + 0.6) * probe).solids()
    assert not (part & bd.Pos(vent_x, sy, BOARD_Z - VENT_H / 2) * probe).solids()
    assert (part & bd.Pos(vent_x, sy, BOARD_Z - VENT_H - 1.0) * probe).solids()
    # До стенок полости 3 мм на плоскости платы.
    nest_gaps = (
        _mask(BOARD_Z, WALL).bounding_box().max.X - rim[2],
        _mask(BOARD_Z, WALL).bounding_box().max.Y - rim[3],
    )
    assert abs(nest_gaps[0] - NEST_GAP) < 0.02, nest_gaps
    assert abs(nest_gaps[1] - NEST_GAP) < 0.02, nest_gaps

    # Стволы языков панели (face.py: TONGUE_W 10,0, TONGUE_T 1,4, наружные грани
    # 3,5 впереди и 49,8 сзади) висят в полости от стыка до верха окна: корпус
    # их не задевает, до дна выемки остаётся не меньше 0,1.
    for x in CLIP_WIN_X:
        for y0 in (3.5, 48.4):
            shaft = bd.Pos(x - 5.0, y0, CLIP_WIN_Z1) * bd.Box(
                10.0, 1.4, TOP_Z - CLIP_WIN_Z1, align=(bd.Align.MIN,) * 3
            )
            v_shaft = _vol(part, shaft)
            assert v_shaft < 1e-6, (x, y0, v_shaft)
        for z in (CLIP_WIN_Z1 + 0.05, 50.0, TOP_Z - 0.05):
            bb = (
                part & bd.Pos(x, NICHE_CY, z) * bd.Box(2 * RELIEF_HALF, 300, 0.05)
            ).bounding_box()
            assert 3.5 - bb.min.Y > 0.1 and bb.max.Y - 49.8 > 0.1, (
                x, z, 3.5 - bb.min.Y, bb.max.Y - 49.8
            )

    # Защёлка: одна деталь с корпусом, гнездо пусто, вварена в стенку.
    assert len(part.solids()) == 1, len(part.solids())
    assert not (part & bd.Pos(cx, cy, zc) * probe).solids(), "гнездо"
    # Сварка: пластина утоплена в стенку на CLIP_SINK, материал зажима заходит
    # в объём стенки — это сплошной материал, а не касание поверхностями.
    wall_slab = bd.Pos(wall_x, cy, zc) * bd.Box(
        WALL, 14.0, 7.0,
        align=(bd.Align.MAX, bd.Align.CENTER, bd.Align.CENTER),
    )
    buried = _vol(clip, wall_slab)
    assert buried > 1.0, buried
    # Тыл гнезда: от стенки гнезда до наружной грани левой стенки.
    back = (cx - CLIP_BORE / 2) - (wall_x - WALL)
    assert back > 0.8, back
    # Гнездо не прорезает стенку: от его min x до внутренней грани стенки.
    gap_wall = (cx - CLIP_BORE / 2) - wall_x
    assert gap_wall > 0.0, gap_wall
    # Срез пластины: кольцо целое — объём в обойме до и после среза одинаков,
    # ушёл только материал пластины вне обоймы (объём печатается). Заливка
    # щелей в обойму R_outer не заходит вовсе, поэтому кольцо меряется уже на
    # готовом зажиме.
    v_ring0 = _vol(clip0, sleeve)
    v_ring = _vol(clip, sleeve)
    assert v_ring > 0.0 and abs(v_ring - v_ring0) < 1e-6, (v_ring0, v_ring)
    assert _vol(seam, sleeve) < 1e-6, _vol(seam, sleeve)
    v_cut = clip0.volume - clip_cut.volume
    # Заливка щелей: губы и зев не тронуты — объём зажима в зоне губ (перед
    # линией щели, впереди грани стенки) до и после заливки одинаков, а в
    # 0,3 перед гранью стенки в габарите прилегания воздуха не осталось.
    lips = bd.Pos(cx, cy + 1.0, cbb.min.Z) * bd.Box(
        1.6, 6.4, cbb.size.Z, align=(bd.Align.MAX, bd.Align.MIN, bd.Align.MIN)
    )
    v_lips0 = _vol(clip_cut, lips)
    v_lips = _vol(clip, lips)
    assert abs(v_lips - v_lips0) < 1e-6, (v_lips0, v_lips)
    band = seam_prism & bd.Pos(wall_x, cy, zc) * bd.Box(
        0.3, 14.0, 7.0, align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER)
    )
    v_band = band.volume
    v_air = (band - part).volume
    assert v_band > 1.0 and v_air < 1e-6, (v_band, v_air)
    # Гнездо пусто под кабель: стержень Ø2,8 по оси на всю высоту зажима.
    rod = bd.Pos(cx, cy, cbb.min.Z - 1) * bd.Cylinder(
        1.4, cbb.size.Z + 2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    v_rod = _vol(part, rod)

    def _side(d):
        """Стержень вбок по линии щели зева, от наружной обоймы к оси гнезда."""
        start = bd.Vector(cx - CLIP_MOUTH_X, cbb.max.Y + 2.0, zc)
        aim = bd.Vector(cx - CLIP_MOUTH_X, cy, zc)
        return bd.sweep(
            bd.Plane(origin=start, z_dir=aim - start) * bd.Circle(d / 2),
            path=bd.Line(start, aim),
        )

    assert v_rod < 1e-6, v_rod
    # Зев смотрит вдоль стенки в +y, в полость: замкнутая часть кольца — со
    # стороны полости (+x), щель открыта в +y и сдвинута к стенке (−x).
    assert (part & bd.Pos(cx + 2.0, cy, zc) * probe).solids(), "кольцо в полость"
    assert not (part & bd.Pos(cx - CLIP_MOUTH_X, cy + 2.2, zc) * probe).solids(), (
        "щель в +y"
    )
    # Зев уже кабеля: Ø3,0 и Ø2,0 вбок не проходят — губы держат, Ø0,7 проходит
    # (щель эталона 2,0 при внешнем масштабе → 1,16; кабель вдавливается с
    # разжимом кольца, как у покупного зажима).
    v_lip = _vol(part, _side(CABLE_D))
    v_2 = _vol(part, _side(2.0))
    v_slit = _vol(part, _side(0.7))
    assert v_lip > 0.3 and v_2 > 0.3, (v_lip, v_2)
    assert v_slit < 0.02, v_slit
    # Провод входит в окно поперёк Y у x=8,5, спускается в полость рядом с
    # обоймой (её верх z=47), на z=50 над зажимом уходит по его верху к оси
    # гнезда и вниз сквозь гнездо к разъёму платы. Разъём платы смотрит в
    # сторону зажима: гнездо в правом заднем углу, торец разъёма — у левого
    # борта гнезда, над его верхом.
    conn = bd.Vector(55.0, 30.0, BOARD_Z + 0.8)
    # Окно открыто на всю толщину стенки: стержень Ø3 поперёк Y на высоте окна
    # (x=8,5 — общая зона канала панели 5,2..11,4 и окна 5,6..12,5) пуст.
    gate = bd.Pos(8.5, 2.3, TOP_Z - 2.0) * bd.Cylinder(1.5, 9.0, rotation=(90, 0, 0))
    v_gate = _vol(part, gate)
    assert v_gate < 1e-6, v_gate
    corner = bd.Vector(8.5, 6.0, 50.0)
    bend = bd.Vector(cx, cy, 50.0)
    v_above = v_gate
    for start, end in ((bd.Vector(8.5, 6.5, TOP_Z - 2.0), corner), (corner, bend)):
        leg = bd.sweep(
            bd.Plane(origin=start, z_dir=end - start) * bd.Circle(1.5),
            path=bd.Line(start, end),
        )
        v_leg = _vol(part, leg)
        assert v_leg < 1e-6, (start, end, v_leg)
        v_above = max(v_above, v_leg)
    v_below = 0.0
    for start, end in (
        (bd.Vector(cx, cy, cbb.min.Z - 2.0), bd.Vector(55.0, 30.0, 16.0)),
        (bd.Vector(55.0, 30.0, 16.0), conn),
    ):
        leg = bd.sweep(
            bd.Plane(origin=start, z_dir=end - start) * bd.Circle(1.5),
            path=bd.Line(start, end),
        )
        v_leg = _vol(part, leg)
        assert v_leg < 1e-6, (start, end, v_leg)
        v_below = max(v_below, v_leg)

    # Окна под крючки: сквозные — в центре окна пусто на всю стенку, над кромкой
    # (z=43,2) и под низом (z=34,5) стенка целая.
    for x in CLIP_WIN_X:
        for front in (True, False):
            zc_win = (CLIP_WIN_Z0 + CLIP_WIN_Z1) / 2
            out_b = _mask(zc_win).bounding_box()
            in_b = _mask(zc_win, WALL).bounding_box()
            y = (out_b.min.Y + in_b.min.Y) / 2 if front else (out_b.max.Y + in_b.max.Y) / 2
            assert not (
                part
                & bd.Pos(x, y, (CLIP_WIN_Z0 + CLIP_WIN_Z1) / 2) * bd.Box(0.2, 0.2, 0.2)
            ).solids(), (x, front)
            for z in (CLIP_WIN_Z1 + 0.7, CLIP_WIN_Z0 - 1.0):
                # 0,3 от наружной грани на этой высоте: выше окна стенка тоньше
                # из-за выемки под ствол, середина окна там уже пустая.
                edge_z = _mask(z).bounding_box()
                y_z = (edge_z.min.Y + 0.3) if front else (edge_z.max.Y - 0.3)
                assert (
                    part & bd.Pos(x, y_z, z) * bd.Box(0.2, 0.2, 0.2)
                ).solids(), (x, front, z)
    print(
        f"защёлка из файла: гнездо {v_rod:.4f}, окно→гнездо {v_above:.4f}, "
        f"к разъёму {v_below:.4f}, "
        f"кабель Ø{CABLE_D:g} в зеве {v_lip:.2f}, Ø2,0 {v_2:.2f}, "
        f"щель Ø0,7 {v_slit:.4f} мм³"
    )

    print(
        f"корпус z={BODY_FLOOR:g}..{part_top:.2f}, стенка {wall_t:.2f} мм, "
        f"дно {floor_box.min.Z:g}..{floor_box.max.Z:g} (толщина "
        f"{floor_box.max.Z - floor_box.min.Z:.2f}), "
        f"низ {bottom.X:.1f}×{bottom.Y:.1f} мм, уклон {BODY_DRAFT:g}°/сторона, "
        f"ступенька на стыке {STEP:g} (итого {FIT + STEP:g} до кармана); "
        f"окна {CLIP_WIN_W:g}×{CLIP_WIN_Z1 - CLIP_WIN_Z0:g} "
        f"x={CLIP_WIN_X[0]:g}/{CLIP_WIN_X[1]:g} z={CLIP_WIN_Z0:g}..{CLIP_WIN_Z1:g}, "
        f"без фаски (полка {WALL - TONGUE_RELIEF:g}), выемки под стволы "
        f"±{RELIEF_HALF:g}×{TONGUE_RELIEF:g} z={CLIP_WIN_Z1:g}..{TOP_Z:g}; "
        f"зазор до реального кармана {min(g[1] for g in gaps):.2f}.."
        f"{max(g[1] for g in gaps):.2f} по X и {min(g[2] for g in gaps):.2f}.."
        f"{max(g[2] for g in gaps):.2f} по Y на "
        f"{'/'.join(f'{g[0]:g}' for g in gaps)}"
    )
    print(
        "зазор до реальной ниши по z: "
        + ", ".join(f"{z:g}: {gx:.2f}/{gy:.2f}" for z, gx, gy in gaps)
        + " мм (X/Y)"
    )
    print(
        f"гнездо платы {BOARD_W:g}×{BOARD_D:g}+{BOARD_CLEAR:g} → "
        f"{px1 - px0:g}×{py1 - py0:g} внутри, борт {RIM_W:g} "
        f"(x {rim[0]:.1f}..{rim[2]:.1f}, y {rim[1]:.1f}..{rim[3]:.1f}), "
        f"плоскость платы z={BOARD_Z:g}, дно z={pocket_floor:g} "
        f"(ниже на {BOARD_POCKET_H:g}), до стенок "
        f"{nest_gaps[0]:.2f}/{nest_gaps[1]:.2f}, прорезь {SLOT_W:g}×{SLOT_H:g} "
        f"в левом борту y={sy:.1f}, углы кармана R{BOARD_R:g}; бортик {LIP_H:g} "
        f"по трём сторонам (верх z={lip_top:.1f}, +X без бортика, проём "
        f"{VENT_W:g}×{VENT_H:g} z={BOARD_Z - VENT_H:g}..{BOARD_Z:g}); "
        f"разъём платы x≈{conn.X:g} y≈{conn.Y:g} "
        f"z={conn.Z:g}"
    )
    print(
        f"защёлка кабеля по образцу Cable clip tape.stl, масштаб 1:{1 / CLIP_OUT:.2f}, "
        f"гнездо {CLIP_BORE:g} (эталон Ø{clip_ref.BORE_D:g} перерезан), "
        f"зев {clip_ref.MOUTH_D * CLIP_OUT:.2f} (эталон {clip_ref.MOUTH_D:g}), "
        f"y={CLIP_Y:g}, z={cbb.min.Z:.2f}..{cbb.max.Z:.2f}; "
        f"габарит {cbb.size.Y:.2f}×{cbb.size.X:.2f}×{cbb.size.Z:.2f} мм, "
        f"в полость {cbb.max.X - wall_x:.2f} мм, ось x={cx:.2f} "
        f"({cx - wall_x:.2f} от внутренней грани, тыл {back:.2f} до наружной, "
        f"до стенки гнезда {gap_wall:.2f}), утоплено {CLIP_SINK:.2f}, "
        f"вварено {buried:.2f} мм³; пластина срезана заподлицо {v_cut:.2f} мм³ "
        f"(выступало {CLIP_PLATE_OUT:.2f} из {clip_ref.PLATE_T * CLIP_OUT:.2f}), "
        f"обойма R{clip_ref.SLEEVE_R * CLIP_OUT:.3f} целая: "
        f"кольцо {v_ring:.2f} мм³; торец пластины залит до грани стенки "
        f"{seam.volume:.2f} мм³ (в {len(seam.solids())} щелях), "
        f"воздуха в 0,3 перед гранью {v_air:.4f} из {v_band:.2f} мм³, "
        f"губы {v_lips:.2f} мм³"
    )
    return part


if __name__ == "__main__":
    body()
