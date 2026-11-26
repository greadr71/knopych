// Knopych panel — прошивка на Arduino (v0.8)
// Плата: Waveshare ESP32-S3-Zero (4 МБ флеш, 2 МБ PSRAM). Подробности: ../../../docs/hardware.md
//  - 6 кнопок (GPIO 1,2,4,7,6,5); светодиоды кнопок 4–6 — GPIO 44,12,11,
//    у кнопок 1–3 светодиоды не припаяны;
//  - кнопки 1..3 — пресеты сиденья, светодиод вкл/выкл (ступень 0 <-> 1);
//  - кнопки 4 и 6 — подогревы: по кругу 0 -> 3 -> 2 -> 1 -> 0, яркость светодиода = ступень;
//    кнопка 5 — вкл/выкл (лобовое);
//  - долгое удержание (1,5 с) кнопок 1..3 — сохранение положения сиденья в слот (делает Mac/ГУ),
//    кнопки 4 — яркость экрана ГУ в другой край (макс <-> мин);
//  - энкодер громкости: A -> GPIO9, B -> GPIO10, кнопка энкодера D -> GPIO13, событие vbtn 0/1;
//  - Wi-Fi НЕ включается никогда: WiFi.h не подключаем;
//  - связь с Mac / ГУ по USB (основной вариант сейчас): текстовые строки, см. README.md.
//    Строки протокола начинаются с "!", всё остальное — журнал для человека.
//    Один порт: нативный USB-Serial/JTAG (Serial);
//  - Bluetooth LE (USE_BLE): включён, MAC печатается в журнал при старте;
//  - режим "local" (по умолчанию: нажатие само меняет светодиод) /
//    "remote" (светодиоды показывают то, что прислал Mac/ГУ).
// Протокол тот же, что у MicroPython-версии ../../../v1/micropython/ — слушатель panel_usb.py подходит.

#include <esp_system.h>

#define VERSION "v0.8"

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
// Светодиоды кнопок 4,5,6 — 44,12,11; у кнопок 1–3 светодиоды не припаяны, вместо них свободные 3,8,43.
// Пины 43/44 — UART0, но UART0 не используем (журнал через USB CDC).
const uint8_t LED[N] = {3, 8, 43, 44, 12, 11};
// Сколько ступеней у кнопки: 3 = как сиденье, 1 = просто вкл/выкл.
// 1..3 — пресеты сиденья (занят/пуст), 4 и 6 — подогревы 0..3, 5 — лобовое вкл/выкл.
const uint8_t MAX_LEVEL[N] = {1, 1, 1, 3, 1, 3};
// Яркость (0..255) для ступени 0..3: глаз видит яркость нелинейно.
const uint8_t BRIGHT[4] = {0, 6, 40, 255};

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

// У кого есть долгое удержание (индекс = кнопка - 1): 1..3 — слоты памяти сиденья, 4 — яркость ГУ.
const bool HOLD[N] = {true, true, true, true, false, false};
const uint32_t HOLD_MS = 1500;   // как у штатного ГУ: удержание кнопки памяти сиденья 1500 мс

// ---------- Состояние ----------
uint8_t level[N];          // текущая ступень каждого светодиода
bool stablePressed[N];     // устоявшееся состояние кнопки
uint8_t sameCount[N];      // сколько опросов подряд отличалось
uint32_t pressStart[N];    // когда кнопка нажалась (для долгого удержания)
bool holdSent[N];          // долгое удержание уже отправлено
bool remoteMode = false;   // true = светодиодами управляет Mac/ГУ
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

// ---------- Светодиоды ----------
uint8_t brightnessFor(uint8_t i, uint8_t lvl) {
  if (lvl == 0) return 0;
  if (MAX_LEVEL[i] == 1) return BRIGHT[3];  // вкл/выкл — сразу полная яркость
  return BRIGHT[lvl > 3 ? 3 : lvl];
}

void setRgb(uint8_t r, uint8_t g, uint8_t b) { rgbLedWrite(RGB_PIN, r, g, b); }

#if USE_BLE
// Префикс UUID — исторические байты 6d656368 62757474, UUID не меняем
#define SERVICE_UUID "6d656368-6275-7474-0001-000000000000"
#define BUTTONS_UUID "6d656368-6275-7474-0002-000000000000"
#define LEDS_UUID    "6d656368-6275-7474-0003-000000000000"
#define DEVICE_NAME  "Knopych"

BLECharacteristic *chButtons = nullptr;
BLECharacteristic *chLeds = nullptr;
volatile bool connected = false;
volatile bool needAdvertise = false;
uint32_t advertiseAt = 0;  // millis(), когда рекламу можно поднимать снова
const uint32_t ADVERTISE_DELAY_MS = 200;  // пауза после разрыва: клиент успевает отцепиться
volatile bool remoteChanged = false;
uint8_t remoteLevel[N];
volatile uint8_t remoteCount = 0;
#endif

void showLevels() {
  for (uint8_t i = 0; i < N; i++) analogWrite(LED[i], brightnessFor(i, level[i]));
#if USE_BLE
  if (chLeds) chLeds->setValue(level, N);
#endif
}

void reportLevels() {
  String s = "leds";
  for (uint8_t i = 0; i < N; i++) s += " " + String(level[i]);
  send(s);
}

// values: ступени (может быть меньше 6 — остальные без изменений).
void applyLevels(const int *values, uint8_t count) {
  for (uint8_t i = 0; i < count && i < N; i++) {
    int v = values[i];
    if (v < 0) v = 0;
    if (v > MAX_LEVEL[i]) v = MAX_LEVEL[i];
    level[i] = v;
  }
  showLevels();
  reportLevels();
}

void ledTest() {
  // Короткая проверка при старте: по очереди на полную яркость.
  for (uint8_t i = 0; i < N; i++) {
    analogWrite(LED[i], 255);
    delay(80);
    analogWrite(LED[i], 0);
  }
}

// ---------- BLE ----------
#if USE_BLE
// MAC панели — по нему мост ГУ подключается. BLEAddress сам приводит порядок байт.
String macStr(const BLEAddress &a) { return a.toString(); }

class ServerCb : public BLEServerCallbacks {
  // Ядро esp32 3.x собрано с NimBLE, поэтому адрес клиента есть только здесь.
  void onConnect(BLEServer *, ble_gap_conn_desc *desc) override {
    connected = true;
    logLine("[ble] connected from " + macStr(BLEAddress(desc->peer_id_addr)));
  }
  void onDisconnect(BLEServer *) override {
    connected = false;
    remoteMode = false;  // без ГУ возвращаемся к локальному режиму
    // Ступени после разрыва считаем от 0: замороженное состояние ГУ уже могло разойтись с машиной.
    for (uint8_t i = 0; i < N; i++) level[i] = 0;
    showLevels();
    advertiseAt = millis();
    needAdvertise = true;
    logLine("[ble] disconnected, advertising again");
  }
};

class LedsCb : public BLECharacteristicCallbacks {
  // Вызывается из BLE-стека: только запоминаем, применяем в loop().
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue();
    if (v.length() < 1) return;
    uint8_t n = v.length() < N ? v.length() : N;
    for (uint8_t i = 0; i < n; i++) remoteLevel[i] = (uint8_t)v[i];
    remoteCount = n;
    remoteMode = true;
    remoteChanged = true;
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

  chLeds = service->createCharacteristic(
      LEDS_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  chLeds->setCallbacks(new LedsCb());
  chLeds->setValue(level, N);

  service->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();
  bleOn = true;
  logLine("[ble] MAC " + macStr(BLEDevice::getAddress()) + " advertising as " DEVICE_NAME);
}
#endif

// ---------- USB: команды от Mac/ГУ ----------
void onCommand(String line) {
  line.trim();
  if (line.length() == 0) return;

  // Разбить на слова.
  String words[8];
  uint8_t nw = 0;
  int pos = 0;
  while (pos < (int)line.length() && nw < 8) {
    while (pos < (int)line.length() && line[pos] == ' ') pos++;
    if (pos >= (int)line.length()) break;
    int end = line.indexOf(' ', pos);
    if (end < 0) end = line.length();
    words[nw++] = line.substring(pos, end);
    pos = end;
  }
  String cmd = words[0];
  cmd.toLowerCase();

  if (cmd == "leds") {
    int values[N];
    uint8_t count = 0;
    for (uint8_t k = 1; k < nw && count < N; k++) {
      const String &w = words[k];
      bool digits = w.length() > 0;
      for (uint16_t j = 0; j < w.length(); j++)
        if (!isDigit(w[j]) && !(j == 0 && w[j] == '-')) digits = false;
      if (!digits) {
        send("err leds: нужны числа 0..3, например: leds 3 1 0 0 0 0");
        return;
      }
      values[count++] = w.toInt();
    }
    if (count == 0) {
      send("err leds: нужны числа 0..3, например: leds 3 1 0 0 0 0");
      return;
    }
    remoteMode = true;
    applyLevels(values, count);
  } else if (cmd == "local") {
    remoteMode = false;
    send("mode local");
  } else if (cmd == "state") {
    reportLevels();
    send(remoteMode ? "mode remote" : "mode local");
  } else if (cmd == "ping") {
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

void pressNow(uint8_t idx) {
  sendEvent("btn " + String(idx + 1));
  if (!remoteMode) {  // локальный режим: меняем сами
    // выкл -> 3 -> 2 -> 1 -> выкл (для вкл/выкл: 0 <-> 1)
    level[idx] = level[idx] == 0 ? MAX_LEVEL[idx] : level[idx] - 1;
    showLevels();
    reportLevels();
  }
}

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

  for (uint8_t i = 0; i < N; i++) {
    pinMode(BTN[i], INPUT_PULLUP);
    pinMode(LED[i], OUTPUT);
    level[i] = 0;
  }
  ledTest();
  showLevels();

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
  reportLevels();
}

void loop() {
  static uint32_t tick = 0;

  pollButtons();
  pollEncoder();
  pollEncoderButton();
  checkHold();
  pollPort(Serial, inBuf);

#if USE_BLE
  // Команда от ГУ по BLE: применяем ступени.
  if (remoteChanged) {
    remoteChanged = false;
    int values[N];
    uint8_t n = remoteCount;
    for (uint8_t i = 0; i < n; i++) values[i] = remoteLevel[i];
    applyLevels(values, n);
  }
  // После отключения BLE снова начинаем рекламироваться. Ждём по millis(), а не delay():
  // кнопки должны опрашиваться каждые 5 мс, иначе короткое нажатие (< 50 мс) теряется.
  if (needAdvertise && millis() - advertiseAt >= ADVERTISE_DELAY_MS) {
    needAdvertise = false;
    BLEDevice::startAdvertising();
    logLine("[ble] advertising again");
  }
#endif

  // Встроенный RGB.
  if (tick % RGB_EVERY == 0) {
    if (!bleOn) {
      // Только USB: зелёный = светодиодами управляет Mac/ГУ, выключен = local.
      setRgb(0, remoteMode ? RGB_BRIGHT : 0, 0);
    }
#if USE_BLE
    else if (connected) {
      setRgb(0, RGB_BRIGHT, 0);
    } else {
      bool blink = (tick / RGB_EVERY) % 2 == 0;
      setRgb(0, 0, blink ? RGB_BRIGHT : 0);
    }
#endif
  }

  tick++;
  delay(POLL_MS);
}
