# -*- coding: utf-8 -*-
"""Трассировка иконок с картинки в SVG без ореола.

Картинка — белые штрихи на чёрном, вокруг линии серый ореол.
Порог яркости 240 оставляет только ядро. Скрипт сборки кейкапов
этот файл не вызывает: он читает уже записанные SVG.

Запуск из корня репозитория:

    .venv/bin/python v1/modeling/keycaps/trace_icons.py
"""

from pathlib import Path

import numpy as np
from PIL import Image
from potrace import BezierSegment, Bitmap, CornerSegment

SRC = Path.home() / "Downloads/icons_corrected.png"
HERE = Path(__file__).resolve().parent
OUT = HERE / "icons"

# Ядро линии. Ореол на этой картинке слабее 240.
THRESHOLD = 240

# (имя, x0, x1, y0, y1) — плотные боксы четырёх глифов.
GLYPHS = (
    ("windshield", 191, 566, 260, 497),
    ("seat-pos-1", 773, 1064, 260, 497),
    ("seat-pos-2", 191, 566, 736, 969),
    ("seat-pos-3", 773, 1064, 736, 969),
)


def _crop(mask, x0, x1, y0, y1, pad=2):
    sub = mask[y0 : y1 + 1, x0 : x1 + 1]
    canvas = np.zeros((sub.shape[0] + 2 * pad, sub.shape[1] + 2 * pad), dtype=bool)
    canvas[pad:-pad, pad:-pad] = sub
    return canvas


def _path_d(curves):
    parts = []
    for curve in curves:
        start = curve.start_point
        parts.append(f"M {start.x:.2f} {start.y:.2f}")
        for seg in curve:
            if isinstance(seg, CornerSegment):
                parts.append(f"L {seg.c.x:.2f} {seg.c.y:.2f}")
                parts.append(f"L {seg.end_point.x:.2f} {seg.end_point.y:.2f}")
            elif isinstance(seg, BezierSegment):
                parts.append(
                    "C "
                    f"{seg.c1.x:.2f} {seg.c1.y:.2f} "
                    f"{seg.c2.x:.2f} {seg.c2.y:.2f} "
                    f"{seg.end_point.x:.2f} {seg.end_point.y:.2f}"
                )
            else:
                raise TypeError(type(seg))
        parts.append("Z")
    return " ".join(parts)


def _write_svg(path, width, height, d):
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">\n'
        f'  <path fill="#000" fill-rule="evenodd" d="{d}"/>\n'
        "</svg>\n",
        encoding="utf-8",
    )


def main():
    image = np.array(Image.open(SRC).convert("L"))
    mask = image >= THRESHOLD
    OUT.mkdir(parents=True, exist_ok=True)
    for name, x0, x1, y0, y1 in GLYPHS:
        crop = _crop(mask, x0, x1, y0, y1)
        # Bitmap инвертирует данные и ищет чёрное. Передаём фон,
        # чтобы после инверсии обводилось ядро линии.
        curves = Bitmap(~crop).trace(turdsize=8, alphamax=1.0, opttolerance=0.2)
        height, width = crop.shape
        _write_svg(OUT / f"{name}.svg", width, height, _path_d(curves))
        print(f"{name}: {width}×{height} px, контуров {len(curves)}")


if __name__ == "__main__":
    main()
