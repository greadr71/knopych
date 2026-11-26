# Knopych panel — прошивка на MicroPython (v0.3-mpy)
# Плата: ESP32-S3 (клон DevKitC-1, модуль N8R2). Подробности: ../../docs/hardware.md
#  - 6 кнопок (GPIO 4,5,6,7,15,16) и 6 светодиодов (GPIO 17,18,8,9,10,11);
#  - кнопка 1 — "сиденье": по кругу выкл -> 3 -> 2 -> 1 -> выкл, яркость = ступень;
#    остальные — вкл/выкл;
#  - Wi-Fi НЕ включается никогда: модуль network не импортируется;
#  - связь с Mac / ГУ по USB (основной вариант сейчас): текстовые строки, см. README.md.
#    Строки протокола начинаются с "!", всё остальное — журнал для человека;
#  - Bluetooth LE (USE_BLE): выключен, пока плате не хватает питания на радио.
#    Протокол BLE тот же, что у Arduino-версии ../firmware/knopych-panel/;
#  - режим "local" (по умолчанию: нажатие само меняет светодиод) /
#    "remote" (светодиоды показывают то, что прислал Mac/ГУ).
# Остановить: Ctrl+C в консоли (mpremote) — попадёшь в REPL.

import os
import sys
import time
import select
import machine
import neopixel
from machine import Pin, PWM
from micropython import const

VERSION = "v0.3-mpy"

# Bluetooth. Включение радио на этой плате роняет питание (BROWNOUT), поэтому пока выключен.
# Включить: True и залить заново (защита ниже не даст плате уйти в вечную перезагрузку).
USE_BLE = False

# ---------- Пины и кнопки ----------
BTN_PINS = (4, 5, 6, 7, 15, 16)
LED_PINS = (17, 18, 8, 9, 10, 11)
N = len(BTN_PINS)
# Сколько ступеней у кнопки: 3 = как сиденье, 1 = просто вкл/выкл.
MAX_LEVEL = (3, 1, 1, 1, 1, 1)
# Яркость (0..255) для ступени 0..3: глаз видит яркость нелинейно.
BRIGHT = (0, 6, 40, 255)

RGB_PIN = 48      # встроенный RGB; если не горит — попробовать 38
RGB_BRIGHT = 20   # 0..255, держим низко: меньше ток

POLL_MS = 5
DEBOUNCE_SAMPLES = 4  # 4 x 5 мс = 20 мс стабильного сигнала
RGB_EVERY = 100       # 100 x 5 мс = раз в 0,5 с

# Защита от просадки питания. Если плата перезагрузилась во время включения BLE
# (питания не хватает радио), этот файл остаётся на флешке. Тогда при следующем
# старте BLE не включаем: кнопки и светодиоды работают, RGB горит красным.
# Файл при этом удаляется, так что следующее включение питания снова пробует BLE.
BLE_TRY_FILE = "ble_try"
BLE_OK_TICKS = 600    # 600 x 5 мс = 3 с без перезагрузки — BLE считается рабочим

# ---------- BLE ----------
# Префикс UUID — исторические байты 6d656368 62757474, UUID не меняем
SERVICE_UUID = "6d656368-6275-7474-0001-000000000000"
BUTTONS_UUID = "6d656368-6275-7474-0002-000000000000"
LEDS_UUID = "6d656368-6275-7474-0003-000000000000"
DEVICE_NAME = "Knopych"

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_ADV_INTERVAL_US = const(100_000)


def _adv_field(kind, value):
    return bytes((len(value) + 1, kind)) + value


RESET_TEXT = {
    machine.PWRON_RESET: "power on (или BROWNOUT — MicroPython их не различает)",
    machine.HARD_RESET: "hard reset",
    machine.WDT_RESET: "watchdog",
    machine.DEEPSLEEP_RESET: "deep sleep",
    machine.SOFT_RESET: "software / crash",
}


def send(line):
    # Строка протокола для Mac/ГУ. Начинается с "!", чтобы отличать от журнала.
    print("!" + line)


class Panel:
    def __init__(self):
        self.btns = [Pin(p, Pin.IN, Pin.PULL_UP) for p in BTN_PINS]
        self.leds = [PWM(Pin(p), freq=1000, duty_u16=0) for p in LED_PINS]
        self.rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)
        self.level = bytearray(N)          # текущая ступень каждого светодиода
        self.stable = [False] * N          # устоявшееся состояние кнопки (True = нажата)
        self.same = [0] * N                # сколько опросов подряд отличалось
        self.conn = None                   # handle подключённого по BLE устройства
        self.remote_mode = False           # True = светодиодами управляет Mac/ГУ
        self.remote_level = None           # новые ступени от BLE, ждут применения в цикле
        self.need_advertise = False
        self.ble = None
        self.ble_failed = False            # BLE выключен защитой от просадки питания
        # USB: читаем команды из того же порта, куда пишем (без блокировки).
        self.usb_poll = select.poll()
        self.usb_poll.register(sys.stdin, select.POLLIN)
        self.usb_buf = ""

    # ---------- Светодиоды ----------
    def brightness(self, i, lvl):
        if lvl == 0:
            return 0
        if MAX_LEVEL[i] == 1:
            return BRIGHT[3]               # вкл/выкл — сразу полная яркость
        return BRIGHT[min(lvl, 3)]

    def show_levels(self):
        for i in range(N):
            self.leds[i].duty_u16(self.brightness(i, self.level[i]) * 257)
        if self.ble:
            self.ble.gatts_write(self.h_leds, bytes(self.level))

    def report_levels(self):
        send("leds " + " ".join(str(x) for x in self.level))

    def apply_levels(self, values):
        # values: список ступеней (может быть короче 6 — остальные без изменений).
        for i in range(min(len(values), N)):
            self.level[i] = min(max(values[i], 0), MAX_LEVEL[i])
        self.show_levels()
        self.report_levels()

    def set_rgb(self, r, g, b):
        self.rgb[0] = (r, g, b)
        self.rgb.write()

    def led_test(self):
        # Короткая проверка при старте: по очереди на полную яркость.
        for led in self.leds:
            led.duty_u16(65535)
            time.sleep_ms(80)
            led.duty_u16(0)

    # ---------- USB ----------
    def poll_usb(self):
        while self.usb_poll.poll(0):
            ch = sys.stdin.read(1)
            if not ch:
                return
            if ch in "\r\n":
                line, self.usb_buf = self.usb_buf.strip(), ""
                if line:
                    self.on_command(line)
            elif len(self.usb_buf) < 80:
                self.usb_buf += ch

    def on_command(self, line):
        parts = line.split()
        cmd, args = parts[0].lower(), parts[1:]
        if cmd == "leds":
            try:
                values = [int(a) for a in args]
            except ValueError:
                send("err leds: нужны числа 0..3, например: leds 3 1 0 0 0 0")
                return
            if not values:
                send("err leds: нужны числа 0..3, например: leds 3 1 0 0 0 0")
                return
            self.remote_mode = True
            self.apply_levels(values)
        elif cmd == "local":
            self.remote_mode = False
            send("mode local")
        elif cmd == "state":
            self.report_levels()
            send("mode " + ("remote" if self.remote_mode else "local"))
        elif cmd == "ping":
            send("pong knopych " + VERSION)
        else:
            send("err unknown: " + line)

    # ---------- BLE ----------
    def setup_ble(self):
        import bluetooth
        ble = bluetooth.BLE()
        ble.active(True)
        ble.config(gap_name=DEVICE_NAME)
        ble.irq(self._irq)
        service = (
            bluetooth.UUID(SERVICE_UUID),
            (
                (bluetooth.UUID(BUTTONS_UUID), _FLAG_READ | _FLAG_NOTIFY),  # 2902 добавляется сам
                (bluetooth.UUID(LEDS_UUID), _FLAG_READ | _FLAG_WRITE),
            ),
        )
        ((self.h_buttons, self.h_leds),) = ble.gatts_register_services((service,))
        ble.gatts_write(self.h_buttons, b"none")
        # Реклама: флаги + имя; UUID сервиса — в ответе на сканирование (иначе не влезает в 31 байт).
        self.adv_data = _adv_field(0x01, b"\x06") + _adv_field(0x09, DEVICE_NAME.encode())
        self.resp_data = _adv_field(0x07, bytes(bluetooth.UUID(SERVICE_UUID)))
        self.ble = ble
        self.show_levels()
        self.advertise()
        print("[ble] advertising as", DEVICE_NAME)

    def advertise(self):
        self.ble.gap_advertise(_ADV_INTERVAL_US, adv_data=self.adv_data, resp_data=self.resp_data)

    def _irq(self, event, data):
        # Вызывается из BLE-стека: только запоминаем, всё остальное — в главном цикле.
        if event == _IRQ_CENTRAL_CONNECT:
            self.conn = data[0]
            print("[ble] connected")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.conn = None
            self.remote_mode = False       # без ГУ возвращаемся к локальному режиму
            self.need_advertise = True
            print("[ble] disconnected")
        elif event == _IRQ_GATTS_WRITE:
            if data[1] != self.h_leds:
                return
            v = self.ble.gatts_read(self.h_leds)
            if len(v) < 1:
                return
            self.remote_mode = True
            self.remote_level = list(v)

    # ---------- Кнопки ----------
    def send_button(self, idx):
        send("btn %d" % (idx + 1))
        if self.ble:
            # send_update=True: уведомление уйдёт всем подписанным BLE-клиентам.
            self.ble.gatts_write(self.h_buttons, ("btn %d" % (idx + 1)).encode(), True)

    def next_level(self, i):
        # выкл -> 3 -> 2 -> 1 -> выкл (для вкл/выкл: 0 <-> 1)
        return MAX_LEVEL[i] if self.level[i] == 0 else self.level[i] - 1

    def on_press(self, idx):
        self.send_button(idx)
        if not self.remote_mode:           # локальный режим: меняем сами
            self.level[idx] = self.next_level(idx)
            self.show_levels()
            self.report_levels()

    def poll_buttons(self):
        # Нажатие засчитывается после 20 мс стабильного LOW.
        for i in range(N):
            raw = self.btns[i].value() == 0
            if raw == self.stable[i]:
                self.same[i] = 0
                continue
            self.same[i] += 1
            if self.same[i] >= DEBOUNCE_SAMPLES:
                self.stable[i] = raw
                self.same[i] = 0
                if raw:
                    self.on_press(i)

    # ---------- Главный цикл ----------
    def step(self, tick):
        self.poll_buttons()
        self.poll_usb()

        # Команда от ГУ по BLE: применяем ступени.
        new = self.remote_level
        if new is not None:
            self.remote_level = None
            self.apply_levels(new)

        # После отключения BLE снова начинаем рекламироваться.
        if self.need_advertise:
            self.need_advertise = False
            time.sleep_ms(200)
            self.advertise()
            print("[ble] advertising again")

        # BLE отработал 3 с без перезагрузки — питание держит, снимаем отметку.
        if tick == BLE_OK_TICKS and self.ble:
            ble_try_done()
            print("[ble] power ok")

        # Встроенный RGB.
        if tick % RGB_EVERY == 0:
            if self.ble_failed:
                self.set_rgb(RGB_BRIGHT, 0, 0)     # красный: BLE выключен из-за питания
            elif not self.ble:
                # Только USB: зелёный = светодиодами управляет Mac/ГУ, выключен = local.
                self.set_rgb(0, RGB_BRIGHT if self.remote_mode else 0, 0)
            elif self.conn is not None:
                self.set_rgb(0, RGB_BRIGHT, 0)
            else:
                blink = (tick // RGB_EVERY) % 2 == 0
                self.set_rgb(0, 0, RGB_BRIGHT if blink else 0)

    def off(self):
        for led in self.leds:
            led.duty_u16(0)
        self.set_rgb(0, 0, 0)
        if self.ble:
            self.ble.active(False)


def ble_crashed_last_time():
    try:
        os.stat(BLE_TRY_FILE)
    except OSError:
        return False
    ble_try_done()
    return True


def ble_try_done():
    try:
        os.remove(BLE_TRY_FILE)
    except OSError:
        pass


def run():
    time.sleep_ms(300)
    print("\nKnopych panel %s, reset reason: %s"
          % (VERSION, RESET_TEXT.get(machine.reset_cause(), "other")))
    panel = Panel()
    panel.led_test()
    panel.show_levels()
    if not USE_BLE:
        ble_try_done()
        print("[ble] off (USE_BLE = False), связь только по USB")
    elif ble_crashed_last_time():
        panel.ble_failed = True
        print("[ble] OFF: прошлый запуск BLE уронил питание (BROWNOUT). Работаю без BLE;"
              " следующее включение питания попробует снова")
    else:
        with open(BLE_TRY_FILE, "w") as f:
            f.write("1")
        panel.setup_ble()
    send("hello knopych " + VERSION)
    panel.report_levels()
    tick = 0
    try:
        while True:
            panel.step(tick)
            tick += 1
            time.sleep_ms(POLL_MS)
    except KeyboardInterrupt:
        print("[stop] остановлено, REPL свободен")
    finally:
        panel.off()


run()
