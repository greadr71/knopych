package ru.knopych.bridge;

import android.content.ContentResolver;
import android.content.SharedPreferences;
import android.os.SystemClock;
import android.provider.Settings;

import java.io.BufferedReader;
import java.io.FileReader;
import java.lang.reflect.Method;

/**
 * adb по Wi-Fi без кабеля. То же, что делает «adb tcpip 5555», но мост делает это сам
 * при каждом старте ГУ (команда wifi_adb on запоминается).
 *
 * Как: выставить свойство порта adbd и перезапустить adbd выключением/включением
 * «Отладки по USB» (Settings.Global.ADB_ENABLED). Пустит ли SELinux приложение system
 * менять эти свойства — не проверено: результат каждой попытки пишется в ответ.
 */
final class WifiAdb {
    static final int PORT = 5555;
    private static final String[] PROPS = {"persist.adb.tcp.port", "service.adb.tcp.port"};

    static String command(Bridge b, SharedPreferences prefs, String arg) {
        switch (arg) {
            case "on":
                // Проверено 8 ноября (ГУ и эмулятор Android 9): SELinux не даёт приложению менять
                // порт adbd (Unable to set property … error 0x18). Остался только ручной режим.
                return "не работает на этом ГУ: Android не даёт приложению включить порт adb."
                        + " Вместо adb: tools/kn.py getprop/settings/dumpsys/logcat.\n" + status(prefs);
            case "off":
                prefs.edit().putBoolean("wifi_adb", false).apply();
                return apply(b, false);
            case "":
            case "status":
                return status(prefs);
            default:
                throw new IllegalArgumentException("wifi_adb on/off/status");
        }
    }

    /** При старте сервиса: если включено, а порт не слушается — включить. */
    /** v0.2 включал это при каждом старте и зря перезапускал adbd. Теперь только выключаем. */
    static void onStart(Bridge b, SharedPreferences prefs) {
        if (prefs.getBoolean("wifi_adb", false)) {
            prefs.edit().putBoolean("wifi_adb", false).apply();
            b.note("adb по Wi-Fi: выключен (на этом ГУ не работает)");
        }
    }

    static String status(SharedPreferences prefs) {
        StringBuilder r = new StringBuilder();
        r.append("wifi_adb=").append(Bridge.onOff(prefs.getBoolean("wifi_adb", false)));
        r.append(" listening_5555=").append(isListening(PORT)).append('\n');
        for (String p : PROPS) r.append(p).append('=').append(get(p)).append('\n');
        r.append("persist.sys.usb.config=").append(get("persist.sys.usb.config")).append('\n');
        return r.toString();
    }

    private static String apply(Bridge b, boolean on) {
        StringBuilder r = new StringBuilder();
        String v = on ? String.valueOf(PORT) : "";
        for (String p : PROPS) {
            try {
                set(p, v);
                r.append("setprop ").append(p).append('=').append(v).append(": ok\n");
            } catch (Throwable t) {
                r.append("setprop ").append(p).append(": ОШИБКА ").append(t.getCause() != null ? t.getCause() : t).append('\n');
            }
        }
        // Перезапуск adbd, чтобы он перечитал порт. Сессия adb по кабелю на секунду оборвётся.
        try {
            ContentResolver cr = b.ctx().getContentResolver();
            Settings.Global.putInt(cr, Settings.Global.ADB_ENABLED, 0);
            SystemClock.sleep(1500);
            Settings.Global.putInt(cr, Settings.Global.ADB_ENABLED, 1);
            r.append("adbd перезапущен (adb_enabled 0 → 1)\n");
        } catch (Throwable t) {
            r.append("перезапуск adbd: ОШИБКА ").append(t).append('\n');
        }
        // adbd поднимается не сразу
        for (int i = 0; i < 10 && isListening(PORT) != on; i++) SystemClock.sleep(500);
        r.append("listening_5555=").append(isListening(PORT));
        return r.toString();
    }

    static String get(String key) {
        try {
            Method m = Class.forName("android.os.SystemProperties").getMethod("get", String.class);
            return (String) m.invoke(null, key);
        } catch (Throwable t) {
            return "ERR(" + t + ")";
        }
    }

    private static void set(String key, String value) throws Exception {
        Method m = Class.forName("android.os.SystemProperties").getMethod("set", String.class, String.class);
        m.invoke(null, key, value);
        if (!value.equals(get(key))) throw new Exception("свойство не изменилось (SELinux?)");
    }

    /** Слушает ли кто-то TCP-порт (по /proc/net/tcp и tcp6, состояние 0A = LISTEN). */
    static boolean isListening(int port) {
        String hex = String.format(":%04X", port);
        for (String f : new String[]{"/proc/net/tcp", "/proc/net/tcp6"}) {
            try (BufferedReader r = new BufferedReader(new FileReader(f))) {
                String line;
                while ((line = r.readLine()) != null) {
                    String[] p = line.trim().split("\\s+");
                    if (p.length > 3 && p[1].endsWith(hex) && "0A".equals(p[3])) return true;
                }
            } catch (Throwable ignored) {
            }
        }
        return false;
    }
}
