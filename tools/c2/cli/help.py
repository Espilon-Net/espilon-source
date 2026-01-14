from utils.display import Display


class HelpManager:
    def __init__(self, command_registry, dev_mode: bool = False):
        self.commands = command_registry
        self.dev_mode = dev_mode

    def show(self, args: list[str]):
        if args:
            self._show_command_help(args[0])
        else:
            self._show_global_help()

    def _show_global_help(self):
        Display.system_message("=== ESPILON C2 HELP ===")
        print("\nCLI Commands:")
        print("  help [command]    Show this help or help for a specific command")
        print("  list              List connected ESP devices")
        print("  send <target>     Send a command to ESP device(s)")
        print("  group <action>    Manage ESP device groups (add, remove, list, show)")
        print("  active_commands   List all currently running commands")
        print("  clear             Clear the terminal screen")
        print("  exit              Exit the C2 application")

        print("\nESP Commands (available to send to devices):")
        for name in self.commands.list():
            handler = self.commands.get(name)
            print(f"  {name:<15} {handler.description}")

        if self.dev_mode:
            Display.system_message("\nDEV MODE ENABLED:")
            print("  You can send arbitrary text commands: send <target> <any text>")

    def _show_command_help(self, command_name: str):
        if command_name == "list":
            Display.system_message("Help for 'list' command:")
            print("  Usage: list")
            print("  Description: Displays a table of all currently connected ESP devices,")
            print("               including their ID, IP address, connection duration, and last seen timestamp.")
        elif command_name == "send":
            Display.system_message("Help for 'send' command:")
            print("  Usage: send <device_id|all|group <group_name>> <command_name> [args...]")
            print("  Description: Sends a command to one or more ESP devices.")
            print("  Examples:")
            print("    send 1234567890 reboot")
            print("    send all get_status")
            print("    send group my_group ping 8.8.8.8")
        elif command_name == "group":
            Display.system_message("Help for 'group' command:")
            print("  Usage: group <action> [args...]")
            print("  Actions:")
            print("    add <group_name> <device_id1> [device_id2...] - Add devices to a group.")
            print("    remove <group_name> <device_id1> [device_id2...] - Remove devices from a group.")
            print("    list - List all defined groups and their members.")
            print("    show <group_name> - Show members of a specific group.")
            print("  Examples:")
            print("    group add my_group 1234567890 ABCDEF1234")
            print("    group remove my_group 1234567890")
            print("    group list")
            print("    group show my_group")
        elif command_name in ["clear", "exit"]:
            Display.system_message(f"Help for '{command_name}' command:")
            print(f"  Usage: {command_name}")
            print(f"  Description: {command_name.capitalize()}s the terminal screen." if command_name == "clear" else f"  Description: {command_name.capitalize()}s the C2 application.")
        else:
            # Check if it's an ESP command
            handler = self.commands.get(command_name)
            if handler:
                Display.system_message(f"Help for ESP Command '{command_name}':")
                print(f"  Description: {handler.description}")
                # Assuming ESP commands might have a usage string or more detailed help
                if hasattr(handler, 'usage'):
                    print(f"  Usage: {handler.usage}")
                if hasattr(handler, 'long_description'):
                    print(f"  Details: {handler.long_description}")
            else:
                Display.error(f"No help available for command '{command_name}'.")
