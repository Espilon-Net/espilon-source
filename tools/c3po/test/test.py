from utils.utils import _print_status, send_to_client
from utils.reboot import reboot
from utils.manager import add_to_group, remove_group, remove_esp_from_group
import time


def system_check(c2):
    _print_status("=============== TEST GLOBAL DU SYSTÈME ===============", "CYAN")
    
    # 1. Liste des clients connectés
    _print_status("[1/10] Liste des clients connectés", "YELLOW")
    if not c2.clients:
        _print_status("Aucun client connecté", "RED", "✗")
        return
    for i, (addr, _) in enumerate(c2.clients.items(), 1):
        print(f"  {i}. {addr[0]}:{addr[1]}")
    _print_status("Liste récupérée", "GREEN", "✓")
    
    # 2. Envoi d'une commande simple ("ls") à chaque client
    _print_status("[2/10] Test d'envoi de commande à chaque client", "YELLOW")
    for addr in list(c2.clients.keys()):
        try:
            response = send_to_client(c2, addr, "ls", wait_response=True)
            if response:
                _print_status(f"Réponse reçue de {addr[0]}", "GREEN", "✓")
            else:
                _print_status(f"Aucune réponse de {addr[0]}", "RED", "✗")
        except:
            _print_status(f"Erreur d'envoi vers {addr[0]}", "RED", "✗")
    
    # 3. Création et remplissage d'un groupe de test
    _print_status("[3/10] Création d’un groupe test et ajout de clients", "YELLOW")
    test_group = "test_all"
    for i, addr in enumerate(c2.clients.keys()):
        if i < 2:  # Limite à 2 clients pour le test
            add_to_group(c2, test_group, addr)
    if test_group in c2.groups:
        _print_status(f"Groupe '{test_group}' créé avec {len(c2.groups[test_group])} clients", "GREEN", "✓")
    else:
        _print_status("Échec création groupe", "RED", "✗")
    
    # 4. Liste des groupes
    _print_status("[4/10] Listing des groupes", "YELLOW")
    if c2.groups:
        for group, members in c2.groups.items():
            print(f"  {group} : {members}")
        _print_status("Groupes listés", "GREEN", "✓")
    else:
        _print_status("Aucun groupe trouvé", "RED", "✗")

    # 5. Reboot d’un seul client
    _print_status("[5/10] Reboot d’un seul client", "YELLOW")
    first_client = list(c2.clients.keys())[0]
    reboot(c2, first_client, mode="single")
    time.sleep(5)

    # 6. Reboot du groupe
    _print_status("[6/10] Reboot du groupe", "YELLOW")
    reboot(c2, test_group, mode="group")
    time.sleep(5)

    # 7. Reboot de tous les clients
    _print_status("[7/10] Reboot de tous les clients", "YELLOW")
    reboot(c2, mode="all")
    time.sleep(5)

    # 8. Attente et vérification de reconnexion
    _print_status("[8/10] Attente de reconnexion des clients", "YELLOW", "!")
    time.sleep(5)
    if c2.clients:
        for addr in c2.clients.keys():
            print(f"  - {addr[0]}:{addr[1]}")
        _print_status("Clients reconnectés", "GREEN", "✓")
    else:
        _print_status("Aucun client reconnecté", "RED", "✗")

    # 9. Retirer un client du groupe
    # check si il y a plusieurs clients dans le groupe
    # si oui, retirer le premier
    # sinon passer le test
    _print_status("[9/10] Retirer un client du groupe", "YELLOW")
    if len(c2.groups[test_group]) > 1:
        first_client = c2.groups[test_group][0]
        remove_esp_from_group(c2, test_group, [first_client])
        if first_client not in c2.groups[test_group]:
            _print_status(f"Client {first_client} retiré du groupe {test_group}", "GREEN", "✓")
        else:
            _print_status(f"Échec de retrait du client {first_client} du groupe {test_group}", "RED", "✗")
    else:
        _print_status("Groupe ne contient qu'un seul client, pas de retrait effectué", "YELLOW", "!")

    # 10. Suppression du groupe
    _print_status("[10/10] Suppression du groupe de test", "YELLOW")
    if test_group in c2.groups:
        remove_group(c2, test_group)
        if test_group not in c2.groups:
            _print_status("Groupe supprimé", "GREEN", "✓")
        else:
            _print_status("Échec de suppression du groupe", "RED", "✗")
    
    _print_status("=============== TEST TERMINÉ ===============", "CYAN")
