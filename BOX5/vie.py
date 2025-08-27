import socket
import json
import time

BOX_NAME = "BOX5"
TARGET_IP = "127.0.0.4"   # IP de BOX4 (à adapter)
TARGET_PORT = 9998
HEARTBEAT_INTERVAL = 10  # secondes entre chaque heartbeat

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_heartbeat():
    message = json.dumps({"boite": BOX_NAME}).encode()
    sock.sendto(message, (TARGET_IP, TARGET_PORT))
    print(f"[HEARTBEAT] Envoyé à {TARGET_IP}:{TARGET_PORT}")

if __name__ == "__main__":
    print(f"[{BOX_NAME}] Démarrage du heartbeat...")
    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL)
