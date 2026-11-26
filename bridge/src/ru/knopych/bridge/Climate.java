package ru.knopych.bridge;

import android.app.ActivityManager;
import android.content.Context;
import android.os.SystemClock;

import java.util.List;

/**
 * Крутилка панели как управление климатом, пока открыт экран климата.
 *
 * Экран сам сообщает о себе (com.gwmv3.hvac.VISIBLE/INVISIBLE), поэтому режим включается и тогда,
 * когда климат открыли штатной кнопкой. Климат закрыт — кнопка открывает экран, вращение крутит громкость.
 * Климат открыт — вращение меняет температуру; с нажатой кнопкой — вентилятор; короткое нажатие закрывает экран.
 *
 * Вызывается из потоков USB и BLE одновременно, поэтому всё под synchronized: состояние одно.
 * К машине отсюда не ходим — шаги выполняет Bridge в своей очереди.
 */
final class Climate {
    /** Штатный экран климата: если он не сверху, режим выключаем сторожевым тиком. */
    private static final String HVAC_ACTIVITY = "com.gwmv3.vehicle.screen.hvac.HvacActivity";
    /** Короче этого отпускание считается коротким нажатием и закрывает экран. */
    private static final long HOLD_MS = 600;
    /** Панель шлёт одно событие в USB и BLE: кнопку склеиваем по времени отдельно нажатие/отпускание. */
    private static final long DUP_VBTN_MS = 120;
    /** То же для вращения — по совпадению delta. */
    private static final long DUP_VOL_MS = 60;
    /** После закрытия экрана вращение какое-то время игнорируем: иначе хвост климата уводит громкость. */
    private static final long MUTE_MS = 400;
    /** Продление экрана не чаще раза в 500 мс — при вращении шаги идут чаще. */
    private static final long REFRESH_MS = 500;

    private final Bridge bridge;
    private boolean visible;
    private boolean pressed;
    private long pressAt;
    /** Климат был открыт в момент нажатия: только такое нажатие закрывает экран на отпускании. */
    private boolean pressArmed;
    /** При нажатой кнопке крутили: такое нажатие экран не закрывает — оно уже меняло вентилятор. */
    private boolean turned;
    private long muteUntil;
    private long lastDownAt, lastUpAt;
    private long lastVolAt;
    private int lastVolDelta;
    private long lastRefreshAt;

    Climate(Bridge bridge) {
        this.bridge = bridge;
    }

    /** VISIBLE/INVISIBLE от штатного экрана климата. */
    synchronized void onScreen(boolean v) {
        visible = v;
        if (!v) {
            pressed = false; // экран гаснет сам — кнопка «отпущена» без события от панели
            muteUntil = SystemClock.elapsedRealtime() + MUTE_MS;
        }
    }

    /** Кнопка энкодера: 1 нажата, 0 отпущена (vbtn из USB и BLE). */
    synchronized void onVbtn(int v) {
        long now = SystemClock.elapsedRealtime();
        if (v == 1) {
            if (now - lastDownAt < DUP_VBTN_MS) return;
            lastDownAt = now;
            pressed = true;
            pressAt = now;
            pressArmed = visible;
            turned = false;
            if (!visible) bridge.climateOpen();
            return;
        }
        if (now - lastUpAt < DUP_VBTN_MS) return;
        lastUpAt = now;
        pressed = false;
        // короткое нажатие без вращения — закрыть экран; нажатие, которым климат открыли, ничего не делает
        if (pressArmed && !turned && now - pressAt < HOLD_MS) bridge.climateClose();
        pressArmed = false;
    }

    /** Вращение на delta щелчков: климат открыт и кнопка нажата — вентилятор, климат открыт — температура, иначе громкость. */
    synchronized void onVolume(int delta) {
        long now = SystemClock.elapsedRealtime();
        if (now < muteUntil) return;
        if (now - lastVolAt < DUP_VOL_MS && delta == lastVolDelta) return;
        lastVolAt = now;
        lastVolDelta = delta;
        if (!visible) bridge.volumeStep(delta);
        else if (pressed) {
            turned = true;
            bridge.climateFan(delta);
        } else bridge.climateTemp(delta);
    }

    /** Продлить экран на 8 с (шаг климата), не чаще раза в 500 мс. */
    synchronized void refreshScreen() {
        long now = SystemClock.elapsedRealtime();
        if (now - lastRefreshAt < REFRESH_MS) return;
        lastRefreshAt = now;
        bridge.climateRefresh();
    }

    /** Сторожевой тик (поток worker): климат открыт, а сверху уже другой экран — режим выключаем. */
    synchronized void onTick() {
        if (!visible) return;
        String top = topActivity();
        if (top == null || HVAC_ACTIVITY.equals(top)) return; // не узнать — считаем, что климат сверху
        visible = false;
        pressed = false;
        bridge.note("климат: сверху " + top + " — режим климата выключен");
    }

    /** Класс верхней активности; null — не прочитать (тогда режим не гасим). */
    private String topActivity() {
        try {
            ActivityManager am = (ActivityManager) bridge.ctx().getSystemService(Context.ACTIVITY_SERVICE);
            List<ActivityManager.RunningTaskInfo> t = am.getRunningTasks(1);
            if (t == null || t.isEmpty() || t.get(0).topActivity == null) return null;
            return t.get(0).topActivity.getClassName();
        } catch (Throwable t) {
            return null;
        }
    }

    /** Строка состояния для диагностики `climate`. */
    synchronized String describe() {
        return "экран: " + (visible ? "виден" : "скрыт") + ", кнопка: " + (pressed ? "нажата" : "отпущена");
    }
}
