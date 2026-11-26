package ru.knopych.bridge;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

/** Держит процесс живым и раз в 3 секунды запускает проверку автосценария. */
public class BridgeService extends Service {
    private static final long TICK_MS = 3000;
    /** Экран климата сам говорит, что показан (см. docs/gwm-api.md); Android 9 — без флагов. */
    private final BroadcastReceiver hvacRx = new BroadcastReceiver() {
        @Override public void onReceive(Context c, Intent i) {
            boolean visible = "com.gwmv3.hvac.VISIBLE".equals(i.getAction());
            Bridge.get(BridgeService.this).onClimateScreen(visible, i.getIntExtra("ISBACK", -1));
        }
    };
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable tick = new Runnable() {
        @Override public void run() {
            Bridge b = Bridge.get(BridgeService.this);
            b.tick();
            if (b.esp != null) try { b.esp.tick(); } catch (Throwable t) { android.util.Log.w(Bridge.TAG, "esp tick: " + t); }
            if (b.ble != null) try { b.ble.tick(); } catch (Throwable t) { android.util.Log.w(Bridge.TAG, "ble tick: " + t); }
            handler.postDelayed(this, TICK_MS);
        }
    };

    static void start(Context ctx) {
        ctx.startForegroundService(new Intent(ctx, BridgeService.class));
    }

    @Override
    public void onCreate() {
        super.onCreate();
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("bridge", "Кнопыч", NotificationManager.IMPORTANCE_MIN));
        Notification n = new Notification.Builder(this, "bridge")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("Кнопыч")
                .setContentText("мост подогревов работает")
                .build();
        startForeground(1, n);
        IntentFilter flt = new IntentFilter("com.gwmv3.hvac.VISIBLE");
        flt.addAction("com.gwmv3.hvac.INVISIBLE");
        registerReceiver(hvacRx, flt);
        final Bridge b = Bridge.get(this);
        b.note("сервис запущен, версия " + b.version());
        // Новое в v0.2 — в try: если сеть или USB не заведутся, подогревы и автосценарий работают как в v0.1
        try {
            if (b.net == null) {
                NetServer ns = new NetServer(b);
                ns.start();
                b.net = ns;
            }
        } catch (Throwable t) {
            b.note("сервер Wi-Fi не запустился: " + t);
        }
        try {
            if (b.esp == null) {
                EspLink e = new EspLink(this, b);
                e.start();
                b.esp = e;
            }
        } catch (Throwable t) {
            b.note("USB/ESP не запустилось: " + t);
        }
        try {
            if (b.ble == null) {
                BleLink l = new BleLink(this, b);
                l.start();
                b.ble = l;
            }
        } catch (Throwable t) {
            b.note("BLE не запустилось: " + t);
        }
        // adb по Wi-Fi из v0.2 на этом ГУ не работает — выключаем, если был включён
        WifiAdb.onStart(b, b.prefs());
        handler.post(tick);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacks(tick);
        try { unregisterReceiver(hvacRx); } catch (Throwable ignored) { }
        Bridge b = Bridge.get(this);
        if (b.esp != null) { b.esp.stop(); b.esp = null; }
        if (b.ble != null) { b.ble.stop(); b.ble = null; }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
