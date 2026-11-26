#include <WiFi.h>
#include <HTTPClient.h>

// Change these values to your Wi-Fi / hotspot details.
const char* WIFI_SSID = "CHENLESS";
const char* WIFI_PASSWORD = "tatlong8";
// Replace with your laptop's current IPv4 address.
const char* SERVER_BASE = "http://10.62.202.26:5000";

const int UP_PIN=18, DOWN_PIN=19, LEFT_PIN=21, RIGHT_PIN=22;
const int START_PIN=23, BUZZER_PIN=26, RED_LED_PIN=32, GREEN_LED_PIN=33;
const unsigned long DEBOUNCE_MS = 10;
const unsigned long LED_POLL_MS = 120;
const unsigned long SOUND_POLL_MS = 150;

struct Button { int pin; const char* direction; bool previous; bool stable; unsigned long changedAt; };
Button buttons[]={{UP_PIN,"UP",HIGH,HIGH,0},{DOWN_PIN,"DOWN",HIGH,HIGH,0},{LEFT_PIN,"LEFT",HIGH,HIGH,0},{RIGHT_PIN,"RIGHT",HIGH,HIGH,0}};
bool startPrevious=HIGH,startStable=HIGH;
unsigned long startChangedAt=0,lastLedPoll=0,lastSoundPoll=0;
String gameState="READY";
String makeUrl(const char* path){return String(SERVER_BASE)+path;}

void toneWait(int hz,int ms){tone(BUZZER_PIN,hz,ms);delay(ms+15);noTone(BUZZER_PIN);}
void startMelody(){toneWait(523,90);toneWait(659,90);toneWait(784,120);toneWait(1047,160);}
void buttonBeep(){tone(BUZZER_PIN,1000,40);}
void foodSound(){toneWait(880,60);toneWait(1175,80);}
void coinSound(){toneWait(988,65);toneWait(1319,65);toneWait(1568,110);}
void deathSound(){toneWait(500,130);toneWait(380,140);toneWait(260,220);}
void powerupSound(){toneWait(784,60);toneWait(988,60);toneWait(1175,100);}

void postJson(const char* path,const String& body){
  if(WiFi.status()!=WL_CONNECTED)return;
  HTTPClient http;
  http.setTimeout(350);
  http.setReuse(true);
  http.begin(makeUrl(path));
  http.addHeader("Content-Type","application/json");
  int code=http.POST(body);
  Serial.printf("POST %s -> HTTP %d\n",path,code);
  http.end();
}
void sendDirection(const char* d){
  tone(BUZZER_PIN, 1000, 40);
  postJson("/direction", String("{\"direction\":\"") + d + "\"}");
}
void sendStart(){
  postJson("/start","{}");
  startMelody();
}

void checkButton(Button &b){
  bool reading=digitalRead(b.pin);
  if(reading!=b.previous){b.changedAt=millis();b.previous=reading;}
  if(millis()-b.changedAt>=DEBOUNCE_MS&&reading!=b.stable){b.stable=reading;if(b.stable==LOW)sendDirection(b.direction);}
}
void checkStart(){
  bool reading=digitalRead(START_PIN);
  if(reading!=startPrevious){startChangedAt=millis();startPrevious=reading;}
  if(millis()-startChangedAt>=DEBOUNCE_MS&&reading!=startStable){startStable=reading;if(startStable==LOW)sendStart();}
}
void pollLeds(){
  if(WiFi.status()!=WL_CONNECTED)return;
  HTTPClient http;
  http.setTimeout(350);
  http.setReuse(true);
  http.begin(makeUrl("/led-status"));
  int code=http.GET();
  if(code==HTTP_CODE_OK){
    String s=http.getString();
    if(s.indexOf("PLAYING")>=0)gameState="PLAYING";
    else if(s.indexOf("GAME_OVER")>=0)gameState="GAME_OVER";
    else gameState="READY";
  }
  http.end();
  if(gameState=="PLAYING"){digitalWrite(GREEN_LED_PIN,HIGH);digitalWrite(RED_LED_PIN,LOW);}
  else if(gameState=="GAME_OVER"){digitalWrite(GREEN_LED_PIN,LOW);digitalWrite(RED_LED_PIN,(millis()/300)%2);}
  else{digitalWrite(GREEN_LED_PIN,LOW);digitalWrite(RED_LED_PIN,LOW);}
}
void pollSounds(){
  if(WiFi.status()!=WL_CONNECTED)return;
  HTTPClient http;
  http.setTimeout(350);
  http.setReuse(true);
  http.begin(makeUrl("/sound-next"));
  int code=http.GET();
  if(code==HTTP_CODE_OK){
    String event=http.getString();
    event.trim();
    if(event=="start")startMelody();
    else if(event=="button")buttonBeep();
    else if(event=="food")foodSound();
    else if(event=="coin")coinSound();
    else if(event=="death")deathSound();
    else if(event=="powerup")powerupSound();
  }
  http.end();
}
void setup(){
  Serial.begin(115200);
  for(Button &b:buttons)pinMode(b.pin,INPUT_PULLUP);
  pinMode(START_PIN,INPUT_PULLUP);pinMode(BUZZER_PIN,OUTPUT);pinMode(RED_LED_PIN,OUTPUT);pinMode(GREEN_LED_PIN,OUTPUT);
  digitalWrite(RED_LED_PIN,LOW);digitalWrite(GREEN_LED_PIN,LOW);noTone(BUZZER_PIN);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while(WiFi.status()!=WL_CONNECTED){delay(250);Serial.print(".");}
  Serial.println();Serial.print("ESP32 IP: ");Serial.println(WiFi.localIP());Serial.print("Flask server: ");Serial.println(SERVER_BASE);
  Serial.println("Controller ready. Each button goes between GPIO and GND.");
  startMelody();
}
void loop(){
  if(WiFi.status()!=WL_CONNECTED){WiFi.reconnect();delay(200);return;}
  for(Button &b:buttons)checkButton(b);
  checkStart();
  if(millis()-lastLedPoll>=LED_POLL_MS){lastLedPoll=millis();pollLeds();}
  if(millis()-lastSoundPoll>=SOUND_POLL_MS){lastSoundPoll=millis();pollSounds();}
  delay(1);
}