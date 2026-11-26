#!/bin/bash
# Сборка приложения-моста без Gradle: javac → d8 → aapt2 → apksigner.
# Результат: build/knopych-bridge-system.apk и build/knopych-bridge-sig.apk
#   system — с sharedUserId=android.uid.system (основной вариант);
#   sig    — без sharedUserId (запасной, если первый не встанет).
# Оба подписаны публичным тестовым ключом AOSP platform — тем же, что и прошивка ГУ.
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
BT="${BUILD_TOOLS:-$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)}"
ANDROID_JAR="${ANDROID_JAR:-$SDK/platforms/android-28/android.jar}"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}"
export PATH="$JAVA_HOME/bin:$PATH"

# Отпечаток сертификата, которым подписаны системные приложения ГУ (проверено 2026-11-07)
EXPECTED_FP="C8:A2:E9:BC:CF:59:7C:2F:B6:DC:66:BE:E2:93:FC:13:F2:FC:47:EC:77:BC:6B:2B:0D:52:C1:1F:51:19:2A:B8"
KEYS=build/keys
AOSP=https://android.googlesource.com/platform/build/+/refs/tags/android-9.0.0_r1/target/product/security

rm -rf build/classes build/stubs build/dex build/variant build/res.zip build/*.apk
mkdir -p build/classes build/stubs build/dex "$KEYS"

# 1. Тестовый ключ платформы AOSP (публичный)
if [ ! -f "$KEYS/platform.pk8" ]; then
  curl -sf "$AOSP/platform.pk8?format=TEXT" | base64 -d > "$KEYS/platform.pk8"
  curl -sf "$AOSP/platform.x509.pem?format=TEXT" | base64 -d > "$KEYS/platform.x509.pem"
fi
FP=$(openssl x509 -in "$KEYS/platform.x509.pem" -noout -fingerprint -sha256 | cut -d= -f2)
if [ "$FP" != "$EXPECTED_FP" ]; then
  echo "ОШИБКА: ключ не совпадает с подписью ГУ: $FP" >&2
  exit 1
fi

# 2. Компиляция (заглушки Aptiv только для компиляции, в APK не попадают)
javac --release 8 -nowarn -encoding UTF-8 -d build/stubs -cp "$ANDROID_JAR" $(find stubs -name '*.java')
javac --release 8 -encoding UTF-8 -d build/classes -cp "$ANDROID_JAR:build/stubs" $(find src -name '*.java')

# 3. dex
"$BT/d8" --release --min-api 28 --lib "$ANDROID_JAR" --classpath build/stubs \
  --output build/dex $(find build/classes -name '*.class')

# 4. Два варианта: ресурсы → манифест → apk → подпись
"$BT/aapt2" compile --dir res -o build/res.zip
for VARIANT in system sig; do
  OUT=build/variant/$VARIANT
  mkdir -p "$OUT"
  if [ "$VARIANT" = system ]; then SU='android:sharedUserId="android.uid.system"'; else SU=''; fi
  sed "s#@SHARED_USER@#$SU#" AndroidManifest.xml > "$OUT/AndroidManifest.xml"
  "$BT/aapt2" link -o "$OUT/unsigned.apk" -I "$ANDROID_JAR" --manifest "$OUT/AndroidManifest.xml" build/res.zip
  (cd build/dex && zip -q -j "../../$OUT/unsigned.apk" classes.dex)
  "$BT/zipalign" -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
  "$BT/apksigner" sign --v1-signing-enabled true --v2-signing-enabled true --key "$KEYS/platform.pk8" --cert "$KEYS/platform.x509.pem" \
    --out "build/knopych-bridge-$VARIANT.apk" "$OUT/aligned.apk"
  "$BT/apksigner" verify --print-certs "build/knopych-bridge-$VARIANT.apk" | grep -i "SHA-256" | head -1
done

mkdir -p apk
cp build/knopych-bridge-system.apk build/knopych-bridge-sig.apk apk/
ls -la apk/*.apk
