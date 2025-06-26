#include <TradeByte/core.hpp>
#include <ixwebsocket/IXWebSocket.h>
#include <iostream>

int main() {
    ix::WebSocketSocketTLSOptions tls;
    ix::WebSocket ws;
    ws.setUrl("ws://example.com");
    ws.setOnMessageCallback([](const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Message) {
            std::cout << msg->str << std::endl;
        }
    });
    ws.start();
    std::string input;
    while (std::getline(std::cin, input)) {
        ws.send(input);
    }
    return 0;
}
