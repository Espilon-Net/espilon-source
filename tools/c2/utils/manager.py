from utils.utils import _print_status
from tools.c2.utils.constant import _color

def add_to_group(c2, group_name, client_address):
    if group_name not in c2.groups:
        c2.groups[group_name] = []

    ip_address = client_address[0]

    if ip_address not in c2.groups[group_name]:
        c2.groups[group_name].append(ip_address)
        _print_status(f"Client {ip_address} ajouté au groupe {group_name}", "GREEN")
    else:
        _print_status(f"Client {ip_address} est déjà dans le groupe {group_name}", "YELLOW", "!")

def list_groups(c2):
    if c2.groups:
        print(f"\n{_color('CYAN')}Groupes disponibles :{_color('RESET')}")
        for group_name, members in c2.groups.items():
            print(f"{group_name}: {', '.join(members)}")
    else:
        _print_status("Aucun groupe disponible", "RED", "⚠")

def remove_group(c2, group_name):
    if group_name in c2.groups:
        del c2.groups[group_name]
        _print_status(f"Groupe {group_name} supprimé", "GREEN")
    else:
        _print_status(f"Groupe {group_name} non trouvé", "RED", "⚠")

def remove_esp_from_group(c2, group_name, esp_list):
    if group_name not in c2.groups:
        _print_status(f"Groupe {group_name} non trouvé", "RED", "⚠")
        return

    for esp in esp_list:
        try:
            index = int(esp) - 1
            if 0 <= index < len(c2.clients):
                client_ip = list(c2.clients.keys())[index][0]
                if client_ip in c2.groups[group_name]:
                    c2.groups[group_name].remove(client_ip)
                    _print_status(f"Client {client_ip} retiré du groupe {group_name}", "GREEN")
                else:
                    _print_status(f"Client {client_ip} n'est pas dans le groupe {group_name}", "RED", "⚠")
            else:
                _print_status(f"Index client {esp} invalide", "RED", "⚠")
        except ValueError:
            if esp in c2.groups[group_name]:
                c2.groups[group_name].remove(esp)
                _print_status(f"Client {esp} retiré du groupe {group_name}", "GREEN")
            else:
                _print_status(f"Client {esp} n'est pas dans le groupe {group_name}", "RED", "⚠")

    if group_name in c2.groups and not c2.groups[group_name]:
        del c2.groups[group_name]
        _print_status(f"Groupe {group_name} supprimé car vide", "YELLOW", "!")
