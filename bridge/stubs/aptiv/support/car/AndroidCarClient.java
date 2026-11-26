package aptiv.support.car;
// Заглушки только для компиляции: сигнатуры сняты с aptiv.support.car.vdex на ГУ.
// В APK они не попадают, на ГУ используется настоящая библиотека.
public class AndroidCarClient {
    public interface AndroidCarClientListener {
        void onAndroidCarConnected();
        void onAndroidCarDisconnected();
    }
    public AndroidCarClient(android.content.Context c, android.os.Handler h) { throw new RuntimeException("stub"); }
    public void registerListener(AndroidCarClientListener l) { throw new RuntimeException("stub"); }
    public void registerDeathRecipient(android.os.IBinder.DeathRecipient r) { throw new RuntimeException("stub"); }
}
