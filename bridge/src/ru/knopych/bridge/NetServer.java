package ru.knopych.bridge;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageInstaller;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Collections;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Связь с Mac по Wi-Fi (общая точка доступа). Работает и без adb.
 *
 *   UDP 5577: на «knopych?» отвечает «knopych <версия> <порт>» — Mac находит ГУ сам.
 *   TCP 5577, простой HTTP, заголовок X-Token обязателен (кроме /ping):
 *     GET  /ping                 — проверка
 *     POST /cmd       тело «команда арг» — те же команды моста, что и tools/kn.py
 *     GET  /logcat?n=2000        — журнал logcat (только чтение)
 *     GET  /shot                 — скриншот экрана (PNG), для проверки вида глазами
 *     POST /install   тело — APK самого моста: ставится без вопросов на экране, мост перезапустится
 *
 * Произвольного shell здесь нет намеренно: для этого есть adb по Wi-Fi (wifi_adb on).
 * /install принимает только пакет ru.knopych.bridge; подпись при обновлении проверяет сам Android.
 * Подключения принимаются только из локальных сетей (10.*, 172.16–31.*, 192.168.*).
 * Токен генерируется один раз, виден на экране моста и по команде token.
 */
final class NetServer {
    static final int PORT = 5577;
    private static final String ACTION_INSTALL = "ru.knopych.bridge.INSTALL_RESULT";
    private static final long MAX_BODY = 50L * 1024 * 1024;

    private final Bridge bridge;
    private final Context ctx;
    private final SharedPreferences prefs;
    private volatile ServerSocket server;
    private volatile String lastClient = "-";

    NetServer(Bridge bridge) {
        this.bridge = bridge;
        this.ctx = bridge.ctx();
        this.prefs = bridge.prefs();
    }

    /** Токен вида 123-456: проще набрать с экрана ГУ. */
    String token() {
        String t = prefs.getString("net_token", null);
        if (t == null || !t.matches("\\d{3}-\\d{3}")) {
            SecureRandom r = new SecureRandom();
            t = String.format(Locale.US, "%03d-%03d", r.nextInt(1000), r.nextInt(1000));
            prefs.edit().putString("net_token", t).apply();
        }
        return t;
    }

    /** Токен с Mac принимается и без дефиса: 123456 = 123-456. */
    private boolean tokenOk(String given) {
        return given != null && digits(given).equals(digits(token()));
    }

    private static String digits(String s) {
        return s.replaceAll("[^0-9]", "");
    }

    void start() {
        token();
        ctx.registerReceiver(new BroadcastReceiver() {
            @Override public void onReceive(Context c, Intent i) {
                bridge.note("установка: status=" + i.getIntExtra(PackageInstaller.EXTRA_STATUS, -999)
                        + " " + i.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE));
            }
        }, new IntentFilter(ACTION_INSTALL));
        thread("net-tcp", this::tcpLoop);
        thread("net-udp", this::udpLoop);
    }

    private static void thread(String name, Runnable r) {
        Thread t = new Thread(r, name);
        t.setDaemon(true);
        t.start();
    }

    String describe() {
        StringBuilder b = new StringBuilder();
        b.append("сервер: ").append(server != null ? "порт " + PORT : "не запущен").append('\n');
        b.append("адреса: ").append(addresses()).append('\n');
        b.append("token=").append(token()).append('\n');
        b.append("последний клиент: ").append(lastClient).append('\n');
        b.append(WifiAdb.status(prefs));
        return b.toString();
    }

    /** IPv4-адреса ГУ, например «wlan0 192.168.43.12». */
    static String addresses() {
        StringBuilder b = new StringBuilder();
        try {
            for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!ni.isUp() || ni.isLoopback()) continue;
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address) {
                        if (b.length() > 0) b.append(", ");
                        b.append(ni.getName()).append(' ').append(a.getHostAddress());
                    }
                }
            }
        } catch (Throwable t) {
            return "ERR " + t;
        }
        return b.length() == 0 ? "нет сети" : b.toString();
    }

    private static boolean local(InetAddress a) {
        return a.isSiteLocalAddress() || a.isLoopbackAddress() || a.isLinkLocalAddress();
    }

    // ---------- UDP: поиск ГУ ----------

    private void udpLoop() {
        while (true) {
            try (DatagramSocket s = new DatagramSocket(null)) {
                s.setReuseAddress(true);
                s.bind(new InetSocketAddress(PORT));
                byte[] buf = new byte[64];
                while (true) {
                    DatagramPacket p = new DatagramPacket(buf, buf.length);
                    s.receive(p);
                    String q = new String(p.getData(), 0, p.getLength(), StandardCharsets.US_ASCII).trim();
                    if (q.equals("knopych?") && local(p.getAddress())) {
                        byte[] a = ("knopych " + bridge.version() + " " + PORT).getBytes(StandardCharsets.US_ASCII);
                        s.send(new DatagramPacket(a, a.length, p.getSocketAddress()));
                    }
                }
            } catch (Throwable t) {
                android.util.Log.w(Bridge.TAG, "udp: " + t);
                android.os.SystemClock.sleep(5000);
            }
        }
    }

    // ---------- TCP: HTTP ----------

    private void tcpLoop() {
        while (true) {
            try (ServerSocket ss = new ServerSocket()) {
                ss.setReuseAddress(true);
                ss.bind(new InetSocketAddress(PORT));
                server = ss;
                bridge.note("сервер Wi-Fi: порт " + PORT + ", " + addresses());
                while (true) {
                    final Socket s = ss.accept();
                    if (!local(s.getInetAddress())) { s.close(); continue; }
                    thread("net-client", () -> handle(s));
                }
            } catch (Throwable t) {
                server = null;
                android.util.Log.w(Bridge.TAG, "tcp: " + t);
                android.os.SystemClock.sleep(5000);
            }
        }
    }

    private void handle(Socket s) {
        try (Socket sock = s) {
            sock.setSoTimeout(60000);
            InputStream in = sock.getInputStream();
            OutputStream out = sock.getOutputStream();
            String reqLine = readLine(in);
            if (reqLine == null) return;
            String[] rl = reqLine.split(" ");
            if (rl.length < 2) return;
            String method = rl[0], target = rl[1];
            Map<String, String> h = new HashMap<>();
            String line;
            while ((line = readLine(in)) != null && !line.isEmpty()) {
                int c = line.indexOf(':');
                if (c > 0) h.put(line.substring(0, c).trim().toLowerCase(Locale.US), line.substring(c + 1).trim());
            }
            String path = target, query = "";
            int q = target.indexOf('?');
            if (q >= 0) { path = target.substring(0, q); query = target.substring(q + 1); }
            lastClient = sock.getInetAddress().getHostAddress() + " " + method + " " + path;

            if (path.equals("/ping")) {
                reply(out, 200, "pong knopych " + bridge.version());
                return;
            }
            if (!tokenOk(h.get("x-token"))) {
                reply(out, 403, "нужен заголовок X-Token (токен: на экране моста или команда token)");
                return;
            }
            long len = h.containsKey("content-length") ? Long.parseLong(h.get("content-length")) : 0;
            if (len > MAX_BODY) { reply(out, 413, "слишком большое тело"); return; }

            switch (method + " " + path) {
                case "POST /cmd": {
                    String body = new String(readBody(in, len), StandardCharsets.UTF_8).trim();
                    String[] p = body.split("\\s+", 2);
                    bridge.note("команда по сети: " + body);
                    String res = bridge.submit(p[0], p.length > 1 ? p[1] : null).get(60, TimeUnit.SECONDS);
                    reply(out, 200, res);
                    return;
                }
                case "GET /logcat": {
                    int n = 2000;
                    for (String kv : query.split("&")) if (kv.startsWith("n=")) n = Integer.parseInt(kv.substring(2));
                    reply(out, 200, logcat(n));
                    return;
                }
                case "GET /shot": {
                    byte[] png = screencap();
                    if (png == null) { reply(out, 500, "screencap не сработал (см. logcat)"); return; }
                    replyBytes(out, "image/png", png);
                    return;
                }
                case "POST /install": {
                    File f = new File(ctx.getCacheDir(), "update.apk");
                    try (FileOutputStream fo = new FileOutputStream(f)) {
                        copy(in, fo, len);
                    }
                    if (f.length() != len) { reply(out, 400, "APK пришёл не целиком"); return; }
                    PackageInfo pi = ctx.getPackageManager().getPackageArchiveInfo(f.getPath(), 0);
                    if (pi == null || !ctx.getPackageName().equals(pi.packageName)) {
                        reply(out, 400, "это не APK моста (" + (pi == null ? "не читается" : pi.packageName) + ")");
                        return;
                    }
                    bridge.note("установка по сети: " + pi.versionName + ", " + len + " байт");
                    reply(out, 200, "принято " + pi.versionName + " (" + len + " байт), ставлю."
                            + " Мост перезапустится — через ~10 с проверь версию.");
                    sock.close();
                    install(f);
                    return;
                }
                default:
                    reply(out, 404, "неизвестный путь: " + method + " " + path);
            }
        } catch (Throwable t) {
            android.util.Log.w(Bridge.TAG, "client: " + t);
        }
    }

    /**
     * Установка обновления. Мы работаем как system, поэтому ставим тем же путём, что и
     * «adb install -r» — командой `pm install -r` (она в машине уже проходила). Программный
     * PackageInstaller на ГУ упирается в «Package upgrade whitelist prevents installing»
     * (прошивка GWM запрещает так обновлять системные приложения), поэтому он только запасной.
     * Успешная установка себя убивает процесс — Android перезапустит по MY_PACKAGE_REPLACED.
     */
    private void install(File apk) {
        // Ровно как «adb install -r»: отдаём APK в `pm install -S <размер>` ПОТОКОМ (stdin).
        // Так системной службе не нужно читать наш приватный файл (её туда не пускает SELinux),
        // а путь через `pm` в машине уже проходил, в отличие от программного PackageInstaller
        // («Package upgrade whitelist prevents installing»).
        try {
            long size = apk.length();
            Process p = new ProcessBuilder("pm", "install", "-r", "-d", "-S", String.valueOf(size))
                    .redirectErrorStream(true).start();
            Thread writer = new Thread(() -> {
                try (OutputStream o = p.getOutputStream(); InputStream i = new FileInputStream(apk)) {
                    copy(i, o, size);
                } catch (Throwable t) {
                    android.util.Log.w(Bridge.TAG, "pm stdin: " + t);
                }
            });
            writer.start();
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            copy(p.getInputStream(), bo, Long.MAX_VALUE);
            p.waitFor(90, TimeUnit.SECONDS);
            writer.join(2000);
            String out = bo.toString("UTF-8").trim();
            bridge.note("pm install: " + out);
            if (out.contains("Success")) return; // процесс вот-вот будет убит системой
            bridge.note("pm install не удался, пробую PackageInstaller");
        } catch (Throwable t) {
            bridge.note("pm install: ошибка " + t + ", пробую PackageInstaller");
        }
        installViaSession(apk);
    }

    private void installViaSession(File apk) {
        try {
            PackageInstaller pi = ctx.getPackageManager().getPackageInstaller();
            PackageInstaller.SessionParams sp = new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
            sp.setAppPackageName(ctx.getPackageName());
            sp.setSize(apk.length());
            int id = pi.createSession(sp);
            try (PackageInstaller.Session s = pi.openSession(id)) {
                try (OutputStream o = s.openWrite("base.apk", 0, apk.length());
                     InputStream i = new FileInputStream(apk)) {
                    copy(i, o, apk.length());
                    s.fsync(o);
                }
                PendingIntent p = PendingIntent.getBroadcast(ctx, id,
                        new Intent(ACTION_INSTALL).setPackage(ctx.getPackageName()), 0);
                s.commit(p.getIntentSender());
            }
        } catch (Throwable t) {
            bridge.note("установка: ошибка " + t);
        }
    }

    // ---------- мелочи ----------

    private static String logcat(int n) {
        try {
            Process p = new ProcessBuilder("logcat", "-d", "-v", "threadtime", "-t", String.valueOf(n))
                    .redirectErrorStream(true).start();
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            copy(p.getInputStream(), bo, Long.MAX_VALUE);
            p.waitFor(10, TimeUnit.SECONDS);
            return bo.toString("UTF-8");
        } catch (Throwable t) {
            return "ERROR " + t;
        }
    }

    private static void reply(OutputStream out, int code, String body) throws Exception {
        byte[] b = (body.endsWith("\n") ? body : body + "\n").getBytes(StandardCharsets.UTF_8);
        String head = "HTTP/1.0 " + code + " X\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: "
                + b.length + "\r\nConnection: close\r\n\r\n";
        out.write(head.getBytes(StandardCharsets.US_ASCII));
        out.write(b);
        out.flush();
    }

    /** Скриншот экрана: screencap пишет PNG в stdout. Под uid 1000 чтение фреймбуфера разрешено. */
    private static byte[] screencap() {
        try {
            Process p = new ProcessBuilder("/system/bin/screencap", "-p")
                    .redirectErrorStream(false).start();
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            copy(p.getInputStream(), bo, Long.MAX_VALUE);
            int code = p.waitFor();
            if (code != 0 || bo.size() < 100) {
                android.util.Log.w(Bridge.TAG, "screencap: код " + code + ", " + bo.size() + " байт");
                return null;
            }
            return bo.toByteArray();
        } catch (Throwable t) {
            android.util.Log.w(Bridge.TAG, "screencap: " + t);
            return null;
        }
    }

    private static void replyBytes(OutputStream out, String type, byte[] body) throws Exception {
        String head = "HTTP/1.1 200 OK\r\nContent-Type: " + type
                + "\r\nContent-Length: " + body.length + "\r\nConnection: close\r\n\r\n";
        out.write(head.getBytes(StandardCharsets.UTF_8));
        out.write(body);
        out.flush();
    }

    private static String readLine(InputStream in) throws Exception {
        StringBuilder b = new StringBuilder();
        int c;
        while ((c = in.read()) != -1) {
            if (c == '\n') return b.toString();
            if (c != '\r') b.append((char) c);
            if (b.length() > 8192) throw new Exception("слишком длинная строка");
        }
        return b.length() == 0 ? null : b.toString();
    }

    private static byte[] readBody(InputStream in, long len) throws Exception {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        copy(in, bo, len);
        return bo.toByteArray();
    }

    private static void copy(InputStream in, OutputStream out, long len) throws Exception {
        byte[] buf = new byte[65536];
        long left = len;
        while (left > 0) {
            int n = in.read(buf, 0, (int) Math.min(buf.length, left));
            if (n < 0) break;
            out.write(buf, 0, n);
            left -= n;
        }
    }
}
