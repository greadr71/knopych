package ru.knopych.bridge;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import java.util.concurrent.TimeUnit;

/**
 * Команды снаружи (adb, MacroDroid «Send Intent», позже — BLE/USB от ESP).
 *
 *   adb shell am broadcast -a ru.knopych.bridge.CMD -n ru.knopych.bridge/.CommandReceiver --es cmd status
 *   ... --es cmd seat_driver --es arg 3
 *
 * Ответ возвращается как result data (его печатает am broadcast) и пишется в logcat с тегом Knopych.
 */
public class CommandReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        BridgeService.start(ctx);
        final String cmd = intent.getStringExtra("cmd");
        final String arg = intent.getStringExtra("arg");
        final PendingResult pr = goAsync();
        final Bridge bridge = Bridge.get(ctx);
        bridge.note("команда: " + cmd + (arg != null ? " " + arg : ""));
        new Thread(() -> {
            String res;
            try {
                res = bridge.submit(cmd, arg).get(50, TimeUnit.SECONDS);
            } catch (Throwable t) {
                res = "ERROR " + t;
            }
            bridge.note("ответ:\n" + res);
            pr.setResultCode(res.startsWith("ERROR") ? 1 : 0);
            pr.setResultData(res);
            pr.finish();
        }).start();
    }
}
