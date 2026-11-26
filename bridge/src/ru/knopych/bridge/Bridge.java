package ru.knopych.bridge;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.SystemClock;
import android.util.Log;

import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Ядро моста: команды, автосценарий, рассылка состояния.
 * Все обращения к машине идут через один фоновый поток, по очереди.
 */
final class Bridge implements Car.Listener {
    static final String TAG = Car.TAG;
    static final String ACTION_CMD = "ru.knopych.bridge.CMD";
    static final String ACTION_STATE = "ru.knopych.bridge.STATE";

    private static Bridge instance;

    static synchronized Bridge get(Context ctx) {
        if (instance == null) instance = new Bridge(ctx.getApplicationContext());
        return instance;
    }

    private final Context ctx;
    private final Car car;
    /** Все обращения к машине — только отсюда, по очереди. */
    private final ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor();
    /** Команды, которые не трогают машину и могут быть долгими (сеть, BLE, USB). */
    private final ExecutorService misc = Executors.newCachedThreadPool();
    /** Крутилка (уставка климата, вентилятор, громкость) — строго по очереди; отложенная сверка тоже здесь. */
    private final ScheduledExecutorService serial = Executors.newSingleThreadScheduledExecutor();
    private final CopyOnWriteArrayList<StateListener> listeners = new CopyOnWriteArrayList<>();
    private final AtomicBoolean statePending = new AtomicBoolean();
    /** Последнее прочитанное состояние машины (для экрана и плашек). */
    private volatile State state = new State();
    /** Крутилка: режим климата, пока экран климата открыт (экран сам шлёт VISIBLE/INVISIBLE). */
    private final Climate climate;
    EspLink esp;
    BleLink ble;
    NetServer net;
    private final SharedPreferences prefs;
    private final ArrayDeque<String> log = new ArrayDeque<>();

    // состояние автосценария (только из потока worker)
    private int lastPower = -1;
    private long onSince;
    private boolean scenarioDone;
    /** Тему в этой поездке уже ставили (сбрасывается при OFF). */
    private boolean themeDone;
    /** Сначала даём ГУ подняться после ACC/ON, потом повторяем, если экран не перекрасился. */
    private static final long THEME_SETTLE_MS = 30000;
    private static final long THEME_RETRY_MS = 60000;
    /** Ставим тему в фоне — tick не должен запускать вторую попытку параллельно. */
    private volatile boolean themeBusy;
    private long lastThemeTry;
    private volatile int themeAttempts;
    /** Сценарий хочет лобовое, но оно пока недоступно (двигатель не запущен) — ждём события. */
    private boolean windshieldWanted;
    private int lastWindshieldRaw = -1;
    private long lastWindshieldPress;
    private long lastWindshieldCheck;
    private long lastStateBroadcast;
    private float lastTemp = Float.NaN;
    private final AtomicBoolean tickPending = new AtomicBoolean();
    /** Дедуп кнопок: одно нажатие панель шлёт и в USB, и в BLE сразу. */
    private static final long BTN_DUP_MS = 300;
    private long lastBtnMs, lastLongMs;
    private int lastBtnN, lastLongN;
    /** Какой режим день/ночи уже применили к яркости: 0 день, 1 ночь, -1 ещё не применяли (только поток worker). */
    private int brightApplied = -1;
    /** С какого момента автосвет непрерывно говорит «день», 0 — не считаем (только поток worker). */
    private long daySince;

    // ---------- стоянка машины (только поток worker) ----------
    /** Сколько машина стояла, чтобы автосценарий не включался на каждой короткой остановке (как в gwm-apps/comfort). */
    static final int PARK_HOURS = 2;
    /** Начало текущей стоянки, 0 — не стоим (или не знаем). */
    private long parkFrom;
    /** Длительность последней закончившейся стоянки, -1 — неизвестна. */
    private long lastPark = -1;

    private Bridge(Context ctx) {
        this.ctx = ctx;
        this.car = new Car(ctx);
        this.climate = new Climate(this);
        this.prefs = ctx.getSharedPreferences("bridge", Context.MODE_PRIVATE);
        parkFrom = prefs.getLong("park_from", 0);
        lastPark = prefs.getLong("park_last", -1);
        car.setListener(this);
    }

    Context ctx() { return ctx; }

    SharedPreferences prefs() { return prefs; }

    String version() {
        try {
            return ctx.getPackageManager().getPackageInfo(ctx.getPackageName(), 0).versionName;
        } catch (Throwable t) {
            return "?";
        }
    }

    // ---------- состояние для экрана и ESP ----------

    /** Снимок состояния машины. -1 — не удалось прочитать. */
    static final class State {
        float outsideTemp = Float.NaN;
        int power = -1, seatDriver = -1, seatPassenger = -1, wheel = -1, windshield = -1, rear = -1;
        /** Занятость слотов памяти сиденья (0 — пусто), может быть пустым. */
        int[] seatMemory = new int[0];
        boolean auto;
        long time;
    }

    interface StateListener {
        /** Вызывается из фонового потока. */
        void onState(State s);
    }

    State state() { return state; }

    void addListener(StateListener l) { listeners.addIfAbsent(l); }

    void removeListener(StateListener l) { listeners.remove(l); }

    /** Перечитать состояние скоро (события от машины склеиваются: не чаще раза в 500 мс). */
    void refreshSoon() {
        if (statePending.compareAndSet(false, true)) {
            worker.schedule(() -> {
                statePending.set(false);
                refreshState();
            }, 500, TimeUnit.MILLISECONDS);
        }
    }

    // ---------- настройки автосценария ----------

    boolean autoEnabled() { return prefs.getBoolean("auto", false); }          // по умолчанию ВЫКЛЮЧЕН
    float autoThreshold() { return prefs.getFloat("auto_threshold", 5f); }     // °C
    int autoSeatLevel() { return prefs.getInt("auto_seat", 3); }
    boolean autoWheel() { return prefs.getBoolean("auto_wheel", true); }
    boolean autoWindshield() { return prefs.getBoolean("auto_windshield", true); }
    long autoDelayMs() { return prefs.getInt("auto_delay_s", 10) * 1000L; }
    // сценарий «тема при включении»
    boolean autoTheme() { return prefs.getBoolean("auto_theme", false); }
    int autoThemeId() { return prefs.getInt("auto_theme_id", 4); }
    // яркость по дню/ночи от автосвета машины
    boolean autoBright() { return prefs.getBoolean("auto_bright", false); }    // по умолчанию ВЫКЛЮЧЕНА

    // ---------- журнал ----------

    synchronized void note(String s) {
        Log.i(TAG, s);
        String line = new SimpleDateFormat("HH:mm:ss", Locale.US).format(new Date()) + " " + s;
        log.addLast(line);
        while (log.size() > 100) log.removeFirst();
    }

    synchronized String dumpLog() {
        StringBuilder b = new StringBuilder();
        for (String s : log) b.append(s).append('\n');
        return b.toString();
    }

    // ---------- выполнение ----------

    Future<String> submit(final String cmd, final String arg) {
        String c = cmd == null ? "" : cmd.trim().toLowerCase(Locale.US);
        boolean slow = c.equals("ble_scan") || c.equals("getprop") || c.equals("settings")
                || c.equals("dumpsys") || c.equals("packages") || c.equals("intents") || c.equals("wifi_adb") || c.equals("net")
                || c.equals("usb_list") || c.equals("esp") || c.equals("esp_send") || c.equals("token") || c.equals("theme")
                || c.equals("ble") || c.equals("ble_mac");
        return (slow ? misc : worker).submit(() -> {
            try {
                return execute(cmd == null ? "status" : cmd.trim().toLowerCase(Locale.US),
                        arg == null ? "" : arg.trim().toLowerCase(Locale.US));
            } catch (Throwable t) {
                note("ошибка в команде " + cmd + " " + arg + ": " + t);
                return "ERROR " + t;
            }
        });
    }

    private void ensureCar() throws Exception {
        if (!car.isReady()) car.connect(20000);
    }

    private String execute(String cmd, String arg) throws Exception {
        switch (cmd) {
            case "ping":
                return "pong";
            case "log":
                return dumpLog();
            case "popup": {
                // отладка плашки: popup <текст> | popup seat 0..3 | popup seat_pass 0..3 | popup wind on|off | popup preset 1..3 [saved|failed]
                String[] w = arg.split("\\s+");
                if (w.length > 1 && w[0].equals("seat")) {
                    Plaque.showSeat(ctx, false, Integer.parseInt(w[1]));
                    return "плашка: сиденье водителя " + w[1];
                }
                if (w.length > 1 && w[0].equals("seat_pass")) {
                    Plaque.showSeat(ctx, true, Integer.parseInt(w[1]));
                    return "плашка: сиденье пассажира " + w[1];
                }
                if (w.length > 1 && w[0].equals("wind")) {
                    boolean on = !w[1].equals("off");
                    Plaque.showWindshield(ctx, on);
                    return "плашка: лобовое " + (on ? "вкл" : "выкл");
                }
                if (w.length > 1 && w[0].equals("preset")) {
                    int n = Integer.parseInt(w[1]);
                    String state = w.length > 2 ? w[2] : "";
                    String cap = state.equals("saved") ? "Слот " + n + " сохранён"
                            : state.equals("failed") ? "Слот " + n + " не сохранён" : "";
                    if (state.isEmpty()) { Plaque.showPreset(ctx, n); return "плашка: пресет " + n; }
                    if (cap.isEmpty()) return "popup preset 1..3 [saved|failed]";
                    Plaque.showPreset(ctx, n, cap);
                    return "плашка: пресет " + n + ", " + cap;
                }
                if (arg.equals("sizes")) { Plaque.sizes(ctx); return "плашка sizes: размеры в журнале"; }
                if (arg.isEmpty()) return "popup <текст> | popup seat 0..3 | popup seat_pass 0..3 | popup wind on|off | popup preset 1..3 [saved|failed]";
                Plaque.show(ctx, arg);
                return "плашка: " + arg;
            }
            case "volume":
                return volumeCommand(arg);
            case "climate":
                return climateCommand(arg);
            case "hvac":
                return hvacCommand(arg);
            // отладка ручки без панели: тот же путь, что строка vbtn/!vol из ESP — дедуп и режим как в жизни
            case "vbtn":
                onEspVbtn(Integer.parseInt(arg));
                return "vbtn " + arg + " -> " + climate.describe();
            case "vol":
                onEspVolume(Integer.parseInt(arg));
                return "vol " + arg + " -> " + climate.describe();
            case "config":
                return config();
            case "version":
                return "knopych-bridge " + version();
            case "auto":
                prefs.edit().putBoolean("auto", parseOnOff(arg)).apply();
                refreshSoon();
                return config();
            case "wifi_adb":
                return WifiAdb.command(this, prefs, arg);
            case "net":
                return net == null ? "сервер не запущен" : net.describe();
            case "token":
                return net == null ? "сервер не запущен" : "token=" + net.token();
            case "usb_list":
                return EspLink.listDevices(ctx);
            case "esp":
                return esp == null ? "ESP: не запущено" : esp.describe();
            case "esp_send":
                if (esp == null || !esp.isConnected()) return "ESP не подключена";
                esp.send(arg);
                SystemClock.sleep(500);
                return esp.describe();
            case "ble":
                return ble == null ? "BLE: не запущено" : ble.describe();
            case "ble_mac":
                return ble == null ? "BLE: не запущено" : ble.setMac(arg);
            case "ui_pad": {
                String[] p = arg.split("\\s+");
                prefs.edit().putInt("ui_pad_left", Integer.parseInt(p[0]))
                        .putInt("ui_pad_top", p.length > 1 ? Integer.parseInt(p[1]) : 0).apply();
                return "отступы экрана: слева " + p[0] + ", сверху " + (p.length > 1 ? p[1] : "0")
                        + " px. Закрой и открой экран «Кнопыч».";
            }
            case "getprop": case "settings": case "dumpsys": case "packages": case "intents":
                return Diag.run(ctx, cmd, arg);
            case "theme":
                return ThemeCtl.command(ctx, arg);
            case "ble_scan":
                return BleScan.run(ctx, arg.isEmpty() ? 8 : Integer.parseInt(arg));
            case "auto_threshold":
                prefs.edit().putFloat("auto_threshold", Float.parseFloat(arg)).apply();
                refreshSoon();
                return config();
            case "auto_seat":
                prefs.edit().putInt("auto_seat", parseLevel(arg)).apply();
                return config();
            case "auto_wheel":
                prefs.edit().putBoolean("auto_wheel", parseOnOff(arg)).apply();
                return config();
            case "auto_windshield":
                prefs.edit().putBoolean("auto_windshield", parseOnOff(arg)).apply();
                return config();
            case "auto_theme":
                prefs.edit().putBoolean("auto_theme", parseOnOff(arg)).apply();
                return config();
            case "auto_theme_id":
                prefs.edit().putInt("auto_theme_id", Integer.parseInt(arg)).apply();
                return config();
            case "auto_bright":
                prefs.edit().putBoolean("auto_bright", parseOnOff(arg)).apply();
                brightApplied = -1; // при следующем включении применим режим заново
                refreshSoon();
                return config();
            case "auto_delay":
                prefs.edit().putInt("auto_delay_s", Integer.parseInt(arg)).apply();
                return config();
        }

        ensureCar();
        switch (cmd) {
            case "status":
                return status();
            case "seat_driver":
                car.setSeat(Car.SEAT_DRIVER, parseLevel(arg));
                return afterSet();
            case "seat_passenger":
                car.setSeat(Car.SEAT_PASSENGER, parseLevel(arg));
                return afterSet();
            case "seat_memory":
                return "seat_memory=" + car.recallSeat(Integer.parseInt(arg));
            case "seat_save":
                return seatSave(Integer.parseInt(arg));
            case "wheel":
                car.setWheel(parseOnOff(arg));
                return afterSet();
            case "windshield":
                return "windshield=" + onOff(car.setWindow(Car.WINDSHIELD, parseOnOff(arg))) + "\n" + status();
            case "rear":
                return "rear=" + onOff(car.setWindow(Car.REAR_WINDOW, parseOnOff(arg))) + "\n" + status();
            case "press_windshield":
                car.pressWindow(Car.WINDSHIELD);
                return afterSet();
            case "press_rear":
                car.pressWindow(Car.REAR_WINDOW);
                return afterSet();
            case "auto_test":
                return runScenario("ручной тест", "force".equals(arg));
            case "button":
                return button(Integer.parseInt(arg));
            case "brightness":
                return brightnessCommand(arg);
            case "prop":
                return prop(arg);
            case "park":
                return parkState();
            case "long":
                return hold(Integer.parseInt(arg));
            default:
                return "неизвестная команда: " + cmd + "\n" + HELP;
        }
    }

    private String afterSet() throws Exception {
        SystemClock.sleep(1000);
        return status();
    }

    /** volume [N] — без N показать текущую, с N поставить (clamp). Без ensureCar: иначе до 20 с ожидания. */
    private String volumeCommand(String arg) {
        if (!car.isReady()) return "громкость: машина не готова";
        if (!arg.isEmpty()) return car.setVolume(Integer.parseInt(arg));
        int v = car.volume();
        int max = car.volumeMax();
        return (v < 0 || max < 0) ? "громкость: ошибка чтения" : "громкость=" + v + "/" + max;
    }

    // ---------- климат (диагностика) ----------

    /**
     * climate [temp up|down] [fan up|down|1..7] — прочитать/записать климат напрямую через AptivCarHvacFunction.
     * Без ensureCar, как volume: не ждать 20 с, если машина не подключена.
     */
    private String climateCommand(String arg) throws Exception {
        if (!car.isReady()) return "климат: машина не готова";
        String[] p = arg.split("\\s+");
        if (p[0].isEmpty()) {
            StringBuilder b = new StringBuilder("климат:\n");
            b.append("power_mode=").append(safe(() -> String.valueOf(car.getPowerMode()))).append('\n');
            b.append(climate.describe()).append('\n');
            b.append("16 водитель: ").append(tempLine(Car.TEMP_DRIVER)).append('\n');
            b.append("17 пассажир: ").append(tempLine(Car.TEMP_PASSENGER)).append('\n');
            b.append("18 вентилятор: ").append(hvacValue(Car.FAN)).append('\n');
            b.append("state 16/17/18: ").append(safe(() -> Car.describeState(car.getHvacState(Car.TEMP_DRIVER))))
                    .append(" / ").append(safe(() -> Car.describeState(car.getHvacState(Car.TEMP_PASSENGER))))
                    .append(" / ").append(safe(() -> Car.describeState(car.getHvacState(Car.FAN)))).append('\n');
            b.append("state 38/40: ").append(safe(() -> Car.describeState(car.getHvacState(Car.TEMP_DRIVER_SET))))
                    .append(" / ").append(safe(() -> Car.describeState(car.getHvacState(Car.FAN_SET))));
            return b.toString();
        }
        String v = p.length > 1 ? p[1] : "";
        if (p[0].equals("temp")) return climateTemp(v);
        if (p[0].equals("fan")) return climateFan(v);
        if (p[0].equals("act")) return climateAct(p);
        if (p[0].equals("raw")) return climateRaw(p);
        if (p[0].equals("abs")) return climateAbs(v);
        throw new IllegalArgumentException("climate | climate temp up|down | climate fan up|down|1..7"
                + " | climate act <id> <0|1> | climate raw <id> <value> | climate abs <°C>");
    }

    /** Сырое значение как «215 (21.5C)»; -1 — чтение не удалось. */
    private static String tempText(int raw) {
        return raw < 0 ? "не прочитать"
                : raw + " (" + String.format(Locale.US, "%.1f", raw / 10f) + "C)";
    }

    private String tempLine(int id) {
        return safe(() -> tempText(car.hvacValue(id)));
    }

    /** hvacValue с -1 при ошибке: диагностика не должна падать. */
    private int hvacValue(int id) {
        try { return car.hvacValue(id); } catch (Throwable t) { return -1; }
    }

    /** climate temp up|down — шаг 32/33 водителя (абсолют в 38 нестабилен, жест 38 = −10 портит HI); читаем 16 до и после. */
    private String climateTemp(String v) throws Exception {
        if (!v.equals("up") && !v.equals("down")) throw new IllegalArgumentException("climate temp up|down");
        return "климат: водитель " + tempStep(v.equals("up") ? 1 : -1) + " (шаг " + v + ")";
    }

    /** climate act <id> <0|1> — один hvac-action без парного отпускания: проверка одиночных id. */
    private String climateAct(String[] p) throws Exception {
        if (p.length < 3) throw new IllegalArgumentException("climate act <id> <0|1>");
        int id = Integer.parseInt(p[1]);
        int v = Integer.parseInt(p[2]);
        car.hvacAction(id, v);
        return "климат: act " + id + "=" + v + " отправлено";
    }

    /** climate raw <id> <value> — прямая запись без клампов; для 16/17/18 читаем через 300 мс. */
    private String climateRaw(String[] p) throws Exception {
        if (p.length < 3) throw new IllegalArgumentException("climate raw <id> <value>");
        int id = Integer.parseInt(p[1]);
        int value = Integer.parseInt(p[2]);
        car.setHvacValue(id, value);
        String s = "климат: raw " + id + "=" + value + " записано";
        if (id != Car.TEMP_DRIVER && id != Car.TEMP_PASSENGER && id != Car.FAN) return s;
        SystemClock.sleep(300);
        return s + " -> " + hvacValue(id);
    }

    /** climate abs <°C> — уставка водителя абсолютом, как штатная шкала: 38 = значение и сразу −10; читаем 16 до и через 450 мс. */
    private String climateAbs(String v) throws Exception {
        float c = Float.parseFloat(v);
        int raw = Math.max(Car.TEMP_MIN, Math.min(Car.TEMP_MAX, Math.round(c * 10f)));
        int was = hvacValue(Car.TEMP_DRIVER);
        String before = safe(() -> Car.describeState(car.getHvacState(Car.TEMP_DRIVER_SET)));
        car.setHvacTempAbsolute(raw);
        SystemClock.sleep(450);
        int now = hvacValue(Car.TEMP_DRIVER);
        String after = safe(() -> Car.describeState(car.getHvacState(Car.TEMP_DRIVER_SET)));
        return "климат: abs " + (raw / 10f) + " -> 38=" + raw + ", -10; водитель " + tempText(was) + " -> " + tempText(now)
                + "; state 38 " + before + " -> " + after;
    }

    /** climate fan up|down — шаги 36/37; climate fan N — абсолют в 40, если не принят, добираем шагами. */
    private String climateFan(String v) throws Exception {
        int was = hvacValue(Car.FAN);
        if (v.equals("up") || v.equals("down")) {
            car.hvacStep(v.equals("up") ? Car.FAN_UP : Car.FAN_DOWN);
            SystemClock.sleep(300);
            return "климат: вентилятор " + was + " -> " + hvacValue(Car.FAN) + " (шаг " + v + ")";
        }
        int want = Math.max(1, Math.min(7, Integer.parseInt(v)));
        car.setHvacValue(Car.FAN_SET, want);
        SystemClock.sleep(300);
        int now = hvacValue(Car.FAN);
        String s = "климат: вентилятор " + was + " -> " + now + (now != want ? " (просили " + want + ")" : "");
        if (now == want) return s;
        if (now < 0) return s; // не читается — шагами не угадать, сколько их нужно
        int steps = Math.min(7, Math.abs(want - now));
        for (int i = 0; i < steps; i++) car.hvacStep(want > now ? Car.FAN_UP : Car.FAN_DOWN);
        SystemClock.sleep(300);
        return s + "; шагами " + steps + " -> " + hvacValue(Car.FAN);
    }

    /** hvac open|close — экран климата: открыть enter_hvac, закрыть sidemenu_showing. */
    private String hvacCommand(String arg) {
        if (arg.equals("open")) {
            ctx.sendBroadcast(new Intent("com.gwmv3.vehicle.enter_hvac").setPackage("com.android.systemui"));
            note("климат: экран открыт командой");
            return "hvac open: отправлено";
        }
        if (arg.equals("close")) {
            ctx.sendBroadcast(new Intent("gwmv3.intent.sidemenu_showing"));
            note("климат: экран закрыт командой");
            return "hvac close: отправлено";
        }
        throw new IllegalArgumentException("hvac open|close");
    }

    /** Экран климата сам сообщает, что показан (BridgeService регистрирует приёмник). */
    void onClimateScreen(boolean visible, int isBack) {
        climate.onScreen(visible);
        note(visible ? "климат: экран открылся" : "климат: экран закрылся (ISBACK=" + isBack + ")");
    }

    /** Кнопка энкодера (vbtn 1 нажата, 0 отпущена) из ESP/BLE — решает Climate. */
    void onEspVbtn(int v) {
        climate.onVbtn(v);
    }

    // ---------- шаги с крутилки (поток serial: по очереди) ----------

    /** Уставка водителя, которую мост поставил и ждёт (сырое °C×10); -1 — не знаем. */
    private int tempWant = -1;
    /** Время последнего щелчка климата: серия держит локальную цель, пауза — перечитываем 16. */
    private long tempAt;
    private boolean tempCheck;
    /** Уровень вентилятора, который мост поставил и ждёт; -1 — не знаем. */
    private int fanWant = -1;
    private long fanAt;
    private boolean fanCheck;
    /** Пауза в серии щелчков, после которой цель больше не считаем своей. */
    private static final long CHAIN_MS = 2000;
    /** Через сколько после последнего щелчка сверяем значение с целью. */
    private static final long SETTLE_MS = 600;

    void climateOpen() {
        ctx.sendBroadcast(new Intent("com.gwmv3.vehicle.enter_hvac").setPackage("com.android.systemui"));
    }

    void climateClose() {
        ctx.sendBroadcast(new Intent("gwmv3.intent.sidemenu_showing"));
    }

    /** Климат живёт 8 с без событий: продлеваем экран. Получателя явно не указано — шлём всем. */
    void climateRefresh() {
        ctx.sendBroadcast(new Intent("com.gwmv3.vehicle.hvac_refresh_8_seconds"));
    }

    /** Ждём, пока значение функции станет want: опросы по 60 мс до 600 мс. Возвращает последнее прочитанное. */
    private int waitHvac(int id, int want) {
        int now = hvacValue(id);
        for (int i = 0; i < 10 && now != want; i++) {
            SystemClock.sleep(60);
            now = hvacValue(id);
        }
        return now;
    }

    /**
     * Шаг уставки водителя: dir > 0 — теплее. На пределе не шагает (шаг всё равно ничего не меняет).
     * Возвращает «230 (23.0C) -> 235 (23.5C)» для ответа команды.
     */
    private String tempStep(int dir) throws Exception {
        int was = hvacValue(Car.TEMP_DRIVER);
        if ((was == Car.TEMP_MAX && dir > 0) || (was == Car.TEMP_MIN && dir < 0)) {
            return tempText(was) + " -> " + tempText(was);
        }
        int up = dir > 0 ? Car.TEMP_DRIVER_UP : Car.TEMP_DRIVER_DOWN;
        car.hvacStep(up);
        int want = was < 0 ? -1 : was + dir * 5; // не прочитать было — проверить нечего
        int now = want < 0 ? hvacValue(Car.TEMP_DRIVER) : waitHvac(Car.TEMP_DRIVER, want);
        if (want >= 0 && now != want) {
            note("климат: шаг не принят с первого раза, повтор");
            car.hvacStep(up);
            now = waitHvac(Car.TEMP_DRIVER, want);
            if (now != want) note("климат: уставка не изменилась: " + tempText(was) + " -> " + tempText(now));
        }
        return tempText(was) + " -> " + tempText(now);
    }

    /** Шаг уставки с крутилки: dir > 0 — теплее. Абсолют в 38 (как штатная шкала), сверка — после серии. */
    void climateTemp(int dir) {
        serial.execute(() -> {
            if (!car.isReady()) return;
            try {
                long now = SystemClock.elapsedRealtime();
                // в серии щелчков цель считаем своей, иначе читаем машину (её могли поменять из штатного экрана)
                int was = tempWant >= 0 && now - tempAt < CHAIN_MS ? tempWant : hvacValue(Car.TEMP_DRIVER);
                if (was < 0) return; // не прочитать — шаг не угадать
                int want = Math.max(Car.TEMP_MIN, Math.min(Car.TEMP_MAX, was + dir * 5));
                if (want == was) return; // предел шкалы
                tempWant = want;
                tempAt = now;
                car.setHvacTempAbsolute(want);
                climate.refreshScreen();
                checkTempLater();
            } catch (Throwable t) {
                note("климат: уставка: " + t);
            }
        });
    }

    /** Сверка после серии щелчков, не чаще одной: 38 мог не приняться — тогда добираем шагами. */
    private void checkTempLater() {
        if (tempCheck) return;
        tempCheck = true;
        serial.schedule(this::verifyTemp, SETTLE_MS, TimeUnit.MILLISECONDS);
    }

    private void verifyTemp() {
        tempCheck = false;
        if (tempWant < 0) return;
        if (SystemClock.elapsedRealtime() - tempAt < SETTLE_MS) { // ещё крутят — подождём
            checkTempLater();
            return;
        }
        try {
            int got = hvacValue(Car.TEMP_DRIVER);
            if (got < 0 || got == tempWant) return;
            note("климат: абсолют не принят: " + tempText(got) + " -> " + tempText(tempWant) + ", шагами");
            int steps = Math.min(6, Math.abs(tempWant - got) / 5);
            for (int i = 0; i < steps; i++) car.hvacStep(tempWant > got ? Car.TEMP_DRIVER_UP : Car.TEMP_DRIVER_DOWN);
            int now = hvacValue(Car.TEMP_DRIVER);
            if (now != tempWant) {
                note("климат: уставка " + tempText(now) + ", ждали " + tempText(tempWant));
                tempWant = -1; // разошлось — следующий щелчок читает машину заново
            }
        } catch (Throwable t) {
            note("климат: сверка уставки: " + t);
        }
    }

    /** Шаг вентилятора с крутилки при удержании кнопки: абсолют в 40, clamp 1..7 (шаги 36/37 не работают). */
    void climateFan(int delta) {
        serial.execute(() -> {
            if (!car.isReady()) return;
            try {
                long now = SystemClock.elapsedRealtime();
                // в серии щелчков уровень считаем своим, иначе читаем машину
                int was = fanWant > 0 && now - fanAt < CHAIN_MS ? fanWant : hvacValue(Car.FAN);
                if (was < 0) return;
                int want = Math.max(1, Math.min(7, was + delta));
                if (want == was) return; // предел
                fanWant = want;
                fanAt = now;
                car.setHvacValue(Car.FAN_SET, want);
                climate.refreshScreen();
                checkFanLater();
            } catch (Throwable t) {
                note("климат: вентилятор: " + t);
            }
        });
    }

    /** Сверка уровня вентилятора после серии щелчков, не чаще одной: 40 мог не приняться — пишем ещё раз. */
    private void checkFanLater() {
        if (fanCheck) return;
        fanCheck = true;
        serial.schedule(this::verifyFan, SETTLE_MS, TimeUnit.MILLISECONDS);
    }

    private void verifyFan() {
        fanCheck = false;
        if (fanWant < 0) return;
        if (SystemClock.elapsedRealtime() - fanAt < SETTLE_MS) { // ещё крутят — подождём
            checkFanLater();
            return;
        }
        try {
            int got = hvacValue(Car.FAN);
            if (got < 0 || got == fanWant) return;
            note("климат: вентилятор не принят: " + got + " -> " + fanWant + ", пишу ещё раз");
            car.setHvacValue(Car.FAN_SET, fanWant);
            int now = hvacValue(Car.FAN);
            if (now != fanWant) {
                note("климат: вентилятор " + now + ", ждали " + fanWant);
                fanWant = -1; // разошлось — следующий щелчок читает машину заново
            }
        } catch (Throwable t) {
            note("климат: сверка вентилятора: " + t);
        }
    }

    /** Шаг громкости с крутилки — тоже в очередь serial: read-modify-write, быстрые щелчки иначе теряются. */
    void volumeStep(int delta) {
        serial.execute(() -> note(car.adjustVolume(delta)));
    }

    String status() throws Exception {
        StringBuilder b = new StringBuilder();
        b.append("power_mode=").append(safe(() -> String.valueOf(car.getPowerMode()))).append('\n');
        b.append("outside_temp=").append(safe(() -> String.valueOf(car.getOutsideTemp())))
                .append(" raw=").append(safe(() -> String.valueOf(car.getOutsideTempRaw()))).append('\n');
        b.append("seat_driver=").append(safe(() -> String.valueOf(car.getValue(Car.SEAT_DRIVER))))
                .append(" state=").append(safe(() -> Car.describeState(car.getState(Car.SEAT_DRIVER)))).append('\n');
        b.append("seat_passenger=").append(safe(() -> String.valueOf(car.getValue(Car.SEAT_PASSENGER))))
                .append(" state=").append(safe(() -> Car.describeState(car.getState(Car.SEAT_PASSENGER)))).append('\n');
        b.append("wheel=").append(safe(() -> String.valueOf(car.getValue(Car.WHEEL))))
                .append(" state=").append(safe(() -> Car.describeState(car.getState(Car.WHEEL)))).append('\n');
        b.append("windshield=").append(safe(() -> onOff(car.isWindowHeatOn(Car.WINDSHIELD))))
                .append(" state=").append(safe(() -> Car.describeState(car.getHvacState(Car.WINDSHIELD)))).append('\n');
        b.append("rear=").append(safe(() -> onOff(car.isWindowHeatOn(Car.REAR_WINDOW))))
                .append(" state=").append(safe(() -> Car.describeState(car.getHvacState(Car.REAR_WINDOW)))).append('\n');
        b.append("auto=").append(onOff(autoEnabled()));
        return b.toString();
    }

    private String config() {
        return "auto=" + onOff(autoEnabled())
                + " threshold=" + autoThreshold() + "C"
                + " seat=" + autoSeatLevel()
                + " wheel=" + onOff(autoWheel())
                + " windshield=" + onOff(autoWindshield())
                + " delay=" + autoDelayMs() / 1000 + "s"
                + "\nauto_theme=" + onOff(autoTheme()) + " theme_id=" + autoThemeId()
                + " park=от " + PARK_HOURS + "ч"
                + "\nauto_bright=" + onOff(autoBright()) + " day=" + AUTO_BRIGHT_DAY + " night=" + AUTO_BRIGHT_NIGHT
                + " window=" + dayWindowText() + " hold=" + DAY_HOLD_MS / 60000 + "m";
    }

    // ---------- автосценарий ----------

    /** Вызывается сервисом раз в несколько секунд (в потоке worker). */
    void tick() {
        if (!tickPending.compareAndSet(false, true)) return; // предыдущий ещё не отработал
        worker.execute(() -> {
            try {
                climate.onTick(); // сторожевой: экран климата уже не сверху — режим выключить
                ensureCar();
                int pm = car.getPowerMode();
                long now = SystemClock.elapsedRealtime();
                if (pm != lastPower) {
                    note("режим питания: " + lastPower + " -> " + pm);
                    // стоянка: закрываем при запуске, открываем при выключении/ACC
                    if (lastPower == -1) {
                        // первый тик: ГУ могло перезагрузиться посреди стоянки — дозакрываем её
                        if (pm == Car.POWER_ON || pm == Car.POWER_CRANK) parkEnded();
                        else if (parkFrom == 0) parkStarted();
                    } else if (pm == Car.POWER_ON || pm == Car.POWER_CRANK) {
                        parkEnded();
                    } else if (pm == Car.POWER_OFF || pm == Car.POWER_ACC) {
                        parkStarted();
                    }
                    if (pm == Car.POWER_ON) {
                        onSince = now;
                        scenarioDone = false;
                    } else if (pm == Car.POWER_OFF || pm == Car.POWER_ACC) {
                        scenarioDone = false;
                        if (pm == Car.POWER_OFF) { themeDone = false; themeAttempts = 0; }
                        else onSince = now; // с ACC тема ждёт столько же, сколько с ON
                        if (windshieldWanted) note("лобовое: зажигание выключено, больше не жду");
                        windshieldWanted = false;
                    }
                    lastPower = pm;
                }
                if (autoTheme() && !themeDone && !themeBusy
                        && (pm == Car.POWER_ACC || pm == Car.POWER_ON)
                        && now - onSince >= THEME_SETTLE_MS
                        && themeAttempts < 5
                        && now - lastThemeTry >= THEME_RETRY_MS) {
                    themeBusy = true;
                    lastThemeTry = now;
                    misc.execute(this::applyAutoTheme);
                }
                if (autoEnabled() && pm == Car.POWER_ON && !scenarioDone && now - onSince >= autoDelayMs()) {
                    // гейт: не греем на каждой короткой остановке, только после долгой стоянки
                    long stood = parkedMs();
                    scenarioDone = true; // в любом случае, иначе проверка повторяется каждые 3 с
                    if (stood >= 0 && stood < PARK_HOURS * 3600000L) {
                        note("сценарий: машина стояла " + humanMs(stood) + ", нужно от " + PARK_HOURS + " ч — пропуск");
                    } else {
                        runScenario("зажигание ON", false);
                    }
                }
                if (autoBright()) applyNightBrightness(pm);
                // Запасная проверка раз в минуту, если событие о доступности лобового вдруг не пришло.
                if (windshieldWanted && pm == Car.POWER_ON && now - lastWindshieldCheck >= 60000) {
                    tryWindshield();
                }
                float t = car.getOutsideTemp();
                if (now - lastStateBroadcast > 60000 || Math.abs(t - lastTemp) >= 0.5f) {
                    lastTemp = t;
                    refreshState();
                }
            } catch (Throwable e) {
                Log.w(TAG, "tick: " + e);
            } finally {
                tickPending.set(false);
            }
        });
    }

    // ---------- стоянка машины ----------

    // shortcut: стоянка считается по стенным часам (System.currentTimeMillis) — перевод часов или
    // пояса её ломает; для гейта «2 ч» допустимо. Считать по elapsedRealtime + время последней
    // стоянки из ГУ, если это станет мешать.
    private void parkStarted() {
        parkFrom = System.currentTimeMillis();
        prefs.edit().putLong("park_from", parkFrom).apply();
        note("стоянка: началась в " + hm(parkFrom));
    }

    private void parkEnded() {
        if (parkFrom <= 0) return;
        lastPark = System.currentTimeMillis() - parkFrom;
        parkFrom = 0;
        prefs.edit().putLong("park_from", 0).putLong("park_last", lastPark).apply();
        note("машина стояла " + humanMs(lastPark));
    }

    /**
     * Сколько машина стояла перед этой поездкой. При включённом зажигании — только что закончившаяся
     * стоянка (lastPark), иначе сценарий на запуске двигателя её не увидит. -1 — неизвестно.
     */
    private long parkedMs() {
        if (lastPower == Car.POWER_ON || lastPower == Car.POWER_CRANK) return lastPark;
        return parkFrom > 0 ? System.currentTimeMillis() - parkFrom : -1;
    }

    private static String humanMs(long ms) {
        if (ms < 0) return "— неизвестно";
        long min = ms / 60000;
        return min >= 60 ? (min / 60) + " ч " + (min % 60) + " мин" : min + " мин";
    }

    private static String hm(long ms) {
        return new SimpleDateFormat("HH:mm", Locale.US).format(new Date(ms));
    }

    /** Команда park: что мост думает про стоянку прямо сейчас (проверка без ожидания 2 ч). */
    private String parkState() {
        String prev = "предыдущая " + humanMs(lastPark);
        if (lastPower == Car.POWER_ON || lastPower == Car.POWER_CRANK) {
            return "стоянка: машина заведена, стояла " + humanMs(lastPark);
        }
        if (parkFrom <= 0) return "стоянка: не отслеживается, " + prev;
        return "стоянка: идёт " + humanMs(parkedMs()) + " (с " + hm(parkFrom) + "), " + prev;
    }

    private String runScenario(String why, boolean force) throws Exception {
        float t = car.getOutsideTemp();
        boolean valid = t > -50 && t < 70;
        if (!force && !(valid && t < autoThreshold())) {
            String s = "сценарий (" + why + "): за бортом " + t + "C, порог " + autoThreshold() + "C — не включаю";
            note(s);
            return s;
        }
        note("сценарий (" + why + "): за бортом " + t + "C — включаю");
        if (autoSeatLevel() > 0) {
            try {
                car.setSeat(Car.SEAT_DRIVER, autoSeatLevel());
                Plaque.showSeat(ctx, false, autoSeatLevel());
            } catch (Throwable e) { note("сиденье: " + e); }
        }
        if (autoWheel()) {
            try { car.setWheel(true); } catch (Throwable e) { note("руль: " + e); }
        }
        if (autoWindshield()) {
            windshieldWanted = true; // включим, как только станет доступно (без ограничения по времени)
            lastWindshieldRaw = -1;
            tryWindshield();
        }
        SystemClock.sleep(1000);
        String st = status();
        note("после сценария:\n" + st);
        return st;
    }

    /**
     * Сценарий «тема при включении» (поток misc: служба тем может отвечать несколько секунд).
     * Ставим до подтверждения, что экран реально перекрасился; если нет — tick повторит через минуту.
     */
    private void applyAutoTheme() {
        int id = autoThemeId();
        try {
            if (ThemeCtl.isApplied(ctx, id)) {
                note("тема: " + id + " уже стоит");
                themeDone = true;
                return;
            }
            themeAttempts++;
            note("тема: ставлю " + id + " (сценарий при включении, попытка " + themeAttempts + ")");
            String r = ThemeCtl.command(ctx, String.valueOf(id)).split("\n")[0];
            note("тема: " + r);
            if (ThemeCtl.isApplied(ctx, id)) {
                themeDone = true;
            } else if (themeAttempts >= 5) {
                note("тема: 5 попыток без перекраски — больше не пытаюсь до выключения");
            } else {
                note("тема: экран не перекрасился — повторю через " + THEME_RETRY_MS / 1000 + " с");
            }
        } catch (Throwable e) {
            note("тема: попытка " + themeAttempts + " не удалась: " + e);
        } finally {
            themeBusy = false;
        }
    }

    /**
     * Включить лобовое, если оно сейчас доступно. Если недоступно (например, state=21 — двигатель
     * не запущен) — ничего не нажимаем и ждём события от машины об изменении его состояния.
     * Нажатие — не чаще раза в 30 с, чтобы не долбить блок.
     */
    private void tryWindshield() {
        long now = SystemClock.elapsedRealtime();
        lastWindshieldCheck = now;
        try {
            if (car.isWindowHeatOn(Car.WINDSHIELD)) {
                note("лобовое уже включено");
                windshieldWanted = false;
                return;
            }
            int raw = car.getHvacState(Car.WINDSHIELD);
            if (!Car.isAvailable(raw)) {
                if (raw != lastWindshieldRaw) {
                    note("лобовое пока недоступно, state=" + Car.describeState(raw) + " — жду, когда станет доступно");
                }
                lastWindshieldRaw = raw;
                return;
            }
            lastWindshieldRaw = raw;
            if (now - lastWindshieldPress < 30000) return;
            lastWindshieldPress = now;
            if (car.setWindow(Car.WINDSHIELD, true)) {
                note("лобовое включено");
                Plaque.showWindshield(ctx, true);
                windshieldWanted = false;
            } else {
                note("лобовое не включилось, хотя доступно: state=" + Car.describeState(car.getHvacState(Car.WINDSHIELD)));
            }
        } catch (Throwable e) {
            note("лобовое: " + e);
        }
    }

    // ---------- кнопки ESP ----------

    /**
     * Нажатие кнопки панели (из ESP или команда button N). Раскладка:
     * 1/2/3 пресет положения сиденья водителя,
     * 4 подогрев водителя (выкл → 3 → 2 → 1 → выкл), 5 лобовое,
     * 6 подогрев пассажира (так же по кругу). Руль и заднее стекло — только командами.
     * Долгое удержание кнопок 1/2/3 — сохранить текущее положение сиденья в слот; 4 — яркость ГУ.
     */
    void onEspButton(final int n) {
        if (dup(n, false)) return;
        worker.execute(() -> {
            try {
                ensureCar();
                note("кнопка " + n + ": " + button(n).replace('\n', ' '));
            } catch (Throwable t) {
                note("кнопка " + n + ": ошибка " + t);
            }
        });
    }

    /**
     * Вращение с энкодера панели. Климат открыт — шаг уставки, закрыт — громкость (решает Climate);
     * дедуп двух каналов тоже там. Сами шаги идут в очередь serial, а не в misc.
     */
    void onEspVolume(final int delta) {
        climate.onVolume(delta);
    }

    /** Долгое удержание кнопки панели (из ESP или команда long N). */
    void onEspLong(final int n) {
        if (dup(n, true)) return;
        worker.execute(() -> {
            try {
                ensureCar();
                String s = hold(n);
                note("кнопка " + n + " удержана: " + s.replace('\n', ' '));
            } catch (Throwable t) {
                note("кнопка " + n + " удержана: ошибка " + t);
            }
        });
    }

    /** true — копия того же события из второго канала: панель шлёт его в USB и BLE одновременно. */
    private synchronized boolean dup(int n, boolean isLong) {
        long now = SystemClock.elapsedRealtime();
        long last = isLong ? lastLongMs : lastBtnMs;
        int lastN = isLong ? lastLongN : lastBtnN;
        if (n == lastN && now - last < BTN_DUP_MS) return true;
        if (isLong) { lastLongN = n; lastLongMs = now; } else { lastBtnN = n; lastBtnMs = now; }
        return false;
    }

    private String hold(int n) throws Exception {
        switch (n) {
            case 1: case 2: case 3: return seatSave(n);
            case 4: return brightnessToggle();
            default: return "долгое удержание у кнопки " + n + " не задано";
        }
    }

    // Долгое удержание кнопки слота = сохранение текущего положения (штатное ГУ: 155 = 1/2/3),
    // после успеха штатный UI сразу вызывает слот.
    private String seatSave(int n) throws Exception {
        car.saveSeat(n);
        SystemClock.sleep(300);
        int r;
        try { r = car.seatMemoryResult(); } catch (Throwable t) { r = -1; }
        refreshSoon(); // занятость слотов в состоянии
        String s = "seat_memory=" + n;
        if (r == 1 || r == 3 || r == 5) {
            car.recallSeat(n);
            refreshSoon();
            Plaque.showPreset(ctx, n, "Слот " + n + " сохранён");
            return s + " сохранён (applied)";
        }
        if (r == 2 || r == 4 || r == 6 || r == 7) {
            Plaque.showPreset(ctx, n, "Слот " + n + " не сохранён");
            if (r == 7) return s + ": машина просит повторить";
            return s + " не сохранился (код " + r + ")";
        }
        Plaque.showPreset(ctx, n, "Слот " + n + ": отправлено");
        return s + ": отправлено, код результата " + r;
    }

    private String button(int n) throws Exception {
        switch (n) {
            case 1: case 2: case 3:
                car.recallSeat(n);
                Plaque.showPreset(ctx, n);
                refreshSoon(); // занятость слотов в состоянии
                return "seat_memory=" + n;
            case 4: {
                int lvl = nextSeat(Car.SEAT_DRIVER);
                Plaque.showSeat(ctx, false, lvl);
                return "seat_driver=" + lvl;
            }
            case 5: {
                // плашка — по намерению: подтверждение от машины может прийти позже нашего ответа
                boolean want = !car.isWindowHeatOn(Car.WINDSHIELD);
                boolean got = toggleWindow(Car.WINDSHIELD);
                Plaque.showWindshield(ctx, want);
                return "windshield=" + onOff(got);
            }
            case 6: {
                int lvl = nextSeat(Car.SEAT_PASSENGER);
                Plaque.showSeat(ctx, true, lvl);
                return "seat_passenger=" + lvl;
            }
            default: throw new IllegalArgumentException("кнопки 1..6");
        }
    }

    private int nextSeat(int id) throws Exception {
        int cur = car.getValue(id);
        int next = cur <= 0 ? 3 : cur - 1;
        car.setSeat(id, next);
        refreshSoon();
        return next;
    }

    private boolean toggleWindow(int id) throws Exception {
        boolean r = car.setWindow(id, !car.isWindowHeatOn(id));
        refreshSoon();
        return r;
    }

    // ---------- яркость экрана ГУ ----------

    // Общая подсветка ГУ — vehicle function 242, диапазон штатного ползунка 1..10 (VHAL 0..100, преобразует SDK).
    // shortcut: запись значением без slider-press/release не проверена на машине — если экран не реагирует,
    // пробовать через AptivCarHvacSettingSlider
    static final int BRIGHT_MIN = 1;
    static final int BRIGHT_MAX = 10;
    // Автояркость по дню/ночи: как в штатном dimmer чужого приложения — день максимум, ночь минимум.
    static final int AUTO_BRIGHT_DAY = 10;
    static final int AUTO_BRIGHT_NIGHT = 1;
    /** Гистерезис: из «ночи» выходим, только если автосвет 3 мин подряд говорит «день» (он дребезжит в пасмурень). */
    static final long DAY_HOLD_MS = 3 * 60 * 1000L;
    /** Дневное окно: внутри него яркость всегда дневная, даже если автосвет говорит «ночь» (пасмурный день). */
    static final int DAY_FROM_HOUR = 8;   // включительно
    static final int DAY_TO_HOUR = 16;    // не включая

    /** Сейчас «дневное» окно 08:00–16:00 по местному времени ГУ. */
    private static boolean dayWindow() {
        int h = Calendar.getInstance().get(Calendar.HOUR_OF_DAY);
        return h >= DAY_FROM_HOUR && h < DAY_TO_HOUR;
    }

    /** Окно для журнала и config: «08-16». */
    private static String dayWindowText() {
        return String.format(Locale.US, "%02d-%02d", DAY_FROM_HOUR, DAY_TO_HOUR);
    }

    private String brightnessCommand(String arg) throws Exception {
        int cur = brightness();
        if (arg.isEmpty()) {
            return cur < 0 ? "brightness: не прочитать"
                    : "brightness=" + cur + " (min " + BRIGHT_MIN + ", max " + BRIGHT_MAX + ")";
        }
        if (arg.equals("toggle")) return brightnessToggle();
        int v = Integer.parseInt(arg);
        if (v < BRIGHT_MIN || v > BRIGHT_MAX) throw new IllegalArgumentException("яркость 1..10 или toggle");
        return brightnessSet(v);
    }

    /** Текущая яркость, -1 если не прочитать. */
    private int brightness() {
        try { return car.getBrightness(); } catch (Throwable t) { return -1; }
    }

    private String brightnessSet(int v) throws Exception {
        int was = brightness();
        car.setBrightness(v);
        SystemClock.sleep(300);  // значение в машине обновляется не мгновенно
        int now = brightness();
        String s = now < 0 ? "brightness: не прочитать" : "brightness=" + now;
        if (now >= 0 && now != v) s += " (просили " + v + ")";
        if (was >= 0) s += " (было " + was + ")";
        return s;
    }

    private String brightnessToggle() throws Exception {
        return brightnessSet(brightness() >= BRIGHT_MAX ? BRIGHT_MIN : BRIGHT_MAX);
    }

    /** Яркость по ночи: при смене режима ставим день=10 / ночь=1 и повторяем через 2 с (ГУ иногда перебивает). */
    private void applyNightBrightness(int pm) {
        if (pm != Car.POWER_ON && pm != Car.POWER_ACC) return;   // OFF — не трогаем
        int dn = car.getDayNight();                              // 0 день, 1 ночь, -1 ошибка
        if (dn < 0) return;
        long now = SystemClock.elapsedRealtime();
        if (dn == 1) daySince = 0;                       // ночь — счётчик стабильного дня сбрасываем
        else if (daySince == 0) daySince = now;          // день начался — запоминаем момент
        final boolean win = dayWindow();
        int mode;
        if (win) mode = 0;                               // 08:00–16:00 всегда день
        else if (dn == 1 || brightApplied != 1) mode = dn == 1 ? 1 : 0;   // в ночь — сразу, пока стоим в дне — сразу
        else mode = now - daySince >= DAY_HOLD_MS ? 0 : 1;                // из ночи — только после 3 мин дня
        if (mode == brightApplied) return;
        final boolean wasNight = brightApplied == 1;
        final boolean held = mode == 0 && dn == 0 && !win && wasNight;
        final int target = mode == 1 ? AUTO_BRIGHT_NIGHT : AUTO_BRIGHT_DAY;
        try {
            if (brightness() != target) car.setBrightness(target);
            brightApplied = mode;
            String why = mode == 1 ? "автосвет: ночь"
                    : held ? "день " + DAY_HOLD_MS / 60000 + " мин подряд"
                    : dn == 1 ? "автосвет: ночь, но " + dayWindowText()
                    : "автосвет: день";
            note("яркость: " + (mode == 1 ? "ночь" : "день") + " → " + target + " (" + why + ")");
            worker.schedule(() -> {                              // ГУ перебивает яркость сразу после смены режима
                if (!autoBright() || brightApplied != mode) return;
                try { if (brightness() != target) car.setBrightness(target); } catch (Throwable t) { note("яркость: повтор " + t); }
            }, 2, TimeUnit.SECONDS);
        } catch (Throwable t) {
            note("яркость: не выставил (" + (mode == 1 ? "ночь" : "день") + "): " + t);
        }
    }

    /** Произвольное VHAL-свойство по id (hex 0x... или десятичное) — ищем сигнал датчика света. */
    private String prop(String arg) throws Exception {
        int id;
        try {
            id = (int) (arg.startsWith("0x") ? Long.parseLong(arg.substring(2), 16) : Long.parseLong(arg));
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("id свойства: 0x11200407 или 287310855");
        }
        try {
            return String.format(Locale.US, "prop 0x%08x = %d", id, car.getPropertyRaw(id));
        } catch (Throwable t) {
            return String.format(Locale.US, "prop 0x%08x: %s", id, t);
        }
    }

    // ---------- рассылка состояния (экран, ESP, MacroDroid) ----------

    @Override
    public void onCarEvent(String what, int id, int value) {
        refreshSoon();
        // лобовое стало доступно (запустили двигатель) — сразу включаем, если сценарий этого ждёт
        if (id == Car.WINDSHIELD && "hvac.state".equals(what) && windshieldWanted) {
            worker.execute(() -> {
                try {
                    if (windshieldWanted && car.getPowerMode() == Car.POWER_ON) tryWindshield();
                } catch (Throwable t) {
                    Log.w(TAG, "windshield event: " + t);
                }
            });
        }
    }

    /** Прочитать состояние, раздать слушателям (экран, ESP) и разослать broadcast. Только из worker. */
    private void refreshState() {
        State st = new State();
        st.outsideTemp = getF(() -> car.getOutsideTemp());
        st.power = getI(() -> car.getPowerMode());
        st.seatDriver = getI(() -> car.getValue(Car.SEAT_DRIVER));
        st.seatPassenger = getI(() -> car.getValue(Car.SEAT_PASSENGER));
        st.wheel = getI(() -> car.getValue(Car.WHEEL));
        st.windshield = getI(() -> car.isWindowHeatOn(Car.WINDSHIELD) ? 1 : 0);
        st.rear = getI(() -> car.isWindowHeatOn(Car.REAR_WINDOW) ? 1 : 0);
        st.seatMemory = getA(car::seatMemoryStatus);
        st.auto = autoEnabled();
        st.time = System.currentTimeMillis();
        state = st;
        for (StateListener l : listeners) {
            try { l.onState(st); } catch (Throwable t) { Log.w(TAG, "listener: " + t); }
        }
        try {
            Intent i = new Intent(ACTION_STATE);
            i.addFlags(Intent.FLAG_INCLUDE_STOPPED_PACKAGES);
            if (!Float.isNaN(st.outsideTemp)) i.putExtra("outside_temp", st.outsideTemp);
            putIf(i, "power_mode", st.power);
            putIf(i, "seat_driver", st.seatDriver);
            putIf(i, "seat_passenger", st.seatPassenger);
            putIf(i, "wheel", st.wheel);
            putIf(i, "windshield", st.windshield);
            putIf(i, "rear", st.rear);
            i.putExtra("auto", st.auto ? 1 : 0);
            ctx.sendBroadcast(i);
            lastStateBroadcast = SystemClock.elapsedRealtime();
        } catch (Throwable e) {
            Log.w(TAG, "broadcastState: " + e);
        }
    }

    private static void putIf(Intent i, String key, int v) {
        if (v >= 0) i.putExtra(key, v);
    }

    private float getF(Getter g) {
        if (!car.isReady()) return Float.NaN;
        try { return ((Number) g.get()).floatValue(); } catch (Throwable t) { return Float.NaN; }
    }

    private int getI(Getter g) {
        if (!car.isReady()) return -1;
        try { return ((Number) g.get()).intValue(); } catch (Throwable t) { return -1; }
    }

    private int[] getA(Getter g) {
        if (!car.isReady()) return new int[0];
        try { return (int[]) g.get(); } catch (Throwable t) { return new int[0]; }
    }

    // ---------- мелочи ----------

    interface Getter { Object get() throws Exception; }

    private static String safe(Getter g) {
        try { return String.valueOf(g.get()); } catch (Throwable t) { return "ERR(" + t + ")"; }
    }

    private static boolean parseOnOff(String s) {
        switch (s) {
            case "on": case "1": case "true": return true;
            case "off": case "0": case "false": return false;
            default: throw new IllegalArgumentException("ожидалось on/off, получено: " + s);
        }
    }

    private static int parseLevel(String s) {
        int v = Integer.parseInt(s);
        if (v < 0 || v > 3) throw new IllegalArgumentException("уровень 0..3");
        return v;
    }

    static String onOff(boolean b) { return b ? "on" : "off"; }

    static final String HELP = "команды: status | seat_driver 0..3 | seat_passenger 0..3 | seat_memory 1..3 | seat_save 1..3 | wheel on/off"
            + " | windshield on/off | rear on/off | press_windshield | press_rear"
            + " | auto on/off | auto_threshold N | auto_seat 0..3 | auto_wheel on/off"
            + " | auto_windshield on/off | auto_delay сек | auto_test [force] | config | log | ping"
            + " | version | button 1..6 | brightness [1..10|toggle] | volume [N] | long 1..4 | prop 0x11200407 | park"
            + " | climate [temp up|down] [fan up|down|1..7] | climate act <id> <0|1> | climate raw <id> <value> | hvac open/close"
            + " | vbtn 0/1 | vol N"
            + " | wifi_adb status/off | net | token | usb_list | esp | esp_send строка | ble | ble_mac MAC"
            + " | ble_scan [сек] | ui_pad слева сверху | theme [1..4|next|probe] | auto_theme on/off | auto_theme_id 1..4"
            + " | auto_bright on/off"
            + " | getprop [фильтр] | settings [system|secure|global] [фильтр] | dumpsys служба [фильтр]"
            + " | packages [фильтр] | intents пакет | popup <текст>|<seat N>|<seat_pass N>|<wind on|off>|<preset N [saved|failed]>";
}
