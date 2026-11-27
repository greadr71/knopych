#!/usr/bin/env python3
"""knopych: связь с мостом на ГУ по Wi-Fi с Mac (без кабеля и без Windows).

ГУ и Mac — в одной Wi-Fi сети (например, точка доступа телефона).

  tools/kn.py find                 найти ГУ в сети и запомнить адрес
  tools/kn.py token 123-456        запомнить токен (виден на экране «Кнопыч», блок «Отладка»)
  tools/kn.py status               любая команда моста: status, log, seat_driver 3, ble_mac AA:BB:CC:DD:EE:FF…
  tools/kn.py install [apk]        обновить мост (по умолчанию bridge/apk/knopych-bridge-system.apk)
  tools/kn.py logcat [строк]       журнал ГУ в logs/wifi-logcat.txt
  tools/kn.py shot [файл]          скриншот экрана ГУ в logs/shot-<дата>.png
  tools/kn.py snap до               снимок: свойства, настройки, пакеты, uimode/overlay → logs/snap-до/
  tools/kn.py diff до после        что изменилось между снимками (так ищем, как включается тема и т.п.)

Только посмотреть (ничего не меняют):
  getprop [фильтр] | settings [system|secure|global] [фильтр] | dumpsys служба [фильтр]
  packages [фильтр] | intents пакет

Адрес и токен хранятся в ~/.knopych.json. Адрес можно задать и так: MB_HOST=192.168.43.12.
Только стандартная библиотека Python.
"""
import difflib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = 5577
CONF = os.path.expanduser("~/.knopych.json")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Что снимать для сравнения «до/после». Тема Android 9 обычно в settings, uimode или overlay.
SNAP = [("settings", "settings all"), ("getprop", "getprop"), ("packages", "packages"),
        ("uimode", "dumpsys uimode"), ("overlay", "dumpsys overlay")]


def load():
    try:
        with open(CONF) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(c):
    with open(CONF, "w") as f:
        json.dump(c, f, indent=1)
    os.chmod(CONF, 0o600)


def find(timeout=3.0):
    """UDP-широковещательный запрос «knopych?» во все сети Mac."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.5)
    targets = {"255.255.255.255"}
    try:  # широковещательные адреса интерфейсов (macOS)
        out = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if "broadcast" in line:
                targets.add(line.split("broadcast")[1].split()[0])
    except OSError:
        pass
    found = {}
    end = time.time() + timeout
    while time.time() < end:
        for t in targets:
            try:
                s.sendto(b"knopych?", (t, PORT))
            except OSError:
                pass
        try:
            data, addr = s.recvfrom(128)
            if data.startswith(b"knopych "):
                found[addr[0]] = data.decode(errors="replace")
        except socket.timeout:
            pass
    return found


def host(c):
    h = os.environ.get("MB_HOST") or c.get("host")
    if not h:
        sys.exit("Адрес ГУ неизвестен: tools/kn.py find (или MB_HOST=…)")
    return h


def request(c, method, path, body=None, timeout=70):
    url = "http://%s:%d%s" % (host(c), PORT, path)
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("X-Token", c.get("tokens", {}).get(host(c), ""))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode("utf-8", errors="replace").strip()
        except OSError:
            msg = ""  # ГУ отказало и сразу закрыло соединение, не дочитав APK
        if e.code == 403:
            msg = "неверный токен для %s. Возьми токен с экрана «Кнопыч» (блок «Отладка») и: tools/kn.py token <токен>" % host(c)
        sys.exit("ГУ ответило %d: %s" % (e.code, msg))
    except (urllib.error.URLError, OSError) as e:
        sys.exit("Нет связи с %s: %s\nГУ и Mac в одной сети? Попробуй tools/kn.py find" % (url, e))


def main(argv):
    c = load()
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]

    if cmd == "find":
        f = find()
        if not f:
            sys.exit("ГУ не нашлось. Проверь: ГУ и Mac в одной Wi-Fi сети, мост запущен (иконка «Кнопыч»).")
        for ip, info in f.items():
            print(ip, info)
        c["host"] = next(iter(f))
        save(c)
        print("Запомнил адрес", c["host"], "" if c.get("tokens", {}).get(c["host"]) else "\nТеперь: tools/kn.py token <токен с экрана ГУ, блок «Отладка»>")
        return
    if cmd == "token":
        if not args:
            sys.exit("tools/kn.py token <токен с экрана «Кнопыч», блок «Отладка»>")
        c.setdefault("tokens", {})[host(c)] = args[0]  # свой токен для каждого адреса (ГУ, эмулятор)
        c.pop("token", None)
        save(c)
        print(request(c, "POST", "/cmd", b"version").strip(), "— токен подошёл")
        return
    if cmd == "install":
        apk = args[0] if args else os.path.join(ROOT, "bridge/apk/knopych-bridge-system.apk")
        # Прошивка GWM не даёт обновлять наш пакет из приложения (whitelist в createSessionInternal),
        # поэтому ставим через adb по Wi-Fi: его служба работает от имени shell, которому можно.
        # Нужен включённый на ГУ adb (один раз: adb root; setprop persist.adb.tcp.port 5555; reboot).
        target = "%s:5555" % host(c)
        subprocess.run(["adb", "connect", target], capture_output=True)
        r = subprocess.run(["adb", "-s", target, "install", "-r", apk], capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        print(out)
        if "Success" in out:
            print("Готово. Проверяю мост…")
            time.sleep(3)
            try:
                with urllib.request.urlopen("http://%s:%d/ping" % (host(c), PORT), timeout=5) as resp:
                    print(resp.read().decode().strip())
            except OSError:
                print("Мост пока не ответил — открой экран «Кнопыч» на ГУ.")
            return
        sys.exit("Установка по adb не прошла (см. выше).\n"
                 "adb по Wi-Fi включён на ГУ? Один раз с кабеля: adb root; "
                 "adb shell setprop persist.adb.tcp.port 5555; adb reboot. На экране ГУ разрешить отладку.")
    if cmd == "logcat":
        n = args[0] if args else "3000"
        text = request(c, "GET", "/logcat?n=" + n)
        os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
        out = os.path.join(ROOT, "logs", "wifi-logcat.txt")
        with open(out, "w") as f:
            f.write(text)
        print("Сохранил", out, "(%d строк)" % text.count("\n"))
        return
    if cmd == "shot":
        # Скриншот экрана ГУ: GET /shot отдаёт PNG.
        req = urllib.request.Request("http://%s:%d/shot" % (host(c), PORT))
        req.add_header("X-Token", c.get("tokens", {}).get(host(c), ""))
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
        except (urllib.error.URLError, OSError) as e:
            sys.exit("Нет связи с %s: %s\nГУ и Mac в одной сети? Попробуй tools/kn.py find" % (host(c), e))
        out = args[0] if args else os.path.join(ROOT, "logs", time.strftime("shot-%Y%m%d-%H%M%S.png"))
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
        print(out)
        return
    if cmd == "snap":
        if not args:
            sys.exit("tools/kn.py snap <имя>")
        d = os.path.join(ROOT, "logs", "snap-" + args[0])
        os.makedirs(d, exist_ok=True)
        for name, q in SNAP:
            with open(os.path.join(d, name + ".txt"), "w") as f:
                f.write(request(c, "POST", "/cmd", q.encode()))
        with open(os.path.join(d, "logcat.txt"), "w") as f:
            f.write(request(c, "GET", "/logcat?n=3000"))
        print("Снимок в", d)
        return
    if cmd == "diff":
        if len(args) < 2:
            sys.exit("tools/kn.py diff <снимок1> <снимок2>")
        a, b = (os.path.join(ROOT, "logs", "snap-" + x) for x in args[:2])
        for name, _ in SNAP:
            la = open(os.path.join(a, name + ".txt")).read().splitlines()
            lb = open(os.path.join(b, name + ".txt")).read().splitlines()
            d = [l for l in difflib.unified_diff(la, lb, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            if d:
                print("== %s ==" % name)
                print("\n".join(d[:200]))
        return

    # всё остальное — команда моста
    print(request(c, "POST", "/cmd", " ".join([cmd] + args).encode()).rstrip())


if __name__ == "__main__":
    main(sys.argv[1:])
