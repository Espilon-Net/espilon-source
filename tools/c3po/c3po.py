import base64
import socket
import threading
import os
from utils.espilon_pb2 import ESPMessage, C2Command
from utils.chacha20 import crypt
from utils.manager import add_to_group, remove_group, remove_esp_from_group
from utils.utils import _print_status, _find_client
from utils.reboot import reboot
from utils.cli import _setup_cli, _color, cli_interface
from tools.c2.utils.constant import HOST, PORT, COMMANDS

from utils.message_process import process_esp_message


class C2Server:
    def __init__(self):
        self.clients = {}
        self.groups = {}

        self.clients_ids = {}

        # For response synchronization
        self.response_events = {}
        self.response_data = {}

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((HOST, PORT))
        self.server.listen(5)

        _setup_cli(self)
        self._start_server()

    # ---------- Core Server Functions ----------
    def _start_server(self):
        print(f"\n{_color('GREEN')}[*] Server is listening on {HOST}:{PORT}{_color('RESET')}")
        threading.Thread(target=self._accept_clients, daemon=True).start()
        cli_interface(self)

    def _accept_clients(self):
        while True:
            client_socket, client_address = self.server.accept()
            threading.Thread(target=self._handle_client, args=(client_socket, client_address)).start()

    def _handle_client(self, client_socket, client_address):
        self._close_existing_client(client_address)
        self.clients[client_address] = client_socket
        _print_status(f"New client connected : {client_address}", "GREEN")

        # Initialize event for this client
        self.response_events[client_address] = threading.Event()
        self.response_data[client_address] = None

        while True:
            try:
                message = client_socket.recv(4096)
                if not message:
                    break

                try:
                    process_esp_message(self, client_address, message)
                    
                except Exception as e:
                    print(f"Error during decryption: {e}")
                    continue

            except (ConnectionResetError, BrokenPipeError):
                break

        _print_status(f"Client {client_address} disconnected", "RED")
        self.clients.pop(client_address, None)
        if client_address in self.response_events:
            del self.response_events[client_address]
        if client_address in self.response_data:
            del self.response_data[client_address]
        client_socket.close()

    # ---------- Client Management ----------
    def _close_existing_client(self, client_address):
        if client_address in self.clients:
            self.clients[client_address].close()
            del self.clients[client_address]
            _print_status(f"Client {client_address} disconnected", "RED")


    # ---------- CLI Interface ----------
    def _complete(self, text, state):
        if text.startswith("reboot "):
            options = [addr[0] for addr in self.clients.keys() if addr[0].startswith(text[7:])]
            options.append("all")
            options.extend(self.groups.keys())
        elif text.startswith("add_group "):
            options = [addr[0] for addr in self.clients.keys() if addr[0].startswith(text[10:])]
        elif text.startswith("remove_group "):
            options = [group for group in self.groups.keys() if group.startswith(text[13:])]
        elif text.startswith("remove_esp_from "):
            parts = text.split()
            if len(parts) >= 2 and parts[1] in self.groups:
                options = self.groups[parts[1]]
        else:
            options = [cmd for cmd in COMMANDS if cmd.startswith(text)]

        return options[state] if state < len(options) else None

    def _handle_reboot(self, parts):
        if len(parts) != 2:
            _print_status("Invalid command. Use 'reboot <id_esp32>', 'reboot all', or 'reboot <group>'", "RED", "⚠")
            return

        target = parts[1]
        if target == "all":
            reboot(self, mode="all")
        elif target in self.groups:
            reboot(self, target, mode="group")
        else:
            client = _find_client(self, target)
            if client:
                reboot(self, client, mode="single")
            else:
                _print_status(f"Client with ID {target} not found", "RED", "⚠")

    def _handle_add_group(self, parts):
        if len(parts) != 3:
            _print_status("Invalid command. Use 'add_group <group> <id_esp32>'", "RED", "⚠")
            return

        group_name, client_id = parts[1], parts[2]
        client = _find_client(self, client_id)
        
        if client:
            add_to_group(self, group_name, client)
        else:
            _print_status(f"Client with ID {client_id} not found", "RED", "⚠")

    def _handle_remove_group(self, parts):
        if len(parts) != 2:
            _print_status(" Invalid command. Use 'remove_group <group>'", "RED", "⚠")
            return
        remove_group(self, parts[1])

    def _handle_remove_esp_from(self, parts):
        if len(parts) < 3:
            _print_status(" Invalid command. Use 'remove_esp_from <group> <esp>[,<esp>...]'", "RED", "⚠")
            return
        
        group_name = parts[1]
        esp_list = []
        for part in parts[2:]:
            esp_list.extend(part.split(','))
        
        remove_esp_from_group(self, group_name, esp_list)

    def _shutdown(self):
        _print_status(" Closing server ...", "YELLOW", "✋")
        for client in list(self.clients.values()):
            client.close()
        self.server.close()
        os._exit(0)

if __name__ == "__main__":
    C2Server()
