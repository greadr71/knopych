package ru.knopych.bridge;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.os.SystemClock;
import android.util.Log;

import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;

/**
 * Панель кнопок ESP32-S3 в USB-порту ГУ (ГУ — USB host).
 * Родной USB ESP32-S3 виден как «USB JTAG_serial debug unit» 303a:1001, класс CDC-ACM
 * (проверено с Mac 2026-11-08). Протокол — текстовые строки, см. docs/firmware.md:
 * плата шлёт «!btn N», мост шлёт «leds a b c d e f».
 *
 * Своя минимальная реализация CDC-ACM поверх UsbManager: найти интерфейс данных (класс 10),
 * два bulk-конца, выставить DTR/RTS как это делает Mac (pyserial). Открытие порта плату
 * не перезагружает, поэтому начинаем с ping/state, а не ждём !hello.
 */
final class EspLink implements Bridge.StateListener {
    static final int VID_ESPRESSIF = 0x303a;
    private static final String ACTION_PERM = "ru.knopych.bridge.USB_PERMISSION";

    private final Context ctx;
    private final Bridge bridge;
    private final UsbManager usb;
    private final ArrayDeque<String> lines = new ArrayDeque<>();

    private UsbDevice device;
    private UsbDeviceConnection conn;
    private UsbInterface dataIf;
    private UsbEndpoint in, out;
    private volatile boolean connected;
    private Thread reader;
    private String hello = "";
    private String lastLeds = "";
    private long lastScan;

    EspLink(Context ctx, Bridge bridge) {
        this.ctx = ctx.getApplicationContext();
        this.bridge = bridge;
        this.usb = (UsbManager) ctx.getSystemService(Context.USB_SERVICE);
    }

    void start() {
        IntentFilter f = new IntentFilter();
        f.addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED);
        f.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        f.addAction(ACTION_PERM);
        ctx.registerReceiver(new BroadcastReceiver() {
            @Override public void onReceive(Context c, Intent i) {
                UsbDevice d = i.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(i.getAction())) {
                    if (d != null && device != null && d.getDeviceName().equals(device.getDeviceName())) {
                        close("отключена");
                    }
                } else {
                    scanSoon();
                }
            }
        }, f);
        bridge.addListener(this);
        scanSoon();
    }

    /** Вызывается из тика сервиса раз в 3 с: найти плату, если её нет; заметить пропажу. */
    void tick() {
        if (connected) {
            if (device != null && !usb.getDeviceList().containsKey(device.getDeviceName())) close("пропала из списка USB");
            return;
        }
        if (SystemClock.elapsedRealtime() - lastScan > 3000) scanSoon();
    }

    private void scanSoon() {
        lastScan = SystemClock.elapsedRealtime();
        new Thread(this::scan, "esp-scan").start();
    }

    private synchronized void scan() {
        if (connected) return;
        for (UsbDevice d : usb.getDeviceList().values()) {
            if (d.getVendorId() == VID_ESPRESSIF) {
                try {
                    open(d);
                } catch (Throwable t) {
                    bridge.note("ESP: не открылась: " + t);
                }
                return;
            }
        }
    }

    private void open(UsbDevice d) throws Exception {
        if (!usb.hasPermission(d)) {
            // Мы android.uid.system (MANAGE_USB): выдаём себе доступ без вопроса на экране.
            try {
                UsbManager.class.getMethod("grantPermission", UsbDevice.class).invoke(usb, d);
            } catch (Throwable t) {
                Log.w(Bridge.TAG, "grantPermission: " + t);
            }
        }
        if (!usb.hasPermission(d)) {
            bridge.note("ESP: нет доступа к USB, спрашиваю на экране");
            usb.requestPermission(d, PendingIntent.getBroadcast(ctx, 0,
                    new Intent(ACTION_PERM).setPackage(ctx.getPackageName()), 0));
            return;
        }
        UsbInterface data = null, comm = null;
        for (int i = 0; i < d.getInterfaceCount(); i++) {
            UsbInterface f = d.getInterface(i);
            if (f.getInterfaceClass() == UsbConstants.USB_CLASS_CDC_DATA && data == null) data = f;
            if (f.getInterfaceClass() == UsbConstants.USB_CLASS_COMM && comm == null) comm = f;
        }
        if (data == null) throw new Exception("нет CDC-интерфейса данных: " + describeDevice(d));
        UsbEndpoint ein = null, eout = null;
        for (int i = 0; i < data.getEndpointCount(); i++) {
            UsbEndpoint e = data.getEndpoint(i);
            if (e.getType() != UsbConstants.USB_ENDPOINT_XFER_BULK) continue;
            if (e.getDirection() == UsbConstants.USB_DIR_IN) ein = e; else eout = e;
        }
        if (ein == null || eout == null) throw new Exception("нет bulk-концов");
        UsbDeviceConnection c = usb.openDevice(d);
        if (c == null) throw new Exception("openDevice вернул null");
        if (!c.claimInterface(data, true)) { c.close(); throw new Exception("claimInterface не удался"); }
        if (comm != null) {
            c.claimInterface(comm, true);
            int idx = comm.getId();
            // SET_LINE_CODING 115200 8N1 (для JTAG-порта не важно, но вреда нет)
            byte[] lc = {0x00, (byte) 0xC2, 0x01, 0x00, 0, 0, 8};
            c.controlTransfer(0x21, 0x20, 0, idx, lc, lc.length, 500);
            // SET_CONTROL_LINE_STATE: DTR=1, RTS=1 — как pyserial на Mac (плату не перезагружает)
            c.controlTransfer(0x21, 0x22, 0x03, idx, null, 0, 500);
        }
        device = d; conn = c; dataIf = data; in = ein; out = eout;
        connected = true;
        lastLeds = "";
        bridge.note("ESP: подключена " + describeDevice(d));
        reader = new Thread(this::readLoop, "esp-read");
        reader.start();
        send("ping");
        onState(bridge.state()); // сразу показать реальное состояние
        bridge.refreshSoon();
    }

    private void readLoop() {
        byte[] buf = new byte[512];
        StringBuilder line = new StringBuilder();
        UsbDeviceConnection c = conn;
        UsbEndpoint e = in;
        while (connected && c == conn) {
            int n = c.bulkTransfer(e, buf, buf.length, 300);
            if (n <= 0) continue; // таймаут — нормально
            for (int i = 0; i < n; i++) {
                char ch = (char) (buf[i] & 0xff);
                if (ch == '\n') {
                    handle(line.toString().trim());
                    line.setLength(0);
                } else if (ch != '\r' && line.length() < 400) {
                    line.append(ch);
                }
            }
        }
    }

    private void handle(String s) {
        if (s.isEmpty()) return;
        synchronized (lines) {
            lines.addLast(s);
            while (lines.size() > 30) lines.removeFirst();
        }
        if (s.startsWith("!btn ")) {
            try {
                int n = Integer.parseInt(s.substring(5).trim());
                bridge.onEspButton(n);
            } catch (NumberFormatException ignored) {
            }
        } else if (s.startsWith("!long ")) {
            try {
                int n = Integer.parseInt(s.substring(6).trim());
                bridge.onEspLong(n);
            } catch (NumberFormatException ignored) {
            }
        } else if (s.startsWith("!vol ")) {
            try {
                bridge.onEspVolume(Integer.parseInt(s.substring(5).trim()));
            } catch (NumberFormatException ignored) {
            }
        } else if (s.startsWith("!vbtn ")) {
            try {
                bridge.onEspVbtn(Integer.parseInt(s.substring(6).trim()));
            } catch (NumberFormatException ignored) {
            }
        } else if (s.startsWith("!hello") || s.startsWith("!pong")) {
            hello = s;
            if (s.startsWith("!hello")) { // плата перезагрузилась — светодиоды заново
                lastLeds = "";
                onState(bridge.state());
            }
        }
    }

    /** Светодиоды в порядке кнопок панели: пресет 1..3, сиденье вод., лобовое, сиденье пасс. */
    @Override
    public void onState(Bridge.State st) {
        if (!connected || st == null || st.time == 0) return;
        String cmd = ledsCmd(levels(st));
        if (cmd.equals(lastLeds)) return;
        lastLeds = cmd;
        send(cmd);
    }

    /**
     * Отправить уровни как есть, минуя сравнение с последним отправленным (мигание кнопки).
     * Кэш всё равно обновляем, иначе следующее состояние не совпадёт с платой.
     */
    synchronized void sendLevels(int[] lv) {
        if (!connected) return;
        lastLeds = ledsCmd(lv);
        send(lastLeds);
    }

    private static String ledsCmd(int[] lv) {
        return "leds " + lv[0] + " " + lv[1] + " " + lv[2] + " " + lv[3] + " " + lv[4] + " " + lv[5];
    }

    /** Шесть ступеней 0..3 в порядке кнопок панели — общая раскладка для USB и BLE. */
    static int[] levels(Bridge.State st) {
        return new int[] { preset(st, 0), preset(st, 1), preset(st, 2),
                lv(st.seatDriver), lv(st.windshield), lv(st.seatPassenger) };
    }

    /**
     * Слот памяти: сама машина отдаёт три состояния — 0 пусто, 1 сохранено, 2 сохранено и сейчас
     * активно (штатный UI рисует 2 как «включено», 1 как «сохранено»). Горит только активный слот;
     * пустой, неактивный или не прочитавшийся — 0.
     */
    private static int preset(Bridge.State st, int i) {
        return st.seatMemory != null && i < st.seatMemory.length && st.seatMemory[i] == 2 ? 1 : 0;
    }

    private static int lv(int v) { return v < 0 ? 0 : v; }

    synchronized void send(String s) {
        if (!connected) return;
        byte[] b = (s + "\n").getBytes(StandardCharsets.US_ASCII);
        int n = conn.bulkTransfer(out, b, b.length, 500);
        if (n < 0) Log.w(Bridge.TAG, "ESP send failed: " + s);
    }

    boolean isConnected() { return connected; }

    /** Перед остановкой моста: вернуть плату в local, чтобы кнопки работали сами. */
    void stop() {
        if (connected) send("local");
        close("мост остановлен");
    }

    private synchronized void close(String why) {
        if (!connected && conn == null) return;
        connected = false;
        try { if (conn != null) { conn.releaseInterface(dataIf); conn.close(); } } catch (Throwable ignored) { }
        conn = null; device = null;
        bridge.note("ESP: " + why);
    }

    String describe() {
        StringBuilder b = new StringBuilder();
        b.append("ESP: ").append(connected ? "подключена " + describeDevice(device) : "нет").append('\n');
        b.append("hello: ").append(hello).append('\n');
        b.append("последние leds: ").append(lastLeds).append('\n');
        b.append("от платы:\n");
        synchronized (lines) { for (String s : lines) b.append("  ").append(s).append('\n'); }
        return b.toString();
    }

    static String describeDevice(UsbDevice d) {
        if (d == null) return "-";
        String name = "";
        try { name = d.getManufacturerName() + " / " + d.getProductName(); } catch (Throwable ignored) { }
        return String.format("%04x:%04x %s %s", d.getVendorId(), d.getProductId(), d.getDeviceName(), name);
    }

    static String listDevices(Context ctx) {
        UsbManager u = (UsbManager) ctx.getSystemService(Context.USB_SERVICE);
        StringBuilder b = new StringBuilder();
        boolean host = ctx.getPackageManager().hasSystemFeature("android.hardware.usb.host");
        b.append("usb host feature=").append(host).append('\n');
        if (u == null) return b.append("UsbManager нет").toString();
        if (u.getDeviceList().isEmpty()) b.append("устройств нет (порт в режиме peripheral? usb mode → host)\n");
        for (UsbDevice d : u.getDeviceList().values()) {
            b.append(describeDevice(d)).append(" доступ=").append(u.hasPermission(d)).append('\n');
            for (int i = 0; i < d.getInterfaceCount(); i++) {
                UsbInterface f = d.getInterface(i);
                b.append("  if").append(f.getId()).append(" class=").append(f.getInterfaceClass())
                        .append(" ep=").append(f.getEndpointCount()).append('\n');
            }
        }
        return b.toString();
    }
}
