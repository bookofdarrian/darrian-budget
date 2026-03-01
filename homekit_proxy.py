#!/usr/bin/env python3
"""
HomeKit Bridge Proxy
Forwards port 21064 from Mac WiFi (172.17.84.3) to Beelink HA (100.117.1.171:21064)
Allows HomePod on Gigstreem WiFi to reach HA HomeKit bridge on wired LAN
"""
import socket
import threading
import sys

LISTEN_HOST = '0.0.0.0'   # Listen on all interfaces (WiFi + Ethernet)
LISTEN_PORT = 21064
TARGET_HOST = '100.95.125.112'   # Beelink via Tailscale (LAN IP unreachable)
TARGET_PORT = 21064

def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

def handle_client(client_sock, addr):
    print(f"[+] Connection from {addr[0]}:{addr[1]} → forwarding to {TARGET_HOST}:{TARGET_PORT}")
    try:
        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target.connect((TARGET_HOST, TARGET_PORT))
        t1 = threading.Thread(target=forward, args=(client_sock, target), daemon=True)
        t2 = threading.Thread(target=forward, args=(target, client_sock), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"[-] Error: {e}")
        client_sock.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(10)
    print(f"[*] HomeKit proxy listening on {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"[*] Forwarding to {TARGET_HOST}:{TARGET_PORT}")
    print(f"[*] HomePod on 172.17.84.x can now reach HA HomeKit bridge")
    print(f"[*] Press Ctrl+C to stop\n")
    try:
        while True:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[*] Proxy stopped.")
        server.close()

if __name__ == '__main__':
    main()
