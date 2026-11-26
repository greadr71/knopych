# -*- coding: utf-8 -*-
"""Сборка: ниша + панель + корпус + энкодер с ручкой и планкой прижима.

Ниша (карман и обод) полупрозрачная: это контекст машины, не наша деталь.
Панель, корпус, энкодер, планка прижима и ручка — ровно те тела, что печатаются
(или берутся с полки) из face.py, body.py, encoder.py, clamp.py, knob_knurl.py
и keycaps.py, собраны вызовом их же функций: никакой второй копии геометрии.
Проверка здесь одна — детали не должны пересекаться, и зазоры посадки видны
числами в сводке.

Запуск: cad run v2/modeling/assembly.py
"""

import build123d as bd
from cad import model

import body as body_part
import clamp as clamp_part
import encoder as encoder_part
import face as face_part
import keycaps as keycap_part
import knob_knurl as knob_part
import niche_panel as niche


def _painted(part, label, color):
    part.label = label
    part.color = color
    return part


@model
def assembly():
    panel = _painted(face_part.face.__wrapped__(), "face", "#141619")
    shell = _painted(body_part.body.__wrapped__(), "body", "#4f7fb0")
    niche_body, _pocket, _shelf = niche._niche_body()
    rim, _void = niche._rim()
    niche_body = _painted(niche_body, "niche", "#8f9aa8" + "55")
    rim = _painted(rim, "rim", "#8f9aa8" + "77")

    # Энкодер: передняя плоскость корпуса — на дне кармана в панели, втулка
    # смотрит вверх. Повёрнут на ENC_ROT, как и карман в панели. Ручка садится
    # низом на 1,0 выше дна углубления — с тем же поворотом, иначе её лыска в
    # гнезде D не совпадёт с лыской вала.
    kx, ky = niche.knob_center()
    enc_rot = bd.Rot(0, 0, face_part.ENC_ROT)
    encoder = _painted(
        bd.Pos(kx, ky, face_part.seat_front_z()) * enc_rot * encoder_part.encoder.__wrapped__(),
        "encoder",
        "#b8bcc2",
    )
    knob = _painted(
        bd.Pos(kx, ky, face_part.knob_bottom_z())
        * enc_rot
        * knob_part.knob_knurl.__wrapped__(),
        "knob",
        "#1c1e22",
    )
    # Поворот действительно применён: ряды выводов теперь по X — размах 15,5 при
    # собственных 6,0 по Y, а три вывода на −X уводят центр габарита от оси вала
    # в минус (−0,25; при нулевом угле было бы +0,25). Дочернее тело меряется в
    # своей рамке, поэтому ту же посадку применяем к нему ещё раз.
    pin_span = (
        max(abs(py) for _, py in encoder_part.ENC_PINS)
        + min(abs(py) for _, py in encoder_part.ENC_PINS)
        + encoder_part.ENC_PIN_D
    )
    pins = bd.Pos(kx, ky, face_part.seat_front_z()) * enc_rot * next(
        child for child in encoder.children if child.label == "enc_pins"
    )
    pins_box = pins.bounding_box()
    assert abs(pins_box.size.X - pin_span) < 0.05, pins_box.size.X
    assert pins_box.center().X < kx, pins_box.center().X - kx
    # Планка прижима: снизу в карман, плита под низом панели, плоская площадка —
    # в плоскость трещотки (жмёт её, лапки проходят по бокам с зазором).
    clamp = _painted(
        bd.Pos(kx, ky, face_part.deck_bottom() - clamp_part.PLATE_T)
        * clamp_part.clamp.__wrapped__(),
        "clamp",
        "#9aa0a8",
    )

    # Кейкапы: `keycaps` собирает их вместе с панелью, а панель в сборке уже
    # есть — берём только шесть тел по метке, вторую панель не тащим.
    caps = [
        child
        for child in keycap_part.keycaps.__wrapped__().children
        if child.label.startswith("keycap_")
    ]
    assert len(caps) == 6, len(caps)

    whole = bd.Compound(
        children=[niche_body, rim, panel, shell, encoder, knob, clamp, *caps]
    )

    # Детали не должны упираться ни в нишу, ни друг в друга.
    for left, right, name in (
        (panel, rim, "панель/обод"),
        (panel, niche_body, "панель/ниша"),
        (shell, niche_body, "корпус/ниша"),
        (shell, rim, "корпус/обод"),
        (panel, shell, "панель/корпус"),
        (panel, encoder, "панель/энкодер"),
        (shell, encoder, "корпус/энкодер"),
        (knob, encoder, "ручка/энкодер"),
        (knob, panel, "ручка/панель"),
        (clamp, panel, "планка/панель"),
        (clamp, encoder, "планка/энкодер"),
        (clamp, shell, "планка/корпус"),
    ):
        clash = (left & right).volume
        assert clash < 1e-6, (name, clash)

    floor = shell.bounding_box().min.Z
    face_z = face_part.top_z(kx)
    print(
        f"сборка: корпус z={floor:.1f}..{shell.bounding_box().max.Z:.1f}, "
        f"панель z={panel.bounding_box().min.Z:.1f}..{panel.bounding_box().max.Z:.1f}, "
        f"обод z={rim.bounding_box().min.Z:.1f}..{rim.bounding_box().max.Z:.1f} мм; "
        f"энкодер z={encoder.bounding_box().min.Z:.1f}..{encoder.bounding_box().max.Z:.1f} "
        f"(корпус до {face_part.seat_front_z():.2f}, втулка до "
        f"{face_part.knob_face_z():.2f}); "
        f"ручка z={knob.bounding_box().min.Z:.2f}..{knob.bounding_box().max.Z:.2f}, "
        f"над лицом {knob.bounding_box().max.Z - face_z:.2f} "
        f"(лицо над крутилкой {face_z:.2f}), под юбкой "
        f"{knob.bounding_box().min.Z - face_part.recess_floor_z():.2f} "
        f"(ход кнопки {face_part.ENC_STROKE:g}, проверка до "
        f"{face_part.KNOB_TRAVEL:g}); "
        f"планка z={clamp.bounding_box().min.Z:.2f}..{clamp.bounding_box().max.Z:.2f}, "
        f"площадка плоская {clamp_part.PAD_X:g}×{clamp_part.PAD_Y:g} "
        f"до z={clamp_part.pad_top_z():.2f} (жмёт трещотку Ø{encoder_part.ENC_ROTOR_D:g}), "
        f"лапки по бокам — зазор "
        f"{encoder_part.ENC_EAR_X - encoder_part.ENC_EAR_W / 2 - clamp_part.PAD_Y / 2:.2f} "
        f"на сторону; провода идут мимо плиты "
        f"{clamp_part.PLATE_X:g} (размах выводов {pin_span:g}); "
        f"кейкапов на лице {len(caps)}; "
        "пересечений нет"
    )
    return whole


if __name__ == "__main__":
    assembly()
