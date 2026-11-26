#!/bin/bash
# Сборка и прошивка панели «Кнопыч» (ESP32-S3).
#   ./build.sh            — только собрать (v2/firmware/knopych-panel, новая панель)
#   ./build.sh upload     — собрать и прошить (порт ищется сам)
#   ./build.sh monitor    — открыть журнал платы (Ctrl+C — выход)
#   ./build.sh listen     — слушать нажатия по USB (v1/micropython/panel_usb.py; --gu — изображать ГУ)
# Другой скетч: SKETCH=v1/firmware/knopych-panel ./build.sh upload, SKETCH=v2/firmware/pin-scan ./build.sh upload.
# Нужен arduino-cli и пакет esp32:esp32 (brew install arduino-cli; см. docs/firmware.md).
set -euo pipefail
cd "$(dirname "$0")"

SKETCH="${SKETCH:-v2/firmware/knopych-panel}"   # другой скетч: SKETCH=v1/archive/radio-test ./build.sh upload
OUT="build/$SKETCH"                                # вложенно: у v1 и v2 скетч называется одинаково
FQBN="esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=4M,PartitionScheme=default,PSRAM=disabled"
PORT="${PORT:-$(ls /dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.wchusbserial* 2>/dev/null | head -1 || true)}"

case "${1:-build}" in
  build)
    mkdir -p "$OUT"
    arduino-cli compile --fqbn "$FQBN" --output-dir "$OUT" "$SKETCH"
    ;;
  upload)
    [ -n "$PORT" ] || { echo "Плата не найдена: подключи ESP по USB"; exit 1; }
    mkdir -p "$OUT"
    arduino-cli compile --fqbn "$FQBN" --output-dir "$OUT" "$SKETCH"
    arduino-cli upload --fqbn "$FQBN" -p "$PORT" --input-dir "$OUT" "$SKETCH"
    ;;
  monitor)
    [ -n "$PORT" ] || { echo "Плата не найдена: подключи ESP по USB"; exit 1; }
    arduino-cli monitor -p "$PORT" -c baudrate=115200
    ;;
  listen)
    [ -n "$PORT" ] || { echo "Плата не найдена: подключи ESP по USB"; exit 1; }
    shift
    # Протокол общий с MicroPython-версией. Нужен Python с pyserial.
    PY=""
    for c in python3 /usr/bin/python3 "$(head -1 "$(command -v mpremote 2>/dev/null || echo /dev/null)" | sed 's/^#!//')"; do
      if [ -n "$c" ] && "$c" -c "import serial" 2>/dev/null; then PY="$c"; break; fi
    done
    [ -n "$PY" ] || { echo "Нужен pyserial: pip3 install pyserial"; exit 1; }
    "$PY" v1/micropython/panel_usb.py --port "$PORT" "$@"
    ;;
  *) echo "usage: $0 [build|upload|monitor|listen [--gu] [--log]]"; exit 1 ;;
esac
