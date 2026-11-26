#!/usr/bin/env python3
"""Слушатель панели «Кнопыч» по USB (Mac). Нужен pyserial.

    python3 panel_usb.py            — показывать нажатия; можно печатать команды для платы
    python3 panel_usb.py --gu       — изображать ГУ: на нажатие сам решает ступень и шлёт её
                                      в светодиоды (как будет делать мост на ГУ)
    python3 panel_usb.py --log      — показывать и журнал платы (строки без "!")
    python3 panel_usb.py --port /dev/cu.xxx

Команды, которые можно напечатать (Enter — отправить):
    leds 3 1 0 0 0 0    светодиоды: ступень 0..3 для каждого (можно меньше 6 чисел)
    local               вернуть плате управление светодиодами
    state               спросить у платы ступени и режим
    ping                проверка связи
Выход — Ctrl+C.
"""
import argparse
import glob
import sys
import threading
import time

import serial

MAX_LEVEL = (3, 1, 1, 1, 1, 1)


def find_port():
    for pattern in ("/dev/cu.usbmodem*", "/dev/cu.wchusbserial*", "/dev/cu.usbserial*"):
        ports = sorted(glob.glob(pattern))
        if ports:
            return ports[0]
    return None


def open_port(name):
    s = serial.Serial()
    s.port = name
    s.baudrate = 115200
    s.timeout = 0.2
    # Не дёргаем линии DTR/RTS: на разъёме COM/UART они перезагружают плату.
    s.dtr = False
    s.rts = False
    s.open()
    return s


def main():
    ap = argparse.ArgumentParser(description="Панель «Кнопыч» по USB")
    ap.add_argument("--port")
    ap.add_argument("--gu", action="store_true", help="изображать ГУ")
    ap.add_argument("--log", action="store_true", help="показывать журнал платы")
    args = ap.parse_args()

    port = args.port or find_port()
    if not port:
        sys.exit("Плата не найдена: подключи ESP по USB")
    s = open_port(port)
    print("Порт %s. Жми кнопки на панели; Ctrl+C — выход." % port)
    if args.gu:
        print("Режим ГУ: на каждое нажатие отвечаю командой leds.")

    lock = threading.Lock()
    state = [0] * 6  # что "ГУ" считает включённым

    def write(line):
        with lock:
            s.write((line + "\n").encode())

    def on_line(line):
        if not line.startswith("!"):
            if args.log and line:
                print("   журнал: " + line)
            return
        msg = line[1:]
        if msg.startswith("btn "):
            n = int(msg.split()[1])
            print(">> КНОПКА %d" % n)
            if args.gu:
                i = n - 1
                state[i] = MAX_LEVEL[i] if state[i] == 0 else state[i] - 1
                cmd = "leds " + " ".join(map(str, state))
                print("<< " + cmd)
                write(cmd)
        elif msg == "vbtn 1":
            print(">> ВЕРТУШОК нажат")
        elif msg == "vbtn 0":
            print(">> ВЕРТУШОК отпущен")
        elif msg.startswith("hello"):
            # Плата (пере)запустилась — например, от открытия порта COM/UART.
            print("   плата запустилась: " + msg[6:])
            if args.gu:
                state[:] = [0] * 6
                write("leds 0 0 0 0 0 0")
        else:
            print("   плата: " + msg)

    def reader():
        buf = b""
        while True:
            try:
                data = s.read(256)
            except serial.SerialException:
                print("!! порт пропал (плата перезагрузилась или отключена)")
                return
            buf += data
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                on_line(raw.decode(errors="replace").strip())

    threading.Thread(target=reader, daemon=True).start()
    # Если плата перезагрузилась от открытия порта, она сама пришлёт "hello";
    # если нет — ответит на ping.
    time.sleep(2)
    write("ping")
    if args.gu:
        write("leds 0 0 0 0 0 0")

    try:
        for line in sys.stdin:
            line = line.strip()
            if line:
                write(line)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            write("local")
        except serial.SerialException:
            pass
        print("\nПока.")


if __name__ == "__main__":
    main()
