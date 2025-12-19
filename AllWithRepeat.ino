#include <Keyboard.h>
#include <Mouse.h>

// --- КОНСТАНТЫ ---
const long BAUD_RATE = 9600;
const int SCREEN_WIDTH = 1920;
const int SCREEN_HEIGHT = 1080;

// Глобальные переменные
bool shouldStop = false;
bool inLoop = false;
bool inRepeat = false;
int repeatCount = 0;
int repeatTarget = 0;
int currentRepeat = 0;

unsigned long lastCommandTime = 0;
const unsigned long COMMAND_DELAY = 10;

void setup() {
  Serial.begin(BAUD_RATE);
  Keyboard.begin();
  Mouse.begin();
  
  while (!Serial);
  Serial.println("Arduino HID Bot is ready (Keyboard + Mouse).");
  Serial.print("Screen resolution set to: ");
  Serial.print(SCREEN_WIDTH);
  Serial.print("x");
  Serial.println(SCREEN_HEIGHT);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Убираем комментарии
    if (command.startsWith("#")) {
      return;
    }
    
    // Обработка команды STOP
    if (command == "STOP") {
      shouldStop = true;
      inLoop = false;
      inRepeat = false;
      Keyboard.releaseAll();
      Mouse.release(MOUSE_LEFT);
      Mouse.release(MOUSE_RIGHT);
      Mouse.release(MOUSE_MIDDLE);
      Serial.println("STOP: Loop terminated");
      return;
    }
    
    // Обработка команды RESET
    if (command == "RESET") {
      shouldStop = false;
      inLoop = false;
      inRepeat = false;
      repeatCount = 0;
      repeatTarget = 0;
      currentRepeat = 0;
      Keyboard.releaseAll();
      Mouse.release(MOUSE_LEFT);
      Mouse.release(MOUSE_RIGHT);
      Mouse.release(MOUSE_MIDDLE);
      Serial.println("RESET: State cleared");
      return;
    }
    
    // Обработка команды REPEAT_START_X
    if (command.startsWith("REPEAT_START_")) {
      if (inRepeat) {
        Serial.println("ERROR: Nested repeats not supported");
        return;
      }
      
      String countStr = command.substring(13); // "REPEAT_START_" имеет 13 символов
      repeatTarget = countStr.toInt();
      
      if (repeatTarget > 0 && repeatTarget <= 999) {
        inRepeat = true;
        repeatCount = 0;
        currentRepeat = 1;
        Serial.print("REPEAT_START: Starting block, will repeat ");
        Serial.print(repeatTarget);
        Serial.println(" times");
      } else {
        Serial.println("ERROR: Invalid repeat count");
      }
      return;
    }
    
    // Обработка команды REPEAT_END
    if (command == "REPEAT_END") {
      if (!inRepeat) {
        Serial.println("REPEAT_END: Not in repeat mode");
        return;
      }
      
      repeatCount++;
      Serial.print("REPEAT_END: Completed iteration ");
      Serial.print(repeatCount);
      Serial.print(" of ");
      Serial.println(repeatTarget);
      
      if (repeatCount >= repeatTarget) {
        // Завершили все повторения
        inRepeat = false;
        repeatCount = 0;
        repeatTarget = 0;
        currentRepeat = 0;
        Serial.println("REPEAT: Block completed");
      } else {
        // Нужно повторить еще раз
        currentRepeat++;
        // Возвращаемся к началу блока повторений
        // (Это делается на стороне Python, здесь просто сбрасываем флаг для команды)
      }
      return;
    }
    
    // Обрабатываем остальные команды
    executeCommand(command);
  }
}

void executeCommand(String command) {
  if (shouldStop && command != "LOOP_START") {
    return;
  }
  
    // Очистка входного буфера перед выполнением команды
  while (Serial.available() > 0) {
    Serial.read();
  }

  while (millis() - lastCommandTime < COMMAND_DELAY) {
    delay(1);
  }
  
  // --- СПЕЦИАЛЬНЫЕ КОМАНДЫ ---
  
  if (command == "LOOP_START") {
    inLoop = true;
    shouldStop = false;
    Serial.println("LOOP_START: Beginning loop");
    return;
  }
  
  if (command == "LOOP_END") {
    if (inLoop && !shouldStop) {
      Serial.println("LOOP_END: Returning to start");
    } else {
      inLoop = false;
      Serial.println("LOOP_END: Loop finished");
    }
    return;
  }
  
  // Команда задержки
  if (command.startsWith("WAIT_")) {
    String waitTimeStr = command.substring(5);
    float waitSeconds = waitTimeStr.toFloat();
    
    if (waitSeconds > 0 && waitSeconds <= 60) {
      Serial.print("WAIT: ");
      Serial.print(waitSeconds);
      Serial.println(" seconds");
      
      unsigned long waitMillis = (unsigned long)(waitSeconds * 1000);
      unsigned long startTime = millis();
      
      while (millis() - startTime < waitMillis) {
        if (shouldStop) {
          Serial.println("WAIT: Interrupted by STOP");
          return;
        }
        delay(10);
      }
    } else {
      Serial.print("WAIT: Invalid time ");
      Serial.println(waitTimeStr);
    }
    return;
  }
  
  // --- КОМАНДЫ КЛАВИАТУРЫ ---
  
  if (command == "WIN") {
    Keyboard.press(KEY_LEFT_GUI);
    Serial.println("KEY: Win key pressed");
  }
  else if (command == "RELEASE_ALL") {
    Keyboard.releaseAll();
    Serial.println("KEY: All keys released");
  }
  // Функциональные клавиши
  else if (command == "F1") {
    Keyboard.write(KEY_F1);
    Serial.println("KEY: F1");
  }
  else if (command == "F2") {
    Keyboard.write(KEY_F2);
    Serial.println("KEY: F2");
  }
  else if (command == "F3") {
    Keyboard.write(KEY_F3);
    Serial.println("KEY: F3");
  }
  else if (command == "F4") {
    Keyboard.write(KEY_F4);
    Serial.println("KEY: F4");
  }
  else if (command == "F5") {
    Keyboard.write(KEY_F5);
    Serial.println("KEY: F5");
  }
  else if (command == "F6") {
    Keyboard.write(KEY_F6);
    Serial.println("KEY: F6");
  }
  else if (command == "F7") {
    Keyboard.write(KEY_F7);
    Serial.println("KEY: F7");
  }
  else if (command == "F8") {
    Keyboard.write(KEY_F8);
    Serial.println("KEY: F8");
  }
  else if (command == "F9") {
    Keyboard.write(KEY_F9);
    Serial.println("KEY: F9");
  }
  else if (command == "F10") {
    Keyboard.write(KEY_F10);
    Serial.println("KEY: F10");
  }
  else if (command == "F11") {
    Keyboard.write(KEY_F11);
    Serial.println("KEY: F11");
  }
  else if (command == "F12") {
    Keyboard.write(KEY_F12);
    Serial.println("KEY: F12");
  }
  // Специальные клавиши
  else if (command == "ESC") {
    Keyboard.write(KEY_ESC);
    Serial.println("KEY: ESC");
  }
  else if (command == "ENTER") {
    Keyboard.write(KEY_RETURN);
    Serial.println("KEY: ENTER");
  }
  else if (command == "TAB") {
    Keyboard.write(KEY_TAB);
    Serial.println("KEY: TAB");
  }
  else if (command == "SPACE") {
    Keyboard.write(' ');
    Serial.println("KEY: SPACE");
  }
  else if (command == "BACKSPACE") {
    Keyboard.write(KEY_BACKSPACE);
    Serial.println("KEY: BACKSPACE");
  }
  else if (command == "DELETE") {
    Keyboard.write(KEY_DELETE);
    Serial.println("KEY: DELETE");
  }
  // Цифры 0-9
  else if (command.length() == 1 && command.charAt(0) >= '0' && command.charAt(0) <= '9') {
    char key = command.charAt(0);
    Keyboard.write(key);
    Serial.print("KEY: Number ");
    Serial.println(key);
  }
  
  lastCommandTime = millis();
  delay(10);
}

void resetAll() {
  shouldStop = true;
  inLoop = false;
  inRepeat = false;
  repeatCount = 0;
  repeatTarget = 0;
  currentRepeat = 0;
  Keyboard.releaseAll();
  Mouse.release(MOUSE_LEFT);
  Mouse.release(MOUSE_RIGHT);
  Mouse.release(MOUSE_MIDDLE);
  delay(100);
}
