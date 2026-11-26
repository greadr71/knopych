#!/usr/bin/env python3
"""Веб-пульт климата на Mac: python3 tools/climate_web.py → http://127.0.0.1:5580

Страница ходит в /cmd этого скрипта, он пересылает команду в мост (POST /cmd, порт 5577)
с токеном из ~/.knopych.json. Адрес ГУ — оттуда же (или MB_HOST=…).
"""
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

CONF = os.path.expanduser("~/.knopych.json")
PORT = 5580


def conf():
    try:
        with open(CONF) as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    host = os.environ.get("MB_HOST") or c.get("host")
    if not host:
        raise SystemExit("Адрес ГУ неизвестен: tools/kn.py find")
    return host, c.get("tokens", {}).get(host, "")


def send(cmd):
    host, token = conf()
    req = urllib.request.Request("http://%s:5577/cmd" % host, data=cmd.encode(), method="POST")
    req.add_header("X-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return "ГУ ответило %d: %s" % (e.code, e.read().decode("utf-8", errors="replace").strip())
    except (urllib.error.URLError, OSError) as e:
        return "нет связи с %s: %s" % (host, e)


PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Климат</title>
<style>
:root{--bg:#111;--fg:#eee;--mute:#888;--card:#1c1c1c;--line:#333;--on:#3d7}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);
  font:16px/1.4 -apple-system,system-ui,sans-serif}
h2{margin:0 0 12px;font-size:15px;color:var(--mute);font-weight:500;letter-spacing:.06em}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.row{display:flex;align-items:center;gap:12px}
.val{font-size:34px;font-variant-numeric:tabular-nums;min-width:120px;text-align:center}
button{appearance:none;border:1px solid var(--line);background:#262626;color:var(--fg);
  font-size:22px;border-radius:12px;width:64px;height:56px;cursor:pointer}
button:active{background:var(--on);color:#000}
button.wide{width:auto;flex:1;font-size:15px;height:42px}
.mut{color:var(--mute);font-size:13px}
#log{white-space:pre-wrap;font:12px/1.35 ui-monospace,monospace;color:var(--mute);
  max-height:190px;overflow:auto}
label{font-size:13px;color:var(--mute);display:flex;gap:6px;align-items:center;margin-top:10px}
</style>
<div class="card">
  <h2>ТЕМПЕРАТУРА ВОДИТЕЛЯ <span class="mut" id="scr"></span></h2>
  <div class="row"><button onclick="temp(-1)">−</button>
    <div class="val" id="t">—</div>
    <button onclick="temp(1)">+</button></div>
  <div class="mut">шаги 32/33, ±0.5 °C</div>
</div>
<div class="card">
  <h2>ВЕНТИЛЯТОР</h2>
  <div class="row"><button onclick="fan(-1)">−</button>
    <div class="val" id="f">—</div>
    <button onclick="fan(1)">+</button></div>
</div>
<div class="card">
  <h2>РУЧКА (ЭМУЛЯЦИЯ)</h2>
  <div class="row"><button class="wide" onclick="cmd('vbtn 1')">Нажать</button>
    <button class="wide" onclick="cmd('vbtn 0')">Отпустить</button></div>
  <div class="row" style="margin-top:8px"><button onclick="cmd('vol -1')">−</button>
    <div class="val mut" id="knob">1 шаг</div>
    <button onclick="cmd('vol 1')">+</button></div>
  <div class="mut">климат открыт: «Нажать» + «−/+» — вентилятор (удержание 0.6 с), просто «−/+» — температура. Закрыт: «−/+» — громкость.</div>
</div>
<div class="card">
  <h2>ЭКРАН</h2>
  <div class="row"><button class="wide" onclick="cmd('hvac open')">Открыть климат</button>
    <button class="wide" onclick="cmd('hvac close')">Закрыть</button></div>
  <div class="row" style="margin-top:8px"><button class="wide" onclick="refresh()">Обновить</button></div>
</div>
<div class="card"><div id="log">—</div></div>
<script>
let t = null, f = null, scr = null;
const out = document.getElementById('log');
async function cmd(c){
  out.textContent = '> ' + c + '\\n…';
  try {
    const r = await fetch('/cmd', {method:'POST', body:c});
    out.textContent = '> ' + c + '\\n' + await r.text();
  } catch(e) { out.textContent = '> ' + c + '\\nошибка: ' + e; }
  setTimeout(refresh, 400);
}
function parse(s){
  const m = /16 водитель: (\\d+) \\(([\\d.]+)C\\)/.exec(s);
  const v = /18 вентилятор: (\\d+)/.exec(s);
  const e = /экран: (виден|скрыт)/.exec(s);
  if (m) t = parseInt(m[2]);
  if (v) f = parseInt(v[1]);
  if (e) scr = e[1];
  document.getElementById('t').textContent = t === null ? '—' : t.toFixed(1);
  document.getElementById('f').textContent = f === null ? '—' : f;
  document.getElementById('scr').textContent = scr ? '· экран ' + scr : '';
}
async function refresh(){
  try {
    const r = await fetch('/cmd', {method:'POST', body:'climate'});
    const s = await r.text();
    parse(s);
    if (!out.textContent.startsWith('>')) out.textContent = s;
  } catch(e) {}
}
function temp(d){ cmd('climate temp ' + (d > 0 ? 'up' : 'down')); }
function fan(d){
  if (f === null) return cmd('climate');
  const n = Math.max(1, Math.min(7, f + d));
  if (n !== f) cmd('climate fan ' + n);
}
refresh();
setInterval(refresh, 4000);
</script>
"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE.encode("utf-8"))

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
        text = send(body.strip()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text)


if __name__ == "__main__":
    host, _ = conf()
    print("климат: http://127.0.0.1:%d  (ГУ %s)" % (PORT, host), flush=True)
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
