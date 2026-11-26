# -*- coding: utf-8 -*-
"""Защёлка кабеля из эталона `ref/cable_clip_tape.stl` — форма берётся из файла.

Файл — покупной зажим 20 × 9,05 × 10 мм: пластина 20×10×1,5 с плоским тылом,
на ней тонкостенное C-кольцо (гнездо Ø6,0, обойма Ø9,1) и клин-подкос.
Гнездо сквозное по Z, зев — боковая щель в кольце.

В файле каждый треугольник лежит дважды (площадь вдвое, `trimesh` даёт объём
1234,557 мм³ — удвоенный). Убираем дубли и склеиваем вершины по точному
совпадению — получается замкнутая оболочка (V−E+F=2, каждое ребро ровно
дважды), объём 617,278 мм³. Её OCC сшивает в валидный solid; никакой формы
здесь не рисуется, все числа — замеры по файлу.
"""

import struct
from pathlib import Path

import build123d as bd
from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_Sewing,
)
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS_Solid

REF = Path(__file__).parent / "ref" / "cable_clip_tape.stl"

# Замеры по файлу: ось гнезда в его координатах, диаметр гнезда и щель зева
# (2,0 — уже кабеля, поэтому кабель входит с разжимом кольца, как у покупного).
BORE_D = 6.0
MOUTH_D = 2.0
# Толщина пластины: поперечные сечения до y=1,45 полные (15×10), на 1,55 —
# уже только кольцо, значит пластина 0..1,5 по y.
PLATE_T = 1.5
# Наружный радиус обоймы: расстояния вершин кольца от оси дают ровное
# плато 4,550..4,561 (Ø9,1) — дальше идёт уже подкос-клин (до R6,9). Берём
# максимум: режущий цилиндр по 4,55 срезал бы вершины кольца на 0,007.
SLEEVE_R = 4.561
AXIS = (10.0, 4.49)


def _triangles(path):
    """Бинарный STL → список треугольников, по 3 точки в каждом."""
    data = Path(path).read_bytes()
    n = struct.unpack_from("<I", data, 80)[0]
    tris = []
    for i in range(n):
        base = 84 + i * 50 + 12  # 80 заголовок + 4 счётчик, дальше 50 на грань
        tris.append([struct.unpack_from("<3f", data, base + 12 * k) for k in range(3)])
    assert len(tris) == n and len(data) >= 84 + 50 * n, (len(tris), n, len(data))
    return tris


def _welded(tris):
    """Склеить вершины по точному совпадению и выбросить двойные грани."""
    index, verts, faces = {}, [], {}
    for tri in tris:
        f = []
        for v in tri:
            if v not in index:
                index[v] = len(verts)
                verts.append(v)
            f.append(index[v])
        faces.setdefault(tuple(sorted(f)), f)
    return verts, list(faces.values())


def _check_closed(verts, faces):
    """Оболочка замкнута: каждое ребро встречается ровно дважды и в обе стороны."""
    edges = {}
    for f in faces:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            edges[(a, b)] = edges.get((a, b), 0) + 1
    bad = [e for e, c in edges.items() if c != 1 or edges.get((e[1], e[0]), 0) != 1]
    assert not bad, f"оболочка не замкнута: {len(bad)} рёбер из {len(edges)}"
    assert len(verts) - len(edges) // 2 + len(faces) == 2, "не сфера по Эйлеру"


def solid():
    """Зажим как валидный solid в координатах файла: пластина y=0..1,5, ось Z."""
    tris = _triangles(REF)
    verts, faces = _welded(tris)
    _check_closed(verts, faces)

    pts = [gp_Pnt(*v) for v in verts]
    sewing = BRepBuilderAPI_Sewing(1e-6)
    for f in faces:
        wire = BRepBuilderAPI_MakePolygon(pts[f[0]], pts[f[1]], pts[f[2]], True)
        sewing.Add(BRepBuilderAPI_MakeFace(wire.Wire()).Face())
    sewing.Perform()
    assert sewing.NbFreeEdges() == 0, f"сшивка: свободных рёбер {sewing.NbFreeEdges()}"

    builder, body = BRep_Builder(), TopoDS_Solid()
    builder.MakeSolid(body)
    shells = TopExp_Explorer(sewing.SewedShape(), TopAbs_SHELL)
    while shells.More():
        builder.Add(body, shells.Current())
        shells.Next()
    part = bd.Solid(body)
    assert len(part.solids()) == 1, len(part.solids())
    return part
