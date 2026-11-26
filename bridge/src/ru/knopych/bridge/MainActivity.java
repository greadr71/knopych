package ru.knopych.bridge;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.PorterDuff;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.Locale;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Экран моста на ГУ Haval Dargo. Наверху — сама кнопочная панель, но не во всю ширину: её лицо
 * нарисовано по модели из v1/modeling/ (145×25 мм, два колодца по три кейкапа, вырез под вертушок
 * ГУ), светодиоды горят по состоянию машины. Подписей под кейкапами нет: назначение кнопки
 * видно по её нажатию, а место отдано сценариям крупным кеглем.
 * Под панелью — панель настроек: сценарии, по нажатию на кейкап — подстраница этой кнопки
 * с разделами «нажатие» и «удержание». Состояние машины — в отладке.
 * Пиксельный шрифт — только подпись продукта: микрозаголовки, числа, клавиши, стрелки.
 * Весь читаемый текст — IBM Plex Sans.
 * Отступы под системные панели GWM: prefs ui_pad_left / ui_pad_top (команда ui_pad <слева> <сверху>).
 * Связь и журнал — отладка, по умолчанию скрыты (prefs ui_diag).
 * Всё, что что-то делает, идёт через Bridge.submit — те же команды, что tools/kn.py.
 */
public class MainActivity extends Activity implements Bridge.StateListener {
    // Палитра: графит #0F1115, волосок #23262E, кейкап #1B1F26 с ободом #8F3F17 и чернилами #121418.
    private static final int BG = 0xFF0F1115,      // фон и дно колодца
            LINE = 0xFF23262E,                     // волосок
            KEY = 0xFF1B1F26,                      // боковина кейкапа, грань клавиши
            ON = 0xFFD66024,                       // светодиод, выбранный кейкап
            RIM = 0xFF8F3F17,                      // обод клавиши-действия
            INK = 0xFF121418,                      // текст на оранжевом
            TEXT = 0xFFF2EAE4,
            DIM = 0xFFBDB2A8,
            FAINT = 0xFF948A81,
            QUIET = 0xFF7E756D,                    // пояснение: тише третичного
            PLATE = 0xFF1A1E25,                    // лицо короба
            CAPTOP = 0xFF262B34,                   // верх кейкапа
            HOLE = 0xFF0A0C10;                     // погасший светодиод

    /** Названия кнопок панели, слева направо. Прописными: микрозаголовок карточки. */
    private static final String[] KEY_NAMES = {
            "ПОЛОЖЕНИЕ 1", "ПОЛОЖЕНИЕ 2", "ПОЛОЖЕНИЕ 3",
            "ПОДОГРЕВ ВОДИТЕЛЯ", "ЛОБОВОЕ СТЕКЛО", "ПОДОГРЕВ ПАССАЖИРА"};

    /** Страницы панели настроек: 0 — сценарии, 1..6 — кнопка панели, 7..9 — сценарии. */
    private static final int PAGE_SCEN = 0, PAGE_AUTO = 7, PAGE_THEME = 8, PAGE_BRIGHT = 9;

    /** Пиксельный шрифт из res/font — подпись продукта. */
    private Typeface pixel;
    private Typeface sys, sysMed;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private Bridge bridge;
    /** Волосок: 1 физический пиксель. */
    private int thin;
    /** Жёлоб: весь текст отступает на него, волоски идут во всю ширину. */
    private int GUT;

    private Panel panel;

    /** Строка состояния машины: живёт в отладке, а не на главном экране. */
    private TextView stateView;

    /** Открытая страница настроек: 0 — сценарии, 1..6 — кнопка панели, 7..9 — сценарии. */
    private int open;
    private final LinearLayout[] zones = new LinearLayout[10];
    private ScrollView settingsScroll;
    /** Затухание у нижней кромки: подсказывает, что ниже есть ещё. */
    private View settingsFade;
    /** Липкая шапка: микрозаголовок «СЦЕНАРИИ» или возврат «‹ Назад». */
    private TextView stickyHead;
    /** Стрелка возврата «‹»: глиф пиксельного шрифта. */
    private TextView backArrow;
    private LinearLayout stickyBar;
    /** Высота липкой шапки, dp: микрозаголовок 30 sp. */
    private static final int STICKY = 60;
    /** Высота кейкапа, dp: надпись 26 sp из IBM Plex стоит в нём по центру. */
    private static final int KEY_H = 76;
    /**
     * Кегль стрелок, dp. В px он округляется до кратного 8: клетка Press Start 2P — 1/8 em,
     * и только при таком размере ступени ложатся на целые пиксели. Чернила →/← 1 em в ширину и
     * 0,875 em в высоту, древко — три клетки. У строк стрелка стоит рядом с названием 34 sp,
     * у возврата — рядом с микрозаголовком 30 sp.
     */
    private static final int ARROW_ROW_DP = 28, ARROW_BACK_DP = 24;

    // автосценарии
    private Button autoKey, thrValue, delayValue, themeKey, wheelKey, windKey;
    private final Button[] seatKeys = new Button[4];
    private final Button[] themeKeys = new Button[ThemeCtl.IDS.length];
    private TextView autoState, autoBrief, themeState, themeBrief;
    // карточка «автояркость по ночи»
    private TextView brightState, brightBrief;
    private Button brightKey;
    /** Что сейчас в машине: режим из журнала и яркость командой, как в карточке кнопки 4. */
    private TextView brightNow;

    // карточки кнопок 4 и 6: уровень подогрева; 5: обогрев; 4: яркость
    private final Button[] cardSeatDriver = new Button[4];
    private final Button[] cardSeatPass = new Button[4];
    private Button cardWind, brightValue;
    /** Яркость ГУ: не приходит в снимке состояния, читаем командой. -1 — неизвестна. */
    private int bright = -1;

    // отладка
    private TextView diagBtn, netView, logView;
    private Button brightBtn;
    private ScrollView diagScroll;

    // ответ на долгую команду
    private LinearLayout resultWrap;
    private TextView resultView;

    private boolean visible, diag, narrow;

    private final Runnable periodic = new Runnable() {
        @Override public void run() {
            if (diag) refreshSlow(); else render();
            ui.postDelayed(this, 3000);
        }
    };

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        BridgeService.start(this);
        bridge = Bridge.get(this);
        pixel = font("pressstart2p", Typeface.MONOSPACE);
        sys = font("ibmplexsans", Typeface.SANS_SERIF);
        sysMed = font("ibmplexsans_medium", Typeface.SANS_SERIF);
        setContentView(build());
    }

    /**
     * Шрифт из res/font по имени: R.java сборка не генерирует (aapt2 без --java),
     * поэтому id берём через getIdentifier. minSdk 28 — getFont() доступен.
     */
    private Typeface font(String name, Typeface fallback) {
        try {
            int id = getResources().getIdentifier(name, "font", getPackageName());
            return getResources().getFont(id);
        } catch (Throwable t) {
            Log.w("knopych", "шрифт " + name + " не прочитался, остаётся системный", t);
            return fallback;
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        visible = true;
        bridge.addListener(this);
        bridge.refreshSoon();
        ui.post(periodic);
    }

    @Override
    protected void onPause() {
        visible = false;
        bridge.removeListener(this);
        ui.removeCallbacks(periodic);
        super.onPause();
    }

    @Override
    public void onState(Bridge.State s) {
        ui.post(this::render);
    }

    // ---------- разметка ----------

    private View build() {
        LinearLayout root = column();
        root.setBackgroundColor(BG);
        // Слева у ГУ GWM системная панель (иконки машины, музыки, дома) поверх приложений,
        // сверху — строка климата. Система про них не сообщает, поэтому отступ задан вручную
        // (команда ui_pad, по умолчанию 5,4% ширины слева и 3% высоты сверху).
        android.util.DisplayMetrics m = getResources().getDisplayMetrics();
        thin = Math.max(1, Math.round(m.density * 0.5f));
        GUT = dp(14);
        int padL = bridge.prefs().getInt("ui_pad_left", m.widthPixels * 54 / 1000);
        int padT = bridge.prefs().getInt("ui_pad_top", m.heightPixels * 3 / 100);
        narrow = m.widthPixels - padL - dp(20) < dp(980);
        root.setPadding(padL, padT, dp(20), dp(14));

        root.addView(header());

        // Панель — справка, а не герой экрана: во всю ширину она съедала треть высоты ГУ,
        // а подписи рядом с ней всё равно не читались. Ширина — три десятых содержимого, по
        // центру; высота следует из пропорции лица короба 145:25, а не задаётся отдельно.
        panel = new Panel();
        int contentW = m.widthPixels - padL - dp(20);
        int panelW = Math.min(contentW, Math.max(dp(260), Math.round(contentW * 0.3f)));
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(
                panelW, Math.round(panelW * Panel.HMM / Panel.WMM));
        pp.gravity = Gravity.CENTER_HORIZONTAL;
        root.addView(panel, pp);

        // Панель настроек под панелью: сценарии, сценарий или карточка нажатого кейкапа.
        FrameLayout area = new FrameLayout(this);
        settingsScroll = scroll(settingsColumn());
        settingsScroll.setFillViewport(true);
        settingsScroll.setOnScrollChangeListener((v, x, y, ox, oy) -> updateFade());
        area.addView(settingsScroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        diagScroll = scroll(columnDiag());
        diagScroll.setVisibility(View.GONE);
        area.addView(diagScroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        LinearLayout stick = column();
        stickyBar = stick;
        stick.setBackgroundColor(BG);
        // Шапка несёт возврат: стрелка влево и слово «Назад» — одна цель на всю ширину.
        LinearLayout headRow = new LinearLayout(this);
        headRow.setOrientation(LinearLayout.HORIZONTAL);
        headRow.setGravity(Gravity.CENTER_VERTICAL);
        headRow.setPadding(GUT, 0, 0, 0);
        headRow.setBackground(sel(0x00000000, KEY));
        headRow.setOnClickListener(v -> page(PAGE_SCEN));
        backArrow = arrow("←", arrowPx(ARROW_BACK_DP), FAINT);
        // рядом строчные буквы, их масса ниже середины строки: стрелку на 1 dp вниз — по оптике
        backArrow.setTranslationY(dp(1));
        headRow.addView(backArrow);
        // «СЦЕНАРИИ» и «Назад» — один и тот же микрозаголовок: меняется только слово
        stickyHead = micro("");
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        hp.leftMargin = dp(8);
        headRow.addView(stickyHead, hp);
        stick.addView(headRow, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(STICKY)));
        stick.addView(hline());
        area.addView(stick, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        settingsFade = new View(this);
        settingsFade.setBackground(new GradientDrawable(GradientDrawable.Orientation.BOTTOM_TOP,
                new int[]{BG, BG & 0x00FFFFFF}));
        settingsFade.setVisibility(View.GONE);
        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(28));
        fp.gravity = Gravity.BOTTOM;
        area.addView(settingsFade, fp);
        root.addView(area, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        resultView = text("", 22, DIM, false);
        resultView.setMaxLines(3);
        resultView.setEllipsize(TextUtils.TruncateAt.END);
        resultView.setPadding(GUT, dp(10), 0, 0);
        resultWrap = column();
        resultWrap.addView(hline());
        resultWrap.addView(resultView);
        resultWrap.setVisibility(View.GONE);
        root.addView(resultWrap, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        setDiag(bridge.prefs().getBoolean("ui_diag", false), false);
        render();
        page(PAGE_SCEN);
        return root;
    }

    /**
     * Шапка: имя продукта, посередине подсказка про нажатие, справа тихий переключатель отладки.
     * Подсказка стоит на одной строке с ними: отдельная строка под шапкой съедала у сценариев
     * 42 dp, а длинный кегль до «ОТЛАДКИ» всё равно не дотягивался — режется многоточием.
     */
    private View header() {
        LinearLayout h = new LinearLayout(this);
        h.setOrientation(LinearLayout.HORIZONTAL);
        h.setGravity(Gravity.CENTER_VERTICAL);
        h.setPadding(GUT, 0, 0, dp(8));

        TextView name = pix("КНОПЫЧ", 22, TEXT);
        name.setLetterSpacing(0.08f);
        h.addView(name);

        TextView ver = pix(bridge.version(), 14, FAINT);
        ver.setLetterSpacing(0.04f);
        LinearLayout.LayoutParams vp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        vp.leftMargin = dp(12);
        h.addView(ver, vp);

        // Подсказка: без неё не догадаться, что панель нажимается. Читаемый шрифт —
        // пиксельный 12 sp с водительского места не читался. В одну строку: перенос рос бы
        // шапкой и отбирал вертикаль у сценариев. 22 sp, а не 26: на ГУ между «КНОПЫЧ» и
        // «ОТЛАДКА» остаётся 277 dp — 26 sp отрезали уже на «Коснитесь кнопки, чт…», 22 sp
        // дотягивают до «Коснитесь кнопки, чтобы…». Целиком фраза не влезает ни при каком
        // читаемом кегле (43 знака — это 580 dp в 26 sp), поэтому многоточие штатное.
        TextView hint = text("Коснитесь кнопки, чтобы открыть её настройки", 22, QUIET, false);
        hint.setSingleLine(true);
        hint.setEllipsize(TextUtils.TruncateAt.END);
        hint.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams hintP = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        hintP.leftMargin = dp(16);
        hintP.rightMargin = dp(8);
        h.addView(hint, hintP);

        diagBtn = new TextView(this);
        diagBtn.setTypeface(pixel);
        diagBtn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        diagBtn.setIncludeFontPadding(false);
        diagBtn.setLetterSpacing(0.1f);
        diagBtn.setGravity(Gravity.CENTER);
        diagBtn.setPadding(dp(20), 0, dp(20), 0);
        diagBtn.setOnClickListener(v -> setDiag(!diag, true));
        h.addView(diagBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(48)));
        return h;
    }

    // --- панель: лицо короба по модели из v1/modeling/

    /**
     * Лицо панели видом спереди: короб 145×25 мм со скруглением 6 мм, рамка 3 мм, два колодца
     * по три кейкапа (шаг 18 мм, кейкап 17 мм, верх 14 мм), полукруглый вырез под вертушок ГУ
     * Ø30 мм по центру нижней кромки. Всё в миллиметрах модели и масштабируется по ширине вида.
     * Цвет несёт только состояние: зажжённый светодиод и обод выбранного кейкапа.
     */
    private final class Panel extends View {
        static final float WMM = 145f, HMM = 25f;
        /** Центры окон свитчей по X, мм. */
        private final float[] cx = {11f, 29f, 47f, 98f, 116f, 134f};
        /**
         * Длинная сторона иконки, мм (из build_keycaps.py). У слотов 10 мм — это длинная сторона
         * сиденья: цифра стоит на нём и выходит за его верх на доли миллиметра, поэтому bbox
         * сиденья и кейкапов 1–3 один и тот же по ширине.
         */
        private final float[] iconW = {10f, 10f, 10f, 12f, 12f, 12f};
        /** Пропорция контура иконки: у слотов по общим границам сиденья и цифры. */
        private final float[] iconAspect = {290.3f / 230.61f, 291.74f / 232.47f, 290.45f / 233.38f,
                525f / 447f, 380f / 242f, 525f / 447f};
        /** Сдвиг центра иконки на юг от центра кейкапа, мм: иконка держится дальше от светодиода. */
        private final float[] iconDown = {2.3f, 2.3f, 2.3f, 1.3f, 2.3f, 1.3f};
        private final Drawable[] icons = new Drawable[6];
        /** 1 — светодиод горит, 0 — погас (неизвестное состояние тоже не горит). */
        final int[] led = new int[6];
        int selected = -1;

        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF r = new RectF();
        private final Rect bounds = new Rect();
        private float s;
        private int pressed = -1;

        Panel() {
            super(MainActivity.this);
            icons[0] = icon("kc_seat1");
            icons[1] = icon("kc_seat2");
            icons[2] = icon("kc_seat3");
            icons[3] = icon("kc_heater");
            icons[4] = icon("kc_wind");
            icons[5] = icon("kc_heater");
        }

        private Drawable icon(String name) {
            try {
                int id = getResources().getIdentifier(name, "drawable", getPackageName());
                return getResources().getDrawable(id, null);
            } catch (Throwable t) {
                Log.w("knopych", "иконка " + name + " не прочиталась", t);
                return null;
            }
        }

        @Override protected void onDraw(Canvas c) {
            s = getWidth() / WMM;
            float w = WMM * s, h = HMM * s;
            float oy = (getHeight() - h) / 2f;

            // лицо короба
            p.setStyle(Paint.Style.FILL);
            p.setColor(PLATE);
            r.set(0, oy, w, oy + h);
            c.drawRoundRect(r, 6 * s, 6 * s, p);
            // кромка лица: без неё силуэт короба теряется на фоне
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(thin);
            p.setColor(LINE);
            c.drawRoundRect(r, 6 * s, 6 * s, p);
            p.setStyle(Paint.Style.FILL);

            // два колодца: кейкап 17 мм + зазор 0,5 мм
            p.setColor(BG);
            for (int i = 0; i < 6; i += 3) {
                r.set((cx[i] - 9f) * s, oy + 3.5f * s, (cx[i + 2] + 9f) * s, oy + 21.5f * s);
                c.drawRoundRect(r, 2 * s, 2 * s, p);
            }

            // вырез под вертушок ГУ: полуокружность Ø30 мм, центр на нижней кромке лица.
            // Только вырез — никакой головки, кромки и риски: ручка живёт в железе, не на экране.
            float kx = 72.5f * s, ky = oy + h, kr = 15f * s;
            p.setColor(BG);
            r.set(kx - kr, ky - kr, kx + kr, ky + kr);
            c.drawArc(r, 180f, 180f, true, p);

            // шесть кейкапов: боковина 17×17, верх 14×14, светодиод на 5 мм севернее центра
            for (int i = 0; i < 6; i++) {
                float x = cx[i] * s, y = oy + 12.5f * s;
                p.setColor(KEY);
                r.set(x - 8.5f * s, y - 8.5f * s, x + 8.5f * s, y + 8.5f * s);
                c.drawRoundRect(r, 2 * s, 2 * s, p);

                p.setStyle(Paint.Style.STROKE);
                p.setStrokeWidth(i == selected ? Math.max(2, thin * 2) : thin);
                p.setColor(i == selected ? ON : LINE);
                c.drawRoundRect(r, 2 * s, 2 * s, p);
                p.setStyle(Paint.Style.FILL);

                // верх кейкапа поднят на 1,2 мм: клавиша видна чуть сверху
                float ty = y - 1.2f * s;
                p.setColor(CAPTOP);
                r.set(x - 7 * s, ty - 7 * s, x + 7 * s, ty + 7 * s);
                c.drawRoundRect(r, 1.5f * s, 1.5f * s, p);

                Drawable d = icons[i];
                if (d != null) {
                    float iw = iconW[i] * s, ih = iw / iconAspect[i];
                    float iy = ty + iconDown[i] * s;
                    bounds.set(Math.round(x - iw / 2), Math.round(iy - ih / 2),
                            Math.round(x + iw / 2), Math.round(iy + ih / 2));
                    d.setBounds(bounds);
                    // гравировка не подсвечивается: состояние несёт только светодиод
                    d.setColorFilter(led[i] == 1 ? TEXT : DIM, PorterDuff.Mode.SRC_IN);
                    // подогрев водителя — та же иконка, спинка в другую сторону
                    boolean mirror = i == 3;
                    if (mirror) {
                        c.save();
                        c.scale(-1f, 1f, x, 0);
                    }
                    d.draw(c);
                    if (mirror) c.restore();
                }

                // цифра слота — часть контура сиденья (kc_seat1..3), красится вместе с ним

                p.setColor(led[i] == 1 ? ON : HOLE);
                float ly = y - 5 * s;
                r.set(x - 2 * s, ly - 0.8f * s, x + 2 * s, ly + 0.8f * s);
                c.drawRoundRect(r, 0.8f * s, 0.8f * s, p);
            }
        }

        /** Кейкап под точкой (1..6) или 0. */
        private int under(float px, float py) {
            float oy = (getHeight() - HMM * s) / 2f;
            py -= oy;
            for (int i = 0; i < 6; i++) {
                if (Math.abs(px - cx[i] * s) <= 8.5f * s && Math.abs(py - 12.5f * s) <= 8.5f * s)
                    return i + 1;
            }
            return 0;
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            float s2 = getWidth() / WMM;
            if (s2 <= 0) return false;
            s = s2;
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    pressed = under(e.getX(), e.getY());
                    return pressed > 0;
                case MotionEvent.ACTION_MOVE:
                    return pressed > 0 && under(e.getX(), e.getY()) == pressed;
                case MotionEvent.ACTION_UP:
                    if (pressed > 0 && under(e.getX(), e.getY()) == pressed) {
                        performClick();
                        selectCard(pressed);
                    }
                    pressed = -1;
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    pressed = -1;
                    return false;
                default:
                    return pressed > 0;
            }
        }
    }

    // --- панель настроек: сценарии или карточка кнопки

    private View settingsColumn() {
        LinearLayout c = column();
        // сверху место под липкую шапку: содержимое уезжает под неё, шапка остаётся
        c.setPadding(0, dp(STICKY) + thin, 0, 0);
        zones[PAGE_SCEN] = (LinearLayout) scenarios();
        c.addView(zones[PAGE_SCEN], new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        for (int n = 1; n <= 6; n++) {
            zones[n] = (LinearLayout) card(n);
            c.addView(zones[n]);
        }
        zones[PAGE_AUTO] = (LinearLayout) autoPage();
        c.addView(zones[PAGE_AUTO]);
        zones[PAGE_THEME] = (LinearLayout) themePage();
        c.addView(zones[PAGE_THEME]);
        zones[PAGE_BRIGHT] = (LinearLayout) brightPage();
        c.addView(zones[PAGE_BRIGHT]);
        return c;
    }

    private View scenarios() {
        LinearLayout l = column();
        // Свободная высота колонки уходит в воздух под строками: строки держат свою высоту
        // и стоят сразу под шапкой секции — дыра между шапкой и первой строкой читается сбоем.
        l.setPadding(GUT, 0, 0, 0);
        autoState = pix("—", 24, FAINT);
        autoBrief = text("", 28, FAINT, false);
        l.addView(scenarioRow(PAGE_AUTO, "Подогрев в холод", autoState, autoBrief));
        l.addView(hline());
        themeState = pix("—", 24, FAINT);
        themeBrief = text("", 28, FAINT, false);
        l.addView(scenarioRow(PAGE_THEME, "Тема при включении", themeState, themeBrief));
        l.addView(hline());
        brightState = pix("—", 24, FAINT);
        brightBrief = text("", 28, FAINT, false);
        l.addView(scenarioRow(PAGE_BRIGHT, "Автояркость по ночи", brightState, brightBrief));
        l.addView(gap());
        return l;
    }

    /** Промежуток, который забирает свободную высоту колонки. */
    private View gap() {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        return v;
    }

    /**
     * Строка сценария — переход в подраздел: название, слово состояния и стрелка строкой,
     * выжимка настроек под ней. В одну строку крупный кегль не встаёт: название, выжимка
     * и состояние начинали резать друг друга многоточием.
     */
    private View scenarioRow(int page, String title, TextView state, TextView brief) {
        LinearLayout h = column();
        h.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        h.setBackground(sel(0x00000000, KEY));
        // Отбивка строки: по ней бьёт палец на ходу. Строк стало три, и 18 dp уже не вставали
        // на 800×562 — 10 dp возвращают высоту в кадр, не уменьшая цель пальца (строка > 100 dp).
        h.setPadding(GUT, dp(10), GUT, dp(10));
        h.setOnClickListener(v -> page(page));

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.addView(text(title, 36, TEXT, true));

        top.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));

        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sp.leftMargin = dp(14);
        top.addView(state, sp);

        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cp.leftMargin = dp(12);
        // у → чернила во всю ширину глифа: поля нет, стрелка встаёт ровно по кромке строки
        top.addView(arrow("→", arrowPx(ARROW_ROW_DP), FAINT), cp);
        h.addView(top);

        brief.setMaxLines(2);
        brief.setEllipsize(TextUtils.TruncateAt.END);
        brief.setPadding(0, dp(6), 0, 0);
        h.addView(brief);
        return h;
    }

    /** Карточка кнопки панели: раздел «нажатие» и раздел «удержание» — прямое управление. */
    private View card(int n) {
        LinearLayout c = column();
        c.setPadding(GUT, 0, 0, dp(18));

        // Заголовок карточки — читаемым шрифтом: «КНОПКА 6 · ПОДОГРЕВ ПАССАЖИРА» пиксельным
        // в 30 sp вдвое шире строки, а мелким он не читался.
        TextView head = text("КНОПКА " + n + " · " + KEY_NAMES[n - 1], 26, DIM, true);
        head.setLetterSpacing(0.06f);
        head.setPadding(0, dp(16), 0, dp(2));
        c.addView(head);

        if (n <= 3) {
            final int slot = n;
            c.addView(section("НАЖАТИЕ", "ставит положение, сохранённое в слоте " + slot));
            c.addView(action("Поставить положение " + slot,
                    v -> cmd("seat_memory", String.valueOf(slot))),
                    new LinearLayout.LayoutParams(dp(380), dp(KEY_H)));
            c.addView(section("УДЕРЖАНИЕ 1,5 С", "сохраняет текущее положение в слот " + slot));
            c.addView(key("Сохранить", v -> cmd("seat_save", String.valueOf(slot))),
                    new LinearLayout.LayoutParams(dp(380), dp(KEY_H)));
        } else if (n == 4 || n == 6) {
            final boolean driver = n == 4;
            final Button[] keys = driver ? cardSeatDriver : cardSeatPass;
            c.addView(section("НАЖАТИЕ", driver
                    ? "уровень подогрева, «выкл» — выключить"
                    : "уровень подогрева пассажира, «выкл» — выключить"));
            c.addView(fieldRow(levelRow(keys, driver ? "seat_driver" : "seat_passenger"),
                    spacer(0.55f)));

            if (driver) {
                c.addView(section("УДЕРЖАНИЕ 1,5 С",
                        "переключает яркость экрана с максимума на минимум и обратно"));
                brightValue = readout();
                c.addView(fieldRow(field("ЯРКОСТЬ СЕЙЧАС", stepper(brightValue,
                        v -> setBright(bright - 1), v -> setBright(bright + 1)), 1f), spacer(0.55f)));
            }
        } else {
            c.addView(section("НАЖАТИЕ", "обогрев лобового стекла"));
            cardWind = key("Включить обогрев", v -> cmd("windshield",
                    bridge.state().windshield == 1 ? "off" : "on"));
            c.addView(cardWind, new LinearLayout.LayoutParams(dp(380), dp(KEY_H)));
            c.addView(hint("При незаведённом двигателе ждёт зажигания"));
        }
        return c;
    }

    /** Заголовок раздела карточки: что делает нажатие и что — удержание. */
    private View section(String title, String note) {
        LinearLayout c = column();
        TextView t = micro(title);
        // Раздел должен липнуть к своему абзацу, а не к предыдущему блоку.
        t.setPadding(0, dp(28), 0, dp(6));
        c.addView(t);
        TextView d = text(note, 26, QUIET, false);
        d.setPadding(0, 0, 0, dp(10));
        c.addView(d);
        return c;
    }

    /** Ряд уровней подогрева: выкл и 1..3 — один и тот же кейкап на месте. */
    private LinearLayout levelRow(Button[] keys, final String channel) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        String[] labels = {"выкл", "1", "2", "3"};
        for (int i = 0; i < 4; i++) {
            final int lvl = i;
            keys[i] = key(labels[i], v -> cmd(channel, String.valueOf(lvl)));
            LinearLayout.LayoutParams kp = new LinearLayout.LayoutParams(0, dp(KEY_H), 1f);
            if (i > 0) kp.leftMargin = dp(6);
            row.addView(keys[i], kp);
        }
        row.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }

    /** Показать страницу: 0 — сценарии, 1..6 — кнопка панели, 7..9 — сценарии. */
    private void page(int n) {
        open = n;
        for (int i = 0; i < zones.length; i++)
            zones[i].setVisibility(open == i ? View.VISIBLE : View.GONE);
        if (panel != null) {
            panel.selected = n >= 1 && n <= 6 ? n - 1 : -1;
            panel.invalidate();
        }
        updateHead();
        if (settingsScroll != null) settingsScroll.scrollTo(0, 0);
        updateFade(); // scrollTo колбэка не даёт: новая страница может быть ниже старой
        if (settingsScroll != null) settingsScroll.post(this::updateFade); // и ещё раз после раскладки новой страницы
        if (n == 4 && bright < 0) readBright();
        // яркость могли поменять руками: открытие подстраницы перечитывает её, а не показывает старое
        if (n == PAGE_BRIGHT) readBright();
    }

    /** Тап по кейкапу: его карточка; повторный тап по тому же кейкапу — назад к сценариям. */
    private void selectCard(int n) {
        page(open == n ? PAGE_SCEN : n);
    }

    /** Яркость ГУ не приходит в снимке состояния: читаем её командой. */
    private void readBright() {
        new Thread(() -> {
            try {
                String r = bridge.submit("brightness", "").get(20, TimeUnit.SECONDS);
                Matcher m = Pattern.compile("brightness=(\\d+)").matcher(r);
                if (m.find()) {
                    bright = Integer.parseInt(m.group(1));
                    ui.post(this::render);
                }
            } catch (Throwable t) {
                Log.w("knopych", "яркость не прочиталась", t);
            }
        }).start();
    }

    /**
     * Последний режим автояркости из журнала («день»/«ночь»), null — ещё не переключался.
     * Режим день/ночь машины в снимке состояния не приходит, а журнал автояркости уже его пишет:
     * строка вида «яркость: ночь → 1 (автосвет: ночь)».
     */
    private String brightMode() {
        Matcher m = Pattern.compile("яркость: (день|ночь) → \\d+").matcher(bridge.dumpLog());
        String mode = null;
        while (m.find()) mode = m.group(1);
        return mode;
    }

    /** Час окна как на часах: 8 → «08:00». */
    private static String clock(int h) {
        return String.format(Locale.US, "%02d:00", h);
    }

    private void setBright(int v) {
        // Пока яркость неизвестна (эмулятор без car-API, машина не ответила) — сначала читаем:
        // клавиша не должна молча ничего не делать.
        if (bright < 0) { readBright(); return; }
        if (v < Bridge.BRIGHT_MIN || v > Bridge.BRIGHT_MAX) return;
        bright = v;
        cmd("brightness", String.valueOf(v));
    }

    /** Подраздел «подогрев в холод»: та же шапка с возвратом, ниже — поля сценария. */
    private View autoPage() {
        LinearLayout c = column();
        c.setPadding(GUT, 0, GUT, dp(18));

        TextView head = micro("ПОДОГРЕВ В ХОЛОД");
        head.setTextColor(DIM);
        head.setPadding(0, dp(16), 0, dp(2));
        c.addView(head);

        autoKey = key("Включить", v -> cmd("auto", bridge.autoEnabled() ? "off" : "on"));
        thrValue = readout();
        delayValue = readout();
        LinearLayout fOn = field("СЦЕНАРИЙ", autoKey, 1.05f);
        LinearLayout fThr = field("ПОРОГ", stepper(thrValue,
                v -> cmd("auto_threshold", fmt(bridge.autoThreshold() - 1)),
                v -> cmd("auto_threshold", fmt(bridge.autoThreshold() + 1))), 1.35f);
        LinearLayout fDelay = field("ЗАДЕРЖКА", stepper(delayValue,
                v -> cmd("auto_delay", String.valueOf(Math.max(0, bridge.autoDelayMs() / 1000 - 5))),
                v -> cmd("auto_delay", String.valueOf(bridge.autoDelayMs() / 1000 + 5))), 1.35f);
        // Три поля в строку влезают только на широком экране; на узком «Включить» режется.
        if (narrow) {
            c.addView(fieldRow(fOn));
            c.addView(fieldRow(fThr, fDelay));
        } else {
            c.addView(fieldRow(fOn, fThr, fDelay));
        }

        LinearLayout seat = new LinearLayout(this);
        seat.setOrientation(LinearLayout.HORIZONTAL);
        for (int i = 0; i < 4; i++) {
            final int lvl = i;
            seatKeys[i] = key(String.valueOf(i), v -> cmd("auto_seat", String.valueOf(lvl)));
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, dp(KEY_H), 1f);
            if (i > 0) p.leftMargin = dp(6);
            seat.addView(seatKeys[i], p);
        }
        wheelKey = key("нет", v -> cmd("auto_wheel", bridge.autoWheel() ? "off" : "on"));
        windKey = key("нет", v -> cmd("auto_windshield", bridge.autoWindshield() ? "off" : "on"));
        c.addView(fieldRow(
                field("СИДЕНЬЕ", seat, 2.05f),
                field("РУЛЬ", wheelKey, 0.8f),
                field("ЛОБОВОЕ", windKey, 0.8f)));

        c.addView(hint("Если зажигание включено и за бортом ниже порога"));
        Button test = action("Проверить сейчас", v -> cmd("auto_test", ""));
        c.addView(test, new LinearLayout.LayoutParams(dp(380), dp(KEY_H)));
        return c;
    }

    /** Подраздел «тема при включении». */
    private View themePage() {
        LinearLayout c = column();
        c.setPadding(GUT, 0, GUT, dp(18));

        TextView head = micro("ТЕМА ПРИ ВКЛЮЧЕНИИ");
        head.setTextColor(DIM);
        head.setPadding(0, dp(16), 0, dp(2));
        c.addView(head);

        themeKey = key("Включить", v -> cmd("auto_theme", bridge.autoTheme() ? "off" : "on"));
        LinearLayout themes = new LinearLayout(this);
        themes.setOrientation(LinearLayout.HORIZONTAL);
        for (int i = 0; i < ThemeCtl.IDS.length; i++) {
            final int id = ThemeCtl.IDS[i];
            themeKeys[i] = key(String.valueOf(id), v -> cmd("auto_theme_id", String.valueOf(id)));
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, dp(KEY_H), 1f);
            if (i > 0) p.leftMargin = dp(6);
            themes.addView(themeKeys[i], p);
        }
        c.addView(fieldRow(
                field("СЦЕНАРИЙ", themeKey, 1.05f),
                field("ТЕМА", themes, 2.95f)));

        c.addView(hint("Один раз за поездку при включении ГУ — тема на экране и приборке"));
        Button now = action("Поставить сейчас", v -> cmd("theme", String.valueOf(bridge.autoThemeId())));
        c.addView(now, new LinearLayout.LayoutParams(dp(380), dp(KEY_H)));
        return c;
    }

    /** Подраздел «автояркость по ночи»: тумблер и что сейчас стоит в машине. */
    private View brightPage() {
        LinearLayout c = column();
        c.setPadding(GUT, 0, GUT, dp(18));

        TextView head = micro("АВТОЯРКОСТЬ ПО НОЧИ");
        head.setTextColor(DIM);
        head.setPadding(0, dp(16), 0, dp(2));
        c.addView(head);

        brightKey = key("Включить", v -> cmd("auto_bright", bridge.autoBright() ? "off" : "on"));
        c.addView(fieldRow(field("СЦЕНАРИЙ", brightKey, 1f)));

        // Режим день/ночь машины в снимке состояния не приходит: берём последнюю запись
        // автояркости из журнала, яркость — командой brightness, как в карточке кнопки 4.
        brightNow = text("", 26, QUIET, false);
        brightNow.setPadding(0, dp(14), 0, 0);
        c.addView(brightNow);

        c.addView(hint("При смене автосвета ставит день " + Bridge.AUTO_BRIGHT_DAY + ", ночь "
                + Bridge.AUTO_BRIGHT_NIGHT + ". Ночь считает только с " + clock(Bridge.DAY_TO_HOUR)
                + " до " + clock(Bridge.DAY_FROM_HOUR) + ": пасмурный день экран не гасит"));
        return c;
    }

    /** Затухание внизу только тогда, когда ниже действительно есть продолжение. */
    private void updateFade() {
        if (settingsFade == null) return;
        settingsFade.setVisibility(!diag && settingsScroll.canScrollVertically(1)
                ? View.VISIBLE : View.GONE);
    }

    // --- отладочная зона: связь и журнал (скрыта по умолчанию)

    private View columnDiag() {
        LinearLayout l = column();
        l.setPadding(GUT, 0, 0, 0);
        // Состояние машины ушло с главного экрана: там оно стояло тихой строкой под панелью
        // и с водительского места всё равно не читалось. Здесь ему место — отладку читают сидя.
        l.addView(microhead("СОСТОЯНИЕ", dp(16)));
        stateView = text("…", 18, TEXT, false);
        stateView.setPadding(0, 0, 0, dp(10));
        l.addView(stateView);
        // Диагностика: видно, меняется ли яркость при записи и от штатного ползунка.
        brightBtn = key("ЯРКОСТЬ 2 С: ВЫКЛ", v -> {
            bridge.brightnessMonitor(!bridge.brightnessMonitorOn());
            render();
        });
        l.addView(brightBtn, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(KEY_H)));
        l.addView(microhead("СВЯЗЬ", dp(16)));
        netView = text("…", 18, TEXT, false);
        netView.setLineSpacing(dp(3), 1f);
        l.addView(netView);
        l.addView(microhead("ЖУРНАЛ", dp(24)));
        logView = new TextView(this);
        logView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        logView.setTypeface(Typeface.MONOSPACE);
        logView.setTextColor(DIM);
        logView.setLineSpacing(dp(3), 1f);
        l.addView(logView);
        return l;
    }

    /** Показать/скрыть связь и журнал; состояние запоминается в prefs "ui_diag". */
    private void setDiag(boolean on, boolean save) {
        diag = on;
        settingsScroll.setVisibility(on ? View.GONE : View.VISIBLE);
        stickyBar.setVisibility(on ? View.GONE : View.VISIBLE);
        diagScroll.setVisibility(on ? View.VISIBLE : View.GONE);
        diagBtn.setText(on ? "СКРЫТЬ" : "ОТЛАДКА");
        diagBtn.setTextColor(on ? ON : FAINT);
        GradientDrawable d = new GradientDrawable();
        d.setColor(on ? KEY : 0x00000000);
        d.setCornerRadius(dp(3));
        if (on) d.setStroke(thin, RIM);
        diagBtn.setBackground(d);
        if (save) bridge.prefs().edit().putBoolean("ui_diag", on).apply();
        if (on) refreshSlow();
    }

    // ---------- обновление ----------

    private void render() {
        Bridge.State s = bridge.state();

        if (stateView != null) stateView.setText(stateLine(s));
        if (brightBtn != null) {
            boolean mon = bridge.brightnessMonitorOn();
            brightBtn.setText(mon ? "ЯРКОСТЬ 2 С: ВКЛ" : "ЯРКОСТЬ 2 С: ВЫКЛ");
            face(brightBtn, mon);
        }
        lights(s);

        boolean auto = bridge.autoEnabled();
        autoKey.setText(auto ? "Включён" : "Включить");
        face(autoKey, auto);
        autoState.setText(auto ? "ВКЛ" : "ВЫКЛ");
        autoState.setTextColor(auto ? ON : FAINT);
        thrValue.setText(show(bridge.autoThreshold()) + " °C");
        for (int i = 0; i < 4; i++) face(seatKeys[i], bridge.autoSeatLevel() == i);
        wheelKey.setText(bridge.autoWheel() ? "да" : "нет");
        face(wheelKey, bridge.autoWheel());
        windKey.setText(bridge.autoWindshield() ? "да" : "нет");
        face(windKey, bridge.autoWindshield());
        delayValue.setText(bridge.autoDelayMs() / 1000 + " с");
        autoBrief.setText("ниже " + show(bridge.autoThreshold()) + " °C · сиденье "
                + level(bridge.autoSeatLevel())
                + (bridge.autoWheel() ? " · руль" : "") + (bridge.autoWindshield() ? " · лобовое" : "")
                + " · задержка " + bridge.autoDelayMs() / 1000 + " с");

        boolean th = bridge.autoTheme();
        themeKey.setText(th ? "Включён" : "Включить");
        face(themeKey, th);
        themeState.setText(th ? "ВКЛ" : "ВЫКЛ");
        themeState.setTextColor(th ? ON : FAINT);
        for (int i = 0; i < themeKeys.length; i++)
            face(themeKeys[i], bridge.autoThemeId() == ThemeCtl.IDS[i]);
        themeBrief.setText("тема " + bridge.autoThemeId() + " · один раз за поездку, при включении ГУ");

        boolean ab = bridge.autoBright();
        brightKey.setText(ab ? "Включён" : "Включить");
        face(brightKey, ab);
        brightState.setText(ab ? "ВКЛ" : "ВЫКЛ");
        brightState.setTextColor(ab ? ON : FAINT);
        // Окно — числами из Bridge: ночь начинается с DAY_TO_HOUR и кончается в DAY_FROM_HOUR.
        brightBrief.setText("по автосвету: день " + Bridge.AUTO_BRIGHT_DAY
                + " · ночь " + Bridge.AUTO_BRIGHT_NIGHT
                + " · ночь с " + clock(Bridge.DAY_TO_HOUR));
        if (brightNow != null) {
            String mode = brightMode();
            brightNow.setText((mode == null ? "режим ещё не переключался" : "сейчас " + mode)
                    + " · яркость " + (bright < 0 ? "—" : bright + " / " + Bridge.BRIGHT_MAX));
        }

        // карточки: уровень подогрева и обогрев показывают состояние машины
        for (int i = 0; i < 4; i++) {
            face(cardSeatDriver[i], s.seatDriver == i);
            face(cardSeatPass[i], s.seatPassenger == i);
        }
        if (cardWind != null) {
            cardWind.setText(s.windshield == 1 ? "Выключить обогрев" : "Включить обогрев");
            face(cardWind, s.windshield == 1);
        }
        if (brightValue != null) {
            // всегда «N / 10»: видно, что это показание, а не третья клавиша рядом с «−»;
            // неизвестное — тем же форматом с тире в числителе.
            brightValue.setText((bright < 0 ? "—" : String.valueOf(bright))
                    + " / " + Bridge.BRIGHT_MAX);
            brightValue.setTextColor(bright < 0 ? FAINT : TEXT);
        }
    }

    /** Светодиоды панели: слоты памяти, подогревы, лобовое. Неизвестное не горит. */
    private void lights(Bridge.State s) {
        if (panel == null) return;
        for (int i = 0; i < 3; i++)
            panel.led[i] = i < s.seatMemory.length && s.seatMemory[i] == 2 ? 1 : 0; // 2 = слот активен, 1 = только сохранён
        panel.led[3] = s.seatDriver > 0 ? 1 : 0;
        panel.led[4] = s.windshield == 1 ? 1 : 0;
        panel.led[5] = s.seatPassenger > 0 ? 1 : 0;
        panel.invalidate();
    }

    /** Состояние машины одной тихой строкой: только то, что известно, иначе одна фраза. */
    private String stateLine(Bridge.State s) {
        StringBuilder b = new StringBuilder();
        if (s.power >= 0) part(b, power(s.power));
        if (!Float.isNaN(s.outsideTemp)) part(b, show(s.outsideTemp) + " °C");
        if (s.seatDriver >= 0) part(b, "водитель " + level(s.seatDriver));
        if (s.seatPassenger >= 0) part(b, "пассажир " + level(s.seatPassenger));
        if (s.wheel >= 0) part(b, "руль " + onoff(s.wheel));
        if (s.rear >= 0) part(b, "заднее " + onoff(s.rear));
        return b.length() == 0 ? "машина не отвечает" : b.toString();
    }

    private static void part(StringBuilder b, String s) {
        if (b.length() > 0) b.append(" · ");
        b.append(s);
    }

    /** Число для глаза: минус типографский (U+2212), а не дефис. */
    private static String show(float f) {
        return fmt(f).replace('-', '\u2212');
    }

    /** Связь и журнал: раз в 3 с (не от событий машины). */
    private void refreshSlow() {
        new Thread(() -> {
            final String net = bridge.net == null ? "сервер не запущен" : bridge.net.describe();
            final String esp = bridge.esp == null ? "ESP: —" : bridge.esp.describe().split("\n")[0];
            final String log = tail(bridge.dumpLog(), 40);
            ui.post(() -> {
                if (!visible) return;
                StringBuilder b = new StringBuilder();
                b.append(esp).append('\n');
                b.append("Wi-Fi: ").append(NetServer.addresses()).append("   порт ").append(NetServer.PORT).append('\n');
                b.append("токен: ").append(bridge.net == null ? "-" : bridge.net.token()).append('\n');
                for (String l : net.split("\n")) if (l.startsWith("последний")) b.append(l).append('\n');
                netView.setText(b.toString().trim());
                logView.setText(log);
                render();
            });
        }).start();
    }

    private void cmd(final String c, final String arg) {
        // долгие команды показывают ответ; короткие видны по светодиодам и клавишам
        if (c.equals("auto_test")) showResult("Проверяю сценарий…");
        else if (c.equals("theme")) showResult("Ставлю тему…");
        new Thread(() -> {
            String r;
            try {
                r = bridge.submit(c, arg).get(60, TimeUnit.SECONDS);
            } catch (Throwable t) {
                r = "ERROR " + t;
            }
            bridge.note("с экрана: " + c + " " + arg);
            final String res = r;
            ui.post(() -> {
                showResult(c.equals("auto_test") || c.equals("theme") || res.startsWith("ERROR") ? res : "");
                render();
                if (diag) refreshSlow();
            });
        }).start();
    }

    private void showResult(String text) {
        resultView.setText(text);
        resultWrap.setVisibility(text.isEmpty() ? View.GONE : View.VISIBLE);
    }

    /** Шапка секции: микрозаголовок «СЦЕНАРИИ» или возврат «‹ Назад» с подстраницы. */
    private void updateHead() {
        if (stickyHead == null) return;
        boolean sub = open != PAGE_SCEN;
        backArrow.setVisibility(sub ? View.VISIBLE : View.GONE);
        stickyHead.setText(sub ? "Назад" : "СЦЕНАРИИ");
    }

    // ---------- мелочи ----------

    /** Клавиша-кейкап: включённая — оранжевая грань с чернилами, выключенная — графит с волоском. */
    private void face(Button b, boolean on) {
        if (b == null) return;
        GradientDrawable d = new GradientDrawable();
        d.setColor(on ? ON : KEY);
        d.setCornerRadius(dp(3));
        d.setStroke(thin, on ? RIM : LINE);
        b.setBackground(d);
        b.setTextColor(on ? INK : TEXT);
    }

    private static String tail(String s, int lines) {
        String[] a = s.split("\n");
        StringBuilder b = new StringBuilder();
        for (int i = Math.max(0, a.length - lines); i < a.length; i++) b.append(a[i]).append('\n');
        return b.toString();
    }

    private static String power(int p) {
        switch (p) {
            case 0: return "выкл";
            case 1: return "ACC";
            case 2: return "ON";
            case 3: return "пуск";
            default: return "—";
        }
    }

    private static String level(int v) { return v < 0 ? "—" : v == 0 ? "выкл" : String.valueOf(v); }

    private static String onoff(int v) { return v < 0 ? "—" : v == 0 ? "выкл" : "вкл"; }

    private static String fmt(float f) {
        return f == Math.round(f) ? String.valueOf(Math.round(f)) : String.format(Locale.US, "%.1f", f);
    }

    private int dp(int v) {
        return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, getResources().getDisplayMetrics());
    }

    private LinearLayout column() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    private ScrollView scroll(View v) {
        ScrollView s = new ScrollView(this);
        s.addView(v);
        return s;
    }

    private View hline() {
        View v = new View(this);
        v.setBackgroundColor(LINE);
        v.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, thin));
        return v;
    }

    /** Фон с состоянием нажатия: волосок вместо анимации, как у настоящего кейкапа. */
    private static StateListDrawable sel(int normal, int pressed) {
        StateListDrawable d = new StateListDrawable();
        d.addState(new int[]{android.R.attr.state_pressed}, new ColorDrawable(pressed));
        d.addState(new int[0], new ColorDrawable(normal));
        return d;
    }

    /** Кегль стрелки в целых пикселях: кратен 8 — клетка шрифта 1/8 em, ступени без сглаживания. */
    private int arrowPx(int dpEm) {
        return Math.max(8, 8 * Math.round(dp(dpEm) / 8f));
    }

    /**
     * Стрелка глифом пиксельного шрифта: размер в px кратен 8 — клетка шрифта (1/8 em) ложится
     * на целые пиксели, ступени не сглаживаются. Межстрочная добавка та же, что у {@link #pix}:
     * у шрифта ascent 1000 / descent 0, и без неё рамка строки короче, чем у соседнего текста.
     */
    private TextView arrow(String glyph, int px, int color) {
        TextView t = new TextView(this);
        t.setText(glyph);
        t.setTextSize(TypedValue.COMPLEX_UNIT_PX, px);
        t.setTextColor(color);
        t.setTypeface(pixel);
        t.setIncludeFontPadding(false);
        t.setLetterSpacing(0f);
        t.setLineSpacing(dp(4), 1f);
        return t;
    }

    /** Пиксельный текст: только подпись продукта — микрозаголовки, значения, клавиши. */
    private TextView pix(String text, float sp, int color) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(color);
        t.setTypeface(pixel);
        t.setIncludeFontPadding(false);
        t.setLineSpacing(dp(4), 1f);   // у шрифта ascent 1000 / descent 0: без добавки строки липнут
        return t;
    }

    /** Системный текст: подписи, справка, пояснения. */
    private TextView text(String text, float sp, int color, boolean medium) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(color);
        t.setTypeface(medium ? sysMed : sys);
        return t;
    }

    private TextView micro(String s) {
        TextView t = pix(s, 30, FAINT);
        t.setLetterSpacing(0.14f);
        return t;
    }

    private TextView microhead(String s, int padTop) {
        TextView t = micro(s);
        t.setPadding(0, padTop, 0, dp(10));
        return t;
    }

    private TextView hint(String s) {
        TextView t = text(s, 26, QUIET, false);
        t.setPadding(0, dp(16), 0, dp(12));
        return t;
    }

    /** Поле настроек: подпись сверху, кейкап под ней. */
    private LinearLayout field(String caption, View control, float weight) {
        LinearLayout c = column();
        TextView t = text(caption, 24, FAINT, false);
        t.setLetterSpacing(0.06f);
        // На узком экране шапка поля ниже: так в раскрытом виде на 800×562 в кадр
        // встают строка сценария и первые два поля целиком.
        t.setPadding(0, dp(narrow ? 12 : 18), 0, dp(6));
        c.addView(t);
        c.addView(control, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(KEY_H)));
        c.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, weight));
        return c;
    }

    /** Пустое место в ряду полей: поле не растягивается на всю ширину. */
    private View spacer(float weight) {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(0, 1, weight));
        return v;
    }

    private View fieldRow(View... fields) {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        for (int i = 0; i < fields.length; i++) {
            LinearLayout.LayoutParams p = (LinearLayout.LayoutParams) fields[i].getLayoutParams();
            // Зазор между полями заметно больше, чем между клавишами внутри поля:
            // иначе «− 5 °C + − 10 с +» читается одной лентой.
            if (i < fields.length - 1) p.rightMargin = dp(24);
            r.addView(fields[i], p);
        }
        return r;
    }

    private Button key(String label, View.OnClickListener l) {
        Key b = new Key();
        b.setText(label);
        b.setAllCaps(false);
        // Надпись кейкапа: короткая («+», «2», «выкл») — пиксельным, подпись продукта.
        // Длинная — IBM Plex: пиксельным в 16 sp она не читалась, а крупным в кейкап
        // не влезает («Поставить положение 1» — 22 клетки em, это полтысячи dp).
        if (label.length() > 4) {
            b.setTypeface(sysMed);
            b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 26);
        } else {
            b.setTypeface(pixel);
            b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 22);
        }
        b.setTextColor(TEXT);
        b.setGravity(Gravity.CENTER);
        b.setSingleLine(true);
        b.setEllipsize(TextUtils.TruncateAt.END);
        b.setMinWidth(0);
        b.setMinimumWidth(0);
        b.setMinHeight(0);
        b.setMinimumHeight(0);
        b.setPadding(dp(8), 0, dp(8), 0);
        b.setBackgroundColor(KEY);
        if (l != null) b.setOnClickListener(l);
        return b;
    }

    /**
     * Клавиша с пиксельным текстом. У Press Start 2P ascent 1000 и descent 0: рамка строки
     * выше глифов, и текст уезжает вверх. Центрируем по тесным границам глифов, а не по строке.
     */
    private final class Key extends Button {
        private final Rect glyphs = new Rect();

        Key() {
            super(MainActivity.this);
            setIncludeFontPadding(false);
        }

        @Override protected void onDraw(Canvas c) {
            CharSequence cs = getText();
            float dy = 0;
            if (cs != null && cs.length() > 0) {
                getPaint().getTextBounds(cs.toString(), 0, cs.length(), glyphs);
                Paint.FontMetrics fm = getPaint().getFontMetrics();
                float line = fm.descent - fm.ascent;
                float top = getPaddingTop();
                float content = getHeight() - top - getPaddingBottom();
                float baseline = top + (content - line) / 2f - fm.ascent;
                dy = top + content / 2f - baseline - (glyphs.top + glyphs.bottom) / 2f;
            }
            c.save();
            c.translate(0, dy);
            super.onDraw(c);
            c.restore();
        }
    }

    /** Кейкап-действие: обод кейкапа, но без оранжевой заливки — она значит «включено». */
    private Button action(String label, View.OnClickListener l) {
        Button b = key(label, l);
        GradientDrawable d = new GradientDrawable();
        d.setColor(KEY);
        d.setCornerRadius(dp(3));
        d.setStroke(thin, RIM);
        b.setBackground(d);
        return b;
    }

    /**
     * Показание между клавишами: не залито и обведено волоском — видно, что это окно значения,
     * а не третья клавиша (иначе «−  —  +» читается тремя кнопками).
     */
    private Button readout() {
        Button b = key("", null);
        b.setClickable(false);
        // без рамки и заливки: число между «−» и «+» не должно выглядеть третьей клавишей
        b.setBackgroundColor(0x00000000);
        // Показание — читаемым шрифтом: пиксельным «−10 °C» в 22 sp шире своего окна.
        b.setTypeface(sysMed);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 26);
        return b;
    }

    private View stepper(Button value, View.OnClickListener minus, View.OnClickListener plus) {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.addView(key("-", minus), new LinearLayout.LayoutParams(0, dp(KEY_H), 1f));
        // значение шире клавиш и без рамки: ряд читается как «минус · число · плюс»
        LinearLayout.LayoutParams vp = new LinearLayout.LayoutParams(0, dp(KEY_H), 1.2f);
        vp.leftMargin = dp(10);
        vp.rightMargin = dp(10);
        r.addView(value, vp);
        r.addView(key("+", plus), new LinearLayout.LayoutParams(0, dp(KEY_H), 1f));
        return r;
    }
}
