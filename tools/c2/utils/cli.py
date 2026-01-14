from utils.manager import list_groups
from utils.constant import _color
# from utils.genhash import generate_random_endpoint, generate_token
from utils.utils import _print_status, _list_clients, _send_command
#from test.test import system_check
# from udp_server import start_cam_server, stop_cam_server
import os
import readline
from utils.sheldon import call

def _setup_cli(c2):
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(' \t\n;')
    readline.set_completer(c2._complete)
    readline.set_auto_history(True)

def _show_menu():
    menu = f"""
{_color('CYAN')}=============== Menu Server ==============={_color('RESET')}



  menu / help                   ->  List of commands



########## Manage Esp32 ##########


  add_group <group> <id_esp32>  ->  Add a client to a group
  list_groups                   ->  List all groups

  remove_group <group>          ->  Remove a group
  remove_esp_from <group> <esp> ->  Remove a client from a group

  reboot <id_esp32>             ->  Reboot a specific client
  reboot <group>                ->  Reboot all clients in a group
  reboot all                    ->  Reboot all clients



########## System C2 Commands ##########


  list                            ->  List all connected clients
  clear                           ->  Clear the terminal screen
  exit                            ->  Exit the server
  start/stop srv_video            ->  Register a camera service



########## Firmware Services client ##########


## Send Commands to firmware ##

    send <id_esp32> <message>                        ->  Send a message to a client
    or 
    send <id_esp32> <start/stop> <service> <args>    -> Start/Stop a service on a specific client

## Start/Stop Services on clients ##

    start proxy <IP> <PORT>         ->  Start a reverse proxy on ur ip port for a specific client
    stop proxy                      ->  Stop the revproxy on a specific client

    start stream <IP> <PORT>        ->  Start camera stream on a specific client
    stop stream                     ->  Stop camera stream on a specific client

    start ap <WIFI_SSID> <PASSWORD> ->  Start an access point on a specific client
                                         (WIFI_SSID and PASSWORD are optional, default_SSID="ESP_32_WIFI_SSID")
    stop ap                         ->  Stop the access point on a specific client
    list_clients                    ->  List all connected clients on the access point

    start sniffer                   ->  Start packet sniffing on clients connected to the access point
    stop sniffer                    ->  Stop packet sniffing on clients connected to the access point

    start captive_portal <WIFI_SSID>  ->  Start a server on a specific client 
                                         (WIFI_SSID is optional, default_SSID="ESP_32_WIFI_SSID")
    stop captive_portal               ->  Stop the server on a specific client 

"""
    print(menu)




def _show_banner():
    banner = rf"""
{_color('CYAN')}Authors : Eunous/grogore, itsoktocryyy, offpath, Wepfen, p2lu

___________
\_   _____/ ____________ |__|  |   ____   ____
 |    __)_ /  ___/\____ \|  |  |  /  _ \ /    \
 |        \\___ \ |  |_> >  |  |_(  <_> )   |  \
/_______  /____  >|   __/|__|____/\____/|___|  /
        \/     \/ |__|                       \/

=============== v 0.1 ==============={_color('RESET')}
"""
    print(banner)




def cli_interface(self):
    _show_banner()
    _show_menu()

    # def _cmd_start(parts):
    #     if len(parts) > 1 and parts[1] == "srv_video":
    #         start_cam_server()
        

    # def _cmd_stop(parts):
    #     if len(parts) > 1 and parts[1] == "srv_video":
    #         stop_cam_server()
        
    commands = {
        "menu": lambda parts: _show_menu(),
        "help": lambda parts: _show_menu(),
        "send": lambda parts: _send_command(self, " ".join(parts)),
        "list": lambda parts: _list_clients(self),
        "clear": lambda parts: os.system('cls' if os.name == 'nt' else 'clear'),
        "exit": lambda parts: self._shutdown(),
        "reboot": lambda parts: self._handle_reboot(parts),
        "add_group": lambda parts: self._handle_add_group(parts),
        "list_groups": lambda parts: list_groups(self),
        "remove_group": lambda parts: self._handle_remove_group(parts),
        "remove_esp_from": lambda parts: self._handle_remove_esp_from(parts),
        # "start": _cmd_start,
        # "stop": _cmd_stop,
        # "system_check": lambda parts: system_check(self),
    }

    while True:
        choix = input(f"\n{_color('BLUE')}striker:> {_color('RESET')}").strip()
        if not choix:
            continue

        parts = choix.split()
        cmd = parts[0]

        try:
            if cmd in commands:
                commands[cmd](parts)
            else:
                call(choix)
        except Exception as e:
            _print_status(f"Erreur: {str(e)}", "RED", "⚠")
