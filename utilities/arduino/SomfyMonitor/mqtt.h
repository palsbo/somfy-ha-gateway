#ifndef MQTT_H
#define MQTT_H

#include <PubSubClient.h>

const char* mqtt_server = "192.168.1.3";
const int   mqtt_port   = 1883;
const char* mqtt_user   = "erik";
const char* mqtt_pass   = "Qm4i5icz-";
const char* mqtt_client = "SomfyGateway";

namespace mqttspace {
  typedef void (*cb_onmqttdata)(char* topic, char* data);
  cb_onmqttdata ondata = nullptr;

  static void callback(char* topic, byte* payload, unsigned int length) {
    char buf[length + 1];
    memcpy(buf, payload, length);
    buf[length] = 0;
    if (ondata) ondata(topic, buf);
  }
}

extern WiFiClient espClient;
extern PubSubClient mqttClient;

class MQTT {
  const char* inTopic  = "somfy/cmd/#";
public:
  void onMessage(mqttspace::cb_onmqttdata cb) {
    mqttspace::ondata = cb;
  }

  void begin() {
    mqttClient.setServer(mqtt_server, mqtt_port);
    mqttClient.setCallback(mqttspace::callback);
  }

  void publish(const char* topic, const char* payload) {
    if (mqttClient.connected()) {
      mqttClient.publish(topic, payload);
    }
  }

  void subscribe(char * topic) {
    mqttClient.subscribe(topic);
  }

  void unsubscribe(char * topic) {
    mqttClient.unsubscribe(topic);
  }

  void loop() {
   if (!mqttClient.connected()) {
      reconnect();
    }
    mqttClient.loop();
  }

void reconnect() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (mqttClient.connect(mqtt_client, mqtt_user, mqtt_pass)) {
      Serial.println("connected");
      mqttClient.publish("outTopic","hello world");
      mqttClient.subscribe(inTopic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}



/*
  void reconnect() {
    if (!mqttClient.connected()) {
      Serial.print("Forsøger MQTT forbindelse...");
      Serial.println (mqttClient.connected());
      if (mqttClient.connect(mqtt_client, mqtt_user, mqtt_pass)) {
        Serial.print("forbundet!");
        Serial.println(mqttClient.connected());
        mqttClient.subscribe(inTopic);
      } else {
        Serial.print("fejlede, rc=");
        Serial.println(mqttClient.state());
      }
    }
  }
*/
};


// Definition af globale objekter (hvis de ikke er i en .cpp fil)
#if !defined(MQTT_GLOBALS)
#define MQTT_GLOBALS
WiFiClient   espClient;
PubSubClient mqttClient(espClient);
#endif

#endif