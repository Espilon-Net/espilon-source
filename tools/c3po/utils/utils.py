from core.chacha20 import crypt
from tools.c2.utils.constant import _color
import threading
import base64
from utils.espilon_pb2 import C2Command

# ==== Print Status ==== #
def _print_status(message, color, icon=""):
    icon_str = f"{icon} " if icon else ""
    print(f"\n{_color(color)}[{icon_str}{message}]{_color('RESET')}")

# ==== Send Command ==== #
def _find_client(c2, identifier):
        try:
            index = int(identifier) - 1
            if 0 <= index < len(c2.clients):
                return list(c2.clients.keys())[index]
        except ValueError:
            for addr in c2.clients.keys():
                if identifier in addr[0]:
                    return addr
        return None

# ==== Find Client by IP ==== #
def _find_client_by_ip(c2, ip_address):
    for addr in c2.clients.keys():
        if addr[0] == ip_address:
            return addr
    return None

# ==== List Client ==== #
def _list_clients(c2):
    if c2.clients:
        _print_status("Clients connectés :", "GREEN")
        for i, (addr, _) in enumerate(c2.clients.items(), start=1):
            print(f"{i}. {addr[0]}:{addr[1]}")
            
        # Send ls command to each client with multithreading and wait for response
        threads = []
        for addr in c2.clients.keys():
            thread = threading.Thread(target=send_to_client, args=(c2, addr, "ping", True))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

    else:
        _print_status("Aucun client connecté", "RED", "⚠")


# ==== Send to Client ==== #
def send_to_client(c2, client_address, message, wait_response=False, timeout=5):
        # print(f"\n{_color('BLUE')}[*] Envoi de message à {client_address}: {message}{_color('RESET')}")
        if client_address in c2.clients:
            try:
                command = C2Command()
                command.payload = message.strip()

                # 2. Sérialiser avec Protobuf
                serialized_command = command.SerializeToString()    
            
                encrypted_message = crypt(serialized_command)
                encoded_message = base64.b64encode(encrypted_message)
                c2.clients[client_address].send(encoded_message)
                _print_status(f"Message envoyé à {client_address}: {message}", "BLUE", "📩")
                
                if wait_response:
                    # Reset the event and wait for the response
                    if client_address in c2.response_events:
                        c2.response_events[client_address].clear()
                        if c2.response_events[client_address].wait(timeout):
                            response = c2.response_data[client_address]
                            return response
                        else:
                            _print_status(f"Pas de réponse de {client_address} dans le délai imparti", "RED", "⚠")
                            return None
                    else:
                        _print_status(f"Erreur: Pas d'événement pour {client_address}", "RED", "⚠")
                        return None
            except:
                _print_status(f"Erreur lors de l'envoi à {client_address}", "RED", "⚠")
        else:
            _print_status(f"Client {client_address} non trouvé", "RED", "⚠")
        return None


# ==== Send Command ==== #
def _send_command(c2, cmd):
    if len(cmd.split()) < 3:
        _print_status(" Commande invalide. Utilisez 'send <id_esp32> <message>'", "RED", "⚠")
        return
    
    if c2.clients:
        client = _find_client(c2, cmd.split()[1])
        print(f"Client trouvé : {client}")
        if client:
            send_to_client(c2, client, " ".join(cmd.split()[2:]))
    else:
        _print_status("Aucun client connecté", "RED", "⚠")