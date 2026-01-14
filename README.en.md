# Espilon

**Espilon** is an embedded agent framework for ESP32 microcontrollers, designed for network surveillance, reconnaissance, and distributed communication in constrained IoT environments. Developed in C with **ESP-IDF**, Espilon demonstrates how to build lightweight, efficient implants capable of communicating via Wi-Fi or GPRS.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.3.2-green.svg)](https://github.com/espressif/esp-idf)
[![Platform](https://img.shields.io/badge/Platform-ESP32-red.svg)](https://www.espressif.com/en/products/socs/esp32)

> **IMPORTANT:** This is a security research and educational tool. It must only be used in authorized penetration testing, controlled environments, CTF competitions, or educational contexts. Unauthorized use against systems you don't own or have explicit permission to test is illegal.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Modules](#modules)
- [C2 Server](#c2-server)
- [Configuration](#configuration)
- [Hardware Requirements](#hardware-requirements)
- [Security](#security)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Authors](#authors)
- [License](#license)

---

## Overview

Initially presented as a PoC at **Le Hack (June 2025)**, Espilon has evolved into a **modular codebase** that enables:

- Understanding embedded agent construction
- Manipulating ESP32's low-level network stack
- Developing specialized modules (sniffer, proxy, reconnaissance, vision)
- Studying IoT communication scenarios in cybersecurity research contexts

The framework is **compatible with all ESP32 variants** supported by ESP-IDF and offers two network modes:

- **Wi-Fi** (802.11 b/g/n)
- **GPRS** (SIM800/808 modules)

---

## Features

### Core Capabilities

- **Dual Network Backend**: WiFi or GPRS connectivity
- **Encrypted C2 Communication**: ChaCha20 encryption with Protocol Buffers serialization
- **Modular Architecture**: Enable/disable components at compile time
- **Async Command Execution**: FreeRTOS-based task management
- **Auto-reconnection**: Persistent TCP connection with automatic recovery
- **Multi-device Support**: Centralized C2 can manage multiple agents simultaneously

### Network Tools

- **ARP Scanner**: Local network discovery
- **Custom ICMP Ping**: Network reachability testing
- **TCP Reverse Proxy**: Traffic forwarding and tunneling
- **802.11 Packet Sniffer**: Monitor mode packet capture
- **Network Traffic Generation**: Controlled testing scenarios

### Wireless Manipulation

- **Fake Access Point**: Rogue AP with WPA2 support
- **Captive Portal**: DNS hijacking with customizable landing page
- **AP+STA Concurrent Mode**: NAPT routing implementation
- **Client Session Tracking**: Monitor connected devices

### Reconnaissance

- **ESP32-CAM Support**: Image capture and UDP streaming
- **BLE Trilateration**: Position estimation using RSSI (WIP)
- **Network Discovery**: Automated reconnaissance capabilities

---

## Architecture

Espilon is built on a **unified core** with an **ESP-IDF component system** activated at compile time.

```
┌─────────────────────────────────────────────────┐
│                  ESP32 Agent                    │
├─────────────────────────────────────────────────┤
│  Modules: Network | FakeAP | Recon | System    │
├─────────────────────────────────────────────────┤
│         Command Registry & Dispatcher           │
├─────────────────────────────────────────────────┤
│    Core: WiFi/GPRS | Crypto | Protobuf | COM   │
├─────────────────────────────────────────────────┤
│         LWIP Stack | FreeRTOS | ESP-IDF         │
└─────────────────────────────────────────────────┘
                       │
                  TCP (encrypted)
                       │
┌─────────────────────────────────────────────────┐
│              C2 Server (Python)                 │
├─────────────────────────────────────────────────┤
│   CLI | Device Registry | Group Management     │
├─────────────────────────────────────────────────┤
│    Transport | Crypto | Protobuf | Commands    │
└─────────────────────────────────────────────────┘
```

### Core Components

The core provides:

- **Network Backend**: WiFi or GPRS (configured via `menuconfig`)
- **Persistent TCP/IP**: Connection management with auto-reconnection
- **Encryption**: ChaCha20 stream cipher
- **Serialization**: nanoPB (Protocol Buffers for embedded systems)
- **Command Parser**: Dispatches commands to registered handlers
- **FreeRTOS Tasks**: Dedicated tasks for connection, processing, and crypto
- **State Management**: Connection state tracking and recovery

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed information.

---

## Getting Started

### Prerequisites

- **ESP-IDF v5.3.2** (or compatible version)
- Python 3.8+ (for C2 server and tools)
- ESP32 development board
- USB-to-Serial adapter (if not integrated)

### Quick Start

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/epsilon.git
cd epsilon
```

2. **Set up ESP-IDF environment**

```bash
. $HOME/esp-idf/export.sh
```

3. **Configure the firmware**

```bash
cd espilon_bot
idf.py menuconfig
```

Navigate to `Espilon Configuration` and set:
- Network backend (WiFi/GPRS)
- C2 server IP and port
- Crypto keys (**CHANGE DEFAULT KEYS**)
- Module selection

4. **Build and flash**

```bash
idf.py build
idf.py -p /dev/ttyUSB0 flash
idf.py monitor
```

5. **Start the C2 server**

```bash
cd tools/c2
python3 c3po.py --port 2626
```

For detailed installation instructions, see [INSTALL.md](docs/INSTALL.md).

---

## Modules

Espilon uses a modular architecture where each module is an isolated ESP-IDF component.

### System Module

Basic device management:
- `system_reboot` - Reboot the device
- `system_mem` - Memory usage statistics
- `system_uptime` - Device uptime

### Network Module

Advanced network capabilities:
- `ping` - ICMP ping with custom parameters
- `arp_scan` - Discover devices on local network
- `proxy_start/stop` - TCP reverse proxy
- `dos_tcp` - Controlled traffic generation (testing only)

### FakeAP Module

Wireless manipulation (authorized testing only):
- `fakeap_start` - Create rogue access point
- `portal_start` - Launch captive portal with DNS hijacking
- `sniffer_start` - 802.11 packet capture
- `fakeap_stop` - Cleanup and restore

### Recon Module

Reconnaissance capabilities:
- `capture` - ESP32-CAM snapshot (JPEG)
- `stream_start/stop` - UDP video streaming
- `trilat_scan` - BLE device discovery (WIP)

See [MODULES.md](docs/MODULES.md) for complete API documentation.

---

## 🎮 C2 Server

Espilon includes a custom C2 server (`c3po`) specifically designed for ESP32 constraints.

### Features

- **Device Registry**: Track connected agents by unique ID
- **Group Management**: Organize devices into logical groups
- **Command Targeting**: Send commands to individuals, groups, or all
- **Interactive CLI**: Tab completion and help system
- **Encrypted Protocol**: ChaCha20 + Protocol Buffers
- **Plugin System**: Extensible command architecture

### Usage

```bash
# Start server
python3 tools/c2/c3po.py --port 2626

# List connected devices
c3po> list

# Send command to device
c3po> send ce4f626b system_mem

# Send to all devices
c3po> send all system_uptime

# Create group
c3po> group add lab ce4f626b a91dd021

# Send to group
c3po> send group lab system_reboot
```

See [tools/c2/README.md](tools/c2/README.md) for detailed C2 documentation.

---

## Configuration

Configuration is done via ESP-IDF's `menuconfig` system.

### Key Settings

```
Espilon Configuration
├── Device ID                    # Unique identifier (CRC32)
├── Network Backend Selection
│   ├── WiFi                     # SSID, password, STA/AP modes
│   └── GPRS                     # APN, SIM800 config
├── C2 Server
│   ├── IP Address               # Server IP
│   └── Port                     # Server port (default: 2626)
├── Cryptography
│   ├── ChaCha20 Key             # 32-byte encryption key
│   └── Nonce                    # 12-byte nonce
└── Modules
    ├── Enable Network Module
    ├── Enable FakeAP Module
    └── Enable Recon Module
        ├── Camera Mode
        └── BLE Trilateration
```

### Security Configuration

**CRITICAL**: Change default crypto keys before deployment!

Default keys are for testing only:
- Default Key: `testde32chars0000000000000000000`
- Default Nonce: `noncenonceno`

Generate secure keys:
```bash
# Generate 32-byte key
openssl rand -hex 32

# Generate 12-byte nonce
openssl rand -hex 12
```

See [SECURITY.md](docs/SECURITY.md) for security best practices.

---

## Hardware Requirements

### Minimum Requirements

- **ESP32** (any variant)
- **Flash**: 4MB minimum
- **WiFi**: Integrated 802.11 b/g/n

### For Camera Module

- **ESP32-CAM** (AI-Thinker or compatible)
- **PSRAM**: Required for image buffering
- **Camera**: OV2640 or compatible

### For GPRS Mode

- **ESP32 DevKit** (any variant)
- **SIM800/SIM808** module
- **UART**: GPIO 26 (RX), 27 (TX)
- **Power Management**: GPIOs 4, 23, 5

See [HARDWARE.md](docs/HARDWARE.md) for detailed pinouts and wiring diagrams.

---

## Security

### Responsible Use

This tool is designed for:
- Authorized penetration testing
- Controlled security research
- Educational purposes
- CTF competitions
- IoT security assessments (with permission)

**NEVER** use for:
- Unauthorized network access
- Malicious attacks
- Privacy violations
- Illegal activities

### Security Considerations

**Current Implementation:**
- ChaCha20 stream cipher (256-bit key)
- Protocol Buffers serialization
- Implicit authentication via encryption

**Known Limitations:**
- Static nonce (should be unique per message)
- No authenticated encryption (no MAC/Poly1305)
- Hardcoded default credentials
- No forward secrecy
- No device enrollment/revocation

**Recommendations:**
- Use ChaCha20-Poly1305 AEAD
- Implement unique nonce per message
- Add device certificate system
- Use TLS/DTLS for transport security

See [SECURITY.md](docs/SECURITY.md) for complete security documentation.

---

## Documentation

- [Installation Guide](docs/INSTALL.md) - Detailed setup instructions
- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [Module API](docs/MODULES.md) - Complete module documentation
- [Protocol Specification](docs/PROTOCOL.md) - C2 communication protocol
- [Hardware Guide](docs/HARDWARE.md) - Pinouts and wiring diagrams
- [Security Best Practices](docs/SECURITY.md) - Security guidelines
- [Development Guide](docs/DEVELOPMENT.md) - Creating custom modules
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

---

## Roadmap

### Short-term

- [ ] Complete GPRS RX implementation
- [ ] BLE trilateration module completion
- [ ] SOCKS5 proxy support
- [ ] Enhanced multi-flasher tool
- [ ] Persistent C2 storage (groups, history)
- [ ] Request/response correlation tracking

### Long-term

#### Mesh IoT Network

- [ ] Bot-to-bot communication
- [ ] Distributed routing protocols
- [ ] OTA firmware updates
- [ ] Extended range via relay
- [ ] Collaborative multilateration
- [ ] Zero-trust mesh architecture

#### Custom PCB

- [ ] Portable design with battery management
- [ ] Integrated antennas (WiFi, GPRS, BLE)
- [ ] Embedded sensors (temperature, motion, etc.)
- [ ] File system storage (SD card)
- [ ] MPU/MCU architecture
- [ ] Blue team & Red team variants

#### Code Improvements

- [ ] Memory optimization
- [ ] Module standardization
- [ ] Enhanced C2 protocols
- [ ] Unit testing framework
- [ ] CI/CD pipeline
- [ ] Docker development environment

---

## Contributing

Contributions are welcome! This project is now open source to benefit the security research and IoT communities.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Guidelines

- Follow the existing code style
- Add tests for new features
- Update documentation
- Ensure security best practices
- Only submit authorized security research

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## Authors

- **@Eun0us** - Main developer, firmware architecture
- **@off-path** - C2 development lead
- **@itsoktocryyy** - Contributor
- **@wepfen** - Contributor

---

## License

[To be determined - Please add appropriate license]

**Recommended licenses for security tools:**
- **MIT License** - Permissive, allows commercial use
- **Apache 2.0** - Permissive with patent protection
- **GPL v3** - Copyleft, modifications must be open source

---

## Acknowledgments

- ESP-IDF team at Espressif
- Le Hack conference for initial presentation
- Security research community
- All contributors and testers

---

## Contact

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/epsilon/issues)
- Discussions: [Community discussions](https://github.com/yourusername/epsilon/discussions)

---

**Legal Disclaimer**: This tool is provided for educational and authorized testing purposes only. Users are solely responsible for ensuring their use complies with applicable laws and regulations. The authors assume no liability for misuse or damage caused by this software.
