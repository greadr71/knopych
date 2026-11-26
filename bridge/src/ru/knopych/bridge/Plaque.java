package ru.knopych.bridge;

import android.content.Context;
import android.content.res.Resources;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * Плашка поверх любого экрана, как штатный индикатор громкости: своё окно, ввод не перехватывает,
 * фокус не забирает, нижний экран не перерисовывается.
 * Окно одно и живёт между вызовами: смена содержимого (уровень подогрева) только перерисовывает плашку,
 * а не снимает и добавляет окно заново.
 */
final class Plaque {
    private static final long SHOW_MS = 2500;
    /** Ширина по содержимому, но не шире: длинные строки переносятся. */
    private static final int MAX_W = 1200;
    /** Включённый подогрев: ступени и иконка. */
    private static final int ACCENT = 0xFFFF9A4D;
    private static final int DIM = 0x66FFFFFF;
    /** Основной текст ГУ: text_main_color. */
    private static final int TEXT = 0xFFFFFFFF;
    private static final Handler handler = new Handler(Looper.getMainLooper());
    private static WindowManager wm;
    private static LinearLayout root;
    private static boolean attached;
    /** Пакет темы, из которого взята текущая рамка: root живёт вечно, фон надо обновлять при смене темы. */
    private static String framePkg;

    /** Скрыть плашку. */
    private static final Runnable hideRun = () -> {
        if (!attached || wm == null || root == null) return;
        try { wm.removeViewImmediate(root); } catch (Throwable ignored) { }
        attached = false;
    };

    /** Просто текст. */
    static void show(Context ctx, String text) {
        fill(ctx, (c, r) -> {
            TextView tv = new TextView(c);
            tv.setText(text);
            tv.setTextColor(TEXT);
            tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 44);
            tv.setGravity(Gravity.CENTER);
            tv.setMaxWidth(MAX_W);
            r.addView(tv);
        });
    }

    /** Подогрев сиденья: три ступени сверху (уровень 1..3), ниже иконка сиденья и подпись. */
    static void showSeat(Context ctx, boolean passenger, int level) {
        fill(ctx, (c, r) -> {
            int lvl = Math.max(0, Math.min(3, level));
            r.addView(steps(c, lvl));
            // иконка кейкапа 525×447: пропорции держим сами, VectorDrawable тянется по bounds
            ImageView ic = icon(c, "kc_heater", 150, 128, !passenger); // три стрелки, у водителя сиденье с другой стороны
            // тускнеем альфой, а не цветом: SRC_ATOP полупрозрачным белым по белому вектору не темнит
            if (lvl > 0) { ic.setColorFilter(ACCENT); ic.setAlpha(1f); }
            else { ic.setColorFilter(null); ic.setAlpha(0.4f); }
            r.addView(ic);
            r.addView(caption(c, passenger ? "Пассажир" : "Водитель"));
        });
    }

    /** Лобовое стекло: иконка и состояние, ступеней нет — оно не ступенчатое. */
    static void showWindshield(Context ctx, boolean on) {
        fill(ctx, (c, r) -> {
            ImageView ic = icon(c, "kc_wind", 212, 135, false);
            if (on) { ic.setColorFilter(ACCENT); ic.setAlpha(1f); }
            else { ic.setColorFilter(null); ic.setAlpha(0.4f); }
            r.addView(ic);
            r.addView(caption(c, on ? "Включено" : "Выключено"));
        });
    }

    /** Слот положения сиденья: три кейкапа в ряд, выбранный slot (1..3) — оранжевый. Без подписи. */
    static void showPreset(Context ctx, int slot) {
        showPreset(ctx, slot, null);
    }

    /** Тот же ряд с подписью: подтверждение сохранения слота. */
    static void showPreset(Context ctx, int slot, String text) {
        fill(ctx, (c, r) -> {
            int cur = Math.max(1, Math.min(3, slot));
            LinearLayout row = new LinearLayout(c);
            row.setOrientation(LinearLayout.HORIZONTAL);
            for (int i = 1; i <= 3; i++) {
                // кейкап 290×231: 130×104 держит пропорции, VectorDrawable тянется по bounds
                ImageView ic = icon(c, "kc_seat" + i, 130, 104, false);
                LinearLayout.LayoutParams p = (LinearLayout.LayoutParams) ic.getLayoutParams();
                if (i > 1) p.leftMargin = dp(c, 7);   // зазор 14 dp между иконками, края без полей
                if (i < 3) p.rightMargin = dp(c, 7);
                if (i == cur) { ic.setColorFilter(ACCENT); ic.setAlpha(1f); }
                else { ic.setColorFilter(null); ic.setAlpha(0.4f); }
                row.addView(ic);
            }
            r.addView(row);
            if (text != null) r.addView(caption(c, text));
        });
    }

    /** Отладка: размеры окна и детей после раскладки (popup sizes). */
    static void sizes(Context ctx) {
        showSeat(ctx, false, 3);
        handler.postDelayed(() -> {
            if (root == null) return;
            StringBuilder b = new StringBuilder("плашка sizes: окно ")
                    .append(root.getWidth()).append('x').append(root.getHeight())
                    .append(", padding ").append(root.getPaddingLeft()).append('/').append(root.getPaddingTop())
                    .append('/').append(root.getPaddingRight()).append('/').append(root.getPaddingBottom());
            for (int i = 0; i < root.getChildCount(); i++) {
                View v = root.getChildAt(i);
                b.append(" | ").append(v.getClass().getSimpleName()).append(' ')
                        .append(v.getWidth()).append('x').append(v.getHeight());
                if (v instanceof LinearLayout) for (int j = 0; j < ((LinearLayout) v).getChildCount(); j++) {
                    View c = ((LinearLayout) v).getChildAt(j);
                    b.append(", ").append(c.getWidth()).append('x').append(c.getHeight());
                }
            }
            Bridge.get(ctx).note(b.toString());
        }, 500);
    }

    private interface Filler {
        void fill(Context ctx, LinearLayout root);
    }

    private static void fill(Context ctx, Filler filler) {
        final Context app = ctx.getApplicationContext();
        handler.post(() -> showOnMain(app, filler));
    }

    private static void showOnMain(Context ctx, Filler filler) {
        if (!ensure(ctx)) return;
        if (!ThemeCtl.currentPkg(ctx).equals(framePkg)) frame(ctx, root);
        handler.removeCallbacks(hideRun);
        root.removeAllViews();
        filler.fill(ctx, root);
        handler.postDelayed(hideRun, SHOW_MS);
    }

    /** Окно создаётся один раз и дальше только наполняется: смена уровня не мигает. */
    private static boolean ensure(Context ctx) {
        if (wm == null) wm = (WindowManager) ctx.getSystemService(Context.WINDOW_SERVICE);
        if (wm == null) return false;
        if (root == null) {
            root = new LinearLayout(ctx);
            root.setOrientation(LinearLayout.VERTICAL);
            root.setGravity(Gravity.CENTER); // и по вертикали: если система раздует окно, содержимое останется по центру
            frame(ctx, root);
            // отступы задаём после фона: padding из .9.png не должен их перебить
            int p = dp(ctx, 48);
            root.setPadding(p, dp(ctx, 36), p, dp(ctx, 36));
        }
        if (attached) return true;

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        lp.gravity = Gravity.CENTER;
        lp.packageName = ctx.getPackageName();
        lp.setTitle("knopych-plaque");
        try {
            wm.addView(root, lp);
        } catch (Throwable t) { // нет права на окно — не роняем сервис
            Bridge.get(ctx).note("плашка: окно не добавилось: " + t);
            return false;
        }
        attached = true;
        return true;
    }

    /** Подложка — штатная рамка ГУ: nine-patch из volume_adjust_frame.png кита. */
    private static void frame(Context ctx, LinearLayout root) {
        framePkg = ThemeCtl.currentPkg(ctx);
        Drawable theme = themeFrame(ctx, framePkg);
        if (theme != null) {
            root.setBackground(theme);
            return;
        }
        int id = ctx.getResources().getIdentifier("plaque_frame", "drawable", ctx.getPackageName());
        if (id != 0) {
            root.setBackgroundResource(id);
            return;
        }
        GradientDrawable bg = new GradientDrawable(); // рамки нет — простая подложка, без прозрачности
        bg.setColor(0xFF000000);
        bg.setCornerRadius(dp(ctx, 21));
        bg.setStroke(dp(ctx, 2), 0xFFA2C1CA);
        root.setBackground(bg);
    }

    /**
     * Рамка активной темы: скин подменяет volume_adjust_frame своим PNG без .9-меток,
     * поэтому режем его сами. Нет скина/рамки — null, ниже сработает вшитая.
     */
    private static Drawable themeFrame(Context ctx, String pkg) {
        if (pkg.isEmpty()) return null;
        try {
            Resources r = ctx.getPackageManager().getResourcesForApplication(pkg);
            int id = r.getIdentifier("volume_adjust_frame", "drawable", pkg);
            if (id == 0) return null;
            Drawable d = r.getDrawable(id, null);
            if (!(d instanceof BitmapDrawable)) return null;
            Bitmap bmp = ((BitmapDrawable) d).getBitmap();
            return bmp == null ? null : new Nine(bmp);
        } catch (Throwable t) { // битая тема — не роняем сервис, рисуем вшитую рамку
            return null;
        }
    }

    /** 9-slice поверх сырого PNG темы: квадратные поля 20 px, середина тянется. */
    private static final class Nine extends Drawable {
        private static final int L = 20, R = 20, T = 20, B = 20;
        private final Bitmap bmp;
        private final Paint paint = new Paint(Paint.FILTER_BITMAP_FLAG);
        private final Rect src = new Rect();
        private final Rect dst = new Rect();

        Nine(Bitmap bmp) { this.bmp = bmp; }

        @Override
        public void draw(Canvas c) {
            Rect b = getBounds();
            int w = bmp.getWidth(), h = bmp.getHeight();
            int dw = b.width(), dh = b.height();
            int dxm = Math.max(0, dw - L - R), dym = Math.max(0, dh - T - B);
            int[] xs = {0, L, w - R, w};
            int[] xd = {0, L, L + dxm, dw};
            int[] ys = {0, T, h - B, h};
            int[] yd = {0, T, T + dym, dh};
            for (int i = 0; i < 3; i++) {
                for (int j = 0; j < 3; j++) {
                    src.set(xs[i], ys[j], xs[i + 1], ys[j + 1]);
                    dst.set(b.left + xd[i], b.top + yd[j], b.left + xd[i + 1], b.top + yd[j + 1]);
                    c.drawBitmap(bmp, src, dst, paint);
                }
            }
        }

        @Override public void setAlpha(int alpha) { paint.setAlpha(alpha); }
        @Override public void setColorFilter(ColorFilter cf) { paint.setColorFilter(cf); }
        @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
        @Override public int getIntrinsicWidth() { return bmp.getWidth(); }
        @Override public int getIntrinsicHeight() { return bmp.getHeight(); }
        // размер окна задаёт содержимое: иначе View берёт минимум из фона (546x167) и рамка распирает плашку
        @Override public int getMinimumWidth() { return 0; }
        @Override public int getMinimumHeight() { return 0; }
    }

    /** Три ступени: 1..3 — сколько горит, 0 — ни одной (выключено). */
    private static View steps(Context ctx, int level) {
        LinearLayout row = new LinearLayout(ctx);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.BOTTOM);
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        rp.bottomMargin = dp(ctx, 18);
        row.setLayoutParams(rp);
        int[] h = {24, 38, 52};
        for (int i = 0; i < 3; i++) {
            View bar = new View(ctx);
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(dp(ctx, 20), dp(ctx, h[i]));
            p.setMargins(dp(ctx, 5), 0, dp(ctx, 5), 0);
            bar.setLayoutParams(p);
            GradientDrawable g = new GradientDrawable();
            g.setCornerRadius(dp(ctx, 4));
            g.setColor(i < level ? ACCENT : DIM);
            bar.setBackground(g);
            row.addView(bar);
        }
        return row;
    }

    /** Иконка кейкапа; pas — зеркалим: у пассажира сиденье с другой стороны. */    private static ImageView icon(Context ctx, String name, int wDp, int hDp, boolean mirror) {
        ImageView iv = new ImageView(ctx);
        int id = ctx.getResources().getIdentifier(name, "drawable", ctx.getPackageName());
        if (id != 0) iv.setImageResource(id);
        iv.setLayoutParams(new LinearLayout.LayoutParams(dp(ctx, wDp), dp(ctx, hDp)));
        if (mirror) iv.setScaleX(-1f);
        return iv;
    }

    private static TextView caption(Context ctx, String text) {
        TextView tv = new TextView(ctx);
        tv.setText(text);
        tv.setTextColor(TEXT);
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 34);
        tv.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(ctx, 18);
        tv.setLayoutParams(p);
        return tv;
    }

    private static int dp(Context ctx, int v) {
        return Math.round(v * ctx.getResources().getDisplayMetrics().density);
    }

    private Plaque() { }
}
