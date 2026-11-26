# -*- coding: utf-8 -*-
"""Энкодер ALPS EC11E15244G1 — эталонная модель для проверок сборки.

Не печатная деталь, а контекст: по ней проверяются окно под корпус в панели,
отверстие под втулку Ø7,0 и место вала с крутилкой. Здесь только габариты
из даташита, никакой второй копии чужих деталей.

Ось вала — +Z, Z=0 — передняя плоскость корпуса, из неё выходит втулка;
сам корпус ниже Z=0.

  z = 0..−4,3       корпус 11,7×12,0, в плане R0,5
  z = −4,3..−3,8    «уголки» выводов: из бока корпуса наружу, 0,8×0,5
  z = −4,3..−8,3    две лапки 1,5×2,6, центры x=±5,5, выступ 4,0
  z = −4,3..−7,8    пять выводов Ø1,0 вниз от оси ряда
  z = −4,3..−4,6    бобышка-трещотка Ø8,0 на оси, выступ до 0,3
  z = 0..+7         втулка Ø7,0
  z = 0..+20        вал Ø6,0, торец с фаской 0,5
  z = +10..+20      лыска D: срез до 4,5 по Y со стороны +Y

Выводы (вид снизу): два ряда, между рядами 14,5. Три энкодера (A/C/B) на
y=−7,5 при x=−2,5, 0, +2,5 и два кнопки (D/E) на y=+7,0 при x=±2,5. Вывод
выходит из бока зелёного основания и загибается вниз: горизонтальный
«уголок» от кромки корпуса (y=±6,0) до оси вывода, и только потом
вертикально вниз.

Числа — даташит ALPS EC11E (серия 30 импульсов с кнопкой, Drawing No.2 и
KiCad-футпринт): корпус 11,7×12,0, вал Ø6,0 с лыской 4,5 (размер поперёк
лыски), втулка гладкая Ø7,0×7,0 (резьбы и гайки у EC11E нет — M7×0,75 у
горизонтальной серии EC11B), выводы Ø1,0, два ряда на +7,0/−7,5, лапки
1,5×2,6 с центрами ±5,5. Толщина корпуса 4,3 (в каталоге 4,5), выступ лапок
4,0 и бобышка Ø8 — замер корпуса штангенциркулем 21.11.2026: в каталоге эти
числа не заданы. ENC_PUSH —
фаска торца вала.

Запуск: cad run v2/modeling/encoder.py
"""

import build123d as bd
from cad import model

ENC_BODY_X = 11.7
ENC_BODY_Y = 12.0
ENC_BODY_T = 4.3  # замер пользователя 21.11.2026, в каталоге 4,5
ENC_BODY_R = 0.5  # скругление корпуса в плане
ENC_EAR_X = 5.5  # центр лапки по X: наружные кромки ±6,25, габарит 12,5
ENC_EAR_W = 1.5  # ширина лапки по X
ENC_EAR_Y = 2.6  # толщина лапки по Y
ENC_EAR_T = 4.0  # выступ лапки вниз: замер пользователя 21.11, в каталоге не задан
ENC_BUSH_D = 7.0
ENC_BUSH_L = 7.0
ENC_SHAFT_D = 6.0
ENC_SHAFT_L = 20.0
ENC_FLAT = 4.5  # размер вала по Y в месте лыски
ENC_FLAT_Z0 = 10.0  # откуда начинается лыска
ENC_PUSH = 0.5  # фаска торца вала
ENC_PIN_D = 1.0
ENC_PIN_L = 3.5
ENC_PIN_CW = 0.8  # «уголок» вывода: ширина по X
ENC_PIN_CH = 0.5  # «уголок» вывода: высота, от −4,5 до −4,0
ENC_ROTOR_D = 8.0  # бобышка-трещотка на задней плоскости
ENC_ROTOR_H = 0.3  # её выступ, также замер, в каталоге не задан
ENC_SHAFT_TOP = 20.0

# Пять выводов: три энкодера на −7,5 и два кнопки на +7,0, между рядами 14,5.
ENC_PINS = (
    (-2.5, -7.5),
    (0.0, -7.5),
    (2.5, -7.5),
    (-2.5, 7.0),
    (2.5, 7.0),
)


def _body():
    """Корпус 11,7×12,0 вниз от Z=0, скругления в плане R0,5."""
    return bd.Pos(0, 0, -ENC_BODY_T) * bd.extrude(
        bd.Plane.XY * bd.RectangleRounded(ENC_BODY_X, ENC_BODY_Y, ENC_BODY_R),
        ENC_BODY_T,
    )


def _ears(body):
    """Две лапки по бокам: 1,5×2,6, вниз от задней плоскости на 4,0."""
    ear = bd.Pos(0, 0, -ENC_BODY_T - ENC_EAR_T) * bd.Box(
        ENC_EAR_W,
        ENC_EAR_Y,
        ENC_EAR_T,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    return body + bd.Pos(-ENC_EAR_X, 0, 0) * ear + bd.Pos(ENC_EAR_X, 0, 0) * ear


def _bush():
    """Втулка Ø7,0 от Z=0 до +7 — гладкий наружный контур резьбы M7×0,75."""
    return bd.Cylinder(
        ENC_BUSH_D / 2,
        ENC_BUSH_L,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )


def _shaft():
    """Вал Ø6,0 до +20: лыска со стороны +Y на z=10..20, торец с фаской 0,5."""
    flat_y = ENC_FLAT - ENC_SHAFT_D / 2  # плоскость лыски: остаётся 4,5 по Y
    shaft = bd.Cylinder(
        ENC_SHAFT_D / 2,
        ENC_SHAFT_L,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    shaft -= bd.Pos(0, flat_y, ENC_FLAT_Z0) * bd.Box(
        2 * ENC_SHAFT_D,
        ENC_SHAFT_D,
        ENC_SHAFT_TOP - ENC_FLAT_Z0,
        align=(bd.Align.CENTER, bd.Align.MIN, bd.Align.MIN),
    )
    top = [e for e in shaft.edges() if abs(e.center().Z - ENC_SHAFT_TOP) < 0.01]
    assert len(top) == 3, [edge.length for edge in top]  # две дуги и ребро лыски
    return bd.chamfer(top, ENC_PUSH)


def _pins():
    """Пять выводов Ø1,0: «уголок» из бока корпуса наружу, потом вниз на 3,5."""
    pin = bd.Cylinder(
        ENC_PIN_D / 2,
        ENC_PIN_L,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    )
    pins = []
    for x, y in ENC_PINS:
        edge = ENC_BODY_Y / 2 if y > 0 else -ENC_BODY_Y / 2
        corner = bd.Pos(x, (edge + y) / 2, -ENC_BODY_T) * bd.Box(
            ENC_PIN_CW,
            abs(y - edge),
            ENC_PIN_CH,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        item = bd.Pos(x, y, -ENC_BODY_T) * pin + corner
        item.label = "enc_pin"
        item.color = "#c0a060"
        pins.append(item)
    return bd.Compound(children=pins, label="enc_pins")


def _rotor():
    """Трещотка: бобышка Ø8,0 под задней плоскостью, выступ до 0,3."""
    return bd.Pos(0, 0, -ENC_BODY_T - ENC_ROTOR_H) * bd.Cylinder(
        ENC_ROTOR_D / 2,
        ENC_ROTOR_H,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )


def _section(part, z, thick=0.1):
    """Габарит сечения в тонком срезе на высоте z — по геометрии, не по константам."""
    slab = bd.Pos(0, 0, z) * bd.Box(40, 40, thick)
    return (part & slab).bounding_box().size


@model
def encoder():
    body = _body()
    box = body.bounding_box()
    # Корпус — ровно 11,7×12,0, верх на Z=0 (мерим до приклейки лапок: они шире).
    assert abs(box.size.X - ENC_BODY_X) < 0.01, box.size.X
    assert abs(box.size.Y - ENC_BODY_Y) < 0.01, box.size.Y
    assert abs(box.max.Z) < 0.01, box.max.Z

    parts = [_ears(body), _bush(), _shaft(), _pins(), _rotor()]
    for part, label, color in zip(
        parts,
        ("enc_body", "enc_bush", "enc_shaft", "enc_pins", "enc_rotor"),
        ("#b8bcc2", "#b8bcc2", "#d7dade", "#c0a060", "#b8bcc2"),
    ):
        part.label = label
        part.color = color
    whole = bd.Compound(children=parts, label="encoder")
    assert len(whole.children) == 5, len(whole.children)

    # Габарит по Z: лапки до −8,5, выводы до −8,0, торец вала +20.
    box = whole.bounding_box()
    assert abs(box.min.Z + ENC_BODY_T + ENC_EAR_T) < 0.01, box.min.Z
    assert abs(box.max.Z - ENC_SHAFT_TOP) < 0.01, box.max.Z
    # Лапки шире корпуса: 2·(5,5 + 0,75) = 12,5 по X, низ −8,5.
    ears = parts[0].bounding_box()
    assert abs(ears.size.X - 2 * (ENC_EAR_X + ENC_EAR_W / 2)) < 0.01, ears.size.X
    assert abs(ears.min.Z + ENC_BODY_T + ENC_EAR_T) < 0.01, ears.min.Z
    # Выводы: ряды 14,5 между осями (габарит 15,5 с Ø1,0), низ −8,0, «уголки» на ±7,5/±7,0.
    pins = parts[3].bounding_box()
    assert abs(pins.size.Y - (14.5 + ENC_PIN_D)) < 0.01, pins.size.Y
    assert abs(pins.size.X - (2 * 2.5 + ENC_PIN_D)) < 0.01, pins.size.X
    assert abs(pins.max.Z + ENC_BODY_T - ENC_PIN_CH) < 0.01, pins.max.Z
    assert abs(pins.min.Z + ENC_BODY_T + ENC_PIN_L) < 0.01, pins.min.Z
    # Бобышка Ø8,0 — на 0,3 ниже задней плоскости, уже лапок и выводов.
    rotor = parts[4].bounding_box()
    assert abs(rotor.size.X - ENC_ROTOR_D) < 0.01, rotor.size.X
    assert abs(rotor.min.Z + ENC_BODY_T + ENC_ROTOR_H) < 0.01, rotor.min.Z
    # Втулка Ø7,0 посередине своей высоты; вал на z=15: Ø6,0 по X, лыска 4,5 по Y.
    bush = _section(whole, ENC_BUSH_L / 2)
    assert abs(bush.X - ENC_BUSH_D) < 0.05, bush.X
    assert abs(bush.Y - ENC_BUSH_D) < 0.05, bush.Y
    shaft = _section(whole, 15.0)
    assert abs(shaft.X - ENC_SHAFT_D) < 0.05, shaft.X
    assert abs(shaft.Y - ENC_FLAT) < 0.05, shaft.Y

    print(
        f"энкодер EC11E: корпус {ENC_BODY_X:g}×{ENC_BODY_Y:g}×{ENC_BODY_T:g} "
        f"R{ENC_BODY_R:g}, лапки {ENC_EAR_W:g}×{ENC_EAR_Y:g} до z={ears.min.Z:.1f} "
        f"по x=±{ENC_EAR_X:g} (габарит {ears.size.X:.1f} по X); "
        f"выводы Ø{ENC_PIN_D:g}×{ENC_PIN_L:g} в {len(ENC_PINS)} шт, "
        f"ряды y=+7,0/−7,5 ({pins.size.Y:.1f} с Ø), до z={pins.min.Z:.1f}; "
        f"трещотка Ø{ENC_ROTOR_D:g} до z={rotor.min.Z:.1f}; "
        f"втулка Ø{bush.X:.2f} z=0..{ENC_BUSH_L:g}; "
        f"вал Ø{shaft.X:.2f} до z={box.max.Z:.1f}, лыска {shaft.Y:.2f} по Y "
        f"с z={ENC_FLAT_Z0:g}, фаска {ENC_PUSH:g}; "
        f"габарит {box.size.X:.1f}×{box.size.Y:.1f}×{box.size.Z:.1f} мм"
    )
    return whole


if __name__ == "__main__":
    encoder()
