// FireSense educational telemetry example. NO pump/valve actuation included.
// Add appropriate ADC level shifting, separate 5V MQ-2 supply and DS18B20 wiring.
#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
const char* SSID = "YOUR_WIFI";
const char* PASSWORD = "YOUR_PASSWORD";
const char* URL = "http://192.168.1.100:8000/api/telemetry"; // change to PC LAN IP
const char* KEY = "demo-device-key";
const int mqPins[3] = {34, 35, 32}; // ADC1 pins; verify voltage <=3.3V
const int tempPins[3] = {4, 16, 17};
OneWire oneWireA(tempPins[0]), oneWireB(tempPins[1]), oneWireC(tempPins[2]);
DallasTemperature tempsA(&oneWireA), tempsB(&oneWireB), tempsC(&oneWireC);
DallasTemperature* temps[3] = {&tempsA,&tempsB,&tempsC};
unsigned long sequenceNo=0;
void setup(){ Serial.begin(115200); for(auto t:temps)t->begin(); WiFi.begin(SSID,PASSWORD); }
void loop(){
  if(WiFi.status()!=WL_CONNECTED){delay(2000);return;}
  String payload="{\"device_id\":\"ESP32-01\",\"sequence\":"+String(sequenceNo++)+",\"zones\":[";
  for(int i=0;i<3;i++){
    temps[i]->requestTemperatures(); float tc=temps[i]->getTempCByIndex(0);
    if(tc<-55 || tc>125){Serial.println("Temperature sensor error");delay(2000);return;}
    if(i)payload+=",";
    payload+="{\"zone_id\":\""+String(char('A'+i))+"\",\"smoke_raw\":"+String(analogRead(mqPins[i]))+",\"temperature_c\":"+String(tc,2)+"}";
  }
  payload+="],\"water\":{\"flow_lpm\":0,\"volume_ml\":0,\"pump_on\":false,\"active_valve\":null}}";
  HTTPClient http;http.begin(URL);http.addHeader("Content-Type","application/json");http.addHeader("X-Device-Key",KEY);
  int status=http.POST(payload);Serial.printf("POST status=%d\n",status);http.end();delay(2000);
}
