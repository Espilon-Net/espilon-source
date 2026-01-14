HOST = '0.0.0.0'
PORT = 2626

# ANSI color codes
COLORS = {
    "RESET": "\033[0m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "BLUE": "\033[94m",
    "YELLOW": "\033[93m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m"
}

def _color(color_name):
    return COLORS.get(color_name, "")

COMMANDS = [
    "", "send", "list", "clear", "exit", "reboot", 
    "add_group", "list_groups", "remove_group", 
    "remove_esp_from", "system_check", "menu", "help",
    "srv_video"
]
