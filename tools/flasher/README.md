# Espilon Multi-Device Flasher

Automated tool for building and flashing multiple ESP32 devices with custom configurations for the Espilon project.

## Features

- Build firmware with custom configurations per device
- Support for WiFi and GPRS modes
- Configurable modules (Network, Recon, FakeAP)
- Multi-device batch processing
- Individual device manual configuration
- Automatic hostname generation
- Build-only and flash-only modes

## Prerequisites

- Python 3.8+
- ESP-IDF v5.3.2 (properly configured with `export.sh`)
- esptool.py (usually included with ESP-IDF)
- ESP32 development boards connected via USB

## Installation

No installation required. The script is standalone.

```bash
cd tools/flasher
chmod +x flash.py
```

## Configuration File

### Structure

The `devices.json` file contains:
- **project**: Path to the `espilon_bot` directory
- **devices**: Array of device configurations

### Example: devices.json

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
      "wifi_ssid": "MyWiFi",
      "wifi_pass": "MyPassword123",
      "hostname": "pixel-8-pro",
      "module_network": true,
      "module_recon": false,
      "module_fakeap": false,
      "recon_camera": false,
      "recon_ble_trilat": false,
      "crypto_key": "testde32chars00000000000000000000",
      "crypto_nonce": "noncenonceno"
    },
    {
      "device_id": "a91dd021",
      "port": "/dev/ttyUSB1",
      "srv_ip": "203.0.113.10",
      "srv_port": 2626,
      "network_mode": "gprs",
      "gprs_apn": "sl2sfr",
      "hostname": "galaxy-s24-ultra",
      "module_network": true,
      "module_recon": false,
      "module_fakeap": false
    }
  ]
}
```

### Device Configuration Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | Yes | - | Unique device identifier (8 hex chars) |
| `port` | Yes | - | Serial port (e.g., `/dev/ttyUSB0`, `COM3`) |
| `srv_ip` | Yes | - | C2 server IP address |
| `srv_port` | No | 2626 | C2 server port |
| `network_mode` | No | "wifi" | Network mode: `"wifi"` or `"gprs"` |
| `wifi_ssid` | WiFi only | - | WiFi network SSID |
| `wifi_pass` | WiFi only | - | WiFi network password |
| `gprs_apn` | GPRS only | "sl2sfr" | GPRS APN |
| `hostname` | No | Random | Device hostname for network identification |
| `module_network` | No | true | Enable network commands module |
| `module_recon` | No | false | Enable reconnaissance module |
| `module_fakeap` | No | false | Enable fake AP module |
| `recon_camera` | No | false | Enable camera reconnaissance (ESP32-CAM) |
| `recon_ble_trilat` | No | false | Enable BLE trilateration |
| `crypto_key` | No | Test key | ChaCha20 encryption key (32 chars) |
| `crypto_nonce` | No | Test nonce | ChaCha20 nonce (12 chars) |

## Usage

### 1. Flash All Devices from Config

```bash
python3 flash.py --config devices.json
```

This will:
1. Read device configurations from `devices.json`
2. Build firmware for each device
3. Flash each device sequentially
4. Display summary report

### 2. Manual Single Device (WiFi)

```bash
python3 flash.py --manual \
  --project /home/user/epsilon/espilon_bot \
  --device-id abc12345 \
  --port /dev/ttyUSB0 \
  --srv-ip 192.168.1.100 \
  --wifi-ssid MyWiFi \
  --wifi-pass MyPassword123
```

### 3. Manual Single Device (GPRS)

```bash
python3 flash.py --manual \
  --project /home/user/epsilon/espilon_bot \
  --device-id def67890 \
  --port /dev/ttyUSB1 \
  --srv-ip 203.0.113.10 \
  --network-mode gprs \
  --gprs-apn sl2sfr
```

### 4. Build Only (No Flash)

Useful for generating firmware files without flashing:

```bash
python3 flash.py --config devices.json --build-only
```

Firmware files are saved to: `espilon_bot/firmware/<device_id>.bin`

### 5. Flash Only (Skip Build)

Flash pre-built firmware:

```bash
python3 flash.py --config devices.json --flash-only
```

Requires firmware files in `espilon_bot/firmware/` directory.

### 6. Enable Modules

```bash
python3 flash.py --manual \
  --project /home/user/epsilon/espilon_bot \
  --device-id xyz98765 \
  --port /dev/ttyUSB0 \
  --srv-ip 192.168.1.100 \
  --wifi-ssid MyWiFi \
  --wifi-pass MyPassword123 \
  --enable-recon \
  --enable-fakeap \
  --enable-ble-trilat
```

### 7. Custom Encryption Keys

```bash
python3 flash.py --manual \
  --project /home/user/epsilon/espilon_bot \
  --device-id secure01 \
  --port /dev/ttyUSB0 \
  --srv-ip 192.168.1.100 \
  --wifi-ssid MyWiFi \
  --wifi-pass MyPassword123 \
  --crypto-key "your32charencryptionkeyhere!!" \
  --crypto-nonce "yournonce12b"
```

## Advanced Features

### Hostname Generation

If `hostname` is not specified, the script generates a realistic device name:
- iPhone models (iPhone-15-pro-max, etc.)
- Android devices (galaxy-s24-ultra, pixel-8-pro, etc.)
- Windows PCs (DESKTOP-XXXXXXX)

This helps devices blend in on networks during authorized testing.

### Configuration Backup

Before building, the script automatically backs up the existing `sdkconfig.defaults` to `sdkconfig.defaults.bak`.

### Firmware Storage

Built firmware is saved in:
```
espilon_bot/firmware/<device_id>.bin
```

This allows:
- Reuse without rebuilding (--flash-only)
- Firmware version archival
- Quick reflashing of multiple devices

## Workflow Examples

### Scenario 1: Initial Setup (3 devices)

1. Edit `devices.json`:
   ```json
   {
     "project": "/home/user/epsilon/espilon_bot",
     "devices": [
       {"device_id": "dev00001", "port": "/dev/ttyUSB0", ...},
       {"device_id": "dev00002", "port": "/dev/ttyUSB1", ...},
       {"device_id": "dev00003", "port": "/dev/ttyUSB2", ...}
     ]
   }
   ```

2. Flash all:
   ```bash
   python3 flash.py --config devices.json
   ```

3. Devices are ready for deployment

### Scenario 2: Update Single Device

1. Modify configuration in `devices.json`
2. Flash only that device:
   ```bash
   # Remove other devices from JSON or use manual mode
   python3 flash.py --manual --device-id dev00002 --port /dev/ttyUSB1 ...
   ```

### Scenario 3: Quick Reflash

```bash
# Build once
python3 flash.py --config devices.json --build-only

# Flash multiple times (testing, replacement devices)
python3 flash.py --config devices.json --flash-only
```

### Scenario 4: WiFi + GPRS Mixed Fleet

```json
{
  "project": "/home/user/epsilon/espilon_bot",
  "devices": [
    {
      "device_id": "wifi001",
      "network_mode": "wifi",
      "wifi_ssid": "HomeNetwork",
      "wifi_pass": "password123",
      ...
    },
    {
      "device_id": "gprs001",
      "network_mode": "gprs",
      "gprs_apn": "sl2sfr",
      ...
    }
  ]
}
```

## Troubleshooting

### Error: "Port not found"

```
❌ Flash failed: Serial port /dev/ttyUSB0 not found
```

**Solution**: Check device connection and port:
```bash
ls /dev/ttyUSB* /dev/ttyACM*
```

Add user to dialout group:
```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

### Error: "Build failed"

```
❌ Build failed for device_id
```

**Solutions**:
1. Verify ESP-IDF is sourced:
   ```bash
   . $HOME/esp-idf/export.sh
   ```

2. Check project path in `devices.json`

3. Manually test build:
   ```bash
   cd espilon_bot
   idf.py build
   ```

### Error: "Permission denied"

```
❌ Permission denied: /dev/ttyUSB0
```

**Solution**:
```bash
sudo chmod 666 /dev/ttyUSB0
# Or add user to dialout group (permanent)
sudo usermod -a -G dialout $USER
```

### Error: "Binary not found"

```
❌ Binary not found: epsilon_bot.bin
```

**Solution**: Check build output for compilation errors. The binary name should match the project configuration.

### WiFi Mode Missing Credentials

```
ValueError: WiFi mode requires wifi_ssid and wifi_pass
```

**Solution**: Ensure `wifi_ssid` and `wifi_pass` are set for devices with `network_mode: "wifi"`.

## Output Example

```
============================================================
# Device 1/3: ce4f626b
############################################################

============================================================
🔧 Building firmware for: ce4f626b (WIFI) on /dev/ttyUSB0
============================================================
✅ Generated sdkconfig.defaults for ce4f626b
🗑️  Removed old sdkconfig
⚙️  Running idf.py build...
✅ Firmware saved: espilon_bot/firmware/ce4f626b.bin

============================================================
🚀 Flashing: ce4f626b (WIFI) on /dev/ttyUSB0
============================================================
📁 Bootloader: espilon_bot/build/bootloader/bootloader.bin
📁 Partitions: espilon_bot/build/partition_table/partition-table.bin
📁 Application: espilon_bot/firmware/ce4f626b.bin
🔌 Port: /dev/ttyUSB0
✅ Successfully flashed ce4f626b

============================================================
📊 SUMMARY
============================================================
✅ Success: 3/3
❌ Failed:  0/3
============================================================
```

## Security Considerations

### Encryption Keys

**WARNING**: The default crypto keys are for TESTING ONLY:
- `crypto_key`: "testde32chars00000000000000000000"
- `crypto_nonce`: "noncenonceno"

For production use:
1. Generate secure keys:
   ```bash
   # 32-byte key
   openssl rand -hex 32

   # 12-byte nonce
   openssl rand -hex 12
   ```

2. Update in `devices.json` or use `--crypto-key` and `--crypto-nonce`

3. **Never commit real keys to version control**

### Device IDs

Generate random device IDs:
```bash
openssl rand -hex 4  # Generates 8-character hex ID
```

## Files Generated

During operation, the script creates:

```
espilon_bot/
├── sdkconfig                   # Generated during build (auto-deleted)
├── sdkconfig.defaults          # Overwritten per device
├── sdkconfig.defaults.bak      # Backup of previous config
├── build/                      # ESP-IDF build artifacts
│   ├── bootloader/
│   ├── partition_table/
│   └── epsilon_bot.bin
└── firmware/                   # Saved firmware binaries
    ├── ce4f626b.bin
    ├── a91dd021.bin
    └── f34592e0.bin
```

## Tips

1. **Batch Processing**: Connect multiple ESP32s to different USB ports, configure all in `devices.json`, and flash them all at once.

2. **Parallel Builds**: For faster processing with many devices, consider building in parallel (future enhancement).

3. **Configuration Templates**: Keep multiple `devices.json` files for different deployment scenarios:
   - `devices-wifi.json`
   - `devices-gprs.json`
   - `devices-production.json`
   - `devices-testing.json`

4. **Firmware Archive**: Save firmware binaries with version tags:
   ```bash
   mkdir -p firmware-archive/v1.0
   cp espilon_bot/firmware/*.bin firmware-archive/v1.0/
   ```

5. **Serial Port Mapping**: Create udev rules for consistent port naming (Linux):
   ```bash
   # /etc/udev/rules.d/99-esp32.rules
   SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="esp32-dev1"
   SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="esp32-dev2"
   ```

## Help

```bash
python3 flash.py --help
```

Displays full usage information with examples.

## Related Documentation

- [Installation Guide](../../docs/INSTALL.md) - Full Espilon setup
- [Hardware Guide](../../docs/HARDWARE.md) - Supported boards and wiring
- [Module API](../../docs/MODULES.md) - Available commands and modules
- [Security](../../docs/SECURITY.md) - Security best practices

## License

Part of the Espilon project. See [LICENSE](../../LICENSE) for details.
