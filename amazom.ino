// amazom.ino - Arduino HID Controller
// Recebe comandos via Serial e executa ações de Mouse e Keyboard
// Compatível com Arduino Leonardo, Pro Micro (ATmega32u4)

#include <Mouse.h>
#include <Keyboard.h>

// ===== LED de Status =====
#if defined(RXLED0) && defined(RXLED1)
  inline void LED_ON()  { RXLED0; }  // ativo-baixo (acende)
  inline void LED_OFF() { RXLED1; }  // apaga
  #define USE_RX_LED 1
#else
  #define LED_PIN LED_BUILTIN
  inline void LED_ON()  { digitalWrite(LED_PIN, HIGH); }
  inline void LED_OFF() { digitalWrite(LED_PIN, LOW);  }
  #define USE_RX_LED 0
#endif

// ===== Variáveis de Estado =====
bool running = false;
bool ledState = false;
unsigned long lastBlink = 0;
const unsigned long BLINK_INTERVAL = 500;

// ===== Funções Auxiliares =====
static inline int clamp(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

void ledSolidOn()  { LED_ON();  ledState = true;  }
void ledSolidOff() { LED_OFF(); ledState = false; }
void ledToggle()   { ledState ? LED_OFF() : LED_ON(); ledState = !ledState; }

void ledUpdate(unsigned long now) {
  if (running) {
    if (!ledState) ledSolidOn();  // Fixo aceso quando rodando
    return;
  }
  // Pisca quando ocioso
  if (now - lastBlink >= BLINK_INTERVAL) {
    ledToggle();
    lastBlink = now;
  }
}

// ===== Setup =====
void setup() {
#if !USE_RX_LED
  pinMode(LED_PIN, OUTPUT);
#endif
  ledSolidOff();

  Serial.begin(115200);
  Serial.setTimeout(100);
  delay(1200);  // Aguarda enumeração USB no Windows

  Mouse.begin();
  Keyboard.begin();

  Serial.println(F("READY"));
}

// ===== Loop Principal =====
void loop() {
  ledUpdate(millis());

  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  // ===== PROTOCOLO DE COMANDOS =====
  // B1 / B0          -> Define estado (running/idle) e LED
  // M dx dy          -> Move mouse relativo [-127..127]
  // CL               -> Clique esquerdo
  // CR               -> Clique direito
  // CM               -> Clique do meio
  // CD               -> Duplo clique esquerdo
  // AC               -> Alt + clique esquerdo
  // K <KEY>          -> Pressiona tecla especial
  // T <texto>        -> Digita texto ASCII
  // P <mods> <key>   -> Pressiona combinação (ex: P CTRL a)
  // S <ms>           -> Sleep/delay em milissegundos

  // ===== Estado LED =====
  if (line == "B1") {
    running = true;
    ledSolidOn();
    Serial.println(F("OK"));
    return;
  }
  if (line == "B0") {
    running = false;
    ledSolidOff();
    Serial.println(F("OK"));
    return;
  }

  // ===== Movimento Mouse =====
  if (line.startsWith("M ")) {
    int sp = line.indexOf(' ', 2);
    if (sp <= 2) { Serial.println(F("ERR M")); return; }

    int dx = line.substring(2, sp).toInt();
    int dy = line.substring(sp + 1).toInt();
    dx = clamp(dx, -127, 127);
    dy = clamp(dy, -127, 127);

    Mouse.move((int8_t)dx, (int8_t)dy, 0);
    Serial.println(F("OK"));
    return;
  }

  // ===== Cliques Mouse =====
  if (line == "CL") {
    Mouse.press(MOUSE_LEFT);
    delay(50);
    Mouse.release(MOUSE_LEFT);
    Serial.println(F("OK"));
    return;
  }

  if (line == "CR") {
    Mouse.press(MOUSE_RIGHT);
    delay(50);
    Mouse.release(MOUSE_RIGHT);
    Serial.println(F("OK"));
    return;
  }

  if (line == "CM") {
    Mouse.press(MOUSE_MIDDLE);
    delay(50);
    Mouse.release(MOUSE_MIDDLE);
    Serial.println(F("OK"));
    return;
  }

  if (line == "CD") {
    Mouse.click(MOUSE_LEFT);
    delay(50);
    Mouse.click(MOUSE_LEFT);
    Serial.println(F("OK"));
    return;
  }

  // ===== Alt + Clique =====
  if (line == "AC") {
    Keyboard.press(KEY_LEFT_ALT);
    delay(10);
    Mouse.press(MOUSE_LEFT);
    delay(50);
    Mouse.release(MOUSE_LEFT);
    Keyboard.release(KEY_LEFT_ALT);
    Serial.println(F("OK"));
    return;
  }

  // ===== Teclas Especiais =====
  if (line.startsWith("K ")) {
    String key = line.substring(2);
    key.trim();
    uint8_t k = 0;

    if (key == "ENTER") k = KEY_RETURN;
    else if (key == "ESC") k = KEY_ESC;
    else if (key == "TAB") k = KEY_TAB;
    else if (key == "SPACE") k = ' ';
    else if (key == "BKSP") k = KEY_BACKSPACE;
    else if (key == "DEL") k = KEY_DELETE;
    else if (key == "UP") k = KEY_UP_ARROW;
    else if (key == "DOWN") k = KEY_DOWN_ARROW;
    else if (key == "LEFT") k = KEY_LEFT_ARROW;
    else if (key == "RIGHT") k = KEY_RIGHT_ARROW;
    else if (key == "HOME") k = KEY_HOME;
    else if (key == "END") k = KEY_END;
    else if (key == "PGUP") k = KEY_PAGE_UP;
    else if (key == "PGDN") k = KEY_PAGE_DOWN;
    else if (key == "F1") k = KEY_F1;
    else if (key == "F2") k = KEY_F2;
    else if (key == "F3") k = KEY_F3;
    else if (key == "F4") k = KEY_F4;
    else if (key == "F5") k = KEY_F5;
    else if (key == "F6") k = KEY_F6;
    else if (key == "F7") k = KEY_F7;
    else if (key == "F8") k = KEY_F8;
    else if (key == "F9") k = KEY_F9;
    else if (key == "F10") k = KEY_F10;
    else if (key == "F11") k = KEY_F11;
    else if (key == "F12") k = KEY_F12;

    if (k == 0) { Serial.println(F("ERR K")); return; }

    Keyboard.press(k);
    delay(10);
    Keyboard.release(k);
    Serial.println(F("OK"));
    return;
  }

  // ===== Digitar Texto =====
  if (line.startsWith("T ")) {
    String txt = line.substring(2);
    for (size_t i = 0; i < txt.length(); i++) {
      Keyboard.write((uint8_t)txt[i]);
      delay(2);
    }
    Serial.println(F("OK"));
    return;
  }

  // ===== Combinação de Teclas =====
  if (line.startsWith("P ")) {
    // Formato: P CTRL a  ou  P CTRL+SHIFT s
    int sp = line.indexOf(' ', 2);
    if (sp <= 2) { Serial.println(F("ERR P")); return; }
    
    String mods = line.substring(2, sp);
    String key = line.substring(sp + 1);
    key.trim();
    
    // Pressiona modificadores
    if (mods.indexOf("CTRL") >= 0) Keyboard.press(KEY_LEFT_CTRL);
    if (mods.indexOf("SHIFT") >= 0) Keyboard.press(KEY_LEFT_SHIFT);
    if (mods.indexOf("ALT") >= 0) Keyboard.press(KEY_LEFT_ALT);
    if (mods.indexOf("GUI") >= 0 || mods.indexOf("WIN") >= 0) Keyboard.press(KEY_LEFT_GUI);
    
    delay(10);
    
    // Pressiona tecla principal
    if (key.length() == 1) {
      Keyboard.press(key[0]);
    }
    
    delay(50);
    Keyboard.releaseAll();
    Serial.println(F("OK"));
    return;
  }

  // ===== Sleep/Delay =====
  if (line.startsWith("S ")) {
    int ms = line.substring(2).toInt();
    if (ms > 0 && ms <= 10000) {
      delay(ms);
      Serial.println(F("OK"));
      return;
    }
    Serial.println(F("ERR S"));
    return;
  }

  Serial.println(F("ERR CMD"));
}
