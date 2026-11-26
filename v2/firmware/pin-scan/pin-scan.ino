// Knopych — pin-scan: какой GPIO к чему припаян на панели (Waveshare ESP32-S3-Zero).
// Диагностический скетч, не основная прошивка. BLE и Wi-Fi не включаются.
//  1) по очереди зажигает кандидатов в светодиоды на 1 с;
//  2) дальше бесконечно слушает все 15 пинов периметра и печатает каждый фронт.
// Светодиоды кнопок 1..3 не припаяны: реально есть только 3 штуки (кнопки 4,5,6).

#define VERSION "v1"

// Только эти пины можно переводить в OUTPUT.
// Светодиоды кнопок 4..6 (какой пин — какая кнопка, не подтверждено).
const uint8_t LED_CAND[] = {11, 12, 44};
const uint8_t NLED = sizeof(LED_CAND);
// Контрольный проход по «пустым» пинам: там гореть ничего не должно.
const uint8_t LED_EMPTY[] = {3, 8, 43};
const uint8_t NEMPTY = sizeof(LED_EMPTY);

// Весь периметр панели: 6 кнопок, 2 пина энкодера, 3 светодиода, 3 пустых.
const uint8_t PIN[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 43, 44};
const uint8_t NPINS = sizeof(PIN);

const uint32_t POLL_MS = 5;  // 5 мс: так видны все фронты квадратуры энкодера

uint8_t prevState[NPINS];

// Ждём, пока USB CDC поднимется: иначе первые строки журнала теряются.
void waitUsb() { delay(2000); }

void ledPass(const uint8_t *pins, uint8_t n, bool empty) {
  for (uint8_t i = 0; i < n; i++) {
    uint8_t p = pins[i];
    // НИКОГДА не OUTPUT на пины кнопок и энкодера (1,2,4,5,6,7,9,10,13):
    // второй контакт у них на GND, выход в HIGH = короткое замыкание.
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
    delay(1000);
    if (empty) Serial.printf("ПУСТО? GPIO %u — ВКЛ (ничего не должно гореть)\n", p);
    else Serial.printf("СВЕТОДИОД? GPIO %u — ВКЛ\n", p);
    digitalWrite(p, HIGH);
    delay(1500);
    digitalWrite(p, LOW);
    pinMode(p, INPUT_PULLUP);
    Serial.printf("GPIO %u — выкл\n", p);
  }
}

void ledPhase() {
  Serial.println("--- ФАЗА 1: СВЕТОДИОДЫ ---");
  ledPass(LED_CAND, NLED, false);
  Serial.println("--- контроль: пины без светодиодов ---");
  ledPass(LED_EMPTY, NEMPTY, true);
}

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
    if (c == 'l' || c == 'L') ledPhase();  // повторить проход по светодиодам
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);  // USB CDC: не ждать, если порт на Mac не открыт
  waitUsb();

  Serial.println();
  Serial.println("=== Knopych pin-scan " VERSION " ===");
  Serial.println("Шаг 1: светодиоды кнопок 4,5,6 (GPIO 11, 12, 44) по очереди. Смотри, какой загорается — запиши GPIO.");
  Serial.println("  Затем контроль по пустым пинам 3, 8, 43: гореть ничего не должно.");
  Serial.println("Шаг 2: все 15 пинов на вход с подтяжкой (по умолчанию HIGH).");
  Serial.println("  кнопка нажата -> LOW, отпущена -> HIGH;");
  Serial.println("  энкодер -> быстрая серия фронтов на двух пинах (A и B);");
  Serial.println("  's' + Enter -> таблица текущих состояний всех 15 пинов.");
  Serial.println("  'l' + Enter -> повторить проход по светодиодам.");
  Serial.println();

  ledPhase();

  Serial.println();
  Serial.println("--- ФАЗА 2: ВХОДЫ ---");
  Serial.println("Жми кнопки по одной, между нажатиями пауза; крути энкодер.");
  inputSetup();
  printStates();
}

void loop() {
  pollInputs();
  pollCommands();
  delay(POLL_MS);
}
