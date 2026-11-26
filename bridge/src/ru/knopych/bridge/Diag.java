package ru.knopych.bridge;

import android.content.ContentResolver;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

/**
 * Диагностика «только посмотреть» (замена adb shell, которого по Wi-Fi нет).
 * Ничего не меняет. Для поиска «как включается X»: снять снимок, нажать X на экране, снять ещё раз
 * и сравнить (tools/kn.py snap / diff) — так находили команды подогревов.
 *
 *   getprop [фильтр]                       свойства системы
 *   settings [system|secure|global] [фильтр] настройки Android (тема, яркость и т.п. часто здесь)
 *   dumpsys служба [фильтр]                 состояние службы, без дополнительных аргументов
 *   packages [фильтр]                       установленные пакеты
 *   intents пакет                           экраны, ресиверы, службы, провайдеры пакета (с чем можно говорить)
 */
final class Diag {
    static String run(Context ctx, String cmd, String arg) throws Exception {
        String[] p = arg.isEmpty() ? new String[0] : arg.split("\\s+");
        switch (cmd) {
            case "getprop":
                return filter(exec("getprop"), p.length > 0 ? p[0] : "");
            case "settings": {
                String table = p.length > 0 ? p[0] : "all";
                String f = p.length > 1 ? p[1] : "";
                if (!table.matches("all|system|secure|global")) {
                    // «settings тема» — фильтр по всем таблицам
                    f = table;
                    table = "all";
                }
                StringBuilder b = new StringBuilder();
                for (String t : new String[]{"system", "secure", "global"}) {
                    if (table.equals("all") || table.equals(t)) b.append(settings(ctx, t, f));
                }
                return b.length() == 0 ? "(ничего не нашлось)" : b.toString();
            }
            case "dumpsys": {
                if (p.length == 0) return filter(exec("dumpsys", "-l"), "");
                // только имя службы: у некоторых служб есть аргументы, которые что-то меняют
                if (!p[0].matches("[a-z0-9_.\\-]+")) throw new IllegalArgumentException("имя службы");
                return filter(exec("dumpsys", p[0]), p.length > 1 ? p[1] : "");
            }
            case "packages":
                return packages(ctx, p.length > 0 ? p[0] : "");
            case "intents":
                if (p.length == 0) throw new IllegalArgumentException("intents пакет");
                return intents(ctx, p[0]);
        }
        throw new IllegalArgumentException(cmd);
    }

    private static String settings(Context ctx, String table, String f) {
        StringBuilder b = new StringBuilder();
        ContentResolver cr = ctx.getContentResolver();
        try (Cursor c = cr.query(Uri.parse("content://settings/" + table), new String[]{"name", "value"}, null, null, null)) {
            List<String> rows = new ArrayList<>();
            while (c != null && c.moveToNext()) {
                String line = table + "/" + c.getString(0) + "=" + c.getString(1);
                if (matches(line, f)) rows.add(line);
            }
            Collections.sort(rows);
            for (String r : rows) b.append(r).append('\n');
        } catch (Throwable t) {
            b.append(table).append(": ERROR ").append(t).append('\n');
        }
        return b.toString();
    }

    private static String packages(Context ctx, String f) {
        PackageManager pm = ctx.getPackageManager();
        List<String> rows = new ArrayList<>();
        for (PackageInfo pi : pm.getInstalledPackages(0)) {
            boolean sys = (pi.applicationInfo.flags & ApplicationInfo.FLAG_SYSTEM) != 0;
            String line = pi.packageName + " " + pi.versionName + (sys ? " [system]" : "");
            if (matches(line, f)) rows.add(line);
        }
        Collections.sort(rows);
        return String.join("\n", rows) + "\n";
    }

    private static String intents(Context ctx, String pkg) throws Exception {
        PackageManager pm = ctx.getPackageManager();
        PackageInfo pi = pm.getPackageInfo(pkg, PackageManager.GET_ACTIVITIES | PackageManager.GET_RECEIVERS
                | PackageManager.GET_SERVICES | PackageManager.GET_PROVIDERS);
        StringBuilder b = new StringBuilder();
        b.append(pkg).append(' ').append(pi.versionName).append('\n');
        if (pi.activities != null) for (android.content.pm.ActivityInfo a : pi.activities)
            b.append("activity ").append(a.name).append(a.exported ? " (exported)" : "").append('\n');
        if (pi.receivers != null) for (android.content.pm.ActivityInfo a : pi.receivers)
            b.append("receiver ").append(a.name).append(a.exported ? " (exported)" : "").append('\n');
        if (pi.services != null) for (android.content.pm.ServiceInfo a : pi.services)
            b.append("service ").append(a.name).append(a.exported ? " (exported)" : "").append('\n');
        if (pi.providers != null) for (android.content.pm.ProviderInfo a : pi.providers)
            b.append("provider ").append(a.name).append(" authority=").append(a.authority).append('\n');
        return b.toString();
    }

    private static boolean matches(String line, String f) {
        return f.isEmpty() || line.toLowerCase(Locale.US).contains(f.toLowerCase(Locale.US));
    }

    private static String filter(String text, String f) {
        if (f.isEmpty()) return text;
        StringBuilder b = new StringBuilder();
        for (String l : text.split("\n")) if (matches(l, f)) b.append(l).append('\n');
        return b.toString();
    }

    private static String exec(String... cmd) throws Exception {
        Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        try (InputStream in = p.getInputStream()) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) > 0 && bo.size() < 8 * 1024 * 1024) bo.write(buf, 0, n);
        }
        if (!p.waitFor(30, TimeUnit.SECONDS)) p.destroy();
        return bo.toString("UTF-8");
    }
}
