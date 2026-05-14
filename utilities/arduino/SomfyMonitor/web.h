#ifndef WEB_H
#define WEB_H

#include <ESPAsyncWebServer.h>
#include "pages.h"

namespace webspace {

AsyncWebServer  server(80);
AsyncWebSocket  websocket("/ws");

typedef void (*cb_ondata)    (uint8_t num, char* payload, char* txbuf);
typedef void (*cb_onopen)    (uint8_t num, char* txbuf);
typedef void (*cb_onclose)   (uint8_t num);

cb_ondata  ondata      = nullptr;
cb_onopen  onconnect   = nullptr;
cb_onclose ondisconnect = nullptr;

void onWsEvent(AsyncWebSocket* server, AsyncWebSocketClient* client,
               AwsEventType type, void* arg, uint8_t* data, size_t len) {
  char txbuf[100] = "";
  switch (type) {
    case WS_EVT_CONNECT:
      if (onconnect) {
        onconnect(client->id(), txbuf);
        if (txbuf[0]) client->text(txbuf);
      }
      break;
    case WS_EVT_DISCONNECT:
      if (ondisconnect) ondisconnect(client->id());
      break;
    case WS_EVT_DATA: {
      AwsFrameInfo* info = (AwsFrameInfo*)arg;
      if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
        data[len] = 0;
        char* payload = (char*)data;
        if (strcmp(payload, "ping") == 0) {
          client->text("pong");
        } else if (ondata) {
          ondata(client->id(), payload, txbuf);
          if (txbuf[0]) client->text(txbuf);
        }
      }
      break;
    }
    default:
      break;
  }
}

} // namespace webspace

class WEB {
public:
  void onMessage(webspace::cb_ondata cb)    { webspace::ondata = cb; }
  void onConnect(webspace::cb_onopen cb)    { webspace::onconnect = cb; }
  void onDisconnect(webspace::cb_onclose cb){ webspace::ondisconnect = cb; }

  void broadcast(const char* buf) {
    webspace::websocket.textAll(buf);
  }

  void begin() {
    webspace::websocket.onEvent(webspace::onWsEvent);
    webspace::server.addHandler(&webspace::websocket);
    webspace::server.on("/", HTTP_GET, [](AsyncWebServerRequest* req) {
      req->send_P(200, "text/html", index_html);
    });
    webspace::server.on("/index.css", HTTP_GET, [](AsyncWebServerRequest* req) {
      req->send_P(200, "text/css", index_css);
    });
    webspace::server.begin();
  }
};

#endif
