# C2 Server Documentation

## TODO

**TODO:**

```md

- Implementer la coexistence entre multiflasher fichier (valid-id.txt - separator "\n" - C2 will only authorize device who are register in 'valid-id.txt' or add c2 command style 'authorizeId <id>' and he will be add into id list & valid-id.txt file)


```

## Overview

This C2 server is a Python-based control plane designed to manage a fleet of ESP devices (agents).

It provides a clean and extensible command-line interface to:

- Manage connected devices by unique ID
- Send commands to individual devices, groups, or all devices
- Organize devices into logical groups
- Display connection duration to the C2
- Support structured commands and raw developer commands
- Serve as a solid base for future plugins and services

The project intentionally favors simplicity, readability, and extensibility.

---

## Architecture Overview

```md

c2/
├── main.py # Entry point
├── core/
│ ├── device.py # Device model
│ ├── registry.py # Connected device registry
│ ├── crypto.py # Encryption wrapper
│ ├── transport.py # Message handling
│ └── groups.py # Group registry
├── commands/
│ ├── base.py # Command base class
│ ├── registry.py # Command registry
│ └── *.py # ESP command implementations
├── cli/
│ ├── cli.py # Interactive CLI
│ └── help.py # Help system
├── logs/
│ └── manager.py # ESP log handling
├── proto/
│ ├── command.proto # Protocol definition
│ └── command_pb2.py # Generated protobuf code
└── utils/
│ └── constant.py # Default script constant
```

---

## Core Concepts

### Device Identity

- Each ESP device is identified by a unique `esp_id`
- Devices are not identified by IP or port
- Reconnecting devices automatically replace their previous session

### Authentication Model

- Authentication is implicit
- If the server can successfully decrypt and parse a message, the device is considered valid
- No explicit handshake is required
- Fully compatible with existing firmware

---

## Running the Server

```bash
python main.py
```

## CLI Usage

### List Connected Devices

```md
list
*Example d'output:*

ID           IP              CONNECTED
----------------------------------------
ce4f626b     192.168.1.42    2m 14s
a91dd021     192.168.1.43    18s
```

The `CONNECTED` column shows how long the device has been connected to the c2

### Help Commands

```text
        help [commands]
*example:* help
output:

=== C2 HELP ===

CLI Commands:
  help [cmd]               Show this help
  list                     List connected ESP devices
  send <target> <command>  Send a command to ESP(s)
  group <action>           Manage ESP groups
  clear                    Clear the screen
  exit                     Exit the C2

ESP Commands:

  reboot     Reboot ESP

DEV MODE ENABLED:
  You can send arbitrary text commands:
  send <id> <any text>
  send group <name> <any text>
  send all <any text>

```

#### Help System

```md
General Help
help

Help for a Specific ESP Command
help reboot

Help for the send Command
help send


The help output is dynamically generated from the registered commands.
```

### Sending Commands

```md
    send <esp_id> <command>
*example:* send ce4f626b reboot # The device named "ce4f626b" will reboot
```

### Send to All Devices

```md
    send all [command]
*example:* send all reboot
```

### Send to a Group

```md
    send group bots 
*example:* send group bots reboot
```

### Developer Mode (RAW Commands)

When `DEV_MODE = True`, arbitrary text commands can be sent:

```md
    send <id> [test 12 34]
*example:* send ce4f626b custom start stream
output **ce4f626b:** "start stream"
```

The commands are sent as-is inside the `Command.command` field.

## Groups

### Add Devices to a Group

```md
    group add "group_name" <id/s>
*example:* group add bots ce4f626b a91dd021

### List Groups
```md
    group list
*Example output:*
bots: ce4f626b, a91dd021
trilat: e2, e3, e1
```

### Show Group Members

```md
    group show [group]
*example:* group show bots
output:
bots: ce4f626b, a91dd021
```

### Remove a Device from a Group

```md
group remove bots ce4f626b
```

Command System
Adding a New ESP Command

Create a new file in commands/, for example status.py

Implement the command handler:

from commands.base import CommandHandler
from proto.command_pb2 import Command

class StatusCommand(CommandHandler):
    name = "status"
    description = "Get device status"

    def build(self, args):
        cmd = Command()
        cmd.command = "status"
        return cmd.SerializeToString()


Register the command in main.py:

commands.register(StatusCommand())


The command will automatically appear in:

CLI tab completion

help

send <id> <command>

## Protocol Definition

// explain nano pb

### Command

```h
message Command {
  string command = 1;
}
```

### Response

```h
message Response {
  string tag = 1;
  string id = 2;
  string message = 3;
  bytes response_data = 4;
}
```

### Log

```h
message Log {
  string tag = 1;
  string id = 2;
  string log_message = 3;
  uint32 log_error_code = 4;
}
```

## Communication

The communication between c2 and bots are end-to-end encrypted.</br>
Method:

```md
    - ChaCha20 symmetric encryption
    - Base64 transport encoding
    - Encryption logic centralized in core/crypto.py
    - Fully compatible with current ESP firmware
```

## Design Limitations (Intentional)

```md
    - No persistent storage (groups reset on restart)
    - No request/response correlation (request-id)
    - No permissions or role management
    - No dynamic plugin loading
```

These are deferred intentionally to keep the core system minimal and clean.

## Suggested Future Extensions

Todo and additional features:

```md
- Plugin system (camera, proxy, trilateration/multilateration / etc.. )
- Persistent user & group storage (JSON) (Multi-Flasher -> devices.json -> id-list.csv [Allow ID on c2])
- Idle time display (last-seen)
- Request/response correlation with request-id
- Protocol versioning
```

---

### Authors

```md
- @off-path
- @Eun0us
```

---