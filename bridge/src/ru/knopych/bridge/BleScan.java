package ru.knopych.bridge;

import android.Manifest;
import android.bluetooth.BluetoothAdapter;import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.SystemClock;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Проверка: даёт ли ГУ (свой стек Bluetooth Aptiv) приложениям сканировать BLE.
 * Нужна для будущей платы с рабочим BLE: если тут пусто — BLE на ГУ нам не помощник.
 */
final class BleScan {
    static String run(Context ctx, int seconds) {
        StringBuilder b = new StringBuilder();
        b.append("feature bluetooth_le=")
                .append(ctx.getPackageManager().hasSystemFeature(PackageManager.FEATURE_BLUETOOTH_LE)).append('\n');
        BluetoothAdapter a = BluetoothAdapter.getDefaultAdapter();
        if (a == null) return b.append("BluetoothAdapter нет").toString();
        b.append("bluetooth включён=").append(a.isEnabled()).append(" имя=").append(a.getName()).append('\n');
        BluetoothLeScanner sc = a.getBluetoothLeScanner();
        if (sc == null) return b.append("BLE-сканер недоступен (Bluetooth выключен?)").toString();
        final Map<String, String> found = new LinkedHashMap<>();
        final String[] err = {null};
        ScanCallback cb = new ScanCallback() {
            @Override public void onScanResult(int type, ScanResult r) {
                String name = r.getScanRecord() != null ? r.getScanRecord().getDeviceName() : null;
                synchronized (found) {
                    found.put(r.getDevice().getAddress(), (name == null ? "?" : name) + " rssi=" + r.getRssi());
                }
            }
            @Override public void onScanFailed(int code) { err[0] = "ошибка сканирования " + code; }
        };
        try {
            sc.startScan(cb);
        } catch (Throwable t) {
            return b.append("startScan: ").append(t).toString();
        }
        SystemClock.sleep(Math.max(1, Math.min(seconds, 30)) * 1000L);
        try { sc.stopScan(cb); } catch (Throwable ignored) { }
        if (err[0] != null) b.append(err[0]).append('\n');
        synchronized (found) {
            b.append("найдено: ").append(found.size()).append('\n');
            for (Map.Entry<String, String> e : found.entrySet()) b.append(e.getKey()).append(' ').append(e.getValue()).append('\n');
        }
        // рантайм-запрос не делаем: без разрешения на местоположение Android отдаёт пустой список
        if (ctx.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            b.append("внимание: разрешение на местоположение не выдано (и не запрошено) — пустой список может быть из-за этого\n");
        }
        return b.toString();
    }
}
