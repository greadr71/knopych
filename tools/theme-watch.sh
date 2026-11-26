#!/bin/bash
# Записать, что происходит на ГУ при смене темы (или любом другом действии на экране).
# Только чтение: ничего на ГУ не меняет.
#
#   tools/theme-watch.sh            # IP по умолчанию
#   MB_HOST=10.x.x.x tools/theme-watch.sh
#
# Что делает:
#   1. adb connect, снимок «до»: свойства, настройки, uimode, overlay, история broadcast.
#   2. Пишет logcat (все буферы), пока вы переключаете тему на экране ГУ.
#   3. Снимок «после», разница и выжимка из logcat по словам theme/night/uimode/overlay/skin.
# Всё складывается в logs/theme-<время>/.

set -u
HOST="${MB_HOST:-192.168.43.12}:5555"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$ROOT/logs/theme-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$D"
A=(adb -s "$HOST")

adb connect "$HOST" >/dev/null
if ! "${A[@]}" shell true 2>/dev/null; then
  echo "ГУ не отвечает по adb ($HOST). ГУ и Mac в одной сети? IP верный?" >&2
  exit 1
fi
"${A[@]}" root >/dev/null 2>&1; sleep 2; adb connect "$HOST" >/dev/null

snap() {  # $1 = before|after
  local s="$D/$1"; mkdir -p "$s"
  "${A[@]}" shell getprop                         > "$s/getprop.txt"
  for ns in system secure global; do
    "${A[@]}" shell settings list $ns | sort      > "$s/settings-$ns.txt"
  done
  "${A[@]}" shell dumpsys uimode                  > "$s/uimode.txt"
  "${A[@]}" shell cmd overlay list                > "$s/overlay.txt" 2>&1
  "${A[@]}" shell dumpsys activity broadcasts history > "$s/broadcasts.txt" 2>&1
  "${A[@]}" shell dumpsys activity top | grep -E "ACTIVITY|mCurConfiguration|uiMode" > "$s/top.txt"
}

echo "Снимок «до»…"
snap before

"${A[@]}" logcat -b all -v threadtime -T 1 > "$D/logcat.txt" 2>&1 &
LC=$!
sleep 1
echo
echo ">>> Переключите тему на экране ГУ (можно туда и обратно). Потом нажмите Enter."
read -r
sleep 2
kill $LC 2>/dev/null

echo "Снимок «после»…"
snap after

{
  for f in "$D"/before/*.txt; do
    n=$(basename "$f")
    [ "$n" = broadcasts.txt ] && continue
    d=$(diff "$f" "$D/after/$n" | grep '^[<>]')
    [ -n "$d" ] && { echo "== $n =="; echo "$d"; echo; }
  done
  echo "== broadcasts: новые action =="
  diff <(grep -o 'act=[^ }]*' "$D/before/broadcasts.txt" | sort -u) \
       <(grep -o 'act=[^ }]*' "$D/after/broadcasts.txt"  | sort -u) | grep '^>'
  echo
  echo "== logcat: theme/night/uimode/overlay/skin/day =="
  grep -iE 'theme|night|uimode|ui_mode|overlay|skin|daymode|day_mode|dark|light' "$D/logcat.txt" \
    | grep -v -iE 'highlight|flight' | head -300
} > "$D/summary.txt"

cat "$D/summary.txt"
echo
echo "Всё в $D (logcat целиком: logcat.txt, $(wc -l < "$D/logcat.txt") строк)"
