package ru.knopych.bridge;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.res.Resources;
import android.graphics.drawable.Drawable;
import android.os.IBinder;
import android.os.Parcel;
import android.os.SystemClock;
import android.provider.Settings;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Тема ГУ (и приборки) через системную службу Aptiv com.aptiv.thememanager.
 * Так же делает штатный магазин тем: bindService → IAptivThemeManager.setTheme(Theme).
 * AIDL не копируем — пишем Parcel вручную (порядок полей из aptiv.thememanager.Theme.writeToParcel).
 * Служба exported=false, но мост работает как uid system — ему можно.
 * Подробно: docs/gwm-api.md → «Тема ГУ».
 */
final class ThemeCtl {
    private static final String PKG = "com.aptiv.thememanager";
    private static final String DESCRIPTOR = "aptiv.thememanager.IAptivThemeManager";
    private static final int TRANSACTION_setTheme = 1;

    /** Известные локальные темы (id → название). Чего нет в прошивке, служба сама откажет. */
    static final int[] IDS = {1, 2, 3, 4};
    private static final String[] NAMES = {"", "异域空间", "空间折叠", "沙漠赤金", "经典流光"};

    private static IBinder binder;
    private static ServiceConnection conn;

    static String command(Context ctx, String arg) throws Exception {
        if (arg.isEmpty()) return describe(ctx);
        if (arg.equals("probe")) return probe(ctx);
        int cur = currentId(ctx);
        int id;
        if (arg.equals("next")) {
            id = IDS[0];
            for (int i = 0; i < IDS.length; i++) if (IDS[i] == cur) id = IDS[(i + 1) % IDS.length];
        } else {
            id = Integer.parseInt(arg);
        }
        if (id == cur && isApplied(ctx, id)) return "тема " + id + " уже стоит\n" + describe(ctx);
        boolean ok = set(ctx, id);
        if (!ok) return "служба тем отказала (тема " + id + " недоступна?)\n" + describe(ctx);
        // служба ждёт ответа приборки (до ~4 с) и только потом пишет настройку
        long until = SystemClock.uptimeMillis() + 10000;
        while (SystemClock.uptimeMillis() < until && currentId(ctx) != id) SystemClock.sleep(300);
        if (currentId(ctx) != id) return "запрос принят, но тема пока не сменилась\n" + describe(ctx);
        // настройку служба пишет сразу, а экран перекрашивает SystemUI: он читает def_… и
        // рассылает app_… (см. docs/gwm-api.md). Ждём, пока совпадёт и это.
        until = SystemClock.uptimeMillis() + 5000;
        while (SystemClock.uptimeMillis() < until && !isApplied(ctx, id)) SystemClock.sleep(300);
        return (isApplied(ctx, id)
                ? "тема переключена на " + id
                : "настройка темы " + id + " записана, но экран не перекрасился") + "\n" + describe(ctx);
    }

    static int currentId(Context ctx) {
        String s = Settings.System.getString(ctx.getContentResolver(), "def_aptiv_config_current_theme_id");
        try { return Integer.parseInt(s.trim()); } catch (Throwable t) { return -1; }
    }

    /** Настройка, которую рассылает SystemUI: по ней приложения и грузят skin (app_…). */
    private static final String APP_PKG = "app_aptiv_config_current_theme_package_name";

    private static String pkg(Context ctx, String key) {
        String s = Settings.System.getString(ctx.getContentResolver(), key);
        return s == null ? "" : s.trim();
    }

    /** Пакет скина, который сейчас на экране; пусто — скина нет (базовая графика прошивки). */
    static String currentPkg(Context ctx) {
        String p = pkg(ctx, APP_PKG);
        return p.isEmpty() ? pkg(ctx, "def_aptiv_config_current_theme_package_name") : p;
    }

    /** Тема стоит и на экране: и настройка службы, и её ретрансляция от SystemUI — наша тема. */
    static boolean isApplied(Context ctx, int id) {
        String def = pkg(ctx, "def_aptiv_config_current_theme_package_name");
        return currentId(ctx) == id && !def.isEmpty() && def.equals(pkg(ctx, APP_PKG));
    }

    static String describe(Context ctx) {
        StringBuilder b = new StringBuilder();
        b.append("theme=").append(currentId(ctx)).append(' ')
                .append(Settings.System.getString(ctx.getContentResolver(), "def_aptiv_config_current_theme_name"))
                .append(" (").append(Settings.System.getString(ctx.getContentResolver(),
                        "def_aptiv_config_current_theme_package_name")).append(")\n");
        b.append("на экране: ").append(pkg(ctx, APP_PKG)).append('\n');
        b.append("темы:");
        for (int id : IDS) b.append(' ').append(id).append('=').append(NAMES[id]);
        b.append("\nкоманды: theme N | theme next | theme probe");
        return b.toString();
    }

    /**
     * Диагностика: что переопределяет пакет текущей темы. Скин подменяет ресурсы по имени entry,
     * поэтому здесь те же имена, что и у штатных плашек ГУ (рамка громкости, рамка поп-апа).
     */
    static String probe(Context ctx) {
        String p = pkg(ctx, APP_PKG);
        if (p.isEmpty()) p = pkg(ctx, "def_aptiv_config_current_theme_package_name");
        if (p.isEmpty()) return "тема не задана (def_/app_…_package_name пусты)";
        StringBuilder b = new StringBuilder("скин: ").append(p).append('\n');
        try {
            Resources r = ctx.getPackageManager().getResourcesForApplication(p);
            String[] draws = {"volume_adjust_frame", "common_popup_02", "common_popup_05",
                    "common_popup_03", "common_popup_big", "common_button02"};
            for (String n : draws) {
                int id = r.getIdentifier(n, "drawable", p);
                if (id == 0) { b.append(n).append(": нет в теме\n"); continue; }
                Drawable d = r.getDrawable(id, null);
                b.append(n).append(": есть, ")
                        .append(d == null ? "null" : d.getClass().getSimpleName())
                        .append(d == null ? "" : " " + d.getIntrinsicWidth() + "x" + d.getIntrinsicHeight())
                        .append('\n');
            }
            String[] cols = {"common_highlight_without_bg", "text_main_color", "common_highlight_progress_bar_left"};
            for (String n : cols) {
                int id = r.getIdentifier(n, "color", p);
                b.append(n).append(": ")
                        .append(id == 0 ? "нет в теме" : String.format("#%08X", r.getColor(id, null)))
                        .append('\n');
            }
        } catch (Throwable t) {
            b.append("пакет темы недоступен: ").append(t);
        }
        return b.toString();
    }

    static boolean set(Context ctx, int id) throws Exception {
        IBinder b = connect(ctx);
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(DESCRIPTOR);
            data.writeInt(1);                 // Theme != null
            data.writeInt(id);                // mThemeID
            data.writeString(id < NAMES.length ? NAMES[id] : ""); // mThemeName (не null)
            data.writeString("set_theme");    // mCommand
            data.writeString("local");        // mThemeLocation
            for (int i = 0; i < 9; i++) data.writeString(""); // filePath … clasterPath
            data.writeInt(0);                 // mClasterFilesize
            data.writeInt(0);                 // mClasterLayoutType
            b.transact(TRANSACTION_setTheme, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally {
            reply.recycle();
            data.recycle();
        }
    }

    /** Вызывать не из главного потока: onServiceConnected приходит именно в главный. */
    private static IBinder connect(Context ctx) throws Exception {
        final CountDownLatch latch = new CountDownLatch(1);
        synchronized (ThemeCtl.class) {
            if (binder != null && binder.isBinderAlive()) return binder;
            binder = null;
            if (conn != null) {
                try { ctx.unbindService(conn); } catch (Throwable ignore) { }
            }
            conn = new ServiceConnection() {
                @Override public void onServiceConnected(ComponentName n, IBinder s) {
                    synchronized (ThemeCtl.class) { binder = s; }
                    latch.countDown();
                }
                @Override public void onServiceDisconnected(ComponentName n) {
                    synchronized (ThemeCtl.class) { binder = null; }
                }
            };
            Intent i = new Intent(DESCRIPTOR).setPackage(PKG);
            if (!ctx.bindService(i, conn, Context.BIND_AUTO_CREATE)) {
                conn = null;
                throw new IllegalStateException("не удалось подключиться к службе тем " + PKG);
            }
        }
        if (!latch.await(5, TimeUnit.SECONDS)) throw new IllegalStateException("служба тем не ответила за 5 с");
        synchronized (ThemeCtl.class) { return binder; }
    }
}
