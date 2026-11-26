package aptiv.support.car;
// Заглушка только для компиляции: сигнатуры сняты с aptiv.support.car на ГУ (GwmSystemUI, VolumePresenter).
// В APK не попадает, на ГУ используется настоящая библиотека.
public class AptivCarAudio {
    public enum VolumeGroup { VG_MEDIA, VG_PROMPT, VG_PHONE, VG_RING, VG_NAVI, VG_NOTIFICATION }
    public AptivCarAudio(AndroidCarClient a, AptivCarClient b) { throw new RuntimeException("stub"); }
    public int getGroupVolume(VolumeGroup g) { throw new RuntimeException("stub"); }
    public int getGroupMaxVolume(VolumeGroup g) { throw new RuntimeException("stub"); }
    public int getGroupMinVolume(VolumeGroup g) { throw new RuntimeException("stub"); }
    public void setGroupVolume(VolumeGroup g, int index) { throw new RuntimeException("stub"); }
}
