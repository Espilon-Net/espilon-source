# Epsilon Tools

This directory contains tools for managing and deploying Epsilon ESP32 agents.

## C2 Server (c2/)

The C2 (Command & Control) server manages communication with deployed ESP32 agents.

### C3PO - Main C2 Server

**c3po** is the primary C2 server used to control Epsilon bots.

Features:

- Asynchronous Python server (asyncio)
- Device registry and management
- Group-based device organization
- Encrypted communications (ChaCha20)
- Interactive CLI interface
- Command dispatching to individual devices, groups, or all

See [c2/README.md](c2/README.md) for complete C2 documentation.

Quick start:

```bash
cd c2
python3 c3po.py --port 2626
```

Authors: **@off-path**, **@eun0us**

## Multi-Device Flasher (flasher/)

The **flasher** tool automates building and flashing multiple ESP32 devices with custom configurations.

### Features

- Batch processing of multiple devices
- Support for WiFi and GPRS modes
- Per-device configuration (ID, network, modules)
- Automatic hostname randomization
- Build-only and flash-only modes
- Full module configuration (Network, Recon, FakeAP)

### Quick Start

1. Edit [flasher/devices.json](flasher/devices.json):

```json
   {
     "project": "/home/user/epsilon/espilon_bot",
     "devices": [
       {
         "device_id": "ce4f626b",
         "port": "/dev/ttyUSB0",
         "srv_ip": "192.168.1.13",
         "srv_port": 2626,
         "network_mode": "wifi",
         "wifi_ssid": "YourWiFi",
         "wifi_pass": "YourPassword",
         "module_network": true,
         "module_recon": false,
         "module_fakeap": false
       }
     ]
   }
```

2. Flash all devices:

```bash
cd flasher
python3 flash.py --config devices.json
```

### Configuration Options

Each device supports:

| Field | Description |
|-------|-------------|
| `device_id` | Unique device identifier (8 hex chars) |
| `port` | Serial port (e.g., `/dev/ttyUSB0`) |
| `srv_ip` | C2 server IP address |
| `srv_port` | C2 server port (default: 2626) |
| `network_mode` | `"wifi"` or `"gprs"` |
| `wifi_ssid` | WiFi SSID (WiFi mode) |
| `wifi_pass` | WiFi password (WiFi mode) |
| `gprs_apn` | GPRS APN (GPRS mode, default: "sl2sfr") |
| `hostname` | Network hostname (random if not set) |
| `module_network` | Enable network commands (default: true) |
| `module_recon` | Enable reconnaissance module |
| `module_fakeap` | Enable fake AP module |
| `recon_camera` | Enable camera reconnaissance (ESP32-CAM) |
| `recon_ble_trilat` | Enable BLE trilateration |
| `crypto_key` | ChaCha20 encryption key (32 chars) |
| `crypto_nonce` | ChaCha20 nonce (12 chars) |

### Hostname Randomization

The flasher automatically randomizes device hostnames to blend in on networks:

- iPhone models (iPhone-15-pro-max, iPhone-14, etc.)
- Android devices (galaxy-s24-ultra, pixel-8-pro, xiaomi-14, etc.)
- Windows PCs (DESKTOP-XXXXXXX)

This helps devices appear as legitimate consumer electronics during authorized security testing.

### Manual Mode

Flash a single device without a config file:

```bash
# WiFi mode
python3 flash.py --manual \
  --project /home/user/epsilon/espilon_bot \
  --device-id abc12345 \
  --port /dev/ttyUSB0 \
  --srv-ip 192.168.1.100 \
  --wifi-ssid MyWiFi \
  --wifi-pass MyPassword

# GPRS mode
python3 flash.py --manual \
  --project /home/user/epsilon/espilon_bot \
  --device-id def67890 \
  --port /dev/ttyUSB1 \
  --srv-ip 203.0.113.10 \
  --network-mode gprs \
  --gprs-apn sl2sfr
```

### Build-Only Mode

Generate firmware without flashing:

```bash
python3 flash.py --config devices.json --build-only
```

Firmware saved to: `espilon_bot/firmware/<device_id>.bin`

### Flash-Only Mode

Flash pre-built firmware:

```bash
python3 flash.py --config devices.json --flash-only
```

See [flasher/README.md](flasher/README.md) for complete documentation.

## NanoPB Tools (nan/)

Tools for Protocol Buffers (nanoPB) code generation for the embedded communication protocol.

Used during development to regenerate Protocol Buffer bindings for ESP32 and Python.

## Additional Resources

- [Installation Guide](../docs/INSTALL.md) - Full Epsilon setup
- [Hardware Guide](../docs/HARDWARE.md) - Supported boards
- [Module API](../docs/MODULES.md) - Available commands
- [Protocol Specification](../docs/PROTOCOL.md) - C2 protocol details
- [Security](../docs/SECURITY.md) - Security best practices

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to Epsilon tools.

## License

Part of the Epsilon project. See [LICENSE](../LICENSE) for details.
