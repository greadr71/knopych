package aptiv.support.car;
public abstract class AptivCarHvacSettingBase {
    public interface FunctionStateCallback { void onChangeEvent(int functionId, int state); }
    public interface FunctionValueCallback { void onChangeEvent(int functionId, int value); }
    public static int getState(int raw) { throw new RuntimeException("stub"); }
    public static int getReason(int raw) { throw new RuntimeException("stub"); }
    public void registerFunctionStateCallback(FunctionStateCallback c) { throw new RuntimeException("stub"); }
    public void registerFunctionValueCallback(FunctionValueCallback c) { throw new RuntimeException("stub"); }
}
