#!/usr/bin/env python3
"""Замена энкодера с ноутбука: страница с −/+ и текущей громкостью моста.

  tools/voltest.py     открывает http://127.0.0.1:8765 в браузере;
                       клики и клавиши ↑/↓ шлют «volume N» на мост (порт 5577).

Нужен только Python 3. Адрес и токен — из ~/.knopych.json (как у tools/kn.py).
"""
import http.server
import json
import os
import urllib.request
import webbrowser

CONF = os.path.expanduser("~/.knopych.json")
PORT = 8765

PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Громкость</title>
<style>
  html,body{margin:0;height:100%;background:#111;color:#eee;
    font:400 16px -apple-system,system-ui,sans-serif;display:flex;
    align-items:center;justify-content:center;user-select:none}
  main{text-align:center}
  #v{font:600 84px/1 ui-monospace,monospace;letter-spacing:-2px}
  #v small{font-size:28px;color:#777}
  #err{height:1.4em;color:#e66;margin-top:.4em}
  .row{display:flex;gap:16px;justify-content:center;margin-top:24px}
  button{width:120px;height:120px;border-radius:24px;border:1px solid #333;
    background:#1c1c1c;color:#eee;font-size:56px;cursor:pointer}
  button:hover{background:#262626}
  button:active{background:#3a3a3a}
</style>
<main>
  <div id="v">–</div>
  <div id="err"></div>
  <div class="row">
    <button id="minus">−</button>
    <button id="plus">+</button>
  </div>
</main>
<script>
const v = document.getElementById('v'), err = document.getElementById('err');
function show(t){ err.textContent='';
  const m = /громкость=(\\d+)\\/(\\d+)/.exec(t);
  if (m) v.innerHTML = m[1] + '<small>/' + m[2] + '</small>';
  else err.textContent = t;
}
function step(d){ fetch('/vol?d=' + d, {method:'POST'}).then(r => r.text()).then(show)
  .catch(e => err.textContent = e); }
document.getElementById('minus').onclick = () => step(-1);
document.getElementById('plus').onclick = () => step(1);
onkeydown = e => { if (e.key === 'ArrowDown' || e.key === '-') step(-1);
                   if (e.key === 'ArrowUp' || e.key === '+') step(1); };
fetch('/now').then(r => r.text()).then(show).catch(e => err.textContent = e);
</script>"""


def conf():
    with open(CONF) as f:
        return json.load(f)


C = conf()
MB = os.environ.get("MB_HOST") or C["host"]
TOK = C.get("tokens", {}).get(MB, "")


def cmd(body):
    r = urllib.request.Request("http://%s:5577/cmd" % MB, data=body.encode(), method="POST")
    r.add_header("X-Token", TOK)
    with urllib.request.urlopen(r, timeout=10) as f:
        return f.read().decode()


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.reply(200, PAGE, "text/html; charset=utf-8")
        elif self.path == "/now":
            self.reply(200, cmd("volume"))
        else:
            self.reply(404, "нет")

    def do_POST(self):
        try:
            cur = cmd("volume")
            n = int(cur.split("=")[1].split("/")[0])
            d = int(self.path.split("d=")[1]) if "d=" in self.path else 0
            self.reply(200, cmd("volume %d" % (n + d)))
        except Exception as e:  # мост недоступен, токен протух — показать на странице
            self.reply(500, "ошибка: %s" % e)

    def reply(self, code, text, ctype="text/plain; charset=utf-8"):
        b = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


srv = None
for p in range(PORT, PORT + 11):  # 8765 занят прошлым запуском — берём следующий
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", p), H)
        PORT = p
        break
    except OSError:
        pass
if srv is None:
    raise SystemExit("нет свободного порта 8765–8775")

url = "http://127.0.0.1:%d" % PORT
print("%s → мост %s (Ctrl+C — выход)" % (url, MB))
webbrowser.open(url)
srv.serve_forever()
