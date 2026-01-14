import readline
import os
import time

from utils.display import Display
from cli.help import HelpManager
from core.transport import Transport
from proto.c2_pb2 import Command

DEV_MODE = True


class CLI:
    def __init__(self, registry, commands, groups, transport: Transport):
        self.registry = registry
        self.commands = commands
        self.groups = groups
        self.transport = transport
        self.help_manager = HelpManager(commands, DEV_MODE)
        self.active_commands = {} # {request_id: {"device_id": ..., "command_name": ..., "start_time": ..., "status": "running"}}

        readline.parse_and_bind("tab: complete")
        readline.set_completer(self._complete)

    # ================= TAB COMPLETION =================

    def _complete(self, text, state):
        buffer = readline.get_line_buffer()
        parts = buffer.split()

        options = []

        if len(parts) == 1:
            options = ["send", "list", "group", "help", "clear", "exit", "active_commands"]

        elif parts[0] == "send":
            if len(parts) == 2:  # Completing target (device ID, 'all', 'group')
                options = ["all", "group"] + self.registry.ids()
            elif len(parts) == 3 and parts[1] == "group":  # Completing group name after 'send group'
                options = list(self.groups.all_groups().keys())
            elif (len(parts) == 3 and parts[1] != "group") or (len(parts) == 4 and parts[1] == "group"):  # Completing command name
                options = self.commands.list()
            # Add more logic here if commands have arguments that can be tab-completed

        elif parts[0] == "group":
            if len(parts) == 2:  # Completing group action
                options = ["add", "remove", "list", "show"]
            elif parts[1] == "add" and len(parts) >= 3:  # Completing device IDs for 'group add'
                # Suggest available device IDs that are not already in the group being added to
                group_name = parts[2] if len(parts) > 2 else ""
                current_group_members = self.groups.get(group_name) if group_name else []
                all_device_ids = set(self.registry.ids())
                options = sorted(list(all_device_ids - set(current_group_members)))
            elif parts[1] in ("remove", "show") and len(parts) == 3:  # Completing group names for 'group remove/show'
                options = list(self.groups.all_groups().keys())
            elif parts[1] == "remove" and len(parts) >= 4: # Completing device IDs for 'group remove'
                group_name = parts[2]
                options = self.groups.get(group_name)

        matches = [o for o in options if o.startswith(text)]
        return matches[state] if state < len(matches) else None

    # ================= MAIN LOOP =================

    def loop(self):
        while True:
            cmd = input(Display.cli_prompt()).strip()
            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0]

            if action == "help":
                self.help_manager.show(parts[1:])
                continue

            if action == "exit":
                return

            if action == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue

            if action == "list":
                self._handle_list()
                continue

            if action == "group":
                self._handle_group(parts[1:])
                continue

            if action == "send":
                self._handle_send(parts)
                continue
            
            if action == "active_commands":
                self._handle_active_commands()
                continue

            Display.error("Unknown command")

    # ================= HANDLERS =================

    def _handle_list(self):
        now = time.time()
        active_devices = self.registry.all()

        if not active_devices:
            Display.system_message("No devices currently connected.")
            return

        Display.system_message("Connected Devices:")
        Display.print_table_header(["ID", "IP Address", "Status", "Connected For", "Last Seen"])

        for d in active_devices:
            connected_for = Display.format_duration(now - d.connected_at)
            last_seen_duration = Display.format_duration(now - d.last_seen)
            Display.print_table_row([d.id, d.address[0], d.status, connected_for, last_seen_duration])

    def _handle_send(self, parts):
        if len(parts) < 3:
            Display.error("Usage: send <id|all|group> <command> [args...]")
            return

        target_specifier = parts[1]
        command_parts = parts[2:]

        devices_to_target = []
        target_description = ""

        # Resolve devices based on target_specifier
        if target_specifier == "all":
            devices_to_target = self.registry.all()
            target_description = "all connected devices"
        elif target_specifier == "group":
            if len(command_parts) < 2:
                Display.error("Usage: send group <name> <command> [args...]")
                return
            group_name = command_parts[0]
            command_parts = command_parts[1:]
            group_members_ids = self.groups.get(group_name)
            if not group_members_ids:
                Display.error(f"Group '{group_name}' not found or is empty.")
                return
            
            active_group_devices = []
            for esp_id in group_members_ids:
                dev = self.registry.get(esp_id)
                if dev:
                    active_group_devices.append(dev)
                else:
                    Display.device_event(esp_id, f"Device in group '{group_name}' is not currently connected.")
            
            if not active_group_devices:
                Display.error(f"No active devices found in group '{group_name}'.")
                return
            
            devices_to_target = active_group_devices
            target_description = f"group '{group_name}' ({', '.join([d.id for d in devices_to_target])})"
        else:
            dev = self.registry.get(target_specifier)
            if dev:
                devices_to_target.append(dev)
                target_description = f"device '{target_specifier}'"
            else:
                Display.error(f"Device '{target_specifier}' not found.")
                return

        if not devices_to_target:
            Display.error("No target devices resolved for sending command.")
            return

        # Build Command
        cmd_name = command_parts[0]
        argv = command_parts[1:]

        request_id_base = f"req-{int(time.time())}"
        Display.system_message(f"Sending command '{cmd_name}' to {target_description}...")

        for i, d in enumerate(devices_to_target):
            cmd = Command()
            cmd.device_id = d.id
            cmd.command_name = cmd_name
            cmd.argv.extend(argv)
            
            request_id = f"{request_id_base}-{i}"
            cmd.request_id = request_id

            Display.command_sent(d.id, cmd_name, request_id)
            self.transport.send_command(d.sock, cmd)
            self.active_commands[request_id] = {
                "device_id": d.id,
                "command_name": cmd_name,
                "start_time": time.time(),
                "status": "running",
                "output": []
            }

    def handle_command_response(self, request_id: str, device_id: str, payload: str, eof: bool):
        if request_id in self.active_commands:
            command_info = self.active_commands[request_id]
            command_info["output"].append(payload)
            if eof:
                command_info["status"] = "completed"
                Display.command_response(request_id, device_id, f"Command completed in {Display.format_duration(time.time() - command_info['start_time'])}")
                # Optionally print full output here if not already streamed
                # Display.command_response(request_id, device_id, "\n".join(command_info["output"]))
                del self.active_commands[request_id]
            else:
                # For streaming output, Display.command_response already prints each line
                pass
        else:
            Display.device_event(device_id, f"Received response for unknown command {request_id}: {payload}")

    def _handle_group(self, parts):
        if not parts:
            Display.error("Usage: group <add|remove|list|show>")
            return

        cmd = parts[0]

        if cmd == "add" and len(parts) >= 3:
            group = parts[1]
            added_devices = []
            for esp_id in parts[2:]:
                if self.registry.get(esp_id): # Only add if device exists
                    self.groups.add_device(group, esp_id)
                    added_devices.append(esp_id)
                else:
                    Display.device_event(esp_id, "Device not found, skipping group add.")
            if added_devices:
                Display.system_message(f"Group '{group}' updated. Added: {', '.join(added_devices)}")
            else:
                Display.system_message(f"No valid devices to add to group '{group}'.")


        elif cmd == "remove" and len(parts) >= 3:
            group = parts[1]
            removed_devices = []
            for esp_id in parts[2:]:
                if esp_id in self.groups.get(group):
                    self.groups.remove_device(group, esp_id)
                    removed_devices.append(esp_id)
                else:
                    Display.device_event(esp_id, f"Device not in group '{group}', skipping remove.")
            if removed_devices:
                Display.system_message(f"Group '{group}' updated. Removed: {', '.join(removed_devices)}")
            else:
                Display.system_message(f"No specified devices found in group '{group}' to remove.")

        elif cmd == "list":
            all_groups = self.groups.all_groups()
            if not all_groups:
                Display.system_message("No groups defined.")
                return
            Display.system_message("Defined Groups:")
            for g, members in all_groups.items():
                Display.system_message(f"  {g}: {', '.join(members) if members else 'No members'}")

        elif cmd == "show" and len(parts) == 2:
            group_name = parts[1]
            members = self.groups.get(group_name)
            if members:
                Display.system_message(f"Members of group '{group_name}': {', '.join(members)}")
            else:
                Display.system_message(f"Group '{group_name}' not found or empty.")

        else:
            Display.error("Invalid group command usage. See 'help group' for details.")

    def _handle_active_commands(self):
        if not self.active_commands:
            Display.system_message("No commands are currently active.")
            return

        Display.system_message("Active Commands:")
        Display.print_table_header(["Request ID", "Device ID", "Command", "Status", "Elapsed Time"])

        now = time.time()
        for req_id, cmd_info in self.active_commands.items():
            elapsed_time = Display.format_duration(now - cmd_info["start_time"])
            Display.print_table_row([
                req_id,
                cmd_info["device_id"],
                cmd_info["command_name"],
                cmd_info["status"],
                elapsed_time
            ])
