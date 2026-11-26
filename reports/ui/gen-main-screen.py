#!/usr/bin/env python3
# Макет главного экрана «Кнопыча» после правки: числа взяты из MainActivity.java
# (padL/padT — 5,4 % ширины и 3 % высоты, GUT 14 dp, шапка 48+8, STICKY 60, KEY_H 76, кегли).
# Рисуем в dp: экран ГУ (800×562 dp, узкий режим, density 1.6) и 1280×720 dp (density 1).
import os

BG, LINE, KEY, ON, RIM = "#0F1115", "#23262E", "#1B1F26", "#D66024", "#8F3F17"
TEXT, DIM, FAINT, QUIET, PLATE, CAPTOP, HOLE = (
    "#F2EAE4", "#BDB2A8", "#948A81", "#7E756D", "#1A1E25", "#262B34", "#0A0C10")
PIX = "ui-monospace, 'DejaVu Sans Mono', 'Courier New', monospace"
SANS = "-apple-system, 'Segoe UI', Roboto, sans-serif"

WMM, HMM = 145.0, 25.0
CX = [11, 29, 47, 98, 116, 134]
ICON_W = [10, 10, 10, 12, 12, 12]
ICON_A = [290.3 / 230.61, 291.74 / 232.47, 290.45 / 233.38, 525 / 447, 380 / 242, 525 / 447]
ICON_DOWN = [2.3, 2.3, 2.3, 1.3, 2.3, 1.3]
LED = [1, 1, 0, 1, 1, 0]          # слоты 1-2 заняты, подогрев водителя 3, лобовое вкл
HINT = "Коснитесь кнопки, чтобы открыть её настройки"


def sans_w(s, size):                      # ширина строки IBM Plex, приблизительно
    return len(s) * 0.52 * size


def pix_w(s, size, tracking):             # ширина строки Press Start 2P: клетка 1 em
    return len(s) * size * (1 + tracking)


def truncated(s, size, avail):
    """Одна строка с многоточием — как TextUtils.TruncateAt.END в шапке."""
    if sans_w(s, size) <= avail:
        return s
    n = int(avail / (0.52 * size)) - 1
    return s[:max(0, n)].rstrip(" ,.") + "…"


def panel(x, y, w, h, sel=-1):
    s = w / WMM                  # px на мм — ровно как Panel.onDraw
    o = [f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.4f})">',
         f'<rect x="0" y="0" width="{WMM}" height="{HMM}" rx="6" fill="{PLATE}" '
         f'stroke="{LINE}" stroke-width="0.4"/>']
    for i in (0, 3):
        o.append(f'<rect x="{CX[i] - 9}" y="3.5" width="54" height="18" rx="2" fill="{BG}"/>')
    o.append(f'<path d="M57.5 25 A15 15 0 0 1 87.5 25 Z" fill="{BG}"/>')
    for i in range(6):
        cxk, ry = CX[i], 12.5
        o.append(f'<rect x="{cxk - 8.5}" y="{ry - 8.5}" width="17" height="17" rx="2" '
                 f'fill="{KEY}" stroke="{ON if i == sel else LINE}" stroke-width="0.4"/>')
        ty = ry - 1.2
        o.append(f'<rect x="{cxk - 7}" y="{ty - 7:.1f}" width="14" height="14" rx="1.5" '
                 f'fill="{CAPTOP}"/>')
        # иконка упрощена до силуэта: в приложении это контуры из res/drawable
        iw, ih = ICON_W[i], ICON_W[i] / ICON_A[i]
        iy = ty + ICON_DOWN[i]
        ink = TEXT if LED[i] else DIM
        m = -1 if i == 3 else 1
        o.append(f'<g transform="translate({cxk},0) scale({m},1) translate({-cxk},0)">')
        if i < 3:
            o.append(f'<rect x="{cxk - iw / 2:.2f}" y="{iy - ih / 2:.2f}" width="{iw:.2f}" '
                     f'height="{ih * 0.55:.2f}" rx="1.4" fill="none" stroke="{ink}" '
                     f'stroke-width="0.55"/>')
            o.append(f'<rect x="{cxk - iw / 2 + 1:.2f}" y="{iy - ih / 2 + ih * 0.62:.2f}" '
                     f'width="{iw - 2:.2f}" height="{ih * 0.2:.2f}" rx="0.8" fill="none" '
                     f'stroke="{ink}" stroke-width="0.55"/>')
            o.append(f'<text x="{cxk}" y="{iy - ih / 2 - 0.7:.2f}" font-family="{PIX}" '
                     f'font-size="2.6" fill="{ink}" text-anchor="middle">{i + 1}</text>')
        elif i == 4:
            o.append(f'<path d="M{cxk - iw / 2:.2f} {iy + ih / 2:.2f} L{cxk - iw / 2 + 2:.2f} '
                     f'{iy - ih / 2:.2f} L{cxk + iw / 2 - 2:.2f} {iy - ih / 2:.2f} '
                     f'L{cxk + iw / 2:.2f} {iy + ih / 2:.2f} Z" fill="none" stroke="{ink}" '
                     f'stroke-width="0.6"/>')
        else:
            o.append(f'<path d="M{cxk - iw / 2:.2f} {iy + 1.6:.2f} q{iw / 4:.2f} -2.6 '
                     f'{iw / 2:.2f} 0 q{iw / 4:.2f} 2.6 {iw / 2:.2f} 0" fill="none" '
                     f'stroke="{ink}" stroke-width="0.6"/>')
            o.append(f'<path d="M{cxk - iw / 2:.2f} {iy - 1.6:.2f} q{iw / 4:.2f} -2.6 '
                     f'{iw / 2:.2f} 0 q{iw / 4:.2f} 2.6 {iw / 2:.2f} 0" fill="none" '
                     f'stroke="{ink}" stroke-width="0.6"/>')
        o.append('</g>')
        o.append(f'<rect x="{cxk - 2}" y="{ry - 5.8}" width="4" height="1.6" rx="0.8" '
                 f'fill="{ON if LED[i] else HOLE}"/>')
    o.append('</g>')
    return "\n".join(o)


def wrap(s, size, avail, max_lines=2):
    """Перенос по словам с многоточием на последней строке — как maxLines 2 в коде."""
    lines, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w).strip()
        if cur and sans_w(t, size) > avail:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
        else:
            cur = t
    if len(lines) < max_lines:
        lines.append(cur)
    if sans_w(lines[-1], size) > avail:
        lines[-1] = truncated(lines[-1], size, avail)
    return lines


def screen(vw, vh, pad_l, pad_t, content_w):
    """Один экран: шапка с подсказкой, панель, липкая шапка, две строки сценария."""
    panel_w = min(content_w, max(260, round(content_w * 0.3)))
    panel_h = round(panel_w * HMM / WMM)
    x0 = pad_l + 14                      # GUT
    o = [f'<rect x="0" y="0" width="{vw}" height="{vh}" fill="{BG}"/>']
    # системные панели GWM, под которыми стоит приложение (ui_pad_left / ui_pad_top)
    o.append(f'<rect x="0" y="0" width="{pad_l}" height="{vh}" fill="#171A20"/>')
    o.append(f'<rect x="0" y="0" width="{vw}" height="{pad_t}" fill="#171A20"/>')
    # шапка 48 + 8: имя, версия, подсказка между ними и «ОТЛАДКА»
    top = pad_t + 24
    name_w = pix_w("КНОПЫЧ", 22, 0.08)
    ver_w = pix_w("v0.14", 14, 0.04)
    diag_w = pix_w("ОТЛАДКА", 20, 0.1) + 40
    o.append(f'<text x="{x0}" y="{top + 8}" font-family="{PIX}" font-size="22" '
             f'font-weight="700" fill="{TEXT}" letter-spacing="1.8">КНОПЫЧ</text>')
    o.append(f'<text x="{x0 + name_w + 12}" y="{top + 6}" font-family="{PIX}" font-size="14" '
             f'fill="{FAINT}" letter-spacing="0.6">v0.14</text>')
    hx0 = x0 + name_w + 12 + ver_w + 16
    hx1 = vw - 20 - diag_w - 8
    o.append(f'<text x="{(hx0 + hx1) / 2:.0f}" y="{top + 9}" font-family="{SANS}" '
             f'font-size="26" fill="{QUIET}" text-anchor="middle">'
             f'{truncated(HINT, 26, hx1 - hx0)}</text>')
    o.append(f'<text x="{vw - 20 - 20}" y="{top + 7}" font-family="{PIX}" font-size="20" '
             f'fill="{FAINT}" text-anchor="end" letter-spacing="2">ОТЛАДКА</text>')
    y = pad_t + 56
    # панель — три десятых содержимого, по центру, высота из пропорции 145:25
    px = pad_l + (content_w - panel_w) / 2
    o.append(panel(px, y, panel_w, panel_h))
    o.append(f'<text x="{px + panel_w + 10}" y="{y + panel_h / 2 + 4}" font-family="{SANS}" '
             f'font-size="13" fill="{QUIET}">{panel_w}×{panel_h} dp</text>')
    y += panel_h
    area_top = y
    # липкая шапка 60 dp + волосок
    o.append(f'<rect x="{pad_l}" y="{area_top}" width="{content_w + 20}" height="60" '
             f'fill="{BG}"/>')
    o.append(f'<text x="{x0}" y="{area_top + 40}" font-family="{PIX}" font-size="30" '
             f'font-weight="700" fill="{FAINT}" letter-spacing="4">СЦЕНАРИИ</text>')
    o.append(f'<rect x="{pad_l}" y="{area_top + 60}" width="{content_w + 20}" height="1" '
             f'fill="{LINE}"/>')
    rows = [("Подогрев в холод", "ВКЛ", ON,
             "ниже 5 °C · сиденье 3 · руль · лобовое · задержка 10 с"),
            ("Тема при включении", "ВЫКЛ", FAINT,
             "тема 4 · один раз за поездку, при включении ГУ")]
    ry = area_top + 61
    for i, (name, state, scol, brief) in enumerate(rows):
        # строка: название 34 sp, состояние 22 sp, стрелка → справа, выжимка 26 sp
        o.append(f'<text x="{x0}" y="{ry + 18 + 36}" font-family="{SANS}" font-size="36" '
                 f'font-weight="500" fill="{TEXT}">{name}</text>')
        o.append(f'<text x="{vw - 20 - 14 - 28 - 12}" y="{ry + 18 + 34}" font-family="{PIX}" '
                 f'font-size="24" fill="{scol}" text-anchor="end">{state}</text>')
        o.append(f'<text x="{vw - 20 - 14}" y="{ry + 18 + 34}" font-family="{PIX}" '
                 f'font-size="28" fill="{FAINT}" text-anchor="end">→</text>')
        avail = content_w - 3 * 14
        for k, line in enumerate(wrap(brief, 28, avail)):
            o.append(f'<text x="{x0}" y="{ry + 18 + 36 + 8 + 28 + k * 36}" '
                     f'font-family="{SANS}" font-size="28" fill="{FAINT}">{line}</text>')
        # отбивка 18, название 36 (строка 47), выжимка 28 (строка 36), до неё 8
        ry += 18 + 47 + 8 + len(wrap(brief, 28, content_w - 3 * 14)) * 36 + 18
        if i == 0:
            o.append(f'<rect x="{pad_l}" y="{ry}" width="{content_w + 20}" height="1" '
                     f'fill="{LINE}"/>')
            ry += 1
    o.append(f'<text x="{pad_l + content_w / 2}" y="{vh - 24}" font-family="{SANS}" '
             f'font-size="13" fill="{QUIET}" text-anchor="middle">'
             f'низ экрана · {vh - 14 - ry} dp воздуха под сценариями (было 6)</text>')
    return "\n".join(o), panel_w, panel_h, ry, area_top


a_html, aw, ah, aend, atop = screen(1280, 720, 69, 21, 1191)
b_html, bw, bh, bend, btop = screen(800, 562, 43, 17, 737)

html = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>«Кнопыч» — главный экран после правки</title>
<style>
  body {{ margin: 0; padding: 28px; background: #0B0D10; color: #BDB2A8;
          font: 15px/1.55 -apple-system, 'Segoe UI', Roboto, sans-serif; }}
  h1 {{ font-size: 20px; color: #F2EAE4; margin: 0 0 6px; }}
  h2 {{ font-size: 14px; color: #948A81; font-weight: 600; margin: 26px 0 8px;
        letter-spacing: .04em; text-transform: uppercase; }}
  p {{ margin: 0 0 10px; max-width: 900px; }}
  .lead {{ color: #948A81; }}
  svg {{ display: block; border: 1px solid #23262E; border-radius: 6px; }}
  table {{ border-collapse: collapse; font-size: 13px; margin: 10px 0 0; }}
  td, th {{ padding: 4px 12px 4px 0; text-align: left; vertical-align: top; }}
  th {{ color: #7E756D; font-weight: 500; }}
  td.n {{ color: #F2EAE4; font-variant-numeric: tabular-nums; }}
  .note {{ color: #7E756D; font-size: 13px; }}
</style></head><body>
<h1>Главный экран «Кнопыча» после правки</h1>
<p class="lead">Числа — из <code>MainActivity.java</code>: отступы <code>ui_pad</code> 5,4 % ширины /
3 % высоты, жёлоб 14 dp, шапка 48+8 dp, липкая шапка 60 dp, кейкап 76 dp. Панель — 30 %
содержимого (не меньше 260 dp), по центру, высота из пропорции 145:25. Шёлкографии и строки
состояния на экране больше нет: состояние машины — в отладке.</p>

<h2>Экран 1280×720 dp (density 1, широкий режим)</h2>
<svg viewBox="0 0 1280 720" width="640" height="360" role="img">{a_html}</svg>

<h2>Экран ГУ 800×562 dp (density 1,6, узкий режим)</h2>
<svg viewBox="0 0 800 562" width="480" height="337" role="img">{b_html}</svg>

<p class="note">Шрифты в макете подменены системными: Press Start 2P и IBM Plex Sans в браузере
нет. Пиксельные надписи набраны моноширинным с трекингом, читаемые — системным sans-serif;
кегли и метрики строк — настоящие. Контуры кейкапов упрощены до силуэта. Подсказка в шапке на
узком экране честно режется многоточием — это и в приложении так.</p>

<h2>Что изменилось в числах</h2>
<table>
<tr><th></th><th>было</th><th>стало</th></tr>
<tr><td>ширина панели (ГУ, 737 dp содержимого)</td><td class="n">300 dp (минимум)</td>
    <td class="n">{bw} dp</td></tr>
<tr><td>высота панели по пропорции 145:25</td><td class="n">52 dp</td>
    <td class="n">{bh} dp</td></tr>
<tr><td>высота панели в % от экрана ГУ</td><td class="n">9,3 %</td>
    <td class="n">{bh / 562 * 100:.1f} %</td></tr>
<tr><td>шёлкография двумя колонками</td><td class="n">26 sp, ~112 dp</td>
    <td class="n">убрана</td></tr>
<tr><td>строка состояния машины</td><td class="n">22 sp, ~62 dp</td>
    <td class="n">в отладке, 18 sp</td></tr>
<tr><td>подсказка «Коснитесь кнопки…»</td><td class="n">20 sp отдельной строкой, 42 dp</td>
    <td class="n">26 sp в шапке, 0 dp</td></tr>
<tr><td>освободилось над сценариями</td><td class="n">—</td><td class="n">~216 dp</td></tr>
<tr><td>микрозаголовки (СЦЕНАРИИ, НАЖАТИЕ)</td><td class="n">20 sp</td><td class="n">30 sp</td></tr>
<tr><td>название сценария</td><td class="n">24 sp</td><td class="n">36 sp</td></tr>
<tr><td>выжимка сценария</td><td class="n">18 sp</td><td class="n">28 sp</td></tr>
<tr><td>надпись клавиши</td><td class="n">16 sp пиксельным</td>
    <td class="n">26 sp IBM Plex / 22 sp пиксельным</td></tr>
<tr><td>кейкап-клавиша</td><td class="n">60 dp</td><td class="n">76 dp</td></tr>
<tr><td>липкая шапка</td><td class="n">46 dp</td><td class="n">60 dp</td></tr>
</table>
<table>
<tr><th>экран</th><th>сценарии занимают</th><th>воздух под ними</th></tr>
<tr><td>1280×720 dp</td><td class="n">{aend - atop - 61} dp</td>
    <td class="n">{720 - 14 - aend} dp</td></tr>
<tr><td>800×562 dp</td><td class="n">{bend - btop - 61} dp</td>
    <td class="n">{562 - 14 - bend} dp</td></tr>
</table>
</body></html>
"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main-screen-after.html")
open(out, "w", encoding="utf-8").write(html)
print(out)
print("панель ГУ: %d×%d dp (%.1f%% высоты); 1280×720: %d×%d dp" % (
    bw, bh, bh / 562 * 100, aw, ah))
