# -*- coding: utf-8 -*-
"""Прижимная планка энкодера — держит корпус в кармане панели снизу.

Корпус ALPS EC11E (encoder.py) входит в панель снизу, а втулка у него гладкая
Ø7,0 — гайкой притягивать нечем. Нажатие на кнопку (6 Н) выдавливает корпус
вниз из кармана, поэтому снизу ставится планка: плоская площадка упирается в
неподвижную бобышку-трещотку Ø8,0 на задней плоскости корпуса и прижимает
корпус к перемычке панели.

Как ставится: припаять пять проводов к выводам, вставить корпус в карман
панели сверху, надвинуть планку снизу и завернуть два самореза M3×12 в
глухие пилоты Ø2,5×10 панели (face.py, ky±12), головки снизу. Продевать
нечего: провода висят по бокам плиты, планка заходит между ними. Саморез
тянет плиту к панели, площадка упирается в корпус — корпус зажат между
площадкой и перемычкой, кнопку можно давить сколько угодно. После установки
планки паять уже нечем, поэтому пайка — первым шагом.

Почему плита узкая: энкодер повёрнут в панели на 90° (face.py, ENC_ROT), его
два ряда выводов смотрят по X — три на x=−7,5, два на x=+7,0 (Ø1,0, размах
15,5). Плита 10,0 по X уже размаха: провода обоих рядов уходят вниз по её
бокам, каждый на свой вывод. Конверт провода Ø3,0 (WIRE_D) даёт 0,5 запаса
у ряда +7,0 и 1,0 у ряда −7,5.

Площадка плоская, без пазов и гнезда: она жмёт неподвижную бобышку-трещотку
Ø8,0 на задней плоскости корпуса (выступ 0,3), а не само тело, поэтому её
верх — плоскость трещотки. По Y она 8,4: лапки после поворота стоят на
y=±5,5 (внутренняя кромка 4,75), до кромки площадки 0,55 на сторону. По X
она 10,0: от кромки до оси ближнего ряда выводов 7,0 — 1,5 с запасом на
гуляние корпуса в кармане ±0,2.

Плита идёт вдоль Y, а не вдоль X, как просилось: по X от оси вала до полости
корпуса всего 10,4 мм (внутренний поясок корпуса), а саморез с запасом 1,5 мм
до торца плиты требует 14,15 — плита 25 по X врезается в корпус на 48 мм³
(проверено на телах). По Y полость 42 мм, там планка встаёт свободно. Поэтому
плита 10,0×30,3 и саморезы на ky±12, а не на kx±11.

Печать FDM, сопло 0,4 мм, слой 0,2 мм, PETG или ASA: плитой на стол,
площадкой вверх. Площадка — цельный прямоугольник, свесов нет — поддержки нет.
Запуск: cad run v2/modeling/clamp.py
"""

import build123d as bd
from cad import model

from encoder import (
    ENC_BODY_T,
    ENC_EAR_W,
    ENC_EAR_X,
    ENC_PIN_D,
    ENC_PINS,
    ENC_ROTOR_D,
    ENC_ROTOR_H,
)
from face import SEAT_FIT, deck_bottom, seat_front_z

# Плита: по X уже размаха выводов 15,5 — провода проходят по бокам; по Y — под
# саморезы.
PLATE_X = 10.0
PLATE_T = 3.0
CORNER_R = 1.5
# Площадка: по Y между лапками (после поворота на 90° они на y=±5,5, кромка
# 4,75 — зазор 0,55 на сторону) и перекрывает трещотку Ø8,0; по X — до выводов.
PAD_X = 10.0
PAD_Y = 8.4
# Саморезы M3: ось на ky±12 (от кромки отверстия до стенки кармана энкодера
# 3,9 материала), Ø3,3; до торца плиты остаётся 1,5 материала.
SCREW_DY = 12.0
SCREW_D = 3.3
SCREW_WALL = 1.5
PLATE_Y = 2 * (SCREW_DY + SCREW_D / 2 + SCREW_WALL)  # 30,3
# Конверт провода: Ø3,0 на жилу, с пайкой и термоусадкой. Провода идут мимо
# плиты, на своём выводе каждый.
WIRE_D = 3.0
# Ряды выводов в рамке энкодера идут по Y; после поворота на 90° (face.ENC_ROT)
# они ложатся на X планки — просвет до них берём по |py|.
PIN_ROW_X = min(abs(py) for _, py in ENC_PINS)  # 7,0: ближний ряд
WIRE_FREE = PIN_ROW_X - PLATE_X / 2 - WIRE_D / 2  # 0,5 у конверта Ø3,0


def plate_bottom_z():
    """Низ плиты: на толщину плиты ниже низа панели."""
    return deck_bottom() - PLATE_T


def pad_top_z():
    """Верх площадки — плоскость трещотки: тело корпуса выше на её выступ."""
    return seat_front_z() - ENC_BODY_T - ENC_ROTOR_H


def pad_h():
    """Высота площадки над низом панели."""
    return pad_top_z() - deck_bottom()


@model
def clamp():
    plate = bd.extrude(
        bd.Plane.XY * bd.RectangleRounded(PLATE_X, PLATE_Y, CORNER_R), PLATE_T
    )
    for side in (-1, 1):
        plate -= bd.Pos(0, side * SCREW_DY, -0.5) * bd.Cylinder(
            SCREW_D / 2,
            PLATE_T + 1.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    plate.label = "plate"
    plate.color = "#9aa0a8"

    top = PLATE_T + pad_h()
    pad = bd.Pos(0, 0, PLATE_T) * bd.Box(
        PAD_X, PAD_Y, pad_h(), align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    pad.label = "pad"
    pad.color = "#9aa0a8"

    part = bd.Compound(children=[plate, pad], label="clamp")

    box = part.bounding_box()
    assert abs(box.size.X - PLATE_X) < 0.01, box.size.X
    assert abs(box.size.Y - PLATE_Y) < 0.01, box.size.Y
    assert abs(box.min.Z) < 0.01, box.min.Z
    assert abs(box.max.Z - top) < 0.01, box.max.Z
    # В сборке плита встаёт ровно под низ панели, площадка — в плоскость трещотки.
    assert abs(plate_bottom_z() + PLATE_T - deck_bottom()) < 0.01
    assert abs(plate_bottom_z() + top - pad_top_z()) < 0.01
    # Площадка стоит на плите всей площадью: свесов нет ни по X, ни по Y.
    assert PAD_X <= PLATE_X and PAD_Y <= PLATE_Y, (PAD_X, PAD_Y)
    for px, py in ((PAD_X / 2 - 0.1, 0), (-PAD_X / 2 + 0.1, 0), (0, PAD_Y / 2 - 0.1)):
        assert (
            part & bd.Pos(px, py, PLATE_T - 0.1) * bd.Box(0.2, 0.2, 0.2)
        ).solids(), (px, py)
    # Верх площадки плоский и сплошной: центр и четыре угла.
    probes = [(0, 0)] + [
        (sx * (PAD_X / 2 - 0.1), sy * (PAD_Y / 2 - 0.1))
        for sx in (-1, 1)
        for sy in (-1, 1)
    ]
    for px, py in probes:
        assert (
            part & bd.Pos(px, py, top - 0.1) * bd.Box(0.2, 0.2, 0.2)
        ).solids(), (px, py)
    # Площадка между лапками: их внутренняя кромка y=±4,75, а кромка площадки
    # плюс гуляние корпуса в кармане и запас 0,1 — меньше.
    assert PAD_Y / 2 + SEAT_FIT + 0.1 < ENC_EAR_X - ENC_EAR_W / 2, PAD_Y
    # Площадка не наезжает на выводы по X: до оси ближнего ряда 7,0.
    assert PAD_X / 2 + SEAT_FIT + 0.1 < PIN_ROW_X - ENC_PIN_D / 2, PAD_X
    # Площадка перекрывает трещотку Ø8,0 на обоих осях: жмёт её, а не тело.
    assert PAD_X / 2 > ENC_ROTOR_D / 2 and PAD_Y / 2 > ENC_ROTOR_D / 2, (PAD_X, PAD_Y)
    # Саморезы: сквозь плиту, до торца плиты ровно SCREW_WALL материала.
    for side in (-1, 1):
        assert not (
            part & bd.Pos(0, side * SCREW_DY, PLATE_T / 2) * bd.Box(0.2, 0.2, 0.2)
        ).solids()
        assert (
            part
            & bd.Pos(0, side * (SCREW_DY + SCREW_D / 2 + 0.75), PLATE_T / 2)
            * bd.Box(0.2, 0.2, 0.2)
        ).solids()
    assert abs(PLATE_Y / 2 - SCREW_DY - SCREW_D / 2 - SCREW_WALL) < 0.01, PLATE_Y
    # Провода проходят по бокам плиты, а не сквозь неё: конверт Ø3,0 на жилу
    # целиком встаёт между кромкой плиты и осью своего вывода.
    assert WIRE_FREE >= 0, WIRE_FREE
    pin_gap = PIN_ROW_X - ENC_PIN_D / 2 - PAD_X / 2  # 1,5
    ear_gap = ENC_EAR_X - ENC_EAR_W / 2 - PAD_Y / 2  # 0,55 на сторону
    far_row_x = max(abs(py) for _, py in ENC_PINS)  # 7,5
    pin_span = PIN_ROW_X + far_row_x + ENC_PIN_D  # 15,5

    print(
        f"планка {box.size.X:.1f}×{box.size.Y:.1f}×{box.size.Z:.2f}: "
        f"плита {PLATE_T:g} на z={plate_bottom_z():.2f}..{deck_bottom():g}, "
        f"площадка плоская {PAD_X:g}×{PAD_Y:g} до z={pad_top_z():.2f} (жмёт трещотку), "
        f"до выводов по X {pin_gap:.2f}, до лапок по Y {ear_gap:.2f} на сторону, "
        f"тело {ENC_BODY_T:g}; "
        f"саморезы Ø{SCREW_D:g} на ky±{SCREW_DY:g} до торца {SCREW_WALL:g}; "
        f"плита {PLATE_X:g} уже размаха выводов {pin_span:g}: провода идут по "
        f"бокам, свободно {WIRE_FREE:.2f} у x=+{PIN_ROW_X:g} и "
        f"{far_row_x - PLATE_X / 2 - WIRE_D / 2:.2f} у x=−{far_row_x:g}"
    )
    return part


if __name__ == "__main__":
    clamp()
