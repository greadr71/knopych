# -*- coding: utf-8 -*-
"""STL печатных деталей панели, сразу в ориентации под слайсер.

Панель — лицом вниз на плиту (наклон 1,72° снят, чтобы легла плоско),
корпус — как есть (дном на стол: вверх дном его дно 29,7 мм шло мостом),
кейкапы — верхом на стол, наклон лица снят, как у панели; гладкая ручка и
прижим — как есть, накатанная ручка — низом вверх (в этой ориентации у неё нет
ни моста, ни открытого гнезда на столе). Геометрия берётся вызовом функций из
face.py, body.py, keycaps.py, knob.py, knob_knurl.py и clamp.py — второй копии нет.

Запуск: cad run v2/modeling/print_stl.py
"""

import math
from pathlib import Path

import build123d as bd

import body as body_part
import clamp as clamp_part
import face as face_part
import keycaps as keycap_part
import knob as knob_part
import knob_knurl as knob_knurl_part

HERE = Path(__file__).parent
OUT = HERE / "stl"
TOL = 0.02


def _caps():
    """Шесть кейкапов из модели `keycaps` без панели, которая в ней тоже есть."""
    shape = keycap_part.keycaps.__wrapped__()
    caps = [child for child in shape.children if child.label.startswith("keycap_")]
    assert len(caps) == 6, len(caps)
    return bd.Compound(children=caps)


def _on_bed(part):
    """Сдвинуть деталь так, чтобы низ стоял на z=0."""
    return bd.Pos(0, 0, -part.bounding_box().min.Z) * part


def _fused(part):
    """Плита и площадка прижима касаются плоскостями — печатаются одной деталью."""
    solids = part.solids()
    return solids[0].fuse(*solids[1:])


def _tilt():
    """Наклон лица в градусах: снимается поворотом по Y, чтобы лицо легло плоско."""
    return math.degrees(math.atan(-face_part.TOP_SLOPE))


def _face_down():
    """Лицо на плиту: переворот и снятие наклона лица 1,72°, иначе легла бы на кромку."""
    return bd.Rot(0, _tilt(), 0) * bd.Rot(180, 0, 0) * face_part.face.__wrapped__()


def main():
    OUT.mkdir(exist_ok=True)
    parts = {
        "face": _on_bed(_face_down()),
        "body": _on_bed(body_part.body.__wrapped__()),
        "keycaps": _on_bed(bd.Rot(0, _tilt(), 0) * bd.Rot(180, 0, 0) * _caps()),
        # Ручки повёрнуты вместе с энкодером: гнездо D должно совпасть с лыской
        # вала; поворот вокруг Z на ориентацию печати не влияет.
        "knob": _on_bed(
            bd.Rot(0, 0, face_part.ENC_ROT) * knob_part.knob.__wrapped__()
        ),
        "knob_knurl": _on_bed(
            bd.Rot(180, 0, 0)
            * bd.Rot(0, 0, face_part.ENC_ROT)
            * knob_knurl_part.knob_knurl.__wrapped__()
        ),
        "clamp": _fused(clamp_part.clamp.__wrapped__()),
    }
    for name, part in parts.items():
        path = OUT / f"{name}.stl"
        bd.export_stl(part, path, tolerance=TOL, angular_tolerance=0.15)
        size = part.bounding_box().size
        print(
            f"{name}.stl  {size.X:.1f}×{size.Y:.1f}×{size.Z:.1f} мм, "
            f"{path.stat().st_size / 1e6:.1f} МБ"
        )


if __name__ == "__main__":
    main()
