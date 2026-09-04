/*
  SecureGate - Stage 9
  JSON-Formatted Event Output for PC Log Collection

  New in this stage:
    - logEvent() now prints one JSON object per line instead of
      human-formatted text, so a Python script on the PC can parse
      it reliably (json.loads() per line).
    - Non-event status prints (waiting/lockout countdown) stay as
      plain text since they're not meant to be logged, just watched.

  Example output line:
    {"timestamp":"2026-09-03 21:14:02","device_id":"SECUREGATE-UNO-01","event":"ACCESS_GRANTED","detail":"Door unlocked"}

  Wiring: unchanged from Stage 8.
*/

#include <SPI.h>
#include <MFRC522.h>
#include <Keypad.h>
#include <Wire.h>
#include <RTClib.h>

RTC_DS1307 rtc;

#define RST_PIN 9
#define SS_PIN  10
MFRC522 mfrc522(SS_PIN, RST_PIN);

byte authorizedUID[4] = {0x13, 0x5A, 0x0C, 0x13};

const byte ROWS = 4;
const byte COLS = 4;

char keys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};

byte rowPins[ROWS] = {2, 3, 4, 5};
byte colPins[COLS] = {6, 7, 8, A0};

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

const char* correctPIN = "8523";
String enteredPIN = "";

const byte MAX_ATTEMPTS = 3;
const unsigned long LOCKOUT_DURATION = 30000;

byte failedAttempts = 0;
bool lockedOut = false;
unsigned long lockoutStartTime = 0;

const byte PIR_PIN = A1;
bool motionActive = false;

const byte BUZZER_PIN = A2;
const byte RELAY_PIN  = A3;

const char* DEVICE_ID = "SECUREGATE-UNO-01";

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!rtc.begin()) {
    Serial.println(F("Could not find RTC. Check wiring (SDA->A4, SCL->A5)."));
    while (1);
  }

  SPI.begin();
  mfrc522.PCD_Init();

  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(RELAY_PIN, LOW);

  logEvent("SYSTEM_START", "SecureGate Stage 9 booted");
}

void loop() {
  checkMotion();

  if (lockedOut) {
    unsigned long elapsed = millis() - lockoutStartTime;

    if (elapsed >= LOCKOUT_DURATION) {
      lockedOut = false;
      failedAttempts = 0;
      logEvent("SYSTEM_RESET", "Lockout period ended");
    } else {
      static unsigned long lastBeep = 0;
      if (millis() - lastBeep > 1000) {
        beep(100);
        lastBeep = millis();
      }
      return;
    }
  }

  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  String uidStr = getUIDString(mfrc522.uid.uidByte, mfrc522.uid.size);

  if (!checkUID(mfrc522.uid.uidByte, mfrc522.uid.size)) {
    logEventWithUID("RFID_AUTH_FAILURE", "Unrecognized card", uidStr);
    registerFailure();
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    return;
  }

  logEventWithUID("RFID_AUTH_SUCCESS", "Card matched", uidStr);

  enteredPIN = "";
  bool submitted = false;

  while (!submitted) {
    checkMotion();
    char key = keypad.getKey();

    if (key) {
      if (key == '#') {
        submitted = true;
      } else if (key == '*') {
        enteredPIN = "";
      } else {
        enteredPIN += key;
      }
    }
  }

  if (enteredPIN.equals(correctPIN)) {
    logEvent("PIN_AUTH_SUCCESS", "Correct PIN");
    logEvent("ACCESS_GRANTED", "Door unlocked");
    failedAttempts = 0;
    unlockRelay();
  } else {
    logEvent("PIN_AUTH_FAILURE", "Incorrect PIN");
    registerFailure();
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

// Builds and prints one JSON line for a basic event (no UID)
void logEvent(const char* eventType, const char* description) {
  Serial.print(F("{\"timestamp\":\""));
  printTimestamp();
  Serial.print(F("\",\"device_id\":\""));
  Serial.print(DEVICE_ID);
  Serial.print(F("\",\"event\":\""));
  Serial.print(eventType);
  Serial.print(F("\",\"detail\":\""));
  Serial.print(description);
  Serial.println(F("\"}"));
}

// Same as logEvent but includes a scanned UID field
void logEventWithUID(const char* eventType, const char* description, String uid) {
  Serial.print(F("{\"timestamp\":\""));
  printTimestamp();
  Serial.print(F("\",\"device_id\":\""));
  Serial.print(DEVICE_ID);
  Serial.print(F("\",\"event\":\""));
  Serial.print(eventType);
  Serial.print(F("\",\"detail\":\""));
  Serial.print(description);
  Serial.print(F("\",\"uid\":\""));
  Serial.print(uid);
  Serial.println(F("\"}"));
}

void printTimestamp() {
  DateTime now = rtc.now();
  Serial.print(now.year());
  Serial.print('-');
  printTwoDigits(now.month());
  Serial.print('-');
  printTwoDigits(now.day());
  Serial.print(' ');
  printTwoDigits(now.hour());
  Serial.print(':');
  printTwoDigits(now.minute());
  Serial.print(':');
  printTwoDigits(now.second());
}

void printTwoDigits(int value) {
  if (value < 10) Serial.print('0');
  Serial.print(value);
}

void beep(int durationMs) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(durationMs);
  digitalWrite(BUZZER_PIN, LOW);
}

void unlockRelay() {
  digitalWrite(RELAY_PIN, HIGH);
  beep(150);
  delay(2000);
  digitalWrite(RELAY_PIN, LOW);
}

void checkMotion() {
  bool motionNow = (digitalRead(PIR_PIN) == HIGH);

  if (motionNow && !motionActive) {
    motionActive = true;
    logEvent("INTRUSION_DETECTED", "Motion sensed");
  } else if (!motionNow && motionActive) {
    motionActive = false;
  }
}

void registerFailure() {
  failedAttempts++;
  beep(300);

  if (failedAttempts >= MAX_ATTEMPTS) {
    lockedOut = true;
    lockoutStartTime = millis();
    logEvent("BRUTE_FORCE_DETECTED", "Lockout triggered");
    logEvent("ACCESS_DENIED", "System locked out");
  } else {
    logEvent("ACCESS_DENIED", "Attempt failed");
  }
}

bool checkUID(byte *scannedUID, byte size) {
  if (size != sizeof(authorizedUID)) return false;
  for (byte i = 0; i < size; i++) {
    if (scannedUID[i] != authorizedUID[i]) return false;
  }
  return true;
}

String getUIDString(byte *buffer, byte bufferSize) {
  String result = "";
  for (byte i = 0; i < bufferSize; i++) {
    if (buffer[i] < 0x10) result += "0";
    result += String(buffer[i], HEX);
    if (i < bufferSize - 1) result += " ";
  }
  result.toUpperCase();
  return result;
}
