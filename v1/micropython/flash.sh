#!/bin/bash
# Панель «Кнопыч» на MicroPython (ESP32-S3).
#   v1/micropython/flash.sh install   — один раз: стереть плату, записать MicroPython и залить main.py
#   v1/micropython/flash.sh upload    — залить свежий main.py и перезапустить плату
#   v1/micropython/flash.sh run       — запустить main.py с Mac, не сохраняя на плату (для проб)
#   v1/micropython/flash.sh repl      — консоль платы: журнал и REPL (выход — Ctrl+X)
#   v1/micropython/flash.sh listen    — слушать нажатия по USB (panel_usb.py; --gu — изображать ГУ)
# Нужны esptool и mpremote (pip install esptool mpremote). Порт ищется сам; другой — PORT=/dev/cu.xxx
set -euo pipefail
cd "$(dirname "$0")"

MPY_VERSION=20260824-v1.29.0
IMAGE="download/ESP32_GENERIC_S3-${MPY_VERSION}.bin"
IMAGE_URL="https://micropython.org/resources/firmware/ESP32_GENERIC_S3-${MPY_VERSION}.bin"
PORT="${PORT:-$(ls /dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.wchusbserial* 2>/dev/null | head -1 || true)}"

need_port() {
  [ -n "$PORT" ] || { echo "Плата не найдена: подключи ESP по USB"; exit 1; }
  echo "Порт: $PORT"
}

case "${1:-}" in
  install)
    need_port
    if [ ! -f "$IMAGE" ]; then
      mkdir -p download
      curl -fL -o "$IMAGE" "$IMAGE_URL"
    fi
    esptool --chip esp32s3 --port "$PORT" erase-flash
    esptool --chip esp32s3 --port "$PORT" --baud 460800 write-flash 0 "$IMAGE"
    echo "MicroPython записан, жду перезапуска платы…"
    sleep 3
    # После прошивки порт может смениться (родной USB) — ищем заново.
    PORT="$(ls /dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.wchusbserial* 2>/dev/null | head -1 || true)"
    need_port
    mpremote connect "$PORT" cp main.py :main.py + reset
    ;;
  upload)
    need_port
    mpremote connect "$PORT" cp main.py :main.py + reset
    ;;
  run)
    need_port
    mpremote connect "$PORT" run main.py
    ;;
  repl)
    need_port
    mpremote connect "$PORT" repl
    ;;
  listen)
    need_port
    shift
    # Нужен Python с pyserial: обычный python3 или тот, на котором стоит mpremote.
    PY=python3
    if ! python3 -c "import serial" 2>/dev/null; then
      PY="$(head -1 "$(command -v mpremote)" | sed 's/^#!//')"
    fi
    "$PY" panel_usb.py --port "$PORT" "$@"
    ;;
  *) echo "usage: $0 install|upload|run|repl|listen [--gu] [--log]"; exit 1 ;;
esac
