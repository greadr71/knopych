// Knopych — pin-scan: какой GPIO к чему припаян на панели (Waveshare ESP32-S3-Zero).
// Диагностический скетч, не основная прошивка. BLE и Wi-Fi не включаются.
// Все 15 пинов периметра держим входами с подтяжкой и бесконечно печатаем каждый фронт.
// Светодиоды кнопок в прошивке больше не используются: их пины (11, 12, 44) — такие же входы,
// в OUTPUT их не переводим никогда (пины кнопок и энкодера сидят на GND, HIGH = короткое замыкание).

#define VERSION "v2"

// Весь периметр панели: 6 кнопок, 2 пина энкодера, 3 бывших пина светодиодов, 3 свободных.
const uint8_t PIN[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 43, 44};
const uint8_t NPINS = sizeof(PIN);

const uint32_t POLL_MS = 5;  // 5 мс: так видны все фронты квадратуры энкодера

uint8_t prevState[NPINS];

// Ждём, пока USB CDC поднимется: иначе первые строки журнала теряются.
void waitUsb() { delay(2000); }

void inputSetup() {
  for (uint8_t i = 0; i < NPINS; i++) {
    pinMode(PIN[i], INPUT_PULLUP);
    prevState[i] = digitalRead(PIN[i]);
  }
}

// Таблица текущих состояний в одну строку — по команде 's'.
void printStates() {
  for (uint8_t i = 0; i < NPINS; i++) Serial.printf("%u:%u ", PIN[i], digitalRead(PIN[i]));
  Serial.println();
}

// Без дребезговой фильтрации: нужны все фронты энкодера, лишние строки не мешают.
void pollInputs() {
  for (uint8_t i = 0; i < NPINS; i++) {
    uint8_t v = digitalRead(PIN[i]);
    if (v == prevState[i]) continue;
    prevState[i] = v;
    Serial.printf("GPIO %u -> %s\n", PIN[i], v ? "HIGH" : "LOW");
  }
}

void pollCommands() {
  while (Serial.available()) {
    int c = Serial.read();
    if (c == 's' || c == 'S') printStates();
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);  // USB CDC: не ждать, если порт на Mac не открыт
  waitUsb();

  Serial.println();
  Serial.println("=== Knopych pin-scan " VERSION " ===");
  Serial.println("Все 15 пинов на вход с подтяжкой (по умолчанию HIGH).");
  Serial.println("  кнопка нажата -> LOW, отпущена -> HIGH;");
  Serial.println("  энкодер -> быстрая серия фронтов на двух пинах (A и B);");
  Serial.println("  's' + Enter -> таблица текущих состояний всех 15 пинов.");
  Serial.println();
  Serial.println("Жми кнопки по одной, между нажатиями пауза; крути энкодер.");
  inputSetup();
  printStates();
}

void loop() {
  pollInputs();
  pollCommands();
  delay(POLL_MS);
}
