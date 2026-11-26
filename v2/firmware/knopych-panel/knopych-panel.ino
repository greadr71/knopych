// Knopych panel — прошивка на Arduino (v1.0)
// Плата: Waveshare ESP32-S3-Zero (4 МБ флеш, 2 МБ PSRAM). Подробности: ../../../docs/hardware.md
//  - 6 кнопок (GPIO 1,2,4,7,6,5); светодиоды кнопок прошивка не использует:
//    их пины (11, 12, 44) не настраиваются вообще и остаются входами, чтобы не светились;
//  - кнопки только шлют события: !btn N и !long N. Ступени/состояние кнопок хранит Mac/ГУ;
//  - долгое удержание (1,5 с) кнопок 1..3 — сохранение положения сиденья в слот (делает Mac/ГУ),
//    кнопки 4 — яркость экрана ГУ в другой край (макс <-> мин);
//  - энкодер громкости: A -> GPIO9, B -> GPIO10, кнопка энкодера D -> GPIO13, событие vbtn 0/1;
//  - Wi-Fi НЕ включается никогда: WiFi.h не подключаем;
//  - связь с Mac / ГУ по USB (основной вариант сейчас): текстовые строки, см. README.md.
//    Строки протокола начинаются с "!", всё остальное — журнал для человека.
//    Один порт: нативный USB-Serial/JTAG (Serial);
//  - Bluetooth LE (USE_BLE): включён, MAC печатается в журнал при старте;
//  - встроенный WS2812 (GPIO 21) — только короткий индикатор связи, постоянного свечения нет:
//    зелёный 3 с после подключения BLE, синее мигание 0,5/0,5 с первые 60 с рекламы, иначе погашен.
// Кнопки и энкодер шлют те же строки, что MicroPython-версия ../../../v1/micropython/;
// LED-команды (leds/local/state) остались только у архивной v1 — здесь их нет.
// Команды по USB: ping -> pong knopych <версия>.

#include <esp_system.h>

#define VERSION "v1.0"

// Bluetooth. Включить: 1 и прошить заново.
#define USE_BLE 1

#if USE_BLE
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#endif

// ---------- Пины и кнопки ----------
const uint8_t N = 6;
const uint8_t BTN[N] = {1, 2, 4, 7, 6, 5};
// Пины 43/44 — UART0, но UART0 не используем (журнал через USB CDC).

// Энкодер громкости ALPS EC11E15244G1: A -> 9, B -> 10, C -> GND.
// кнопка энкодера D -> GPIO13
const uint8_t ENC_A = 9;
const uint8_t ENC_B = 10;
const uint8_t ENC_SW = 13;
const uint8_t ENC_TRANSITIONS_PER_DETENT = 2;  // 30 щелчков/оборот, 4 перехода на импульс, 15 импульсов => 2 на щелчок
#define ENC_INVERT 0  // 1 — если на машине шаги идут не в ту сторону (провода перепаивать не нужно)

const uint8_t RGB_PIN = 21;    // встроенный WS2812 на ESP32-S3-Zero
const uint8_t RGB_BRIGHT = 20; // 0..255, держим низко: меньше ток

const uint32_t POLL_MS = 5;
const uint8_t DEBOUNCE_SAMPLES = 10;  // 10 x 5 мс = 50 мс стабильного сигнала
const uint32_t RGB_EVERY = 100;      // 100 x 5 мс = раз в 0,5 с
const uint32_t RGB_BLINK_MS = RGB_EVERY * POLL_MS;  // половина периода мигания

// У кого есть долгое удержание (индекс = кнопка - 1): 1..3 — слоты памяти сиденья, 4 — яркость ГУ.
const bool HOLD[N] = {true, true, true, true, false, false};
const uint32_t HOLD_MS = 1500;   // как у штатного ГУ: удержание кнопки памяти сиденья 1500 мс

// ---------- Состояние ----------
bool stablePressed[N];     // устоявшееся состояние кнопки
uint8_t sameCount[N];      // сколько опросов подряд отличалось
uint32_t pressStart[N];    // когда кнопка нажалась (для долгого удержания)
bool holdSent[N];          // долгое удержание уже отправлено
bool bleOn = false;
uint8_t encPrev;           // предыдущее состояние квадратуры A<<1|B
int8_t encAcc;             // накопленные переходы в текущую сторону

// ---------- Вывод: USB ----------
// На ESP32-S3-Zero один USB: нативный USB-Serial/JTAG, /dev/cu.usbmodem101.
void outLine(const String &s) { Serial.println(s); }

// Строка протокола для Mac/ГУ. Начинается с "!", чтобы отличать от журнала.
void send(const String &s) { outLine("!" + s); }

// Журнал для человека.
void logLine(const String &s) { outLine(s); }

// ---------- Встроенный RGB ----------
void setRgb(uint8_t r, uint8_t g, uint8_t b) { rgbLedWrite(RGB_PIN, r, g, b); }

#if USE_BLE
// Префикс UUID — исторические байты 6d656368 62757474, UUID не меняем
#define SERVICE_UUID "6d656368-6275-7474-0001-000000000000"
#define BUTTONS_UUID "6d656368-6275-7474-0002-000000000000"
#define DEVICE_NAME  "Knopych"

const uint32_t CONNECT_GREEN_MS = 3000;    // зелёный столько после подключения
const uint32_t ADVERTISE_SHOW_MS = 60000;  // синее мигание только первые 60 с рекламы

BLECharacteristic *chButtons = nullptr;
volatile bool connected = false;
volatile bool needAdvertise = false;
uint32_t advertiseAt = 0;  // millis(), когда рекламу можно поднимать снова
const uint32_t ADVERTISE_DELAY_MS = 200;  // пауза после разрыва: клиент успевает отцепиться
uint32_t connectedAt = 0;      // millis() подключения: зелёный 3 с
uint32_t advertisingSince = 0; // millis() старта рекламы: синее мигание 60 с
#endif

// ---------- BLE ----------
#if USE_BLE
// MAC панели — по нему мост ГУ подключается. BLEAddress сам приводит порядок байт.
String macStr(const BLEAddress &a) { return a.toString(); }

class ServerCb : public BLEServerCallbacks {
  // Ядро esp32 3.x собрано с NimBLE, поэтому адрес клиента есть только здесь.
  void onConnect(BLEServer *, ble_gap_conn_desc *desc) override {
    connected = true;
    connectedAt = millis();
    logLine("[ble] connected from " + macStr(BLEAddress(desc->peer_id_addr)));
  }
  void onDisconnect(BLEServer *) override {
    connected = false;
    advertisingSince = millis();
    advertiseAt = millis();
    needAdvertise = true;
    logLine("[ble] disconnected, advertising again");
  }
};

void setupBle() {
  BLEDevice::init(DEVICE_NAME);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCb());
  BLEService *service = server->createService(SERVICE_UUID);

  chButtons = service->createCharacteristic(
      BUTTONS_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  chButtons->addDescriptor(new BLE2902());
  chButtons->setValue("none");

  service->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);
  advertisingSince = millis();
  BLEDevice::startAdvertising();
  bleOn = true;
  logLine("[ble] MAC " + macStr(BLEDevice::getAddress()) + " advertising as " DEVICE_NAME);
}
#endif

// ---------- USB: команды от Mac/ГУ ----------
void onCommand(String line) {
  line.trim();
  line.toLowerCase();
  if (line.length() == 0) return;

  if (line == "ping") {
    send("pong knopych " VERSION);
  } else {
    send("err unknown: " + line);
  }
}

// Буфер строки ввода.
String inBuf;

void pollPort(Stream &port, String &buf) {
  while (port.available()) {
    char ch = port.read();
    if (ch == '\r' || ch == '\n') {
      String line = buf;
      buf = "";
      onCommand(line);
    } else if (buf.length() < 80) {
      buf += ch;
    }
  }
}

// ---------- Кнопки ----------
// Событие кнопки для Mac/ГУ: строка протокола и та же строка в BLE-характеристику.
void sendEvent(const String &msg) {
  send(msg);
#if USE_BLE
  if (chButtons) {
    chButtons->setValue(msg.c_str());
    if (connected) chButtons->notify();
  }
#endif
}

void pressNow(uint8_t idx) { sendEvent("btn " + String(idx + 1)); }

void onPress(uint8_t idx) {
  if (HOLD[idx]) {  // такие кнопки отличаем по длительности: btn шлём на отпускании
    pressStart[idx] = millis();
    holdSent[idx] = false;
    return;
  }
  pressNow(idx);
}

// Долгое удержание: одно событие в момент, когда порог набран.
void checkHold() {
  for (uint8_t i = 0; i < N; i++) {
    if (HOLD[i] && stablePressed[i] && !holdSent[i] &&
        millis() - pressStart[i] >= HOLD_MS) {
      holdSent[i] = true;
      sendEvent("long " + String(i + 1));
    }
  }
}

void pollButtons() {
  // Нажатие засчитывается после 50 мс стабильного LOW.
  for (uint8_t i = 0; i < N; i++) {
    bool raw = digitalRead(BTN[i]) == LOW;
    if (raw == stablePressed[i]) {
      sameCount[i] = 0;
      continue;
    }
    if (++sameCount[i] >= DEBOUNCE_SAMPLES) {
      stablePressed[i] = raw;
      sameCount[i] = 0;
      if (raw) {
        onPress(i);
      } else if (HOLD[i] && !holdSent[i]) {
        pressNow(i);  // короткое нажатие — как раньше, но по отпусканию
      }
    }
  }
}

// ---------- Энкодер ----------
// Таблица валидных переходов квадратуры, индекс = (prev << 2) | cur, cur = A<<1|B.
// +-1 — переход в одну/другую сторону, 0 — невалидный (оба пина разом, дребезг) — пропускаем.
void pollEncoder() {
  static const int8_t DIR[16] = {0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0};
  uint8_t cur = (digitalRead(ENC_A) << 1) | digitalRead(ENC_B);
  int8_t delta = DIR[(encPrev << 2) | cur];
  encPrev = cur;
  if (delta == 0) return;
  encAcc += ENC_INVERT ? -delta : delta;
  // Щелчок = 2 перехода: |acc| >= 2 -> шаг громкости.
  if (encAcc >= (int8_t)ENC_TRANSITIONS_PER_DETENT) {
    encAcc -= ENC_TRANSITIONS_PER_DETENT;
    sendEvent("vol 1");
  } else if (encAcc <= -(int8_t)ENC_TRANSITIONS_PER_DETENT) {
    encAcc += ENC_TRANSITIONS_PER_DETENT;
    sendEvent("vol -1");
  }
}

// Кнопка энкодера: событие в момент нажатия и отпускания.
void pollEncoderButton() {
  static bool stable = false;   // не нажата: подтяжка держит HIGH
  static uint8_t sameCount = 0;
  bool raw = digitalRead(ENC_SW) == LOW;
  if (raw == stable) {
    sameCount = 0;
    return;
  }
  if (++sameCount < 4) return;  // 4 x 5 мс = 20 мс стабильного сигнала
  sameCount = 0;
  stable = raw;
  if (raw) {
    sendEvent("vbtn 1");
    logLine("вертушок: нажат");
  } else {
    sendEvent("vbtn 0");
    logLine("вертушок: отпущен");
  }
}

const char *resetReasonText(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON:   return "power on";
    case ESP_RST_SW:        return "software";
    case ESP_RST_PANIC:     return "crash (panic)";
    case ESP_RST_INT_WDT:   return "watchdog (int)";
    case ESP_RST_TASK_WDT:  return "watchdog (task)";
    case ESP_RST_WDT:       return "watchdog";
    case ESP_RST_BROWNOUT:  return "BROWNOUT (просадка питания)";
    case ESP_RST_USB:       return "usb";
    case ESP_RST_EXT:       return "external pin";
    default:                return "other";
  }
}

// ---------- setup / loop ----------
void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);  // USB CDC: не ждать, если порт на Mac не открыт

  esp_reset_reason_t reason = esp_reset_reason();
  logLine("");
  logLine(String("Knopych panel " VERSION ", reset reason: ") + resetReasonText(reason));

  // Пины бывших светодиодов кнопок (11, 12, 44) не трогаем: остаются входами и не светятся.
  for (uint8_t i = 0; i < N; i++) pinMode(BTN[i], INPUT_PULLUP);

  pinMode(ENC_A, INPUT_PULLUP);
  pinMode(ENC_B, INPUT_PULLUP);
  pinMode(ENC_SW, INPUT_PULLUP);
  encPrev = (digitalRead(ENC_A) << 1) | digitalRead(ENC_B);  // иначе первый опрос даёт ложный шаг
  encAcc = 0;

#if USE_BLE
  setupBle();
#else
  logLine("[ble] off (USE_BLE = 0), связь только по USB");
#endif

  send("hello knopych " VERSION);
}

void loop() {
  static uint32_t tick = 0;

  pollButtons();
  pollEncoder();
  pollEncoderButton();
  checkHold();
  pollPort(Serial, inBuf);

#if USE_BLE
  // После отключения BLE снова начинаем рекламироваться. Ждём по millis(), а не delay():
  // кнопки должны опрашиваться каждые 5 мс, иначе короткое нажатие (< 50 мс) теряется.
  if (needAdvertise && millis() - advertiseAt >= ADVERTISE_DELAY_MS) {
    needAdvertise = false;
    BLEDevice::startAdvertising();
    logLine("[ble] advertising again");
  }
#endif

  // Встроенный RGB — короткий индикатор связи, постоянного свечения нет.
  if (tick % RGB_EVERY == 0) {
    if (!bleOn) {
      setRgb(0, 0, 0);  // только USB: не светим вообще
    }
#if USE_BLE
    else if (connected) {
      setRgb(0, millis() - connectedAt < CONNECT_GREEN_MS ? RGB_BRIGHT : 0, 0);
    } else {
      bool blink = ((millis() - advertisingSince) / RGB_BLINK_MS) % 2 == 0;
      bool show = millis() - advertisingSince < ADVERTISE_SHOW_MS;
      setRgb(0, 0, show && blink ? RGB_BRIGHT : 0);
    }
#endif
  }

  tick++;
  delay(POLL_MS);
}
