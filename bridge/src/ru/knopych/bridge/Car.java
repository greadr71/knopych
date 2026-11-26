package ru.knopych.bridge;

import android.content.Context;
import android.os.SystemClock;
import android.util.Log;

import aptiv.support.car.AndroidCarClient;
import aptiv.support.car.AptivCarAudio;
import aptiv.support.car.AptivCarClient;
import aptiv.support.car.AptivCarHvac;
import aptiv.support.car.AptivCarHvacFunction;
import aptiv.support.car.AptivCarHvacSettingBase;
import aptiv.support.car.AptivCarSettingFunction;
import aptiv.support.car.AptivCarVariable;

/**
 * Обёртка над API Aptiv на ГУ. Подключение повторяет штатное приложение климата
 * (com.gwmv3.vehicle, VehicleApplication.connectCarHelper): см. docs/gwm-api.md.
 *
 * Все методы блокирующие: вызывать только из фонового потока.
 */
final class Car {
    static final String TAG = "Knopych";

    // Значением: AptivCarSettingFunction.setVehicleFunctionValue(id, value)
    static final int SEAT_DRIVER = 64;       // FUNCTION_SEAT_HEATING_DRIVER, 0..3
    static final int SEAT_PASSENGER = 65;    // FUNCTION_SEAT_HEATING_PASSENGER, 0..3
    static final int WHEEL = 149;            // FUNCTION_COMFORT_STEER_WHEEL_HEAT_ONOFF, 0/1
    static final int SEAT_MEMORY = 155;      // пресет положения сиденья: 1/2/3 = сохранить в слот, 4/5/6 = вызвать слот
    static final int SEAT_MEMORY_RESULT = 156;   // код результата сохранения: 1/3/5 успех, 2/4/6 неуспех, 7 повтор
    static final int SEAT_MEMORY_STATUS = 157; // занятость слотов памяти сиденья, 0 — пусто
    static final int BRIGHTNESS = 242;       // общая подсветка ГУ, 1..10
    static final int POWER_MODE_FN = 15;     // FUNCTION_POWER_MODE

    // Импульсом: AptivCarHvacFunction.setHvacFunctionAction(id, 1), затем (id, 0)
    static final int WINDSHIELD = 12;        // FUNCTION_HVAC_FRONT_WINDSHIELD_HEAT_ONOFF
    static final int REAR_WINDOW = 11;       // FUNCTION_HVAC_REAR_DEFROST_ONOFF

    // Климат (AptivCarHvacFunction): чтение — getHvacFunctionValue, запись — setHvacFunctionValue
    static final int TEMP_DRIVER = 16;       // сырое = °C × 10, 160..320, шаг 5
    static final int TEMP_PASSENGER = 17;
    static final int FAN = 18;               // 1..7
    static final int TEMP_DRIVER_SET = 38;   // абсолютная запись температуры водителя
    static final int TEMP_PASSENGER_SET = 39;
    static final int FAN_SET = 40;
    static final int TEMP_MIN = 160, TEMP_MAX = 320;
    // Шаги ±1 (импульс как у стёкол): 32/33 водитель, 34/35 пассажир, 36/37 вентилятор
    static final int TEMP_DRIVER_UP = 32, TEMP_DRIVER_DOWN = 33;
    static final int TEMP_PASSENGER_UP = 34, TEMP_PASSENGER_DOWN = 35;
    static final int FAN_UP = 36, FAN_DOWN = 37;

    // Режим питания (AptivCarSettingFunction.getCurrentPowerMode)
    static final int POWER_OFF = 0, POWER_ACC = 1, POWER_ON = 2, POWER_CRANK = 3;

    // Сырое значение температуры за бортом (vendor property APTIV_OUTSIDE_TEMPERATURE)
    static final int PROP_OUTSIDE_TEMP_RAW = 0x21402039;

    // Длительность «нажатия» на кнопку стекла. Штатный экран шлёт 1 на нажатие и 0 на отпускание.
    private static final long PRESS_MS = 150;

    interface Listener {
        void onCarEvent(String what, int functionId, int value);
    }

    private final Context ctx;
    private AndroidCarClient androidClient;
    private AptivCarClient aptivClient;
    private AptivCarSettingFunction setting;
    private AptivCarHvacFunction hvacFn;
    private AptivCarHvac hvac;
    /** Громкость медиа (AudioManager.setStreamVolume реальную громкость не меняет). */
    private AptivCarAudio audio;
    /** День/ночь от автосвета машины; создаётся только при живой связи (иначе навсегда -1). */
    private AptivCarVariable variable;
    private volatile boolean ready;
    private Listener listener;

    Car(Context ctx) {
        this.ctx = ctx.getApplicationContext();
    }

    void setListener(Listener l) {
        listener = l;
    }

    boolean isReady() {
        return ready;
    }

    /** Подключиться к сервисам машины. Повторяет попытки до timeoutMs. */
    synchronized void connect(long timeoutMs) throws Exception {
        if (ready) return;
        long deadline = SystemClock.elapsedRealtime() + timeoutMs;
        Throwable last = null;
        if (androidClient == null) androidClient = new AndroidCarClient(ctx, null);
        if (aptivClient == null) aptivClient = new AptivCarClient(ctx, null);
        while (SystemClock.elapsedRealtime() < deadline) {
            try {
                if (setting == null) {
                    AptivCarSettingFunction s = new AptivCarSettingFunction(androidClient, aptivClient);
                    s.initFunction();
                    setting = s;
                }
                if (hvacFn == null) {
                    AptivCarHvacFunction h = new AptivCarHvacFunction(androidClient, aptivClient);
                    h.initFunction();
                    hvacFn = h;
                }
                if (hvac == null) hvac = new AptivCarHvac(androidClient);
                setting.getCurrentPowerMode(); // проверка, что связь есть
                if (variable == null) variable = new AptivCarVariable(androidClient);
                // Своим try: класса может не быть в этом билде — остальной мост должен работать.
                if (audio == null) {
                    try { audio = new AptivCarAudio(androidClient, aptivClient); }
                    catch (Throwable t) { Log.w(TAG, "AptivCarAudio: " + t); }
                }
                registerCallbacks();
                ready = true;
                Log.i(TAG, "car connected");
                return;
            } catch (Throwable t) {
                last = t;
                Log.w(TAG, "car connect retry: " + t);
                SystemClock.sleep(1000);
            }
        }
        throw new Exception("не удалось подключиться к сервисам машины: " + last, last);
    }

    private void registerCallbacks() {
        for (int id : new int[]{SEAT_DRIVER, SEAT_PASSENGER, WHEEL, POWER_MODE_FN, SEAT_MEMORY, SEAT_MEMORY_STATUS, BRIGHTNESS}) {
            try { setting.registerFunction(id); } catch (Throwable t) { Log.w(TAG, "registerFunction " + id + ": " + t); }
        }
        for (int id : new int[]{WINDSHIELD, REAR_WINDOW, TEMP_DRIVER, TEMP_PASSENGER, FAN,
                TEMP_DRIVER_SET, TEMP_PASSENGER_SET, FAN_SET,
                TEMP_DRIVER_UP, TEMP_DRIVER_DOWN, TEMP_PASSENGER_UP, TEMP_PASSENGER_DOWN, FAN_UP, FAN_DOWN}) {
            try { hvacFn.registerFunction(id); } catch (Throwable t) { Log.w(TAG, "registerFunction hvac " + id + ": " + t); }
        }
        try {
            setting.registerFunctionValueCallback(new AptivCarHvacSettingBase.FunctionValueCallback() {
                @Override public void onChangeEvent(int id, int value) { fire("setting.value", id, value); }
            });
            setting.registerFunctionStateCallback(new AptivCarHvacSettingBase.FunctionStateCallback() {
                @Override public void onChangeEvent(int id, int state) { fire("setting.state", id, state); }
            });
            hvacFn.registerFunctionValueCallback(new AptivCarHvacSettingBase.FunctionValueCallback() {
                @Override public void onChangeEvent(int id, int value) { fire("hvac.value", id, value); }
            });
            hvacFn.registerFunctionStateCallback(new AptivCarHvacSettingBase.FunctionStateCallback() {
                @Override public void onChangeEvent(int id, int state) { fire("hvac.state", id, state); }
            });
        } catch (Throwable t) {
            Log.w(TAG, "register callbacks: " + t);
        }
    }

    private void fire(String what, int id, int value) {
        Log.i(TAG, "event " + what + " id=" + id + " value=" + value);
        Listener l = listener;
        if (l != null) l.onCarEvent(what, id, value);
    }

    // ---------- чтение ----------

    int getValue(int id) throws Exception {
        return setting.getVehicleFunctionValue(id);
    }

    int getState(int id) throws Exception {
        return setting.getVehicleFunctionState(id);
    }

    int getPowerMode() throws Exception {
        return setting.getCurrentPowerMode();
    }

    int getBrightness() throws Exception {
        return setting.getVehicleFunctionValue(BRIGHTNESS);
    }

    /** Занятость слотов памяти сиденья: [0] — слот 1. 0 — слот пустой. */
    int[] seatMemoryStatus() throws Exception {
        int[] v = setting.getVehicleFunctionValueArray(SEAT_MEMORY_STATUS);
        return v == null ? new int[0] : v;
    }

    boolean isWindowHeatOn(int id) throws Exception {
        return hvacFn.getHvacFunctionValue(id) == 1;
    }

    int getHvacState(int id) throws Exception {
        return hvacFn.getHvacFunctionState(id);
    }

    /** Значение функции климата: температуры 16/17 (сырое = °C × 10), вентилятор 18. */
    int hvacValue(int id) throws Exception {
        return hvacFn.getHvacFunctionValue(id);
    }

    float getOutsideTemp() throws Exception {
        return hvac.getOutsideTemp();
    }

    int getOutsideTempRaw() throws Exception {
        return hvac.getPropertyValue(PROP_OUTSIDE_TEMP_RAW);
    }

    /** День/ночь по решению автосвета машины: 0 день, 1 ночь, -1 не прочитать. */
    int getDayNight() {
        try { return variable == null ? -1 : variable.getDayNightMode(); } catch (Throwable t) { return -1; }
    }

    /** Произвольное свойство по id — для диагностики. */
    int getPropertyRaw(int id) throws Exception {
        return hvac.getPropertyValue(id);
    }

    /** Состояние функции в читаемом виде: "state/reason" (см. FUNCTION_STATE_* в docs/gwm-api.md). */
    static String describeState(int raw) {
        try {
            return raw + " (state=" + AptivCarHvacSettingBase.getState(raw)
                    + ", reason=" + AptivCarHvacSettingBase.getReason(raw) + ")";
        } catch (Throwable t) {
            return String.valueOf(raw);
        }
    }

    /**
     * Можно ли сейчас управлять функцией. В машине 8 ноября: доступно — raw 64 (state=64, reason=0);
     * лобовое без запущенного двигателя — raw 21 (state=16, reason=5).
     */
    static boolean isAvailable(int raw) {
        try {
            return AptivCarHvacSettingBase.getReason(raw) == 0 && AptivCarHvacSettingBase.getState(raw) == 64;
        } catch (Throwable t) {
            return raw == 64;
        }
    }

    // ---------- громкость ----------

    private static final AptivCarAudio.VolumeGroup VG = AptivCarAudio.VolumeGroup.VG_MEDIA;

    /** Верхняя граница громкости медиа; -1 — не прочитать. */
    int volumeMax() {
        try {
            return audio == null ? -1 : audio.getGroupMaxVolume(VG);
        } catch (Throwable t) {
            Log.w(TAG, "volumeMax: " + t);
            return -1;
        }
    }

    /** Текущая громкость медиа; -1 — не прочитать. */
    int volume() {
        try {
            return audio == null ? -1 : audio.getGroupVolume(VG);
        } catch (Throwable t) {
            Log.w(TAG, "volume: " + t);
            return -1;
        }
    }

    /** Шаг громкости (энкодер панели). Возвращает строку для журнала. */
    String adjustVolume(int delta) {
        try {
            if (audio == null) return "громкость: машина не готова";
            return applyVolume(audio.getGroupVolume(VG) + delta);
        } catch (Throwable t) {
            return "громкость: ошибка " + t;
        }
    }

    /** Поставить громкость с clamp в границах машины. Возвращает строку для журнала. */
    String setVolume(int v) {
        try {
            if (audio == null) return "громкость: машина не готова";
            return applyVolume(v);
        } catch (Throwable t) {
            return "громкость: ошибка " + t;
        }
    }

    private String applyVolume(int v) throws Exception {
        int max = audio.getGroupMaxVolume(VG);
        int next = Math.max(0, Math.min(max, v));
        audio.setGroupVolume(VG, next);
        return "громкость=" + next + "/" + max;
    }

    // ---------- запись ----------

    void setSeat(int id, int level) throws Exception {
        if (level < 0 || level > 3) throw new IllegalArgumentException("уровень 0..3");
        Log.i(TAG, "setVehicleFunctionValue(" + id + ", " + level + ")");
        setting.setVehicleFunctionValue(id, level);
    }

    /** Вызвать сохранённое положение сиденья: n = 1..3 → значение функции 4/5/6. */
    int recallSeat(int n) throws Exception {
        if (n < 1 || n > 3) throw new IllegalArgumentException("пресет 1..3");
        Log.i(TAG, "setVehicleFunctionValue(" + SEAT_MEMORY + ", " + (n + 3) + ")");
        setting.setVehicleFunctionValue(SEAT_MEMORY, n + 3);
        return n;
    }

    /** Сохранить текущее положение сиденья в слот: n = 1..3 → значение функции 1/2/3. */
    int saveSeat(int n) throws Exception {
        if (n < 1 || n > 3) throw new IllegalArgumentException("пресет 1..3");
        Log.i(TAG, "setVehicleFunctionValue(" + SEAT_MEMORY + ", " + n + ")");
        setting.setVehicleFunctionValue(SEAT_MEMORY, n);
        return n;
    }

    /** Код результата сохранения: 1/3/5 успех, 2/4/6 неуспех, 7 — попробуйте снова. */
    int seatMemoryResult() throws Exception {
        return setting.getVehicleFunctionValue(SEAT_MEMORY_RESULT);
    }

    void setWheel(boolean on) throws Exception {
        Log.i(TAG, "setVehicleFunctionValue(" + WHEEL + ", " + (on ? 1 : 0) + ")");
        setting.setVehicleFunctionValue(WHEEL, on ? 1 : 0);
    }

    void setBrightness(int v) throws Exception {
        Log.i(TAG, "setVehicleFunctionValue(" + BRIGHTNESS + ", " + v + ")");
        setting.setVehicleFunctionValue(BRIGHTNESS, v);
    }

    /** Одно «нажатие» кнопки стекла: переключает состояние. */
    void pressWindow(int id) throws Exception {
        Log.i(TAG, "setHvacFunctionAction(" + id + ", 1/0)");
        hvacFn.setHvacFunctionAction(id, 1);
        SystemClock.sleep(PRESS_MS);
        hvacFn.setHvacFunctionAction(id, 0);
    }

    /** Записать функцию климата значением (38/39 температура, 40 вентилятор). */
    void setHvacValue(int id, int value) throws Exception {
        Log.i(TAG, "setHvacFunctionValue(" + id + ", " + value + ")");
        hvacFn.setHvacFunctionValue(id, value);
    }

    /** Абсолютная уставка водителя, как штатная шкала: 38 = °C×10 и сразу за ним кадр отпускания 38 = −10. */
    void setHvacTempAbsolute(int raw) throws Exception {
        Log.i(TAG, "setHvacFunctionValue(38, " + raw + ") + release -10");
        hvacFn.setHvacFunctionValue(TEMP_DRIVER_SET, raw);
        hvacFn.setHvacFunctionValue(TEMP_DRIVER_SET, -10);
    }

    /** Один шаг климата (32/33, 34/35, 36/37): импульс 1 → PRESS_MS → 0, как у стёкол. */
    void hvacStep(int id) throws Exception {
        Log.i(TAG, "setHvacFunctionAction(" + id + ", 1/0)");
        hvacFn.setHvacFunctionAction(id, 1);
        SystemClock.sleep(PRESS_MS);
        hvacFn.setHvacFunctionAction(id, 0);
    }

    /** Одиночный action климата без парного отпускания — для диагностики по id. */
    void hvacAction(int id, int v) throws Exception {
        Log.i(TAG, "setHvacFunctionAction(" + id + ", " + v + ")");
        hvacFn.setHvacFunctionAction(id, v);
    }

    /**
     * Привести обогрев стекла в нужное состояние: прочитать → «нажать» только если нужно →
     * дождаться подтверждения. Возвращает итоговое состояние.
     */
    boolean setWindow(int id, boolean on) throws Exception {
        if (isWindowHeatOn(id) == on) {
            Log.i(TAG, "window " + id + " already " + on);
            return on;
        }
        pressWindow(id);
        long deadline = SystemClock.elapsedRealtime() + 3000;
        while (SystemClock.elapsedRealtime() < deadline) {
            SystemClock.sleep(250);
            if (isWindowHeatOn(id) == on) return on;
        }
        return isWindowHeatOn(id);
    }
}
