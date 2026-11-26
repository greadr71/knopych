#!/usr/bin/env python3
"""Иконка «Кнопыч»: один крупный кейкап с буквой К. Пишет adaptive-XML, PNG-фолбэк, SVG-превью.

Лаунчер ГУ (1920x720, density 160) рисует иконку 160x160 px. Основной вариант — adaptive:
лаунчер сам вырезает маску из 108dp, поэтому весь арт вписан в безопасную зону 66.
PNG-бакеты 48/72/96/144/192 — фолбэк для API < 26, на этом ГУ не используются.

Почему один кейкап: шесть кейкапов и тонкий обод 1.65 в мелком размере превращались в кашу.
Один кейкап с буквой высотой 40 и штрихом 5.7 читается.

Геометрия (108x108): кейкап 76x72 r13 по центру (16,18), грань 64x54 r9 (22,24) —
обод 6 по бокам и сверху, передняя стенка 12 снизу (толстый низ = объём клавиши).
Буква К высотой 40 по центру грани. Весь арт сжат коэффициентом ART = 66/76 = 0.868,
чтобы влезть в безопасную зону adaptive-иконки.
Правишь числа здесь и гоняешь: python3 reports/ui/gen_icon.py
"""
import pathlib
import subprocess
import tempfile

from PIL import Image

CANVAS = 108
BG_R = 12                     # радиус подложки; лаунчер ГУ режет по своему, но так ровнее
CAP_W, CAP_H = 76.0, 72.0     # кейкап целиком (обод + стенка)
CAP_R = 13.0
CAP_X = (CANVAS - CAP_W) / 2  # 16
CAP_Y = (CANVAS - CAP_H) / 2  # 18
SIDE = 6.0                    # обод по бокам
TOP = 6.0                     # обод сверху
WALL = 12.0                   # передняя стенка снизу
FACE_W, FACE_H = CAP_W - 2 * SIDE, CAP_H - TOP - WALL   # 64 x 54
FACE_R = 9.0
GLYPH_H = 40.0                # высота буквы; у глифов высота 12, отсюда масштаб 3.33

C_FACE, C_EDGE, C_INK, C_BG = "#D66024", "#8F3F17", "#121418", "#121418"
DESC = "кейкап 76x72 r13, грань 64x54 r9, обод 6, стенка 12, буква К высотой 40"

SAFE = 66.0                   # безопасная зона adaptive-иконки: за неё лаунчер режет
ART = SAFE / CAP_W            # 0.868 — во сколько сжат весь арт

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
RES = 768                     # рендер 4x от xxxhdpi, дальше LANCZOS вниз
BUCKETS = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}


def fx(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def box_path(x, y, w, h, r):
    return (f"M{fx(x + r)},{fx(y)} H{fx(x + w - r)} A{r},{r} 0 0 1 {fx(x + w)},{fx(y + r)} "
            f"V{fx(y + h - r)} A{r},{r} 0 0 1 {fx(x + w - r)},{fx(y + h)} "
            f"H{fx(x + r)} A{r},{r} 0 0 1 {fx(x)},{fx(y + h - r)} "
            f"V{fx(y + r)} A{r},{r} 0 0 1 {fx(x + r)},{fx(y)} Z")


# Буква К — контур из Press Start 2P (fontTools), базовая линия y=0, верх в -y:
# ink от -6 до 6 по x и от -13.71 до -1.71 по y, центр ink (0, -7.71).
GLYPH_K = ("M-0.86 -10.29H0.86V-8.57H2.57V-6.86H4.29V-3.43H6V-1.71H2.57V-3.43H0.86V-6.86"
           "H-2.57V-1.71H-6V-13.71H-2.57V-8.57H-0.86ZM6 -13.71V-12H4.29V-10.29H0.86V-12"
           "H2.57V-13.71Z")
G_SCALE = GLYPH_H / 12.0      # 3.33
G_X = CAP_X + SIDE + FACE_W / 2                 # 54
G_Y = CAP_Y + TOP + FACE_H / 2 + 7.71 * G_SCALE  # 76.7 — ink встаёт в центр грани


def svg_markup(size, with_bg):
    c = CANVAS / 2
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" '
             f'width="{size}" height="{size}" viewBox="0 0 {CANVAS} {CANVAS}">']
    if with_bg:
        lines.append(f'    <rect width="{CANVAS}" height="{CANVAS}" rx="{fx(BG_R)}" fill="{C_BG}" />')
    lines.append(f'    <g transform="translate({fx(c)},{fx(c)}) scale({fx(ART)}) '
                 f'translate({fx(-c)},{fx(-c)})">')
    lines.append(f'    <path fill="{C_EDGE}" d="{box_path(CAP_X, CAP_Y, CAP_W, CAP_H, CAP_R)}" />')
    lines.append(f'    <path fill="{C_FACE}" '
                 f'd="{box_path(CAP_X + SIDE, CAP_Y + TOP, FACE_W, FACE_H, FACE_R)}" />')
    lines.append(f'    <g transform="translate({fx(G_X)},{fx(G_Y)}) scale({fx(G_SCALE)})">'
                 f'<path fill="{C_INK}" d="{GLYPH_K}" /></g>')
    lines.append('    </g>')
    lines.append('</svg>')
    return "\n".join(lines)


def write_adaptive(path):
    pathlib.Path(path).write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!-- Адаптивная иконка «Кнопыч»: лаунчер сам вырезает маску.\n'
        f'     {DESC}, весь арт сжат в безопасную зону {fx(SAFE)} из {CANVAS}.\n'
        '     Пересобрать: python3 reports/ui/gen_icon.py -->\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background" />\n'
        '    <foreground android:drawable="@drawable/ic_launcher_foreground" />\n'
        '</adaptive-icon>\n', encoding="utf-8")


def write_xml(path):
    # group: p*ART + CANVAS/2*(1-ART) — сжатие арта вокруг центра холста
    shift = CANVAS / 2 * (1 - ART)
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<!-- «Кнопыч»: один кейкап с буквой К, foreground для adaptive-иконки.',
             f'     {DESC}. Весь арт сжат в безопасную зону {fx(SAFE)} из {CANVAS}.',
             f'     Стенка {C_EDGE}, грань {C_FACE}, буква {C_INK} контуром Press Start 2P.',
             '     Пересобрать: python3 reports/ui/gen_icon.py -->',
             '<vector xmlns:android="http://schemas.android.com/apk/res/android"',
             f'    android:width="{CANVAS}dp" android:height="{CANVAS}dp"',
             f'    android:viewportWidth="{CANVAS}" android:viewportHeight="{CANVAS}">',
             f'    <group android:translateX="{fx(shift)}" android:translateY="{fx(shift)}" '
             f'android:scaleX="{fx(ART)}" android:scaleY="{fx(ART)}">',
             f'        <path android:fillColor="{C_EDGE}" '
             f'android:pathData="{box_path(CAP_X, CAP_Y, CAP_W, CAP_H, CAP_R)}" />',
             f'        <path android:fillColor="{C_FACE}" '
             f'android:pathData="{box_path(CAP_X + SIDE, CAP_Y + TOP, FACE_W, FACE_H, FACE_R)}" />',
             f'        <group android:translateX="{fx(G_X)}" android:translateY="{fx(G_Y)}" '
             f'android:scaleX="{fx(G_SCALE)}" android:scaleY="{fx(G_SCALE)}">',
             f'            <path android:fillColor="{C_INK}" android:pathData="{GLYPH_K}" />',
             '        </group>',
             '    </group>',
             '</vector>']
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_svg(path, with_bg):
    head = [f'<!-- {DESC} -->', svg_markup(512, with_bg)]
    pathlib.Path(path).write_text("\n".join(head) + "\n", encoding="utf-8")


def write_pngs(res_dir):
    """Один рендер в RES px через headless Chrome, дальше LANCZOS во все плотности."""
    with tempfile.TemporaryDirectory() as tmp:
        page = pathlib.Path(tmp, "icon.html")
        page.write_text('<!doctype html><meta charset="utf-8">'
                        '<style>html,body{margin:0;background:transparent}svg{display:block}</style>'
                        + svg_markup(RES, True), encoding="utf-8")
        shot = pathlib.Path(tmp, "icon.png")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--default-background-color=00000000",
                        f"--screenshot={shot}", f"--window-size={RES},{RES}", page.as_uri()],
                       check=True, capture_output=True)
        big = Image.open(shot).convert("RGBA")
    if big.size != (RES, RES):
        raise SystemExit(f"Chrome отдал {big.size}, ждали {RES}x{RES}")
    for bucket, px in BUCKETS.items():
        dst = res_dir / f"mipmap-{bucket}" / "ic_launcher.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        big.resize((px, px), Image.LANCZOS).save(dst)
        print(f"{dst} {px}x{px}")


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    res = here.parent.parent / "bridge/res"
    write_xml(res / "drawable/ic_launcher_foreground.xml")
    write_adaptive(res / "mipmap-anydpi-v26/ic_launcher.xml")
    write_svg(here / "icon-keycaps.svg", False)
    write_svg(here / "icon-full-keycaps.svg", True)
    write_pngs(res)
    print("ok")
