#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 22
#define SS_PIN 21

MFRC522 mfrc522(SS_PIN, RST_PIN);


const char* WIFI_SSID = "Galaxy M30sD8BA";
const char* WIFI_PASS = "12345678";

const char* SERVER_URL =
    "http://192.168.71.222:8000/debit";

float amount = 40.0;

void setup() {
  Serial.begin(115200);

  SPI.begin();
  mfrc522.PCD_Init();

  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  Serial.println("Ready");
}

void loop() {

  if (!mfrc522.PICC_IsNewCardPresent())
    return;

  if (!mfrc522.PICC_ReadCardSerial())
    return;

  String uid = "";

  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }

  uid.toUpperCase();

  Serial.println(uid);

  if (WiFi.status() == WL_CONNECTED) {

    HTTPClient http;

    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    String body =
      "{\"uid\":\"" + uid +
      "\",\"amount\":" +
      String(amount, 2) +
      "}";

    int code = http.POST(body);

    Serial.print("HTTP: ");
    Serial.println(code);

    if (code > 0) {
      Serial.println(http.getString());
    }

    http.end();
  }

  delay(2000);
}