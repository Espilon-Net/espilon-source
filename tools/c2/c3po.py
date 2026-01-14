#!/usr/bin/env python3
import socket
import threading
import re
import sys
import time # Added missing import

#!/usr/bin/env python3
import socket
import threading
import re
import sys

from core.registry import DeviceRegistry
from core.transport import Transport
from logs.manager import LogManager
from cli.cli import CLI
from commands.registry import CommandRegistry
from commands.reboot import RebootCommand
from core.groups import GroupRegistry
from utils.constant import HOST, PORT
from utils.display import Display # Import Display utility

# Strict base64 validation (ESP sends BASE64 + '\n')
BASE64_RE = re.compile(br'^[A-Za-z0-9+/=]+$')

RX_BUF_SIZE = 4096
DEVICE_TIMEOUT_SECONDS = 60 # Devices are considered inactive after 60 seconds without a heartbeat
HEARTBEAT_CHECK_INTERVAL = 10 # Check every 10 seconds


# ============================================================
# Client handler
# ============================================================
def client_thread(sock: socket.socket, addr, transport: Transport, registry: DeviceRegistry):
    Display.system_message(f"Client connected from {addr}")
    buffer = b""
    device_id = None # To track which device disconnected

    try:
        while True:
            data = sock.recv(RX_BUF_SIZE)
            if not data:
                break

            buffer += data

            # Strict framing by '\n' (ESP behavior)
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.strip()

                if not line:
                    continue

                # Ignore noise / invalid frames
                if not BASE64_RE.match(line):
                    Display.system_message(f"Ignoring non-base64 data from {addr}")
                    continue

                try:
                    # Pass registry to handle_incoming to update device status
                    transport.handle_incoming(sock, addr, line)
                    # After successful handling, try to get device_id
                    # This is a simplification; a more robust solution might pass device_id from transport
                    # For now, we assume the first message will register the device
                    if not device_id and registry.get_device_by_sock(sock):
                        device_id = registry.get_device_by_sock(sock).id
                except Exception as e:
                    Display.error(f"Transport error from {addr}: {e}")

    except Exception as e:
        Display.error(f"Client error from {addr}: {e}")

    finally:
        try:
            sock.close()
        except Exception:
            pass
        if device_id:
            Display.device_event(device_id, "Disconnected")
            registry.remove(device_id) # Remove device from registry on disconnect
        else:
            Display.system_message(f"Client disconnected from {addr}")


# ============================================================
# Main server
# ============================================================
def main():
    header = """

    $$$$$$$\   $$$$$$\  $$\   $$\  $$$$$$\  $$$$$$$$\  $$$$$$\   $$$$$$\   $$$$$$\ 

$$$$$$$$\  $$$$$$\  $$$$$$$\ $$$$$$\ $$\       $$$$$$\  $$\   $$\        $$$$$$\   $$$$$$\        
$$  _____|$$  __$$\ $$  __$$\\_$$  _|$$ |     $$  __$$\ $$$\  $$ |      $$  __$$\ $$  __$$\       
$$ |      $$ /  \__|$$ |  $$ | $$ |  $$ |     $$ /  $$ |$$$$\ $$ |      $$ /  \__|\__/  $$ |      
$$$$$\    \$$$$$$\  $$$$$$$  | $$ |  $$ |     $$ |  $$ |$$ $$\$$ |      $$ |       $$$$$$  |      
$$  __|    \____$$\ $$  ____/  $$ |  $$ |     $$ |  $$ |$$ \$$$$ |      $$ |      $$  ____/       
$$ |      $$\   $$ |$$ |       $$ |  $$ |     $$ |  $$ |$$ |\$$$ |      $$ |  $$\ $$ |            
$$$$$$$$\ \$$$$$$  |$$ |     $$$$$$\ $$$$$$$$\ $$$$$$  |$$ | \$$ |      \$$$$$$  |$$$$$$$$\       
\________| \______/ \__|     \______|\________|\______/ \__|  \__|       \______/ \________|      
                                                                                                  
                                                                                                  
                                                                                                  
 $$$$$$\   $$$$$$\  $$$$$$$\   $$$$$$\                                                            
$$  __$$\ $$ ___$$\ $$  __$$\ $$  __$$\                                                           
$$ /  \__|\_/   $$ |$$ |  $$ |$$ /  $$ |                                                          
$$ |        $$$$$ / $$$$$$$  |$$ |  $$ |                                                          
$$ |        \___$$\ $$  ____/ $$ |  $$ |                                                          
$$ |  $$\ $$\   $$ |$$ |      $$ |  $$ |                                                          
\$$$$$$  |\$$$$$$  |$$ |       $$$$$$  |                                                          
 \______/  \______/ \__|       \______/                                                             

    ESPILON C2 Framework - Command and Control Server
    """
    Display.system_message(header)
    Display.system_message("Initializing ESPILON C2 core...")

    # ============================
    # Core components
    # ============================
    registry = DeviceRegistry()
    logger = LogManager()
    
    # Initialize CLI first, then pass it to Transport
    commands = CommandRegistry()
    commands.register(RebootCommand())
    groups = GroupRegistry()
    
    # Placeholder for CLI, will be properly initialized after Transport
    cli_instance = None 
    transport = Transport(registry, logger, cli_instance) # Pass a placeholder for now

    cli_instance = CLI(registry, commands, groups, transport)
    transport.set_cli(cli_instance) # Set the actual CLI instance in transport

    cli = cli_instance # Assign the initialized CLI to 'cli'

    # ============================
    # TCP server
    # ============================
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((HOST, PORT))
    except OSError as e:
        Display.error(f"Failed to bind server to {HOST}:{PORT}: {e}")
        sys.exit(1)

    server.listen()
    Display.system_message(f"Server listening on {HOST}:{PORT}")

    # Function to periodically check device status
    def device_status_checker():
        while True:
            now = time.time()
            for device in registry.all():
                if now - device.last_seen > DEVICE_TIMEOUT_SECONDS:
                    if device.status != "Inactive":
                        device.status = "Inactive"
                        Display.device_event(device.id, "Status changed to Inactive (timeout)")
                elif device.status == "Inactive" and now - device.last_seen <= DEVICE_TIMEOUT_SECONDS:
                    # If a device that was inactive sends a heartbeat, set it back to Connected
                    device.status = "Connected"
                    Display.device_event(device.id, "Status changed to Connected (heartbeat received)")
            time.sleep(HEARTBEAT_CHECK_INTERVAL)

    # CLI thread
    threading.Thread(target=cli.loop, daemon=True).start()
    # Device status checker thread
    threading.Thread(target=device_status_checker, daemon=True).start()

    # Accept loop
    while True:
        try:
            sock, addr = server.accept()
            threading.Thread(
                target=client_thread,
                args=(sock, addr, transport, registry), # Pass registry to client_thread
                daemon=True
            ).start()
        except KeyboardInterrupt:
            Display.system_message("Shutdown requested. Exiting...")
            break
        except Exception as e:
            Display.error(f"Server error: {e}")

    server.close()


if __name__ == "__main__":
    main()
