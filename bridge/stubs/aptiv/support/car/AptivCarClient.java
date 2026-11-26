package aptiv.support.car;
public class AptivCarClient {
    public interface AptivCarClientListener {
        void onAptivCarConnected();
        void onAptivCarDisconnected();
    }
    public AptivCarClient(android.content.Context c, android.os.Handler h) { throw new RuntimeException("stub"); }
    public void registerListener(AptivCarClientListener l) { throw new RuntimeException("stub"); }
    public void registerDeathRecipient(android.os.IBinder.DeathRecipient r) { throw new RuntimeException("stub"); }
}
