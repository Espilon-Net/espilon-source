import socket
import threading
import time

clients = {}
lock = threading.Lock()

def load_all_commands(filename="commands.txt"):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[!] File {filename} not found.")
        return []

def handle_client(client_socket, address):
    client_id = f"{address[0]}:{address[1]}"
    print(f"[+] New client connected  : {client_id}")

    with lock:
        clients[client_id] = client_socket

    commands = load_all_commands()

    try:
        for cmd in commands:
            print(f"[→] Send to {client_id} : {cmd}")
            client_socket.sendall((cmd + "\n").encode())

            # Attente de la réponse du client avant de continuer
            data = client_socket.recv(4096)
            if not data:
                print(f"[!] Client {client_id} has closed connexion.")
                break
            print(f"[←] Résponse from {client_id} : {data.decode(errors='ignore')}")

    except Exception as e:
        print(f"[!] Error with {client_id} : {e}")

    finally:
        with lock:
            if client_id in clients:
                del clients[client_id]
        client_socket.close()
        print(f"[-] Client disconnected : {client_id}")

def accept_connections(server_socket):
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()

def start_server(host="0.0.0.0", port=2021):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"[Server] Listening on {host}:{port}")

    threading.Thread(target=accept_connections, args=(server,), daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    start_server()
