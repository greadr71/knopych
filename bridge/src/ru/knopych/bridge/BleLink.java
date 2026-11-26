package ru.knopych.bridge;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothProfile;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.SystemClock;

import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.UUID;

/**
 * Панель по BLE: GATT-клиент, подключение по MAC (без скана — не нужен ACCESS_FINE_LOCATION).
 *
 * Протокол тот же, что по USB:
 *   сервис  6d656368-6275-7474-0001-000000000000;
 *   BUTTONS …-0002 read+notify, ASCII «btn N» / «long N» (без «!» — его добавляет только USB).
 * Сопряжения нет, характеристики без шифрования.
 *
 * Подключение: connectGatt(autoConnect=true) — стек сам ждёт плату и переподключает;
 * плюс повтор из тика сервиса (BridgeService, 3 с), если GATT закрыт после ошибки
 * (status 133 — обычный сбой первого коннекта на Android).
 */
final class BleLink {
    private static final UUID SERVICE = UUID.fromString("6d656368-6275-7474-0001-000000000000");
    private static final UUID BUTTONS = UUID.fromString("6d656368-6275-7474-0002-000000000000");
    private static final UUID CCCD = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
    /** Ключ в тех же prefs («bridge»), что и остальные настройки. Пусто = BLE выключен. */
    static final String PREF_MAC = "ble_mac";
    /** Пауза между попытками: тик 3 с, поэтому на деле раз в 6 с. */
    private static final long RETRY_MS = 5000;
    /**
     * Сколько ждать autoConnect, прежде чем признать его зависшим.
     * На Android 9 после перезагрузки ГУ (и после включения/выключения радио) ожидающее
     * соединение иногда не даёт вообще ни одного колбэка: gatt != null, connected = false,
     * и tick() без этого срока не переподключается. На машине 21 ноября после повторного
     * включения авто панель так и не подключилась, и в журнале не было ни строки про BLE.
     */
    private static final long PENDING_MS = 20000;

    private final Context ctx;
    private final Bridge bridge;
    private final SharedPreferences prefs;

    private volatile BluetoothGatt gatt;
    private volatile BluetoothGattCharacteristic chButtons;
    private volatile boolean connected;
    /** notify включён: CCCD записан успешно. Только тогда кнопки реально дойдут. */
    private volatile boolean notifyOn;
    private volatile int lastStatus = -1;
    private volatile long lastAttempt;

    BleLink(Context ctx, Bridge bridge) {
        this.ctx = ctx.getApplicationContext();
        this.bridge = bridge;
        this.prefs = bridge.prefs();
    }

    String mac() { return prefs.getString(PREF_MAC, ""); }

    void start() {
        if (!mac().isEmpty()) connect();
    }

    /** Тик сервиса (главный поток, раз в 3 с): после разрыва подключаемся заново. */
    void tick() {
        if (connected || mac().isEmpty()) return;
        long now = SystemClock.elapsedRealtime();
        if (gatt != null) {
            // autoConnect вернул объект, но колбэков нет — считаем попытку сдохшей и начинаем заново
            if (now - lastAttempt < PENDING_MS) return;
            bridge.note("BLE: " + PENDING_MS / 1000 + " с без ответа на autoConnect — переподключаюсь");
            close("нет ответа на autoConnect");
        } else if (now - lastAttempt < RETRY_MS) {
            return;
        }
        connect();
    }

    /** ble_mac <MAC> — запомнить и подключиться; пусто — выключить BLE. */
    synchronized String setMac(String arg) {
        String m = arg == null ? "" : arg.trim().toUpperCase(Locale.US);
        if (!m.isEmpty() && !BluetoothAdapter.checkBluetoothAddress(m)) {
            return "BLE: это не MAC: " + arg + " (нужно AA:BB:CC:DD:EE:FF)";
        }
        prefs.edit().putString(PREF_MAC, m).apply();
        close("MAC изменён");
        if (!m.isEmpty()) connect();
        return describe();
    }

    private synchronized void connect() {
        if (mac().isEmpty() || gatt != null) return;
        BluetoothAdapter a = BluetoothAdapter.getDefaultAdapter();
        if (a == null || !a.isEnabled()) return; // нечего делать без радио, в describe видно почему
        lastAttempt = SystemClock.elapsedRealtime();
        try {
            BluetoothDevice d = a.getRemoteDevice(mac());
            // autoConnect: стек ждёт плату сам и переподключает после разрыва,
            // поэтому connectGatt не «сдаётся» через 30 с, а висит до появления платы.
            gatt = d.connectGatt(ctx, true, cb);
            if (gatt == null) bridge.note("BLE: connectGatt вернул null");
        } catch (Throwable t) {
            bridge.note("BLE: не подключилась: " + t);
        }
    }

    synchronized void close(String why) {
        BluetoothGatt g = gatt;
        gatt = null;
        chButtons = null;
        boolean was = connected;
        connected = false;
        notifyOn = false;
        if (g != null) {
            try { g.disconnect(); } catch (Throwable ignored) { }
            try { g.close(); } catch (Throwable ignored) { }
        }
        if (was) bridge.note("BLE: " + why);
    }

    void stop() {
        close("мост остановлен");
    }

    private final BluetoothGattCallback cb = new BluetoothGattCallback() {
        @Override public void onConnectionStateChange(BluetoothGatt g, int status, int newState) {
            handleConnection(g, status, newState);
        }

        @Override public void onServicesDiscovered(BluetoothGatt g, int status) {
            handleServices(g, status);
        }

        @Override public void onDescriptorWrite(BluetoothGatt g, BluetoothGattDescriptor d, int status) {
            handleDescriptor(g, d, status);
        }

        @Override public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic c) {
            if (!BUTTONS.equals(c.getUuid())) return;
            byte[] v = c.getValue();
            if (v != null) handleLine(new String(v, StandardCharsets.US_ASCII).trim());
        }
    };

    private synchronized void handleConnection(BluetoothGatt g, int status, int newState) {
        if (g != gatt) { g.close(); return; } // колбэк от старого соединения
        lastStatus = status;
        if (newState == BluetoothProfile.STATE_CONNECTED && status == BluetoothGatt.GATT_SUCCESS) {
            connected = true;
            bridge.note("BLE: подключена " + mac());
            // без сервисов канал мёртв: не оставляем «подключена» навсегда — закрываем и ждём tick()
            if (!g.discoverServices()) close("discoverServices не принят");
            return;
        }
        connected = false;
        notifyOn = false;
        chButtons = null;
        bridge.note("BLE: отключена (status=" + status + ")");
        gatt = null;
        try { g.disconnect(); } catch (Throwable ignored) { }
        try { g.close(); } catch (Throwable ignored) { } // иначе течёт fd; переподключение — из tick()
        lastAttempt = SystemClock.elapsedRealtime();
    }

    private synchronized void handleServices(BluetoothGatt g, int status) {
        if (g != gatt) return;
        // любой сбой setup закрывает соединение: иначе tick() видит connected и не переподключается
        if (status != BluetoothGatt.GATT_SUCCESS) {
            close("discoverServices status=" + status);
            return;
        }
        BluetoothGattService s = g.getService(SERVICE);
        if (s == null) {
            close("сервис не найден");
            return;
        }
        chButtons = s.getCharacteristic(BUTTONS);
        if (chButtons == null) {
            close("не нашла BUTTONS");
            return;
        }
        g.setCharacteristicNotification(chButtons, true);
        BluetoothGattDescriptor d = chButtons.getDescriptor(CCCD);
        if (d == null) {
            close("у BUTTONS нет CCCD (notify не включить)");
            return;
        }
        d.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
        if (!g.writeDescriptor(d)) close("writeDescriptor не принят");
    }

    private synchronized void handleDescriptor(BluetoothGatt g, BluetoothGattDescriptor d, int status) {
        if (g != gatt || !CCCD.equals(d.getUuid())) return;
        if (status != BluetoothGatt.GATT_SUCCESS) {
            close("notify не включился (status=" + status + ")");
            return;
        }
        notifyOn = true;
        bridge.note("BLE: notify на BUTTONS включён");
        bridge.refreshSoon();
    }

    /** «btn N» / «long N» / «vol N» из BLE — в те же обработчики, что и у USB (EspLink.handle). */
    private void handleLine(String s) {
        if (s.startsWith("btn ")) {
            try { bridge.onEspButton(Integer.parseInt(s.substring(4).trim())); } catch (NumberFormatException ignored) { }
        } else if (s.startsWith("long ")) {
            try { bridge.onEspLong(Integer.parseInt(s.substring(5).trim())); } catch (NumberFormatException ignored) { }
        } else if (s.startsWith("vol ")) {
            try { bridge.onEspVolume(Integer.parseInt(s.substring(4).trim())); } catch (NumberFormatException ignored) { }
        } else if (s.startsWith("vbtn ")) {
            try { bridge.onEspVbtn(Integer.parseInt(s.substring(5).trim())); } catch (NumberFormatException ignored) { }
        }
    }

    String describe() {
        String m = mac();
        StringBuilder b = new StringBuilder();
        if (m.isEmpty()) b.append("BLE: нет MAC (ble_mac AA:BB:CC:DD:EE:FF)");
        else if (connected) b.append("BLE: подключена ").append(m);
        else b.append("BLE: не подключена (status=").append(lastStatus).append(')');
        b.append('\n').append("MAC: ").append(m.isEmpty() ? "-" : m).append('\n');
        BluetoothAdapter a = BluetoothAdapter.getDefaultAdapter();
        b.append("bluetooth: ").append(a == null ? "нет" : a.isEnabled() ? "включён" : "выключен").append('\n');
        b.append("notify: ").append(notifyOn ? "да" : "нет");
        return b.toString();
    }
}
